import asyncio
import time
import random
import datetime
import json
import os
import re
from typing import Any
from plugins.llm_utils import PluginLLM
from plugins.base import BasePlugin
import consts

class DreamerPlugin(BasePlugin):
    name = "Dreamer"
    priority = 20
    
    default_config = {
        "wake_time": "09:00",
        "interval": 1800,
        "temperature": 0.7,
        "max_tokens": 1000,
        "memory_seeds": 3,
        "night_buffer_size": 20,
        "trigger_commands": [
            "/dream",
            "/force_dream"
        ]
    }

    def __init__(self, context) -> None:
        super().__init__(context)
        self.last_dream_date = None
        
        self.wake_time = self.config.get("wake_time", "09:00")
        self.llm = PluginLLM(context_name="Dreamer")
        
        state = self.load_state()
        self.last_dream_date = state.get("last_dream_date")

    async def on_tick(self, bot) -> None:
        if not self.enabled: return
        
        # Check Time
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M")
        current_date = now.strftime("%Y-%m-%d")
        
        # Trigger at specific time, once per day
        if current_time == self.wake_time and self.last_dream_date != current_date:
            self.last_dream_date = current_date
            self.save_state({"last_dream_date": self.last_dream_date})
            await self.broadcast_dream(bot)

    async def broadcast_dream(self, bot) -> None:
        print("\033[95m   [Dreamer] Constructing Morning Dream...\033[0m")
        self.log("Constructing Morning Dream...")
        
        # 1. Gather Ingredients (Memories & Lore)
        ingredients = []
        cortex = self.ctx.get_cortex()
        
        if cortex:
            # Get random episodes (Use Logs Only)
            try:
                data = await cortex.ask_data(consts.IPC_GET_RANDOM_LOGS, n=3)
                if data and isinstance(data, list):
                    for m in data:
                        # Clean artifacts if it's a logbook
                        clean_m = re.sub(r"[\**.*?\**]", "", m) # Remove headers like [TOPICS]
                        clean_m = re.sub(r"\**.*?\**", "", clean_m) # Remove bold markers
                        clean_m = clean_m.replace("LOGBOOK FORMAT", "").strip()
                        if len(clean_m) > 20:
                            ingredients.extend([f"Memory Fragment: {clean_m[:500]}..."])
            except Exception as e:
                print(f"   [Dreamer] IPC Error: {e}")

        # Get random lore
        lore_path = os.path.join(os.path.dirname(consts.CONFIG_PATH), "lore.json")
        if os.path.exists(lore_path):
            try:
                import json
                with open(lore_path, "r", encoding="utf-8") as f:
                    lore = json.load(f)
                    if lore:
                        keys = random.sample(list(lore.keys()), min(2, len(lore)))
                        ingredients.extend([f"Lore Item: {k} ({lore[k]['definition']})" for k in keys])
            except: pass

        if not ingredients:
            ingredients = ["The void is empty", "Fern is a raccoon"]

        context_str = "\n".join(ingredients)
        
        if len(context_str) > 6000:
            context_str = context_str[:6000] + "..."

        # 2. Generate Dream
        prompt = f"""
        You are Fern. You just woke up and are telling your friends about a weird dream you had.
        The dream was a surreal remix of these actual memories and concepts:
        
        {context_str}
        
        INSTRUCTIONS:
        - Write a single chaotic, surreal paragraph describing the dream.
        - Mix the memories together illogically (e.g. "I saw Ishan fighting a dragon made of Gatorade").
        - Be funny, confused, and slightly unhinged.
        - Start with something like "ugh had the weirdest dream..." or "ok listen..."
        - Lowercase, minimal punctuation.
        """

        try:
            dream_text = await self.llm.generate(prompt)
            if not dream_text: return
            
            print(f"\033[96m   [Dreamer] Broadcasting: {dream_text[:50]}...\033[0m")
            self.log(f"--- MORNING DREAM ---\n{dream_text}\n----------------------")
            
            # 3. Send to Chat
            await self.ctx.send_message(dream_text)
            
            # Log it
            if cortex:
                cortex.update_history("assistant", f"[Morning Dream]: {dream_text}")
                
        except Exception as e:
            print(f"   [!] Dream Gen Error: {e}")

    async def on_local_command(self, command: str) -> bool:
        if not self.enabled: return True
        
        if command == "/force_dream":
            print("   -> Manually forcing Morning Dream...")
            bot = self.ctx._bot
            asyncio.create_task(self.broadcast_dream(bot))
            return False
            
        return True

def register(ctx):
    p = DreamerPlugin(ctx)
    ctx._bot.dreamer = p
    return p