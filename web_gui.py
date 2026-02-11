import os
import sys
import subprocess

# --- AUTO-VENV RELAUNCHER ---
# Check if running inside the virtual environment
def ensure_venv():
    # Standard way to check venv in Python 3.3+
    in_venv = sys.prefix != sys.base_prefix
    
    if not in_venv:
        # Determine paths
        base_dir = os.path.dirname(os.path.abspath(__file__))
        venv_dir = os.path.join(base_dir, ".venv")
        
        # Windows specific path for venv python
        if sys.platform == "win32":
            venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
        else:
            venv_python = os.path.join(venv_dir, "bin", "python")
            
        if os.path.exists(venv_python):
            # Re-launch the script with the venv python
            # We use subprocess.call to replace the current process effectively from the user's perspective
            print(f"Switching to virtual environment: {venv_python}")
            try:
                subprocess.call([venv_python] + sys.argv)
                sys.exit(0)
            except KeyboardInterrupt:
                sys.exit(0)
            except Exception as e:
                print(f"Failed to relaunch in venv: {e}")
                sys.exit(1)
        else:
            print(f"Warning: .venv not found at {venv_python}. Attempting to run with current interpreter.")

ensure_venv()

import asyncio
import uvicorn
import socket
import re
from collections import deque

# Disable Fortran Control-C handler for Windows stability
os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'

# Add root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from insta import AsyncFernBot
from web.backend import api

# Global reference for the interceptor to access
bot_ref = None

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

# --- LOG INTERCEPTOR ---
class StreamInterceptor:
    def __init__(self, original):
        self.original = original
        self.loop = None
        self.ansi_escape = re.compile(r'\x1b\[[0-9;]*m')

    def write(self, message):
        # Always write to the actual console first
        self.original.write(message)
        
        if message.strip() and self.loop and self.loop.is_running():
            try:
                clean_text = self.ansi_escape.sub('', message).strip()
                if clean_text:
                    # 1. Broadcast to WebSocket
                    try:
                        asyncio.run_coroutine_threadsafe(
                            api.manager.broadcast({"type": "log", "text": clean_text}),
                            self.loop
                        )
                    except (RuntimeError, asyncio.CancelledError):
                        pass # Loop is likely closing

                    # 2. Append to History (thread-safe via deque)
                    if bot_ref and hasattr(bot_ref, 'log_history'):
                        bot_ref.log_history.append(clean_text)
            except Exception:
                pass

    def flush(self):
        self.original.flush()
        
    def set_loop(self, loop):
        self.loop = loop

async def main():
    global bot_ref
    
    # 0. Setup Log Interception
    loop = asyncio.get_running_loop()
    interceptor = StreamInterceptor(sys.stdout)
    sys.stdout = interceptor
    interceptor.set_loop(loop)
    
    # 1. Initialize Bot & History
    bot = AsyncFernBot()
    # Using deque(maxlen=200) automatically handles the size limit for us
    bot.log_history = deque(maxlen=200)
    bot_ref = bot
    
    # 2. Inject Bot into API
    api.bot_instance = bot
    
    # 3. Create Server Config
    # Minimal config to prevent Uvicorn default loggers from interfering
    log_config = {
        "version": 1, 
        "disable_existing_loggers": False
    }

    config = uvicorn.Config(
        api.app, 
        host="0.0.0.0", 
        port=8080, 
        log_config=log_config,
        log_level="info", 
        access_log=False
    )
    server = uvicorn.Server(config)

    # UI Feedback
    local_ip = get_local_ip()
    print("\n" + "="*50)
    print(f"FERN WEB INTERFACE ACTIVE")
    print(f"Local Access:  http://localhost:8080")
    print(f"Mobile Access: http://{local_ip}:8080")
    print("="*50 + "\n")
    
    # 4. Run concurrent tasks
    shutdown_event = asyncio.Event()

    def signal_handler():
        print("\n[!] Ctrl+C received. Initiating shutdown...")
        shutdown_event.set()
        if bot_ref:
            bot_ref.keep_running = False

    loop = asyncio.get_running_loop()
    # Add signal handlers if not on Windows (where we disabled the default handler) or handle via try/except block in main
    if sys.platform != 'win32':
        loop.add_signal_handler(signal.SIGINT, signal_handler)
        loop.add_signal_handler(signal.SIGTERM, signal_handler)

    bot_task = asyncio.create_task(bot.run())
    server_task = asyncio.create_task(server.serve())

    try:
        # Wait for either shutdown event or tasks to complete
        done, pending = await asyncio.wait(
            [bot_task, server_task, asyncio.create_task(shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED
        )
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        print("\n[!] Shutting down...")
        shutdown_event.set()
        
        # Stop Bot
        if bot_ref:
            await bot_ref.shutdown()
            
        # Stop Server (force if needed)
        server.should_exit = True
        
        # Cancel remaining tasks
        if not bot_task.done(): bot_task.cancel()
        if not server_task.done(): server_task.cancel()
        
        await api.manager.shutdown()
        
        # Wait for tasks to clean up
        await asyncio.gather(bot_task, server_task, return_exceptions=True)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        import signal
        asyncio.run(main())
    except KeyboardInterrupt:
        # Fallback for Windows if the signal handler didn't catch it
        pass
    except Exception as e:
        sys.__stdout__.write(f"Startup Error: {e}\n")