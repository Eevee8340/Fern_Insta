import os
import json
import asyncio
import re
from typing import Any, Optional
from plugins.llm_utils import PluginLLM
from plugins.base import BasePlugin
import config
import consts

class MimicPlugin(BasePlugin):
    name = "Mimic"
    priority = 90
    
    default_config = {
        "temperature": 0.1,
        "max_tokens": 2000,
        "sample_lines": 200,
        "ignored_senders": [
            "system",
            "admin"
        ],
        "trigger_commands": [
            "/clone",
            "/unclone"
        ]
    }

    def __init__(self, context) -> None:
        super().__init__(context)
        
        self.clones_file = os.path.join(self.data_dir, "clones.json")
        self.clones = {}
        self.load_clones()
        
        # Batch I/O
        self.log_buffer = {} # handle -> [lines]
        self.buffer_limit = 5
        
        self.sample_lines = self.config.get("sample_lines", 200)
        self.triggers = self.config.get("trigger_commands", ["/clone", "/unclone"])

        self.original_profile = config.PROFILE
        self.active_clone = None

        self.llm = PluginLLM(context_name="Mimic")

    def load_clones(self) -> None:
        if os.path.exists(self.clones_file):
            try:
                with open(self.clones_file, "r") as f:
                    self.clones = json.load(f)
            except: self.clones = {}

    def save_clones(self) -> None:
        try:
            with open(self.clones_file, "w") as f:
                json.dump(self.clones, f, indent=2)
        except Exception as e:
            self.log(f"Failed to save clones: {e}")

    def flush_buffer(self, safe_handle: str):
        if safe_handle not in self.log_buffer or not self.log_buffer[safe_handle]:
            return
            
        # Keep logs in user_data/ for now as they are shared, or move to a central logs dir
        # For now, let's keep them in USER_DATA_DIR as they might be used by other parts of the system
        file_path = os.path.join(consts.USER_DATA_DIR, f"{safe_handle}.txt")
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.writelines(self.log_buffer[safe_handle])
            self.log_buffer[safe_handle] = []
        except Exception as e:
            print(f"   [!] Mimic Log Error: {e}")

    async def on_chat_message(self, sender: str, text: str, bubble: Any, **kwargs) -> bool:
        if not self.enabled: return True
        
        trace_id = kwargs.get("trace_id")
        
        handle = sender
        match = re.search(r"\(@(.*?)\)", sender)
        if match:
            handle = "@" + match.group(1)
        else:
            handle = re.split(r"(\s+replied\s+to|\s+\(replied\s+to)", sender, flags=re.IGNORECASE)[0].strip()

        safe_handle = "".join([c for c in handle if c.isalnum() or c in "._-"])
        is_placeholder = text.startswith("[") and text.endswith("]")
        
        if safe_handle and not safe_handle.startswith("You") and not is_placeholder:
            if safe_handle not in self.log_buffer:
                self.log_buffer[safe_handle] = []
            
            self.log_buffer[safe_handle].append(f"{text}\n")
            
            if len(self.log_buffer[safe_handle]) >= self.buffer_limit:
                self.flush_buffer(safe_handle)

        text_lower = text.lower().strip()
        if text_lower.startswith("/fern clone"):
            target = text.split("clone")[-1].strip()
            if target.lower() == "me":
                target = safe_handle
            if target:
                await self.activate_clone(target)
            return False 

        if text_lower.startswith("/fern unclone"):
            await self.restore_original()
            return False

        if self.active_clone and re.search(rf"\b{re.escape(self.active_clone)}\b", text):
            if sender == "You" or sender.startswith("You"):
                return True
            if self.active_clone in sender:
                return True

            if not self.ctx.is_busy and not self.ctx.is_sleeping:
                print(f"\u001b[93m   -> Clone {self.active_clone} was mentioned! Intercepting...\u001b[0m")
                await self.ctx.reply(sender, text, bubble, trace_id=trace_id)
                return False 

        return True

    async def on_local_command(self, command: str, **kwargs) -> bool:
        if not self.enabled: return True

        if command.startswith("/clone "):
            target = command.split("/clone ")[1].strip()
            await self.activate_clone(target)
            return False
        
        if command == "/unclone":
            await self.restore_original()
            return False
        
        return True

    async def activate_clone(self, target_handle: str) -> None:
        if not target_handle.startswith("@") and not target_handle.startswith("You"):
             potential_match = f"@{target_handle}"
             # Check both old and new possible locations
             if potential_match in self.clones or os.path.exists(os.path.join(consts.USER_DATA_DIR, f"{potential_match}.txt")):
                 target_handle = potential_match

        if target_handle in self.clones:
            prompt = self.clones[target_handle]
            self.ctx.set_profile(prompt)
            self.active_clone = target_handle
            print(f"\033[92m   [+] Activated Clone: {target_handle}\033[0m")
            return

        print(f"\033[93m   [*] Generating clone for {target_handle}...\033[0m")
        self.log(f"Generating clone for {target_handle}...")
        
        safe_handle = "".join([c for c in target_handle if c.isalnum() or c in "._-"])
        
        # Ensure pending logs are flushed before reading
        self.flush_buffer(safe_handle)
        
        log_path = os.path.join(consts.USER_DATA_DIR, f"{safe_handle}.txt")
        
        if not os.path.exists(log_path):
            print(f"\033[91m   [!] No data found for {target_handle}\033[0m")
            return
            
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                sample = "".join(lines[-self.sample_lines:])
                
            # Truncate to safe limit (~3-4k tokens)
            if len(sample) > 12000:
                sample = sample[-12000:]
                sample = "..." + sample[3:]
        except Exception:
            return
            
        prompt_request = f"""
        You are given chat messages from a person.
        Your task is to write a System Prompt that makes an AI behave exactly like that person.
        Study how they talk, not what they say.

        Capture:
        slang, spelling, grammar, casing
        emojis, punctuation, message length
        tone (chill, rude, sarcastic, dry, chaotic, soft, etc.)
        how they react when confused, annoyed, joking, or challenged
        what they don't say (things they avoid or ignore)

        Rules:
        The AI must sound like a real human, not an assistant.
        No explanations, no helpful framing, no safety talk.
        Do not improve their language or behavior.
        If they are inconsistent, keep it inconsistent.
        If unsure, respond the way they would (guess, joke, ignore, deflect).

        Output rules:
        Output only the system prompt.
        Start with: You are {target_handle}.
        Write instructions in second person.
        No markdown, no commentary.
        Chat samples:
        {sample}
        """
        
        try:
            clone_prompt = await self.llm.generate(prompt_request, system_instruction="You are an expert at analyzing text style and creating personas.")
            
            if not clone_prompt:
                print("   [!] Generation failed (Empty response)")
                return
            
            clone_prompt += "\n\nIMPORTANT: Do NOT prefix your messages with your name (e.g., 'User:'). Just output the raw message text directly."
            
            self.clones[target_handle] = clone_prompt
            self.save_clones()
            
            self.ctx.set_profile(clone_prompt)
            self.active_clone = target_handle
            print(f"\033[92m   [+] Generated & Activated Clone: {target_handle}\033[0m")
            
        except Exception as e:
            print(f"   [!] Generation Failed: {e}")

    async def restore_original(self) -> None:
        self.ctx.set_profile(self.original_profile)
        self.active_clone = None
        print("\033[92m   [+] Restored Original Persona\033[0m")

def register(ctx):
    p = MimicPlugin(ctx)
    # The loader will automatically subscribe standard methods if they exist
    # but we can still set special references
    ctx._bot.mimic_plugin = p
    return p