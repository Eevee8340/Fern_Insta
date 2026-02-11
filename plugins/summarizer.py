import os
import time
import asyncio
import json
from typing import Any, List
from plugins.llm_utils import PluginLLM
from plugins.base import BasePlugin
import consts
from services.event_bus import event_bus
from services.tracing import tracer

class SummarizerPlugin(BasePlugin):
    name = "Archivist"
    priority = 50
    
    default_config = {
        "batch_size": 50,
        "temperature": 0.2,
        "max_tokens": 2000,
        "trigger_commands": [
            "/recap",
            "/force_summary",
            "/clearmem"
        ]
    }

    def __init__(self, context) -> None:
        super().__init__(context)
        self.archive_buffer: List[str] = []  
        self.running_summary: str = "" 
        self.iteration_count: int = 0  
        self.is_summarizing = False
        
        self.batch_size = self.config.get("batch_size", 50)
        self.triggers = self.config.get("trigger_commands", ["/recap", "/force_summary", "/clearmem"])
        
        self.llm = PluginLLM(context_name="Archivist")
        self.load_internal_state()

    def load_internal_state(self):
        data = self.load_state()
        if data:
            self.archive_buffer = data.get("buffer", [])
            self.running_summary = data.get("running_summary", "")
            self.iteration_count = data.get("iteration_count", 0)

    def save_internal_state(self):
        self.save_state({
            "buffer": self.archive_buffer,
            "running_summary": self.running_summary,
            "iteration_count": self.iteration_count
        })

    async def on_chat_message(self, sender: str, text: str, bubble: Any, **kwargs) -> bool:
        if not self.enabled: return True

        msg_entry = f"{sender}: {text}"
        self.archive_buffer.append(msg_entry)
        self.save_internal_state()
        
        if len(self.archive_buffer) >= self.batch_size:
            trace_id = kwargs.get("trace_id")
            if trace_id:
                tracer.log_event(trace_id, "summarizer_batch_triggered")
            asyncio.create_task(self.process_batch())
            
        return True 

    async def on_local_command(self, command: str) -> bool:
        if not self.enabled: return True
        
        if command in self.triggers:
            if command == "/clearmem":
                self.archive_buffer = []
                self.running_summary = ""
                self.iteration_count = 0
                self.save_internal_state()
                print("   -> Archivist Buffer & Running Summary Wiped.")
                cortex = self.ctx.get_cortex()
                if cortex:
                    cortex.send_command("clearmem")
                return False
            else:
                print("   -> Manual Summary Triggered")
                if self.archive_buffer:
                    asyncio.create_task(self.process_batch(force=True))
                else:
                    print("   -> Buffer is empty, nothing to summarize.")
                return False

        return True

    async def process_batch(self, force: bool = False) -> None:
        if self.is_summarizing: return
        self.is_summarizing = True
        
        current_batch = list(self.archive_buffer)
        if not force:
             current_batch = current_batch[:self.batch_size]
        
        if not current_batch:
            self.is_summarizing = False
            return

        print(f"\033[93m   -> 🧠 Updating Rolling Context (Iteration {self.iteration_count + 1}/5)...\033[0m")
        self.log(f"Updating Rolling Context (Iteration {self.iteration_count + 1}/5)...")

        try:
            chat_text = "\n".join(current_batch)
            if len(chat_text) > 12000:
                chat_text = chat_text[:12000] + "\n...(truncated)..."

            prompt = f"""
            You are an Intelligence Officer updating a SITUATION REPORT based on recent conversation.
            
            PREVIOUS REPORT:
            {self.running_summary if self.running_summary else "No previous report."}

            NEW MESSAGES:
            {chat_text}
            
            INSTRUCTIONS:
            Integrate the NEW MESSAGES into a single, cohesive report. 
            Update the following sections:

            [TOPICS]: Combined list of all main topics discussed so far in this session.
            [USER_STATE]: Describe the current mood, activity, or status of users based on the latest interaction.
            [NEW_FACTS]: 
            - Extract and append concrete, permanent facts about users.
            - If a new message contradicts the previous report, prioritize the NEW message.
            [KEY_EVENTS]: 
            - List significant milestones or decisions made during the entire conversation block.

            Maintain a professional, objective tone. Do NOT use narrative prose.
            """

            new_summary = await self.llm.generate(
                prompt, 
                system_instruction="You are a precise intelligence archivist. You maintain a running situation report of chat logs."
            )
            
            if new_summary and len(new_summary) > 10:
                self.running_summary = new_summary
                self.iteration_count += 1
                
                cortex = self.ctx.get_cortex()
                if cortex:
                    # END OF CYCLE: EXTRACT FACTS & COMMIT TO LONG TERM MEMORY
                    if self.iteration_count >= 5:
                        print(f"\033[96m   -> 🧠 Cycle Complete. Extracting Facts & Archiving Narrative Log...\033[0m")
                        self.log("Cycle Complete. Extracting Facts & Archiving Narrative Log...")
                        
                        # Get involved users for tagging
                        involved_users = []
                        if os.path.exists("aliases.json"):
                            try:
                                with open("aliases.json", "r") as f:
                                    alias_map = json.load(f)
                                    summary_lower = self.running_summary.lower()
                                    for name, handle in alias_map.items():
                                        if name.lower() in summary_lower:
                                            involved_users.append(handle.replace("@", ""))
                            except: pass

                        # 1. EXTRACT FACTS (FROM FINAL SUMMARY)
                        cortex.analyze_batch(self.running_summary, users=involved_users)

                        # 2. ARCHIVE NARRATIVE LOG
                        try:
                            log_entry = {
                                "timestamp": time.time(),
                                "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "summary": self.running_summary,
                                "raw_count": self.batch_size * 5
                            }
                            # Keep writing to central history logs, but also log to plugin log
                            with open(consts.HISTORY_LOGS_PATH, "a", encoding="utf-8") as f:
                                f.write(json.dumps(log_entry) + "\n")
                            
                            cortex.add_memory(self.running_summary, source="log_entry", user="system")
                            
                            # 3. Emit Event for Profiler and Lore
                            if involved_users:
                                involved_users = list(set(involved_users))
                                await event_bus.emit(consts.EVENT_NARRATIVE_LOGGED, involved_users)

                        except Exception as le:
                            print(f"   [!] History Log Error: {le}")
                        
                        # Reset for next cycle
                        self.running_summary = ""
                        self.iteration_count = 0
                
                self.save_internal_state()
            else:
                print("   -> Rolling Summary Update Failed (No output).")

            n_removed = len(current_batch)
            self.archive_buffer = self.archive_buffer[n_removed:]
            self.save_internal_state()

        except Exception as e:
            print(f"\033[91m   -> Archivist Error: {e}\033[0m")
            self.log(f"Error: {e}")
        finally:
            self.is_summarizing = False

def register(ctx):
    return SummarizerPlugin(ctx)


