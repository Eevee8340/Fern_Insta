from typing import Any
import consts
from services.event_bus import event_bus

PRIORITY = 90

class CoreCommandsPlugin:
    def __init__(self, ctx):
        self.ctx = ctx

    async def handle_local_command(self, command: str) -> bool:
        cortex = self.ctx.get_cortex()
        bot = self.ctx._bot
        
        if command == "/sleep":
            if not bot.is_sleeping:
                print(f"\033[95m   -> Local Command: SLEEP\033[0m")
                await self.ctx.send_message("Going to sleep... zzz")
                
                if cortex:
                    cortex.send_command("sleep")
                bot.is_sleeping = True
            else:
                print(f"\033[93m   -> Already sleeping.\033[0m")
            return False

        elif command == "/wake":
            if bot.is_sleeping:
                print(f"\033[95m   -> Local Command: WAKE\033[0m")
                await self.ctx.send_message("Waking up...")
                
                if cortex:
                    cortex.send_command("wake")
                
                bot.is_sleeping = False
                await self.ctx.send_message("I'm back.")
            else:
                print(f"\033[93m   -> Already awake.\033[0m")
            return False

        elif command == "/clearmem":
            print(f"\033[95m   -> Local Command: CLEAR MEMORY\033[0m")
            if cortex:
                cortex.send_command("clearmem")
            await self.ctx.send_message("Memory wiped.")
            return False

        elif command == "/ping":
            print(f"\033[95m   -> Local Command: PONG!\033[0m")
            return False

        elif command.startswith("/say "):
            text = command[5:]
            print(f"\033[95m   -> Local Command: SAY '{text}'\033[0m")
            await self.ctx.send_message(text)
            return False
        
        return True

def register(ctx):
    p = CoreCommandsPlugin(ctx)
    event_bus.subscribe(consts.EVENT_LOCAL_COMMAND, p.handle_local_command)