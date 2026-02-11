import os
import json
import time
import asyncio
from datetime import datetime
from typing import Any
import consts
from services.event_bus import event_bus

LEADERBOARD_FILE = "leaderboard.json"
PRIORITY = 50

class LeaderboardPlugin:
    def __init__(self, context):
        self.ctx = context
        self.data = {
            "all_time": {},
            "weekly": {},
            "daily": {},
            "last_daily_reset": time.time(),
            "last_weekly_reset": time.time()
        }
        
        # Batch I/O State
        self.pending_updates = 0
        self.last_save_time = time.time()
        self.batch_limit = 10
        self.save_interval = 60
        
        self.load_data()

    def load_data(self):
        if os.path.exists(LEADERBOARD_FILE):
            try:
                with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except: pass
        
        for key in ["all_time", "weekly", "daily"]:
            if key not in self.data: self.data[key] = {}
        if "last_daily_reset" not in self.data: self.data["last_daily_reset"] = time.time()
        if "last_weekly_reset" not in self.data: self.data["last_weekly_reset"] = time.time()

    def save_data(self):
        try:
            with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            self.pending_updates = 0
            self.last_save_time = time.time()
        except Exception as e:
            print(f"   [Leaderboard] Save Error: {e}")

    def check_resets(self):
        now_dt = datetime.now()
        now_ts = now_dt.timestamp()
        updated = False

        # 9 AM Daily Reset
        today_9am = now_dt.replace(hour=9, minute=0, second=0, microsecond=0)
        last_daily = datetime.fromtimestamp(self.data.get("last_daily_reset", 0))

        if now_dt >= today_9am and last_daily < today_9am:
            print("   [Leaderboard] 9 AM Daily Reset Triggered...")
            self.data["daily"] = {}
            self.data["last_daily_reset"] = now_ts
            updated = True

        # Weekly Reset (Maintain 7-day interval but sync with 9 AM trigger if possible)
        if now_ts - self.data.get("last_weekly_reset", 0) >= 604800:
            if now_dt >= today_9am:
                print("   [Leaderboard] Weekly Reset Triggered (Synced to 9 AM)...")
                self.data["weekly"] = {}
                self.data["last_weekly_reset"] = now_ts
                updated = True
        
        if updated:
            self.save_data()

    async def on_chat_message(self, sender: str, text: str, bubble: Any, **kwargs) -> bool:
        # Ignore self and system messages
        if sender.startswith("You"):
            return True
            
        # Avoid tracking the bot itself if it somehow echoes back
        # Assuming config.BOT_NAME / config.BOT_HANDLE are available or just check for "fern" as a whole word if strict config isn't imported
        if sender.lower() == "fern" or " fern " in f" {sender.lower()} ":
             return True

        if text.strip().lower().startswith("/fern top"):
            cmd_suffix = text.strip()[6:] 
            await self.on_local_command(f"/{cmd_suffix}")
            return False

        handle = sender
        if "(" in sender and ")" in sender:
            try:
                handle = sender.split("(")[1].split(")")[0]
            except: pass
        
        handle = handle.strip()
        
        self.check_resets()

        self.data["all_time"][handle] = self.data["all_time"].get(handle, 0) + 1
        self.data["weekly"][handle] = self.data["weekly"].get(handle, 0) + 1
        self.data["daily"][handle] = self.data["daily"].get(handle, 0) + 1
        
        self.pending_updates += 1
        if self.pending_updates >= self.batch_limit or (time.time() - self.last_save_time > self.save_interval):
            self.save_data()
            
        return True

    async def on_local_command(self, command: str) -> bool:
        cmd = command.lower().strip()
        
        category = None
        title = ""
        
        if cmd == "/top":
            category = "all_time"
            title = "🏆 All-Time Yappers"
        elif cmd in ["/top week", "/top weekly"]:
            category = "weekly"
            title = "📅 Weekly Yappers"
        elif cmd in ["/top day", "/top daily"]:
            category = "daily"
            title = "🔥 Daily Yappers"
            
        if category:
            stats = self.data.get(category, {})
            if not stats:
                print(f"   [Leaderboard] No data for {category} yet.")
                return False

            sorted_users = sorted(stats.items(), key=lambda item: item[1], reverse=True)[:5]
            
            msg = f"{title}:\n"
            for i, (user, count) in enumerate(sorted_users, 1):
                medal = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else "4." if i==4 else "5."
                msg += f"{medal} {user}: {count}\n"
            
            await self.ctx.send_message(msg)
            return False

        return True

def register(ctx):
    p = LeaderboardPlugin(ctx)
    event_bus.subscribe(consts.EVENT_CHAT_MESSAGE, p.on_chat_message, priority=PRIORITY)
    event_bus.subscribe(consts.EVENT_LOCAL_COMMAND, p.on_local_command, priority=PRIORITY)