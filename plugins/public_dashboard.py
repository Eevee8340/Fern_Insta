import os
import json
import time
import glob
from typing import Any
import plugins.config as plugin_config
import consts
from services.event_bus import event_bus
import http.server
import socketserver
import threading
import functools

PRIORITY = 10

class PublicDashboardPlugin:
    def __init__(self, context) -> None:
        self.ctx = context
        self.last_sync_time = 0
        self.sync_interval = 60 # Seconds
        
        self.settings = plugin_config.PLUGIN_CONFIG.get("PublicDashboard", {})
        self.enabled = plugin_config.PLUGIN_ENABLED.get("PublicDashboard", True)
        
        # Paths
        self.public_dist_path = os.path.join(consts.ROOT_DIR, "web", "public", "dist")
        self.public_db_path = os.path.join(self.public_dist_path, "db.json")
        
        # Caching State
        self.cache = {
            "leaderboard": {"mtime": 0, "data": {}},
            "lore": {"mtime": 0, "data": {}},
            "profiles": {} # handle -> {mtime, data}
        }
        
        # Create directory if not exists
        os.makedirs(self.public_dist_path, exist_ok=True)
        
        # Start Server
        if self.enabled:
            self.start_server()

    def start_server(self):
        try:
            handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=self.public_dist_path)
            # Allow address reuse to prevent "Address already in use" on reload
            socketserver.TCPServer.allow_reuse_address = True
            self.httpd = socketserver.TCPServer(("0.0.0.0", 8856), handler)
            
            self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self.server_thread.start()
            print(f"\033[92m   [PublicDash] Serving on http://localhost:8856\033[0m")
        except Exception as e:
            print(f"\033[91m   [PublicDash] Failed to start server: {e}\033[0m")

    async def on_tick(self, bot) -> None:
        if not self.enabled: return
        
        current_time = time.time()
        if current_time - self.last_sync_time > self.sync_interval:
            self.last_sync_time = current_time
            await self.run_export(bot)

    async def run_export(self, bot) -> None:
        # print("\033[90m   [PublicDash] Exporting data...\033[0m")
        try:
            data = self.gather_data(bot)
            with open(self.public_db_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"   [!] PublicDash Export Error: {e}")

    def _load_if_modified(self, path: str, cache_key: str, default_val: Any) -> Any:
        if not os.path.exists(path):
            return default_val
            
        mtime = os.path.getmtime(path)
        cache_entry = self.cache.get(cache_key)
        
        # Special case for profiles dict
        if cache_key == "profiles":
            # This helper is for single file objects, handled differently below
            return default_val

        if cache_entry and cache_entry["mtime"] == mtime:
            return cache_entry["data"]
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.cache[cache_key] = {"mtime": mtime, "data": data}
                return data
        except:
            return default_val

    def gather_data(self, bot) -> dict:
        # 1. Status (Always Dynamic)
        status = {
            "is_alive": True,
            "is_sleeping": getattr(bot, "is_sleeping", False),
            "last_updated": int(time.time()),
            "msg_count": len(getattr(bot, "log_history", [])) 
        }
        
        # 2. Leaderboard
        lb_path = os.path.join(consts.ROOT_DIR, "leaderboard.json")
        leaderboard = self._load_if_modified(lb_path, "leaderboard", {})
            
        # 3. Lore
        lore_path = os.path.join(consts.ROOT_DIR, "lore.json")
        lore = self._load_if_modified(lore_path, "lore", {})
            
        # 4. User Profiles (Smart Cache)
        profiles_out = []
        profiles_dir = os.path.join(consts.ROOT_DIR, "user_profiles")
        
        if os.path.exists(profiles_dir):
            current_files = glob.glob(os.path.join(profiles_dir, "*.json"))
            
            for fpath in current_files:
                fname = os.path.basename(fpath)
                mtime = os.path.getmtime(fpath)
                
                profile_data = {}
                cached_profile = self.cache["profiles"].get(fname)
                
                if cached_profile and cached_profile["mtime"] == mtime:
                    profile_data = cached_profile["data"]
                else:
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            p = json.load(f)
                            # Sanitize Profile
                            sanitized = {
                                "handle": p.get("handle", "Unknown"),
                                "aliases": p.get("aliases", []),
                                "title": p.get("title", "Resident"),
                                "pfp_url": p.get("pfp_url"),
                                "traits": p.get("traits", []), 
                                "quote": p.get("quote", ""),
                                "relationships": p.get("relationships", {}),
                                "fern_thought": p.get("fern_thought", ""),
                                "last_updated": p.get("last_updated", 0),
                            }
                            profile_data = sanitized
                            self.cache["profiles"][fname] = {"mtime": mtime, "data": sanitized}
                    except: continue

                # Calculate Message Count (Dynamic, from Leaderboard)
                if profile_data:
                    # Create a copy so we don't mutate the cache with dynamic data
                    p_copy = profile_data.copy()
                    handle = p_copy["handle"]
                    
                    count = leaderboard.get("all_time", {}).get(handle, 0)
                    if count == 0 and not handle.startswith("@"):
                        count = leaderboard.get("all_time", {}).get(f"@{handle}", 0)
                    
                    p_copy["message_count"] = count
                    profiles_out.append(p_copy)
                
        return {
            "status": status,
            "leaderboard": leaderboard,
            "lore": lore,
            "profiles": profiles_out
        }

    async def on_local_command(self, command: str) -> bool:
        if not self.enabled: return True
        
        if command == "/force_export":
            print("   -> Manually forcing Public Export...")
            bot = self.ctx._bot
            await self.run_export(bot)
            return False
            
        return True

def register(ctx):
    p = PublicDashboardPlugin(ctx)
    event_bus.subscribe(consts.EVENT_TICK, p.on_tick, priority=PRIORITY)
    event_bus.subscribe(consts.EVENT_LOCAL_COMMAND, p.on_local_command, priority=PRIORITY)
