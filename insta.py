import asyncio
import sys
import os
import json
import threading
import queue
import time
import random
import uuid
import multiprocessing
import gc
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Generator, Tuple
from playwright.async_api import TimeoutError, Page, Route, Request as PlaywrightRequest

import config
import consts
from plugin_loader import PluginManager
from cortex import CortexProcess
from web.backend.api import manager

# New Services
from services.browser_manager import BrowserManager
from services.cortex_client import CortexClient
from services.backup_service import backup_service
from services.event_bus import event_bus
from services.throttling import TokenBucket
from services.network_observer import NetworkObserver
from services.message_processor import MessageProcessor
from services.error_reporter import error_reporter
from services.tracing import tracer

class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"

class AsyncFernBot:
    def __init__(self) -> None:
        self.browser_mgr: BrowserManager = BrowserManager()
        self.page: Optional[Page] = None
        
        self.is_sleeping: bool = False
        self.command_queue: asyncio.Queue = asyncio.Queue()
        self.is_busy: bool = False
        self.is_typing: bool = False
        self.plugin_manager: PluginManager = PluginManager(self)
        self.last_msg_time: float = 0.0
        self.latest_screenshot: Optional[bytes] = None
        
        # Stability
        self.throttler = TokenBucket(10, 0.5)
        self.cortex_health_lock = asyncio.Lock()
        self.cortex_failures = 0
        
        # Split-Brain Architecture
        self.cortex_input: multiprocessing.Queue = multiprocessing.Queue()
        self.cortex_output: multiprocessing.Queue = multiprocessing.Queue()
        self.cortex_process: Optional[CortexProcess] = None
        self.cortex_initialized: bool = False
        self.cortex: Optional[CortexClient] = None # Initialized in initialize()
        
        # State
        self.processed_cache: Set[str] = set()
        
        # Network Perception State
        self.captured_app_id: Optional[str] = None
        self.current_thread_id: Optional[str] = None
        self.my_user_id: Optional[str] = None
        self.user_map: Dict[str, str] = {}
        
        # Services
        self.network_observer = NetworkObserver(self.log)
        self.message_processor = MessageProcessor(self.my_user_id, self.user_map)
        
        self.last_msg_id: Optional[str] = None
        self.last_left_sender: str = "Unknown"
        self.last_network_activity: float = time.time()
        self.last_fetch_time: float = 0.0
        
        # History Buffer for UI
        self.message_history: List[Dict[str, Any]] = []
        self.log_history: List[str] = []
        
        # Split-Brain Architecture
        self.restart_browser_flag: bool = False
        self.keep_running: bool = True
        
        # Task Tracking
        self.background_tasks: Set[asyncio.Task] = set()
        
        # Metrics
        self.last_tps: float = 0.0
        self.last_mem: str = "0/0"
        self.last_context: str = ""
        self.last_rag_info: Dict[str, Any] = {}

    async def log(self, text: str) -> None:
        print(text)

    async def initialize(self) -> bool:
        if self.cortex_initialized:
             return True

        # 0. Backup DB
        backup_service.create_backup()
        
        self.loop = asyncio.get_running_loop()
        await self.log(f"{Colors.HEADER}1. Initializing Cortex (AI Process)...{Colors.ENDC}")
        self.cortex_process = CortexProcess(self.cortex_input, self.cortex_output)
        self.cortex_process.start()
        
        # Initialize Async Client
        self.cortex = CortexClient(self.cortex_input, self.cortex_output)
        
        await self.log(f"{Colors.HEADER}2. Cortex starting in background...{Colors.ENDC}")

        await self.log(f"{Colors.HEADER}3. Loading Plugins...{Colors.ENDC}")
        self.plugin_manager.load_plugins()
        
        # Register Error Handler
        event_bus.set_error_handler(self.notify_admin)
        
        # Emit System Start
        await event_bus.emit(consts.EVENT_SYSTEM_START, self)
        
        asyncio.create_task(self.listen_to_cortex())
        return True

    async def notify_admin(self, error_msg: str) -> None:
        """Safe error reporting."""
        error_reporter.report(error_msg, context="AsyncFernBot")
        
        # Only attempt browser interaction if likely safe
        if self.page and not self.page.is_closed() and not self.restart_browser_flag:
            try:
                # Directly switch thread to avoid deadlock if called from main loop
                if await self.browser_mgr.switch_thread(consts.ADMIN_THREAD_ID):
                    self.current_thread_id = consts.ADMIN_THREAD_ID
                    
                    # Wait a bit for switch to complete
                    await asyncio.sleep(3)
                    
                    async def msg_gen():
                        yield f"[CRITICAL ERROR REPORT]\n{error_msg}"
                    
                    await self.type_and_send(msg_gen())
            except Exception as e:
                print(f"   [!] Failed to notify admin via DM: {e}")

    async def listen_to_cortex(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            try:
                msg = await loop.run_in_executor(None, self.get_from_queue)
                if msg:
                    await self.handle_cortex_message(msg)
                else:
                    await asyncio.sleep(0.05)
            except Exception as e:
                print(f"Cortex Listener Error: {e}")
                await self.notify_admin(f"Cortex Listener Error: {e}")
                await asyncio.sleep(1)

    def get_from_queue(self) -> Optional[Dict[str, Any]]:
        try:
            return self.cortex_output.get(block=False)
        except queue.Empty:
            return None

    async def handle_cortex_message(self, msg: Dict[str, Any]) -> None:
        msg_type = msg.get("type")
        req_id = msg.get("req_id")
        await manager.broadcast(msg)
        
        # Delegate to Async Client for request/response matching
        if self.cortex:
            self.cortex.handle_response(msg)

        if msg_type == consts.IPC_INIT_COMPLETE:
            if msg.get("success"):
                await self.log(f"{Colors.GREEN}   [+] Cortex Online (Ready).{Colors.ENDC}")
                self.cortex_initialized = True
            else:
                await self.log(f"{Colors.FAIL}   [!] Cortex Init Failed: {msg.get('error')}{Colors.ENDC}")
                await self.notify_admin(f"Cortex Init Failed: {msg.get('error')}")

        if msg_type == consts.IPC_ERROR:
             await self.notify_admin(f"Cortex Process Error: {msg.get('error')}")

        if msg_type == consts.IPC_META:
            self.last_tps = msg.get("tps", 0.0)
            self.last_mem = msg.get("mem_usage", "0/0")
            self.last_context = msg.get("prompt_log", "")
            self.last_rag_info = msg.get("rag_info", {})

    async def start_stdin_listener(self) -> None:
        loop = asyncio.get_running_loop()
        def listener() -> None:
            while True:
                line = sys.stdin.readline()
                if not line: break
                if line.strip(): loop.call_soon_threadsafe(self.command_queue.put_nowait, line.strip())
        threading.Thread(target=listener, daemon=True).start()

    # --- NETWORK HELPERS ---
    def update_user_map(self, data_root: Dict[str, Any]) -> None:
        thread_data = {}
        if "thread" in data_root: thread_data = data_root["thread"]
        elif "data" in data_root and "thread" in data_root["data"]: thread_data = data_root["data"]["thread"]
        else: thread_data = data_root

        if not thread_data: return

        try:
            if "viewer_id" in thread_data: 
                self.my_user_id = str(thread_data["viewer_id"])
                
            users = thread_data.get("users", [])
            for u in users:
                uid = str(u.get("pk") or u.get("id"))
                username = u.get("username")
                full_name = u.get("full_name")
                pfp_url = u.get("profile_pic_url")
                
                if uid and username:
                    display = f"{full_name} (@{username})" if full_name else f"@{username}"
                    self.user_map[uid] = display
                    
                    # Save PFP URL to profile
                    if pfp_url:
                        self._save_pfp_to_profile(username, pfp_url)
        except: pass

    def _save_pfp_to_profile(self, username: str, pfp_url: str) -> None:
        try:
            import urllib.request
            import socket
            
            # Skip if URL looks like a generic placeholder (Instagram often uses these)
            if not pfp_url or "s150x150" in pfp_url or "default_profile_pic" in pfp_url:
                return

            safe_handle = "".join([c for c in username if c.isalnum() or c in "._-"])
            p_path = os.path.join(consts.USER_PROFILES_DIR, f"{safe_handle}.json")
            
            # Local Avatar Path
            avatars_dir = os.path.join("user_data", "avatars")
            if not os.path.exists(avatars_dir): os.makedirs(avatars_dir)
            
            local_filename = f"{safe_handle}.jpg"
            local_path = os.path.join(avatars_dir, local_filename)
            public_url = f"/avatars/{local_filename}"
            
            # Download Image
            try:
                # Add a simple user-agent to prevent 403s
                opener = urllib.request.build_opener()
                opener.addheaders = [('User-agent', 'Mozilla/5.0')]
                urllib.request.install_opener(opener)
                # Use a timeout to prevent hanging the main loop
                urllib.request.urlretrieve(pfp_url, local_path, timeout=5)
            except (urllib.error.URLError, socket.timeout, ConnectionResetError) as e:
                # Silently fail for common network issues
                public_url = pfp_url # Fallback to remote URL
            except Exception:
                public_url = pfp_url
            
            profile = {}
            if os.path.exists(p_path):
                with open(p_path, "r", encoding="utf-8") as f:
                    profile = json.load(f)
            
            # Only update if changed
            if profile.get("pfp_url") != public_url:
                profile["pfp_url"] = public_url
                with open(p_path, "w", encoding="utf-8") as f:
                    json.dump(profile, f, indent=2)
        except Exception:
            pass

    async def capture_headers(self, route: Route, request: PlaywrightRequest) -> None:
        await self.network_observer.capture_headers(route, request)
        if self.network_observer.captured_app_id:
             self.captured_app_id = self.network_observer.captured_app_id

    async def fetch_latest_message_secure(self) -> Optional[Dict[str, Any]]:
        self.network_observer.current_thread_id = self.current_thread_id
        # Sync back activity timestamp if fetch succeeds
        result = await self.network_observer.fetch_latest_message_secure()
        if result:
            self.last_network_activity = self.network_observer.last_network_activity
        return result

    async def process_network_message(self, msg_node: Dict[str, Any]) -> None:
        # 1. Start Trace
        trace_id = tracer.start_trace("instagram_network_msg")
        
        # Sync Identity
        self.message_processor.update_identity(self.my_user_id)
        
        msg_obj, metadata = self.message_processor.process_node(msg_node)
        
        if not msg_obj:
            tracer.log_event(trace_id, "skipped_duplicate_or_self")
            tracer.end_trace(trace_id)
            return

        tracer.log_event(trace_id, "message_parsed", {"sender": msg_obj["sender"]})

        # Sync back the state
        self.last_msg_id = self.message_processor.last_msg_id
        
        sender_full = msg_obj["sender"]
        content = msg_obj["text"]
        reply_log = msg_obj.get("reply_log", "")
        
        # Log the main message
        await self.log(f"{Colors.GREEN}>>> [{msg_obj['display_time']}] {sender_full}: {content}{Colors.ENDC}")
        self.last_msg_time = time.time()
        
        self.message_history.append(msg_obj)
        if len(self.message_history) > 100: self.message_history.pop(0)
        
        await manager.broadcast(msg_obj)

        if msg_obj.get("is_placeholder"):
            tracer.log_event(trace_id, "skipped_placeholder")
            tracer.end_trace(trace_id)
            return

        tracer.log_event(trace_id, "dispatching_plugins")
        handled = await self.plugin_manager.dispatch(consts.EVENT_CHAT_MESSAGE, sender_full, content, metadata, trace_id=trace_id)
        if handled is False or self.is_sleeping:
            tracer.log_event(trace_id, "stopped_by_plugin_or_sleep", {"handled": handled, "sleeping": self.is_sleeping})
            if not self.is_busy:
                tracer.end_trace(trace_id)
            return

        if not self.cortex:
            tracer.log_event(trace_id, "no_cortex_client")
            tracer.end_trace(trace_id)
            return

        # Throttling Check for Passive Engagement
        is_direct = "fern" in sender_full.lower() or "reply" in sender_full.lower() 
        
        if not is_direct:
            if not self.throttler.take():
                print(f"{Colors.WARNING}   [!] Throttled: Skipping analysis for {sender_full}{Colors.ENDC}")
                self.cortex.update_history("user", f"{sender_full}: {content}")
                tracer.log_event(trace_id, "throttled")
                tracer.end_trace(trace_id)
                return

        # Cortex Logic
        tracer.log_event(trace_id, "asking_engagement")
        should_reply, reason = await self.cortex.ask_engagement(sender_full, content, trace_id=trace_id)
        tracer.log_event(trace_id, "engagement_result", {"should_reply": should_reply, "reason": reason})
        
        if should_reply:
            if reply_log:
                await self.log(reply_log)
                
            await self.log(f"{Colors.GREEN}   -> Engaging ({reason}){Colors.ENDC}")
            asyncio.create_task(self.execute_reply(sender_full, content, parent_context=metadata.get("parent_context", ""), trace_id=trace_id))
        else:
            if "fern" not in sender_full.lower():
                 self.cortex.update_history("user", f"{sender_full}: {content}")
            tracer.end_trace(trace_id)

    async def type_and_send(self, response_generator: Generator[str, None, None], trace_id: Optional[str] = None) -> None:
        if not self.page: return
        self.is_typing = True
        if trace_id: tracer.log_event(trace_id, "typing_started")
        
        try:
            print(f"{Colors.BLUE}   -> Fern is typing...{Colors.ENDC}")
            buf = ""
            full_text = ""
            chars_typed = 0

            async for token in response_generator:
                if not token: continue
                sys.__stdout__.write(token)
                sys.__stdout__.flush()
                buf += token
                full_text += token
                
                if len(buf) >= config.TYPING_CHUNK_SIZE or buf.endswith((" ", "\n", ".")):
                    parts = buf.split('\n')
                    for i, part in enumerate(parts):
                        if part: await self.page.keyboard.type(part)
                        if i < len(parts) - 1: await self.page.keyboard.press("Shift+Enter")
                    chars_typed += len(buf)
                    buf = ""
                    await asyncio.sleep(random.uniform(config.TYPING_DELAY_MIN, config.TYPING_DELAY_MAX))

            if buf:
                parts = buf.split('\n')
                for i, part in enumerate(parts):
                    if part: await self.page.keyboard.type(part)
                    if i < len(parts) - 1: await self.page.keyboard.press("Shift+Enter")
                chars_typed += len(buf)

            await asyncio.sleep(min(1.0, chars_typed * 0.02))
            await self.page.keyboard.press("Enter")
            
            if trace_id: tracer.log_event(trace_id, "message_sent", {"chars": chars_typed})
            
            msg_obj = {"type": "chat_message", "sender": "Fern", "text": full_text, "timestamp": time.time()}
            self.message_history.append(msg_obj)
            if len(self.message_history) > 100: self.message_history.pop(0)
            
            await manager.broadcast(msg_obj)
            print("")

        except Exception as e:
            print(f"\n{Colors.FAIL}   -> Error typing message: {e}{Colors.ENDC}")
            await self.notify_admin(f"Error typing message: {e}")
        finally:
            self.is_typing = False
            if trace_id: tracer.end_trace(trace_id)

    async def execute_reply(self, sender: str, text: str, bubble: Any = None, parent_context: str = "", trace_id: Optional[str] = None) -> None:
        if not self.page: return
        self.is_busy = True
        try:
            await asyncio.sleep(random.uniform(config.REPLY_DELAY_MIN, config.REPLY_DELAY_MAX))
            
            # 1. UI Interaction: Click Reply
            if trace_id: tracer.log_event(trace_id, "ui_reply_clicking")
            try:
                # 1. Find the Text Element (div[dir="auto"])
                search_term = text.strip()
                use_exact = len(search_term) < 5
                
                # Primary Selector
                text_el = self.page.locator('div[dir="auto"]').filter(has_text=search_term).last
                if await text_el.count() == 0:
                     text_el = self.page.get_by_text(search_term, exact=use_exact).last

                if await text_el.count() > 0:
                    await text_el.scroll_into_view_if_needed()
                    # Clicking is often more reliable than hovering to reveal action buttons
                    await text_el.click(force=True) 
                    await asyncio.sleep(0.5)

                    # 2. Find the Reply Button (SVG)
                    # Based on DOM: svg[aria-label="Reply to message from ..."]
                    reply_btns = self.page.locator('svg[aria-label*="Reply"]').filter(has=self.page.locator(":visible"))
                    
                    if await reply_btns.count() > 0:
                        # Assuming the last visible reply button corresponds to the last visible message
                        await reply_btns.last.click(force=True)
                        await asyncio.sleep(0.2)
                    else:
                        # Fallback to right-click
                        await text_el.click(button="right", force=True)
                        await asyncio.sleep(0.5)
                        await self.page.get_by_text("Reply", exact=True).last.click(force=True)
            except Exception:
                # Ensure the message box is focused at least
                try:
                    await self.page.click('div[aria-label="Message"][contenteditable="true"]', timeout=1000)
                except: pass

            # 2. LLM Generation
            if trace_id: tracer.log_event(trace_id, "generation_started")
            token_stream = await self.cortex.generate(sender, text, context=parent_context, trace_id=trace_id)
            await self.type_and_send(token_stream, trace_id=trace_id)
            
        except Exception as e:
            print(f"Reply Task Error: {e}")
            await self.notify_admin(f"Reply Task Error: {e}")
            if trace_id: tracer.end_trace(trace_id)
        finally: self.is_busy = False
    async def monitor_cortex_health(self) -> None:
        print(f"{Colors.CYAN}[Health] Cortex Heartbeat Monitor Started.{Colors.ENDC}")
        while self.keep_running:
            await asyncio.sleep(30)
            if not self.cortex or not self.cortex_process or not self.cortex_process.is_alive():
                continue
                
            try:
                # Ping
                alive = await self.cortex.ping(timeout=10.0)
                if alive:
                    self.cortex_failures = 0
                else:
                    self.cortex_failures += 1
                    print(f"{Colors.WARNING}[Health] Cortex Ping Failed ({self.cortex_failures}/3){Colors.ENDC}")
            except Exception as e:
                print(f"[Health] Ping Error: {e}")
                await self.notify_admin(f"Cortex Ping Error: {e}")
                self.cortex_failures += 1
            
            if self.cortex_failures >= 3:
                print(f"{Colors.FAIL}[Health] Cortex Unresponsive. Initiating Restart...{Colors.ENDC}")
                await self.restart_cortex()

    async def restart_cortex(self) -> None:
        async with self.cortex_health_lock:
            await self.log(f"{Colors.HEADER}--- RESTARTING AI CORE ---{Colors.ENDC}")
            
            # 1. Kill Old Local Process
            if self.cortex_process:
                try:
                    self.cortex_process.terminate()
                    self.cortex_process.join(timeout=2)
                    if self.cortex_process.is_alive():
                        self.cortex_process.kill()
                except: pass
            
            # 2. Re-create (Using SAME Queues for simplicity in Phase 1)
            # If queues are corrupted, this will fail, but handling queue rotation requires 
            # restarting the listener task too.
            try:
                # Drain Queues to prevent reading old garbage
                while not self.cortex_output.empty():
                    try: self.cortex_output.get_nowait()
                    except: break
                
                self.cortex_process = CortexProcess(self.cortex_input, self.cortex_output)
                self.cortex_process.start()
                
                # Re-init client (clears pending futures)
                self.cortex = CortexClient(self.cortex_input, self.cortex_output)
                
                self.cortex_failures = 0
                await self.log(f"{Colors.GREEN}   [+] Cortex Process Respawned.{Colors.ENDC}")
                
                # Notify admin of the incident
                await self.notify_admin("Cortex restarted due to unresponsiveness.")
                
            except Exception as e:
                print(f"{Colors.FAIL}[Health] Restart Failed: {e}{Colors.ENDC}")
                await self.notify_admin(f"Cortex Restart Failed: {e}")

    async def process_commands(self) -> None:
        # --- TEST TRIGGER ---
        if os.path.exists("trigger_admin_test.txt"):
            print(f"{Colors.WARNING}[TEST] trigger_admin_test.txt detected. Sending test DM...{Colors.ENDC}")
            try: os.remove("trigger_admin_test.txt")
            except: pass
            await self.notify_admin("This is a manual test of the Admin Notification System.")
        # --------------------

        while not self.command_queue.empty():
            cmd = await self.command_queue.get()
            if cmd == "/restart_browser":
                 self.restart_browser_flag = True
                 return
            if cmd.startswith("/switch_thread "):
                 thread_id = cmd.split(" ")[1].strip()
                 if await self.browser_mgr.switch_thread(thread_id):
                     self.current_thread_id = thread_id
                     self.captured_app_id = None
                     print(f"{Colors.GREEN}   -> Switched to Thread ID: {thread_id}{Colors.ENDC}")
                     if self.page: await self.page.reload()
                 return

            if cmd.startswith("/"):
                if cmd == "/reload":
                    self.cortex_input.put({"type": consts.IPC_COMMAND, "cmd": "reload"})
                else:
                    await self.plugin_manager.dispatch(consts.EVENT_LOCAL_COMMAND, cmd)

    async def run(self) -> None:
        if not await self.initialize(): return
        await self.start_stdin_listener()
        
        # Start Health Monitor
        t_health = asyncio.create_task(self.monitor_cortex_health())
        self.background_tasks.add(t_health)

        while self.keep_running:
            self.restart_browser_flag = False
            try:
                if not self.keep_running: break
                
                try:
                    self.page = await self.browser_mgr.launch()
                    self.network_observer.attach_page(self.page)
                except Exception as e:
                    if not self.keep_running: break
                    print(f"{Colors.FAIL}[Launch Error] {e}{Colors.ENDC}")
                    await self.notify_admin(f"Launch Error: {e}")
                    await asyncio.sleep(5)
                    continue

                # Optimize: Only intercept API calls, let images/assets load directly
                await self.page.route("**/api/v1/**", self.capture_headers)
                
                def handle_ws(ws: Any) -> None:
                    async def process_frame(frame_data: Any) -> None:
                        self.last_network_activity = time.time()
                        decoded_text = ""
                        try:
                            if isinstance(frame_data, bytes):
                                decoded_text = frame_data.decode('utf-8', errors='ignore')
                            elif isinstance(frame_data, str):
                                decoded_text = frame_data
                        except: pass
                        
                        # Broader trigger for DMs where Thread ID might not be in the delta payload
                        should_fetch = False
                        if self.current_thread_id:
                            if self.current_thread_id in decoded_text:
                                should_fetch = True
                            # Common indicators of a message update in IG's protocol
                            elif '"text":' in decoded_text or '"item_id":' in decoded_text:
                                should_fetch = True
                            elif "thread_key" in decoded_text or "replace" in decoded_text:
                                should_fetch = True
                        
                        if should_fetch:
                            # Debounce check
                            if time.time() - self.last_fetch_time > 1.5:
                                self.last_fetch_time = time.time()
                                full_data = await self.fetch_latest_message_secure()
                                if full_data:
                                    self.update_user_map(full_data)
                                    if "thread" in full_data and "items" in full_data["thread"]:
                                        items = full_data["thread"]["items"]
                                        if items:
                                            await self.process_network_message(items[0])

                    ws.on("framereceived", lambda frame: asyncio.create_task(
                        process_frame(frame.body if hasattr(frame, 'body') else frame)
                    ))

                self.page.on("websocket", handle_ws)
                await self.browser_mgr.handle_popups()
                
                current_url = self.browser_mgr.current_url
                if "/t/" in current_url:
                    parts = current_url.split("/t/")
                    if len(parts) > 1:
                        self.current_thread_id = parts[1].strip("/")
                        await self.log(f"   [+] Detected Thread ID: {self.current_thread_id}")

                await self.log(f"\n{Colors.HEADER}6. Fern is listening (Network Mode)...{Colors.ENDC}")
                
                init_data = await self.fetch_latest_message_secure()
                if init_data:
                    self.update_user_map(init_data)
                    if "thread" in init_data and init_data["thread"]["items"]:
                        last_id = init_data["thread"]["items"][0]["item_id"]
                        self.last_msg_id = last_id
                        self.message_processor.last_msg_id = last_id
                        print(f"   [+] Synced. Last Msg ID: {self.last_msg_id}")

                self.is_busy = False 

                async def view_updater() -> None:
                    while not self.restart_browser_flag and self.keep_running:
                        try:
                            # LAZY SCREENSHOT: Only take if someone is watching or we need a refresh
                            if self.page and (manager.has_active_connections or self.is_typing):
                                self.latest_screenshot = await self.page.screenshot(type='jpeg', quality=50)
                            await asyncio.sleep(5.0)
                        except: await asyncio.sleep(5)
                
                t_view = asyncio.create_task(view_updater())
                self.background_tasks.add(t_view)
                t_view.add_done_callback(self.background_tasks.discard)
                
                async def network_watchdog() -> None:
                    while not self.restart_browser_flag and self.keep_running:
                        await asyncio.sleep(10)
                        
                        # 1. Activity Check
                        if time.time() - self.last_network_activity > 300:
                            await self.log(f"{Colors.WARNING}[Watchdog] No activity for 5m. Restarting...{Colors.ENDC}")
                            self.restart_browser_flag = True
                            continue

                        # 2. Page Crash Check
                        try:
                            if self.page and self.page.is_closed():
                                await self.log(f"{Colors.FAIL}[Watchdog] Page closed unexpectedly.{Colors.ENDC}")
                                self.restart_browser_flag = True
                        except: pass

                t_watch = asyncio.create_task(network_watchdog())
                self.background_tasks.add(t_watch)
                t_watch.add_done_callback(self.background_tasks.discard)

                while not self.restart_browser_flag and self.keep_running:
                    await self.process_commands()
                    if self.restart_browser_flag: break
                    
                    # Emit Tick
                    await event_bus.emit(consts.EVENT_TICK, self)
                    
                    await asyncio.sleep(0.5)
                
                for t in [t_view, t_watch]:
                    if not t.done(): t.cancel()
                await asyncio.gather(t_view, t_watch, return_exceptions=True)
                await self.browser_mgr.close()

            except Exception as e:
                if not self.keep_running: break
                
                print(f"{Colors.FAIL}Main Loop Error: {e}{Colors.ENDC}")
                import traceback
                traceback.print_exc()
                try: await self.notify_admin(f"Main Loop Crash: {e}")
                except: pass
                await asyncio.sleep(5)

    async def shutdown(self) -> None:
        print(f"{Colors.HEADER}Shutting down Cortex...{Colors.HEADER}")
        
        self.keep_running = False
        
        if self.background_tasks:
            for task in self.background_tasks:
                task.cancel()
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
            self.background_tasks.clear()

        if self.cortex_process and self.cortex_process.is_alive():
            try:
                self.cortex_input.put({"type": consts.IPC_SHUTDOWN})
                self.cortex_process.terminate()
                self.cortex_process.join(timeout=0.1)
            except: pass
        
        await self.browser_mgr.close()
        print("Shutdown complete.")