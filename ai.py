import logging
import random
import time
import re
import datetime
import os
from typing import List, Generator, Tuple, Optional, Dict, Any, Callable
from jinja2 import Template

# Disable Fortran Control-C handler to prevent immediate abortion
os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'

import gc
import json
import sys
from sentence_transformers import SentenceTransformer, CrossEncoder

import config
import consts
from fern_memory import FernMemoryDB
from services.tracing import tracer

# Conditional Imports
try:
    from openai import OpenAI, APIConnectionError
except ImportError:
    OpenAI = None

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("FernAI")

# --- GLOBAL FORMATTING RULES ---
# Removed redundant FORMATTING_INSTRUCTION as it is covered by the System Profile.

class FernAI:
    def __init__(self) -> None:
        self.client: Optional[Any] = None
        self.local_llm: Optional[Any] = None
        self.current_mem_usage: str = "0/0"
        self.last_tps: float = 0.0
        self.last_prompt_log: str = ""
        self.last_rag_info: Dict[str, Any] = {}
        
        # Load embedding model (Moved from FernMemoryDB for memory optimization)
        print("   [+] Loading Memory Encoder (all-MiniLM-L6-v2)...")
        self.encoder: SentenceTransformer = SentenceTransformer('all-MiniLM-L6-v2')
        
        print("   [+] Loading Memory Reranker (ms-marco-MiniLM-L-6-v2)...")
        self.reranker: CrossEncoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        
        # Initialize Backend based on Config
        if config.USE_IN_PROCESS_LLM:
            self._init_local_llm()
        else:
            self._init_remote_client()

        # Regex Patterns
        self.replied_pattern: re.Pattern = re.compile(r"\s*replied to you", re.IGNORECASE)
        self.hallucination_pattern: re.Pattern = re.compile(r"^[\w\s.\-\(\)\@]+:\s*", re.IGNORECASE)
        self.prefix_pattern: re.Pattern = re.compile(r"^[\(\[]?fern[\) \]]?\s*:\s*", re.IGNORECASE)
        
        self.system_instruction: str = config.PROFILE
        self.chat_history: List[dict] = []
        self.history_char_limit: int = config.HISTORY_CHAR_LIMIT
        
        # Seed History
        self.seed_history()

        # Bot State
        self.bot_name: str = config.BOT_NAME
        self.bot_handle: str = config.BOT_HANDLE
        self.triggers: List[str] = config.TRIGGERS
        self.last_reply_time: float = 0.0
        self.reply_streak: int = 0

        # Personality Parameters
        self.base_chaos_rate: float = config.BASE_CHAOS_RATE
        self.continuation_rate: float = config.CONTINUATION_RATE
        
        # Long Term Memory
        try:
            self.memory_db: Optional[FernMemoryDB] = FernMemoryDB()
        except Exception as e:
            print(f"   [!] Memory DB Load Failed: {e}")
            self.memory_db = None

    def _init_local_llm(self) -> None:
        if not Llama:
            print(f"[!] llama-cpp-python not installed. Cannot use local mode.")
            return

        if not os.path.exists(config.MODEL_PATH):
            raise FileNotFoundError(f"Model file '{config.MODEL_PATH}' missing.")

        print(f"   [+] Loading Local LLM ({config.MODEL_PATH})...")
        try:
            # Direct In-Process Binding
            self.local_llm = Llama(
                model_path=config.MODEL_PATH,
                n_ctx=config.CONTEXT_WINDOW,
                n_gpu_layers=config.GPU_LAYERS,
                verbose=False
            )
            
            # Enable Prompt Caching
            try:
                from llama_cpp import LlamaRAMCache
                self.local_llm.set_cache(LlamaRAMCache())
                print(f"   [+] Local LLM Loaded (Prompt Caching: ENABLED).")
            except ImportError:
                print(f"   [+] Local LLM Loaded (Prompt Caching: NOT SUPPORTED).")
                
        except Exception as e:
            print(f"   [!] Failed to load Local LLM: {e}")

    def _init_remote_client(self) -> None:
        if not OpenAI:
            print(f"   [!] openai package not installed. Remote mode unavailable.")
            return
            
        print(f"   [+] Connecting to Remote LLM at {config.REMOTE_LLM_URL}...")
        self.client = OpenAI(base_url=config.REMOTE_LLM_URL, api_key="sk-no-key-required")

    def seed_history(self) -> None:
        self.chat_history = [
            {"role": "user", "content": "who are u?"},
            {"role": "assistant", "content": "i'm fern lol. why?"}
        ]
        self.log_memory_usage()

    # --- SERVER COMPATIBILITY STUBS (Safe to remove later, kept for cortex.py calls) ---
    def start_server(self) -> None: pass
    def stop_server(self) -> None: pass

    def clear_memory(self) -> None:
        self.seed_history()
        print("Memory cleared & Reseeded.")

    def flush_facts(self) -> None:
        """Wipes all strict facts from the database (Long Term Memory)."""
        if self.memory_db:
            try:
                # 1. Fetch all fact IDs
                data = self.memory_db.collection.get(where={"source": "strict_fact"})
                ids = data.get("ids", [])
                if ids:
                    self.memory_db.collection.delete(ids=ids)
                    print(f"   [AI] Flushed {len(ids)} facts from DB.")
                else:
                    print("   [AI] No facts found to flush.")
            except Exception as e:
                print(f"   [!] Fact Flush Error: {e}")

    def analyze_batch(self, text_block: str) -> Dict[str, Any]:
        """Analyzes a batch of logs to produce Strict Facts."""
        if not self.local_llm and not self.client: return {"facts": []}

        # Truncate input
        if len(text_block) > 12000:
            text_block = text_block[:12000] + "..."

        prompt = f"""
        Extract atomic, Subject-Verb-Object facts from the following summary.
        A fact should be a single, searchable statement about permanent identity or preferences.
        
        SUMMARY:
        {text_block}

        RULES:
        1. Focus ONLY on:
           - User Identity (Names, jobs, roles).
           - Permanent Preferences (Likes, dislikes, opinions on games/movies/foods).
           - Relationships (Who is friends with whom).
        2. IGNORE: 
           - Temporary states ("User is tired", "User is playing a game now").
           - Greetings or meta-talk about the chat.
           - Bot-specific opinions.
        3. FORMATTING:
           - Use simple Subject-Verb-Object sentences.
           - NO passive voice.
           - GOOD: "Alice likes pizza."
           - BAD: "Alice mentioned that she likes pizza."
        
        OUTPUT FORMAT: JSON Object with a "facts" key containing a list of strings.
        """
        
        # GBNF Grammar for: { "facts": ["str", "str"] }
        gbnf_grammar = r'''
        root ::= "{" ws "\"facts\"" ":" ws stringlist "}"
        stringlist ::= "[" ws "]" | "[" ws string ("," ws string)* ws "]"
        string ::= "\"" ([^"\\] | "\\" .)* "\""
        ws ::= [ \t\n]*
        '''

        try:
            messages = [{"role": "system", "content": "You are a data extraction engine. Output JSON."}, {"role": "user", "content": prompt}]
            
            full_response = ""
            
            if config.USE_IN_PROCESS_LLM and self.local_llm:
                try:
                    from llama_cpp import LlamaGrammar
                    grammar = LlamaGrammar.from_string(gbnf_grammar)
                    resp = self.local_llm.create_chat_completion(
                        messages=messages, 
                        max_tokens=1000, 
                        temperature=0.1,
                        grammar=grammar
                    )
                except ImportError:
                    # Fallback if grammar not supported
                    resp = self.local_llm.create_chat_completion(messages=messages, max_tokens=1000, temperature=0.1)

                full_response = resp['choices'][0]['message']['content']

            elif self.client:
                # Pass grammar in extra_body for remote llama.cpp compatible servers
                resp = self.client.chat.completions.create(
                    model="local-model", 
                    messages=messages, 
                    max_tokens=1000, 
                    temperature=0.1,
                    extra_body={"grammar": gbnf_grammar} 
                )
                full_response = resp.choices[0].message.content
            
            print(f"   [DEBUG] LLM Raw Response: {full_response[:50]}...")

            # Clean potential markdown
            clean_text = full_response.strip()
            if clean_text.startswith("```"):
                clean_text = clean_text.split("```", 1)[-1]
                if clean_text.startswith("json"):
                    clean_text = clean_text[4:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
            clean_text = clean_text.strip()

            import json
            return json.loads(clean_text)

        except Exception as e:
            print(f"Batch Analysis Error: {e}")
            return {"facts": []}

    def update_history(self, role: str, text: str) -> None:
        self.chat_history.append({"role": role, "content": text})

        # Message Count Limit (Keep last 30 messages)
        if len(self.chat_history) > 30:
            self.chat_history = self.chat_history[-30:]

        current_length = sum(len(m["content"]) for m in self.chat_history)
        while current_length > self.history_char_limit and self.chat_history:
            removed = self.chat_history.pop(0)
            current_length -= len(removed["content"])

        if role == "assistant":
            self.last_reply_time = time.time()
            self.reply_streak += 1
            
        self.log_memory_usage()

    def log_memory_usage(self) -> None:
        try:
            full_context = self.system_instruction + "".join([m["content"] for m in self.chat_history])
            est_tokens = int(len(full_context) / 3.5)
            self.current_mem_usage = f"~{est_tokens}/{config.CONTEXT_WINDOW}"
        except Exception: pass

    def get_social_context(self, user_name: str, message_text: str = "") -> List[dict]:
        match = re.search(r"@([\w.-]+)", user_name)
        handle = match.group(1) if match else user_name
        safe_handle = "".join([c for c in handle if c.isalnum() or c in "._-"])
        
        target_handles = [safe_handle]
        
        # Find mentions in text
        if message_text:
            mentions = re.findall(r"@([\w.-]+)", message_text)
            for m in mentions:
                clean = "".join([c for c in m if c.isalnum() or c in "._-"])
                if clean and clean not in target_handles and clean.lower() != self.bot_handle.replace("@","",).lower():
                    target_handles.append(clean)
        
        social_notes = []
        
        for h in target_handles:
            profile_path = os.path.join(consts.USER_PROFILES_DIR, f"{h}.json")
            if os.path.exists(profile_path):
                try:
                    with open(profile_path, "r", encoding="utf-8") as f:
                        profile = json.load(f)
                        
                        traits = ", ".join(profile.get("traits", []))
                        
                        relationships = profile.get("relationships", {})
                        rel_list = []
                        for target, status in relationships.items():
                            rel_list.append(f"{target}: {status}")
                        
                        rel_str = " | ".join(rel_list) if rel_list else "None"
                        
                        note = f"[User Profile: @{h}]\n"
                        if traits: note += f"[Traits: {traits}]\n"
                        note += f"[Relationships: {rel_str}]"
                        
                        social_notes.append({"role": "system", "content": note})
                except Exception: pass
                
        return social_notes

    def get_lore_context(self, text: str) -> str:
        """Scans text for known slang in lore.json"""
        lore_path = os.path.join(os.path.dirname(consts.CONFIG_PATH), "lore.json")
        found_lore = []
        
        if os.path.exists(lore_path):
            try:
                with open(lore_path, "r", encoding="utf-8") as f:
                    lore_db = json.load(f)
                    
                text_lower = text.lower()
                for term, data in lore_db.items():
                    if term in text_lower:
                        found_lore.append(f"'{term}': {data['definition']} (Origin: {data.get('origin', 'Unknown')})")
            except: pass
            
        if found_lore:
            return "\n".join(found_lore)
        return ""

    def analyze_engagement(self, sender: str, text: str, trace_id: Optional[str] = None, trace_cb: Optional[Callable] = None) -> Tuple[bool, str]:
        current_time = time.time()
        text_lower = (text or "").lower().strip()
        sender_clean = (sender or "").replace(" (Cached)", "")

        if sender_clean.startswith("You") or \
           self.bot_handle.lower() in sender_clean.lower() or \
           self.bot_name.lower() == sender_clean.lower():
            if trace_cb: trace_cb("engagement_check_failed", {"reason": "self"})
            return False, "Self"

        if "replied to you" in (sender or "").lower():
            if trace_cb: trace_cb("engagement_check_passed", {"reason": "direct_reply"})
            return True, "Direct Reply"

        if any(t in text_lower for t in self.triggers):
            self.reply_streak = 0
            if trace_cb: trace_cb("engagement_check_passed", {"reason": "mention"})
            return True, "Direct Mention"

        if (current_time - self.last_reply_time) < config.COOLDOWN_SECONDS:
            if trace_cb: trace_cb("engagement_check_failed", {"reason": "cooldown"})
            return False, "Cooling Down"

        last_role = self.chat_history[-1]["role"] if self.chat_history else ""
        if last_role == "assistant":
            chance = self.continuation_rate
            if len(text_lower) < 4 and "?" not in text_lower: chance = 0.15
            elif "?" in text_lower: chance = 0.95

            if random.random() < chance: 
                if trace_cb: trace_cb("engagement_check_passed", {"reason": "momentum"})
                return True, "Momentum"
            else:
                self.reply_streak = 0
                if trace_cb: trace_cb("engagement_check_failed", {"reason": "momentum_broken"})
                return False, "Momentum Broken"

        if random.random() < self.base_chaos_rate:
            if trace_cb: trace_cb("engagement_check_passed", {"reason": "chaos"})
            return True, "Chaos Roll"

        self.reply_streak = 0
        if trace_cb: trace_cb("engagement_check_failed", {"reason": "ignored"})
        return False, "Ignored"

    def _clean_log_content(self, text: str) -> str:
        """Sanitizes RAG logs by removing artifact headers and fixing handles."""
        # Remove entire sections that we don't want in the prompt
        # Specifically: [USER_STATE] and [NEW_FACTS] as these are handled by Profiler/Fact System
        # Handle both [SECTION] and **[SECTION]** formats
        text = re.sub(r"(\*\*|)?\[USER_STATE\].*?(?=\n(\*\*|)?\[|\Z)", "", text, flags=re.DOTALL)
        text = re.sub(r"(\*\*|)?\[NEW_FACTS\].*?(?=\n(\*\*|)?\[|\Z)", "", text, flags=re.DOTALL)

        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            clean = line.strip()
            if not clean: continue
            
            # 1. Skip Artifact Headers
            if clean.startswith("**Structuring") or clean.startswith("**STRUCTURED") or "LOGBOOK FORMAT" in clean:
                continue
            if clean.startswith("---") or clean.startswith("___"):
                continue
            
            # 2. Fix Markdown Headers [**TOPICS**] -> [TOPICS]
            clean = re.sub(r"\[\*\*(.*?)\*\*\]", r"[\1]", clean)
            
            # 3. Fix File-Path Handles (@user_profiles\name.json) -> (@name)
            # Matches: @user_profiles\name.json or @user_data\name.txt
            clean = re.sub(r"@user_profiles[\/\\]([\w.]+)\.json", r"@\1", clean)
            clean = re.sub(r"@user_data[\/\\]([\w.]+)\.txt", r"@\1", clean)
            
            cleaned_lines.append(clean)
            
        return '\n'.join(cleaned_lines).strip()

    def generate_response(self, user_name: str, message_text: str, context: str = "", trace_id: Optional[str] = None, trace_cb: Optional[Callable] = None) -> Generator[str, None, None]:
        if not self.local_llm and not self.client:
            yield "i have no brain rn (llm init failed)"
            return

        try:
            if user_name: user_name = self.replied_pattern.sub("", user_name).strip()
            if "replied to you" in (message_text or "").lower():
                clean_text = self.replied_pattern.split(message_text)[-1].strip()
            else:
                clean_text = (message_text or "").strip()

            context_msg = f"{user_name}: {clean_text}"
            self.update_history("user", context_msg)
            
            # --- RAG ---
            rag_context = ""
            if self.memory_db and clean_text:
                if trace_cb: trace_cb("rag_started")
                try:
                    # Generate embedding for the query
                    if trace_cb: trace_cb("rag_encoding_query")
                    vector = self.encoder.encode(clean_text, show_progress_bar=False).tolist()
                    
                    # 1. Broad Retrieval (Recall 25 candidates) - NOW SCOPED BY USER
                    if trace_cb: trace_cb("rag_retrieval")
                    structured_data = self.memory_db.recall_structured(vector, n_logs=1, n_facts=25, username=user_name)
                    
                    rag_parts = []
                    
                    # A. Relevant Logs (Raw History)
                    logs = structured_data.get("log_entries", [])
                    
                    if logs:
                        # Clean logs before injecting
                        cleaned_logs = [self._clean_log_content(l) for l in logs]
                        log_text = "\n\n".join(cleaned_logs)
                        rag_parts.append(f"--- RELEVANT HISTORY LOGS ---\n{log_text}")

                    # B. Facts (Rerank 25 down to 5)
                    candidate_facts = structured_data.get("facts", [])
                    unique_facts = []
                    
                    if candidate_facts:
                        # Rerank using Cross-Encoder
                        if trace_cb: trace_cb("rag_reranking")
                        pairs = [[clean_text, f] for f in candidate_facts]
                        scores = self.reranker.predict(pairs)
                        
                        # DEBUG: Print scores to tune threshold
                        print(f"   [RAG Debug] Candidates: {len(candidate_facts)}, Top Score: {max(scores) if len(scores) > 0 else 0}")
                        
                        # Sort by score (Descending)
                        ranked_facts = sorted(zip(scores, candidate_facts), key=lambda x: x[0], reverse=True)
                        
                        # Take top 5 regardless of absolute score (scores are logits)
                        filtered_facts = [f for score, f in ranked_facts][:10]
                        
                        # Deduplication against recent history
                        recent_text = " ".join([m["content"] for m in self.chat_history[-10:]]).lower()
                        unique_facts = [f for f in filtered_facts if f.lower() not in recent_text]
                    
                    self.last_rag_info = {
                        "logs": logs,
                        "facts": unique_facts
                    }
                    
                    if unique_facts:
                        fact_list = "\n".join([f"- {f}" for f in unique_facts])
                        rag_parts.append(f"--- VERIFIED FACTS ---\n{fact_list}")

                    if rag_parts:
                        rag_context = "\n\n".join(rag_parts)
                        print(f"   -> RAG: {len(logs)} Logs, {len(unique_facts)} Facts.")
                    
                    if trace_cb: trace_cb("rag_completed", {"facts_found": len(unique_facts)})
                        
                except Exception as e:
                    print(f"   [!] RAG Error: {e}")
                    if trace_cb: trace_cb("rag_error", {"error": str(e)})

            lore_context = self.get_lore_context(clean_text)

            # Capture granular debug data for UI
            self.last_rag_info = {
                "query": clean_text,
                "logs": structured_data.get("log_entries", []) if 'structured_data' in locals() else [],
                "facts": unique_facts if 'unique_facts' in locals() else [],
                "social": [],
                "lore": lore_context,
                "system": self.system_instruction
            }

            system_content_template = """
            {{ profile }}

            {% if rag %}
            ### CRITICAL MEMORY CONTEXT
            The following facts are verified history. You MUST align your response with them:
            {{ rag }}
            {% endif %}

            {% if lore %}[Grimoire/Slang Definitions:
            {{ lore }}]{% endif %}
            """
            
            sys_render = Template(system_content_template).render(
                profile=self.system_instruction,
                rag=rag_context,
                lore=lore_context
            )
            
            now_str = datetime.datetime.now().strftime("%I:%M %p")
            time_metadata = {"role": "system", "content": f"[System Note: Current Time is {now_str}]"}
            
            # Inject Reply Context if present
            extra_context = []
            if context:
                extra_context.append({"role": "system", "content": f"[Context: {context}]"})
            
            # Insert context before the latest message (which is at the end of chat_history)
            if self.chat_history:
                messages = [{"role": "system", "content": sys_render}] + self.chat_history[:-1] + extra_context + [self.chat_history[-1]] + [time_metadata]
            else:
                messages = [{"role": "system", "content": sys_render}] + extra_context + [time_metadata]

            # Debug Log
            prompt_log = ""
            for m in messages: prompt_log += f"[{m['role'].upper()}]: {m['content']}\n"
            self.last_prompt_log = prompt_log 

            # --- GENERATION ---
            if trace_cb: trace_cb("llm_call_started")
            start_gen_time = time.time()
            token_count = 0
            full_response = ""
            buffer = ""
            started = False
            
            stop_sequences = ["\n[", f"\n{self.bot_name}:", f"\n{self.bot_handle}:", "\nUser:", "\nAssistant:"]

            # GENERATOR SOURCE
            if config.USE_IN_PROCESS_LLM and self.local_llm:
                # Direct Binding
                stream = self.local_llm.create_chat_completion(
                    messages=messages,
                    max_tokens=config.MAX_TOKENS,
                    temperature=config.TEMPERATURE,
                    stream=True,
                    stop=stop_sequences
                )
            elif self.client:
                # Remote API
                stream = self.client.chat.completions.create(
                    model="local-model",
                    messages=messages,
                    max_tokens=config.MAX_TOKENS,
                    temperature=config.TEMPERATURE,
                    stream=True,
                    stop=stop_sequences
                )
            else:
                yield "Error: No Backend"
                return

            # STREAM PROCESSING
            for chunk in stream:
                if config.USE_IN_PROCESS_LLM:
                    # Llama-cpp-python structure
                    delta = chunk['choices'][0]['delta']
                    content = delta.get('content')
                else:
                    # OpenAI structure
                    content = chunk.choices[0].delta.content
                
                if not content: continue
                token_count += 1

                if not started:
                    if trace_cb: trace_cb("llm_first_token")
                    buffer += content
                    # Reduced buffer to 2 chars for instant response
                    if len(buffer) < 2 and ":" not in buffer and "\n" not in buffer and "]" not in buffer:
                        continue
                        
                    clean_buffer = self.prefix_pattern.sub("", buffer)
                    clean_buffer = self.hallucination_pattern.sub("", clean_buffer)
                    if clean_buffer != buffer: buffer = clean_buffer
                    
                    yield buffer
                    full_response += buffer
                    started = True
                else:
                    full_response += content
                    yield content
            
            if not started and buffer:
                 buffer = self.prefix_pattern.sub("", buffer)
                 yield buffer
                 full_response += buffer

            # METRICS
            duration = time.time() - start_gen_time
            if duration > 0: self.last_tps = token_count / duration
            if trace_cb: trace_cb("llm_generation_finished", {"tps": self.last_tps, "tokens": token_count})

            # CLEANUP HISTORY
            sanitized_response = self.prefix_pattern.sub("", full_response)
            sanitized_response = re.sub(r"^\s*\[(.*)\]\s*$", r"\1", sanitized_response.strip())
            self.update_history("assistant", sanitized_response)

        except Exception as e:
            logger.error(f"Generation Error: {e}")
            yield f"error: {e}"

    def __del__(self) -> None:
        if self.local_llm:
             del self.local_llm
             gc.collect()
