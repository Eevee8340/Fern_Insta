import os
import time
from typing import Any
import consts
from services.event_bus import event_bus

LOG_FILE = os.path.join(consts.USER_DATA_DIR, "chat.log")

class LoggerPlugin:
    def __init__(self, context) -> None:
        self.ctx = context
        # Ensure directory exists
        if not os.path.exists(consts.USER_DATA_DIR):
            os.makedirs(consts.USER_DATA_DIR)

    async def on_chat_message(self, sender: str, text: str, bubble: Any, **kwargs) -> bool:
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] {sender}: {text}\n"
            
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"   [!] Chat Logger Error: {e}")
            
        return True

def register(ctx):
    p = LoggerPlugin(ctx)
    event_bus.subscribe(consts.EVENT_CHAT_MESSAGE, p.on_chat_message, priority=1000) # High priority to log first
