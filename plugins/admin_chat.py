import re
import config
import consts
from services.event_bus import event_bus

PRIORITY = 100

class AdminChatPlugin:
    def __init__(self, ctx):
        self.ctx = ctx

    async def handle_chat_command(self, sender, text, bubble, **kwargs):
        # 1. Secure Handle Extraction
        handle_match = re.search(r"\(@(.*?)\)", sender)
        if not handle_match:
            # Fallback for simpler formats or direct handles
            clean_sender = sender.strip()
            if clean_sender.startswith("@"):
                user_handle = clean_sender
            else:
                return True # Can't verify identity
        else:
            user_handle = f"@{handle_match.group(1)}"

        # 2. Strict Admin Verification
        if user_handle.lower() != config.ADMIN_USERNAME.lower():
            return True 

        # 3. Command Parsing
        text_lower = text.lower().strip()
        bot = self.ctx._bot
        
        if not text_lower.startswith("/fern "):
            return True

        cmd_parts = text.strip().split(" ", 2) # ["/fern", "command", "args..."]
        if len(cmd_parts) < 2:
            return True
            
        action = cmd_parts[1].lower()
        args = cmd_parts[2] if len(cmd_parts) > 2 else ""

        if action == "sleep":
            print(f"   [Admin] Triggering Sleep...")
            bot.command_queue.put_nowait("/sleep")
            return False
            
        elif action in ["wake", "wakey"]:
            print(f"   [Admin] Triggering Wake...")
            bot.command_queue.put_nowait("/wake")
            return False
            
        elif action == "clearmem":
            bot.command_queue.put_nowait("/clearmem")
            return False

        elif action == "ping":
            bot.command_queue.put_nowait("/ping")
            return False
            
        elif action == "say":
            if args:
                bot.command_queue.put_nowait(f"/say {args}")
            return False
                
        return True # Continue

def register(ctx):

    p = AdminChatPlugin(ctx)

    event_bus.subscribe(consts.EVENT_CHAT_MESSAGE, p.handle_chat_command, priority=PRIORITY)
