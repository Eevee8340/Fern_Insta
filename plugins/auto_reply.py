import asyncio
import config
import consts
from services.event_bus import event_bus

PRIORITY = 10

class AutoReplyPlugin:
    def __init__(self, ctx):
        self.ctx = ctx

    async def handle_auto_reply(self, sender, text, bubble, **kwargs):
        bot = self.ctx._bot
        cortex = self.ctx.get_cortex()
        trace_id = kwargs.get("trace_id")
        
        # Extract Metadata
        parent_context = ""
        reply_log = ""
        if isinstance(bubble, dict):
            parent_context = bubble.get("parent_context", "")
            reply_log = bubble.get("reply_log", "")
        
        # 1. Check if sleeping
        if bot.is_sleeping:
            return False 
            
        # 2. Check if busy (prevent double reply)
        if bot.is_busy:
            return False

        if not cortex:
            return True

        # 3. Analyze Engagement (IPC)
        should_reply, reason = await cortex.ask_engagement(sender, text, trace_id=trace_id)

        if should_reply:
            if reply_log:
                print(reply_log)
            print(f"\033[95m   -> Fern decided to reply! ({reason})\033[0m")
            bot.is_busy = True
            asyncio.create_task(bot.execute_reply(sender, text, bubble, parent_context=parent_context, trace_id=trace_id))
            return False 
        else:
            print(f"   -> Ignored ({reason})")
            
            is_self = sender.startswith("You") or \
                      config.BOT_HANDLE.lower() in sender.lower() or \
                      config.BOT_NAME.lower() in sender.lower()

            if not is_self:
                cortex.update_history("user", f"{sender}: {text}")
            
            return False

def register(ctx):

    p = AutoReplyPlugin(ctx)

    event_bus.subscribe(consts.EVENT_CHAT_MESSAGE, p.handle_auto_reply, priority=PRIORITY)