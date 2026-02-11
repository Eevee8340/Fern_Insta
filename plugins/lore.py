import os
import json
import asyncio
import re
import time
from datetime import datetime
import textwrap
from typing import Any, Dict, List
from plugins.llm_utils import PluginLLM
import config
import plugins.config as plugin_config
import consts
from services.event_bus import event_bus

LORE_PATH = os.path.join(os.path.dirname(consts.CONFIG_PATH), "lore.json")
STATE_FILE = os.path.join(consts.USER_DATA_DIR, "lore_state.json")
PRIORITY = 60

class LorePlugin:
    def __init__(self, context) -> None:
        self.ctx = context
        self.enabled = plugin_config.PLUGIN_ENABLED.get("Lore", True)
        self.llm = PluginLLM(context_name="Lore")
        
        # Load Lore
        self.lore_db = {}
        self.load_lore()
        
        # Buffer State
        self.log_counter = 0
        self.update_threshold = 5  # Run after every 5 narrative logs
        self.load_state()

    def load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.log_counter = data.get("log_counter", 0)
            except: pass

    def save_state(self):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({"log_counter": self.log_counter}, f, indent=2)
        except Exception as e:
            print(f"   [!] Failed to save lore state: {e}")

    def load_lore(self):
        if os.path.exists(LORE_PATH):
            try:
                with open(LORE_PATH, "r", encoding="utf-8") as f:
                    self.lore_db = json.load(f)
            except: self.lore_db = {}

    def save_lore(self):
        try:
            with open(LORE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.lore_db, f, indent=2)
        except Exception as e:
            print(f"   [!] Lore Save Error: {e}")

    def log_debug_dump(self, source: str, raw_text: str, error: str):
        """Logs failed LLM outputs for debugging."""
        try:
            log_path = os.path.join(consts.USER_DATA_DIR, "llm_debug_failures.log")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n[{timestamp}] [{source}] Error: {error}\n")
                f.write("Raw Output:\n")
                f.write(raw_text + "\n")
                f.write("-" * 50 + "\n")
        except Exception as e:
            print(f"   [!] Failed to write debug log: {e}")

    async def on_narrative_logged(self, users: List[str]) -> None:
        if not self.enabled: return
        
        self.log_counter += 1
        # print(f"   [Lore] Narrative Buffer: {self.log_counter}/{self.update_threshold}")
        self.save_state()
        
        if self.log_counter >= self.update_threshold:
            self.log_counter = 0
            self.save_state()
            print(f"\033[96m   [Lore] Threshold reached. Scanning Grimoire...\033[0m")
            asyncio.create_task(self.update_lore_from_history())

    async def update_lore_from_history(self, specific_logs: List[str] = None) -> None:
        # 1. Fetch Recent Logs
        recent_logs = []
        if specific_logs:
            recent_logs = specific_logs
        elif os.path.exists(consts.HISTORY_LOGS_PATH):
            try:
                with open(consts.HISTORY_LOGS_PATH, "r", encoding="utf-8") as f:
                    # Efficiently read last 10 lines
                    lines = f.readlines()
                    last_n = lines[-10:]
                    for line in last_n:
                        try:
                            entry = json.loads(line)
                            recent_logs.append(f"[{entry.get('date')}] {entry.get('summary')}")
                        except: pass
            except Exception as e:
                print(f"   [Lore] Log Read Error: {e}")
                return

        if not recent_logs: return
        
        context_text = "\n".join(recent_logs)
        if len(context_text) > 12000:
             context_text = context_text[-12000:]
             context_text = "..." + context_text[3:]
        
        # 2. Prepare Current Dictionary (Titles only to save tokens)
        known_terms = list(self.lore_db.keys())
        
        prompt = f"""
        You are the Keeper of the Grimoire (a dictionary of group slang, memes, and inside jokes).
        
        RECENT CHRONICLES (Last 10 Events):
        {context_text}
        
        CURRENT KNOWN TERMS:
        {", ".join(known_terms)}
        
        INSTRUCTIONS:
        1. Analyze the chronicles for NEW slang, specialized terms, or recurring memes that are NOT in the known list.
        2. Check if any EXISTING terms are used in a new way that changes their definition.
        3. Ignore generic words. Focus on unique group culture.
        4. Don't only add the words you understand, try to understand the meaning of the words through conversation.
        
        OUTPUT JSON:
        {{
            "new_entries": [
                {{ "term": "term_name", "definition": "definition", "category": "Slang|Event|Inside Joke" }}
            ],
            "updates": [
                {{ "term": "existing_term", "new_definition": "updated definition" }}
            ]
        }}
        """

        gbnf_lore = textwrap.dedent(r'''
            ws ::= [ \t\n]*
            string ::= "\"" ([^"\\\r\n] | "\\" .)* "\""
            item ::= "{" ws "\"term\"" ":" ws string "," ws "\"definition\"" ":" ws string "," ws "\"category\"" ":" ws string "}"
            change ::= "{" ws "\"term\"" ":" ws string "," ws "\"new_definition\"" ":" ws string "}"
            
            # Limit to max 5 items to prevent token overflow
            items ::= "[" ws (item ("," ws item ("," ws item ("," ws item ("," ws item)?)?)?)?)? "]"
            changes ::= "[" ws (change ("," ws change ("," ws change ("," ws change ("," ws change)?)?)?)?)? "]"
            
            root ::= "{" ws "\"new_entries\"" ":" ws items "," ws "\"updates\"" ":" ws changes "}"
        ''')

        try:
            raw_text = await self.llm.generate(prompt, grammar=gbnf_lore)
            if not raw_text: return
            
            # Clean potential markdown
            clean_text = raw_text.strip()
            if clean_text.startswith("```"):
                clean_text = clean_text.split("```", 1)[-1]
                if clean_text.startswith("json"):
                    clean_text = clean_text[4:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
            clean_text = clean_text.strip()

            try:
                data = json.loads(clean_text)
            except json.JSONDecodeError as je:
                print(f"   [!] Lore JSON Error: {je}")
                print(f"   [!] Raw Output (First 100c): {clean_text[:100]}...")
                self.log_debug_dump("Lore_Update", clean_text, str(je))
                return

            changes_made = False
            
            # Process New Entries
            for entry in data.get("new_entries", []):
                term = entry.get("term", "").lower().strip()
                if term and term not in self.lore_db:
                    self.lore_db[term] = {
                        "definition": entry.get("definition"),
                        "category": entry.get("category", "Slang"),
                        "origin": "Extracted from History",
                        "first_seen": time.time(),
                        "usage_count": 1
                    }
                    print(f"   [+] Lore Added: {term}")
                    changes_made = True
            
            # Process Updates
            for update in data.get("updates", []):
                term = update.get("term", "").lower().strip()
                if term in self.lore_db:
                    old_def = self.lore_db[term].get("definition", "")
                    new_def = update.get("new_definition")
                    if new_def and len(new_def) > len(old_def): # Heuristic: Longer is usually better
                        self.lore_db[term]["definition"] = new_def
                        self.lore_db[term]["last_updated"] = time.time()
                        print(f"   [*] Lore Updated: {term}")
                        changes_made = True

            if changes_made:
                self.save_lore()
                
        except Exception as e:
            print(f"   [!] Lore Analysis Error: {e}")

def register(ctx):
    p = LorePlugin(ctx)
    event_bus.subscribe(consts.EVENT_NARRATIVE_LOGGED, p.on_narrative_logged, priority=PRIORITY)
    ctx._bot.lore_plugin = p
