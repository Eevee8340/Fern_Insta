import os
import json
import asyncio
import re
import time
from datetime import datetime
from typing import Any, Dict, List
from plugins.llm_utils import PluginLLM
import config
import plugins.config as plugin_config
import consts
from services.event_bus import event_bus

PROFILES_DIR = consts.USER_PROFILES_DIR
STATE_FILE = os.path.join(consts.USER_DATA_DIR, "profiler_state.json")
PRIORITY = 75 

class ProfilerPlugin:
    def __init__(self, context) -> None:
        self.ctx = context
        if not os.path.exists(PROFILES_DIR):
            os.makedirs(PROFILES_DIR)
            
        self.settings = plugin_config.PLUGIN_CONFIG.get("Profiler", {})
        self.enabled = plugin_config.PLUGIN_ENABLED.get("Profiler", True)
        
        # Track A: Narrative Threshold
        self.narrative_counts = {}
        self.narrative_threshold = 20 
        
        # Track B: Active Users (For daily 9 AM quote trigger)
        self.active_users = set()
        self.last_quote_reset = 0
        
        self.llm = PluginLLM(context_name="Profiler")
        self.load_state()

    def load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.narrative_counts = data.get("narrative_counts", {})
                    self.active_users = set(data.get("active_users", []))
                    self.last_quote_reset = data.get("last_quote_reset", 0)
            except: pass

    def save_state(self):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "narrative_counts": self.narrative_counts,
                    "active_users": list(self.active_users),
                    "last_quote_reset": self.last_quote_reset
                }, f, indent=2)
        except Exception as e:
            print(f"   [!] Failed to save profiler state: {e}")

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

    def get_safe_handle(self, sender: str) -> str:
        handle = sender
        match = re.search(r"\(@(.*?)\)", sender)
        if match:
            handle = "@" + match.group(1)
        else:
            handle = re.split(r"(\s+replied\s+to|\s+\(replied\s+to)", sender, flags=re.IGNORECASE)[0].strip()
        
        return "".join([c for c in handle if c.isalnum() or c in "._-"])

    async def on_narrative_logged(self, users: List[str]) -> None:
        if not self.enabled: return
        
        for user in users:
            self.narrative_counts[user] = self.narrative_counts.get(user, 0) + 1
            # print(f"   [Profiler] {user} narrative progress: {self.narrative_counts[user]}/{self.narrative_threshold}")
            
            if self.narrative_counts[user] >= self.narrative_threshold:
                print(f"\033[96m   [Profiler] Narrative Threshold reached for {user}. Updating Persona...\033[0m")
                asyncio.create_task(self.update_narrative_profile(user))
                self.narrative_counts[user] = 0
        
        self.save_state()

    async def check_quote_resets(self):
        now_dt = datetime.now()
        today_9am = now_dt.replace(hour=9, minute=0, second=0, microsecond=0)
        last_reset = datetime.fromtimestamp(self.last_quote_reset)

        if now_dt >= today_9am and last_reset < today_9am:
            print(f"\033[96m   [Profiler] 9 AM Quote Regeneration Triggered...\033[0m")
            self.last_quote_reset = now_dt.timestamp()
            
            # Update quotes for all users who were active since last reset
            for user_handle in list(self.active_users):
                print(f"   [Profiler] Daily Quote Update for {user_handle}")
                asyncio.create_task(self.update_quote_profile(user_handle))
            
            self.active_users = set()
            self.save_state()

    async def on_chat_message(self, sender: str, text: str, bubble: Any, **kwargs) -> bool:
        if not self.enabled: return True
        if sender.startswith("You"): return True
        
        await self.check_quote_resets()
        
        handle = self.get_safe_handle(sender)
        if handle not in self.active_users:
            self.active_users.add(handle)
            self.save_state()
            
        return True

    # --- TRACK A: NARRATIVE UPDATE (Title, Traits, Relationships, Fern Thought) ---
    async def update_narrative_profile(self, handle: str, specific_logs: List[Dict] = None) -> None:
        narrative_context = ""
        mentioned_handles = []
        try:
            logs = []
            if specific_logs:
                logs = specific_logs
            elif os.path.exists(consts.HISTORY_LOGS_PATH):
                with open(consts.HISTORY_LOGS_PATH, "r", encoding="utf-8") as f:
                    for line in f:
                        if handle in line:
                            entry = json.loads(line)
                            logs.append(entry)
            
            # If reading from file, we scan summary for handles.
            # If using specific_logs, we do the same.
            
            # Simple scan for other handles in these relevant logs
            for entry in logs:
                summary = entry.get("summary", "")
                found = re.findall(r"@([\w\._]+)", summary)
                for m in found:
                    clean = m.strip()
                    if clean != handle.replace("@", ""):
                        mentioned_handles.append(clean)
            
            recent_logs = logs[-15:]
            narrative_context = "\n".join([f"[{l.get('date', '')}] {l.get('summary', '')}" for l in recent_logs])
            # Truncate to prevent context overflow (Increased to ~4k tokens since 8k ctx is stable)
            if len(narrative_context) > 12000:
                narrative_context = narrative_context[-12000:]
                narrative_context = "..." + narrative_context[3:]
        except Exception as e:
            print(f"   [Profiler] History fetch error: {e}")
            return

        # 2. Fetch Long-Term Facts (The "Truth")
        long_term_facts = []
        cortex = self.ctx.get_cortex()
        if cortex:
            try:
                long_term_facts = await cortex.get_facts_by_user(handle)
            except: pass
        
        facts_text = "\n".join([f"- {f}" for f in long_term_facts]) if long_term_facts else "None."

        # 3. Load Peer Profiles (Relationship Web)
        peer_context = ""
        mentioned_handles = list(set(mentioned_handles))[:5] # Limit to top 5 to save tokens
        if mentioned_handles:
            peer_lines = []
            for peer in mentioned_handles:
                p_path = os.path.join(PROFILES_DIR, f"{peer}.json")
                if os.path.exists(p_path):
                    try:
                        with open(p_path, "r", encoding="utf-8") as f:
                            p_data = json.load(f)
                            # Extract what THEY think of THIS user
                            rel_to_user = p_data.get("relationships", {}).get(handle, "Unknown")
                            peer_lines.append(f"@{peer} thinks {handle} is: '{rel_to_user}'")
                    except: pass
            if peer_lines:
                peer_context = "\n".join(peer_lines)
                if len(peer_context) > 2000:
                    peer_context = peer_context[:2000] + "..."

        # Load existing profile
        existing_profile = {}
        profile_path = os.path.join(PROFILES_DIR, f"{handle}.json")
        if os.path.exists(profile_path):
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    existing_profile = json.load(f)
            except: pass

        # Load Cast Mapping
        from services.alias_manager import AliasManager
        aliases = AliasManager.load_aliases()
        alias_str = ", ".join([f'"{k}": @{v}' for k,v in aliases.items()])

        prompt = f"""
        Review the User Profile for '{handle}'.
        
        STRUCTURED LOGS (Recent Activity):
        {narrative_context}

        LONG-TERM FACTS (Validated Truths):
        {facts_text}

        PEER PERSPECTIVES (What others think of {handle}):
        {peer_context or "None available."}

        CAST MAPPING:
        {alias_str}

        CURRENT PROFILE:
        {json.dumps(existing_profile, indent=2)}
        
        INSTRUCTIONS:
        You are a Conservative Editor.
        1. Review the NEW history against the CURRENT profile.
        2. Use LONG-TERM FACTS to validate or correct Traits.
        3. Assign/Update 'title' ONLY if there is a major personality shift.
        4. Assign/Update 'traits' ONLY if new traits are observed.
        5. Update 'relationships' based on recent dynamics with ANY mentioned users (e.g. "@alice": "Rival", "@bob": "Bestie").
        6. **MANDATORY:** Write/Update 'fern_thought'. This is your private internal monologue about this user. It must be fresh and honest.
        
        RULES:
        - Output a JSON "Patch". Only include fields that MUST change.
        - If a field is still accurate, OMIT it.
        - 'fern_thought' is ALWAYS required if the current one is empty or outdated.
        - DO NOT change the 'quote'.
        """

        # Simplified Grammar (Standard JSON Object)
        gbnf_grammar = r'''
        root ::= object
        object ::= "{" ws ( member ("," ws member)* )? "}" ws
        member ::= string ws ":" ws value
        value ::= string | number | object | array | true | false | null
        string ::= "\"" ([^"\\\r\n] | "\\" .)* "\"" ws
        number ::= "-" ? [0-9]+ ( "." [0-9]* )? ( [eE] [-+]? [0-9]+ )? ws
        array ::= "[" ws ( value ("," ws value)* )? "]" ws
        true ::= "true" ws
        false ::= "false" ws
        null ::= "null" ws
        ws ::= [ \t\n]*
        '''

        try:
            # Use simplified grammar
            raw_text = await self.llm.generate(prompt, grammar=gbnf_grammar)
            if raw_text:
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
                    new_data = json.loads(clean_text)
                    if new_data:
                        self.update_profile(handle, new_data)
                        print(f"   [Profiler] Narrative Profile patched for {handle}.")
                except json.JSONDecodeError as e:
                     print(f"   [!] Profiler JSON Error. Raw: {clean_text[:50]}...")
                     self.log_debug_dump(f"Profiler_Narrative_{handle}", clean_text, str(e))

        except Exception as e:
            print(f"   [!] Profiler Narrative Error: {e}")
            # print(f"   [DEBUG] Raw Text: {raw_text}") # Uncomment if needed

    # --- TRACK B: QUOTE UPDATE (Quote Only) ---
    async def update_quote_profile(self, handle: str) -> None:
        raw_lines = ""
        try:
            safe_handle = handle.replace("@", "")
            raw_path = os.path.join(consts.USER_DATA_DIR, f"{safe_handle}.txt")
            if os.path.exists(raw_path):
                with open(raw_path, "r", encoding="utf-8") as f:
                    # Use splitlines to handle various newline formats safely
                    lines = f.read().splitlines()
                    # Filter empty lines and take the last 100
                    clean_lines = [l.strip() for l in lines if l.strip()]
                    recent_lines = clean_lines[-100:]
                    # Join with double newlines to ensure the LLM treats them as separate messages
                    raw_lines = "\n\n".join(recent_lines)
        except: return

        if not raw_lines: return

        prompt = f"""
        Find the single best "Golden Quote" for user '{handle}'.
        
        RAW CHAT LINES:
        {raw_lines}
        
        INSTRUCTIONS:
        1. Read the lines.
        2. Select ONE verbatim line that is funny, iconic, or defines their personality.
        3. It MUST be an exact copy of the text.
        4. Keep it short 5-30 words and ORIGINAL AS IT WAS IN THE RAW CHAT LINES.
        
        OUTPUT JSON:
        {{ "quote": "The selected line" }}
        """
        
        gbnf_quote = r"""
        root ::= "{" ws "\"quote\"" ":" ws string "}"
        string ::= "\"" ([^"\\\r\n] | "\\" .)* "\""
        ws ::= [ \t\n]*
        """

        try:
            raw_text = await self.llm.generate(prompt, grammar=gbnf_quote)
            if raw_text:
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
                    new_data = json.loads(clean_text)
                    self.update_profile(handle, new_data)
                    print(f"   [Profiler] Quote updated for {handle}.")
                except Exception as e:
                    self.log_debug_dump(f"Profiler_Quote_{handle}", clean_text, str(e))

        except Exception as e:
            print(f"   [!] Profiler Quote Error: {e}")

    def update_profile(self, handle: str, new_data: Dict[str, Any]) -> None:
        file_path = os.path.join(PROFILES_DIR, f"{handle}.json")
        
        # Determine Aliases from aliases.json
        from services.alias_manager import AliasManager
        alias_map = AliasManager.load_aliases()
        user_aliases = [name for name, h in alias_map.items() if h.replace("@", "") == handle]

        profile = {
            "handle": handle,
            "aliases": user_aliases,
            "title": "The Unknown",
            "traits": [],
            "quote": "",
            "relationships": {}
        }
        
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    profile.update(existing)
            except: pass

        # Partial Merge (The "Patch")
        profile["aliases"] = user_aliases # Ensure aliases are always up to date
        if "title" in new_data: profile["title"] = new_data["title"]
        if "quote" in new_data: profile["quote"] = new_data["quote"]
        if "traits" in new_data: profile["traits"] = new_data["traits"]
        if "fern_thought" in new_data: profile["fern_thought"] = new_data["fern_thought"]
        if "relationships" in new_data:
            if not isinstance(profile.get("relationships"), dict): profile["relationships"] = {}
            profile["relationships"].update(new_data["relationships"])
            
        # Hard Cleanup for migration
        profile.pop("feats", None)
        profile.pop("current_arc", None)
        profile.pop("inventory", None)
        profile.pop("archetype", None)

        profile["last_updated"] = time.time()
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2)

def register(ctx):
    p = ProfilerPlugin(ctx)
    event_bus.subscribe(consts.EVENT_NARRATIVE_LOGGED, p.on_narrative_logged)
    event_bus.subscribe(consts.EVENT_CHAT_MESSAGE, p.on_chat_message)
    ctx._bot.profiler = p