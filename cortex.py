import multiprocessing
import time
import sys
import traceback
import queue
import signal
import threading
from typing import Optional, Dict, Any, Callable

# Local imports
import config
import consts
from ai import FernAI

class CortexProcess(multiprocessing.Process):
    def __init__(self, input_queue: multiprocessing.Queue, output_queue: multiprocessing.Queue) -> None:
        super().__init__()
        self.input_queue: multiprocessing.Queue = input_queue
        self.output_queue: multiprocessing.Queue = output_queue
        self.ai: Optional[FernAI] = None
        self.running: bool = True
        self.handlers: Dict[str, Callable] = {}

    def _register_handlers(self) -> None:
        self.handlers = {
            consts.IPC_SHUTDOWN: self.handle_shutdown,
            consts.IPC_GENERATE: self.handle_generation,
            consts.IPC_ENGAGEMENT: self.handle_engagement,
            consts.IPC_ADD_MEMORY: self.handle_add_memory,
            consts.IPC_ANALYZE_BATCH: self.handle_analyze_batch,
            consts.IPC_GET_RANDOM_MEMS: self.handle_get_random_memories,
            consts.IPC_GET_RANDOM_LOGS: self.handle_get_random_logs,
            consts.IPC_GET_HISTORY_STATS: self.handle_get_history_stats,
            consts.IPC_GET_CHAT_HISTORY: self.handle_get_chat_history,
            consts.IPC_GET_ALL_MEMORIES: self.handle_get_all_memories,
            consts.IPC_GET_MEMORY_GRAPH: self.handle_get_memory_graph,
            consts.IPC_GET_FACTS_BY_USER: self.handle_get_facts_by_user,
            consts.IPC_DELETE_MEMORY: self.handle_delete_memory,
            consts.IPC_UPDATE_HISTORY: self.handle_update_history,
            consts.IPC_COMMAND: self.handle_command,
            consts.IPC_HEARTBEAT: self.handle_heartbeat
        }

    def run(self) -> None:
        """Main loop of the Cortex process."""
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        
        print("Initializing AI Core...")
        self._register_handlers()
        
        try:
            self.ai = FernAI()
            self.output_queue.put({"type": consts.IPC_INIT_COMPLETE, "success": True})
        except Exception as e:
            print(f"Critical Init Error: {e}")
            traceback.print_exc()
            self.output_queue.put({"type": consts.IPC_INIT_COMPLETE, "success": False, "error": str(e)})
            return

        print("AI Core Online. Waiting for signals...")

        try:
            while self.running:
                try:
                    task: Dict[str, Any] = self.input_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                try:
                    msg_type = task.get("type")
                    handler = self.handlers.get(msg_type)
                    
                    if handler:
                        handler(task)
                    else:
                        print(f"[Cortex] Unknown IPC Message: {msg_type}")
                        
                except Exception as e:
                    print(f"Task Error: {e}")
                    traceback.print_exc()
                    try: self.output_queue.put({"type": consts.IPC_ERROR, "error": str(e)})
                    except: pass

        finally:
            if self.ai:
                self.ai.stop_server()
            
            try:
                self.input_queue.close()
                self.output_queue.close()
            except: pass
            
            print("Process Exited.")

    # --- HANDLERS ---

    def handle_shutdown(self, task: Dict[str, Any]) -> None:
        self.running = False
        print("Shutting down...")

    def handle_heartbeat(self, task: Dict[str, Any]) -> None:
        self.output_queue.put({
            "type": consts.IPC_HEARTBEAT_ACK, 
            "req_id": task.get("id")
        })

    def handle_generation(self, task: Dict[str, Any]) -> None:
        # Offload blocking generation to a thread so Heartbeats still process
        t = threading.Thread(target=self._run_generation, args=(task,))
        t.start()

    def _run_generation(self, task: Dict[str, Any]) -> None:
        sender = task.get("sender", "Unknown")
        text = task.get("text", "")
        context = task.get("context", "")
        req_id = task.get("id")
        trace_id = task.get("trace_id")
        
        if context:
            print(f"\033[90m   [Cortex] Context Aware: {context[:30]}...\033[0m")
        
        if not self.ai: return

        # Callback to pipe trace events back to main process
        def trace_cb(name, data=None):
            if trace_id:
                self.output_queue.put({
                    "type": consts.IPC_TRACE_EVENT,
                    "trace_id": trace_id,
                    "event": name,
                    "data": data or {}
                })

        try:
            gen = self.ai.generate_response(sender, text, context=context, trace_id=trace_id, trace_cb=trace_cb)
            
            for token in gen:
                if not self.running: break
                self.output_queue.put({
                    "type": consts.IPC_TOKEN,
                    "req_id": req_id,
                    "content": token
                })
                
            self.output_queue.put({
                "type": consts.IPC_META,
                "req_id": req_id,
                "trace_id": trace_id,
                "tps": getattr(self.ai, "last_tps", 0),
                "mem_usage": getattr(self.ai, "current_mem_usage", "0/0"),
                "prompt_log": getattr(self.ai, "last_prompt_log", ""),
                "rag_info": getattr(self.ai, "last_rag_info", {})
            })

            self.output_queue.put({
                "type": consts.IPC_GEN_COMPLETE,
                "req_id": req_id
            })
        except Exception as e:
            print(f"[Cortex] Generation Error: {e}")
            self.output_queue.put({"type": consts.IPC_ERROR, "error": str(e)})

    def handle_engagement(self, task: Dict[str, Any]) -> None:
        sender = task.get("sender", "Unknown")
        text = task.get("text", "")
        req_id = task.get("id")
        trace_id = task.get("trace_id")
        
        if not self.ai: return

        # Callback to pipe trace events back to main process
        def trace_cb(name, data=None):
            if trace_id:
                self.output_queue.put({
                    "type": consts.IPC_TRACE_EVENT,
                    "trace_id": trace_id,
                    "event": name,
                    "data": data or {}
                })

        should_reply, reason = self.ai.analyze_engagement(sender, text, trace_id=trace_id, trace_cb=trace_cb)
        
        self.output_queue.put({
            "type": consts.IPC_ENGAGEMENT_RESULT,
            "req_id": req_id,
            "trace_id": trace_id,
            "should_reply": should_reply,
            "reason": reason
        })

    def handle_add_memory(self, task: Dict[str, Any]) -> None:
        text = task.get("text", "")
        source = task.get("source", "unknown")
        user = task.get("user", "unknown")
        
        if self.ai and self.ai.memory_db and text:
            vector = self.ai.encoder.encode(text, show_progress_bar=False).tolist()
            self.ai.memory_db.add_memory(text, vector, source, user)

    def handle_analyze_batch(self, task: Dict[str, Any]) -> None:
        text_block = task.get("text", "")
        users = task.get("users", [])
        if self.ai and text_block:
            result = self.ai.analyze_batch(text_block)
            facts = result.get("facts", [])
            for fact in facts:
                fact_user = "system"
                fact_lower = fact.lower()
                for u in users:
                    if u.lower() in fact_lower:
                        fact_user = u
                        break
                vec = self.ai.encoder.encode(fact, show_progress_bar=False).tolist()
                self.ai.memory_db.add_memory(fact, vec, source="strict_fact", username=fact_user)
            print(f"   [Cortex] Batch Analyzed: {len(facts)} facts extracted.")

    def handle_get_random_memories(self, task: Dict[str, Any]) -> None:
        n = task.get("n", 3)
        req_id = task.get("id")
        memories = []
        if self.ai and self.ai.memory_db:
            try:
                raw_docs = self.ai.memory_db.get_random(n)
                if raw_docs and isinstance(raw_docs[0], list):
                    memories = raw_docs[0]
                else:
                    memories = raw_docs
            except Exception: pass
        self.output_queue.put({"type": consts.IPC_DATA_RESPONSE, "req_id": req_id, "data": memories})

    def handle_get_random_logs(self, task: Dict[str, Any]) -> None:
        n = task.get("n", 3)
        req_id = task.get("id")
        logs = []
        if self.ai and self.ai.memory_db:
            try: logs = self.ai.memory_db.get_random_logs(n)
            except Exception: pass
        self.output_queue.put({"type": consts.IPC_DATA_RESPONSE, "req_id": req_id, "data": logs})

    def handle_get_history_stats(self, task: Dict[str, Any]) -> None:
        req_id = task.get("id")
        if not self.ai: return
        history = self.ai.chat_history
        count = len(history)
        total_chars = sum(len(m["content"]) for m in history)
        self.output_queue.put({
            "type": consts.IPC_DATA_RESPONSE,
            "req_id": req_id,
            "data": {
                "msg_count": count,
                "char_count": total_chars,
                "history_preview": history[-10:] if count > 0 else [],
                "mem_usage": getattr(self.ai, "current_mem_usage", "0/0")
            }
        })

    def handle_get_chat_history(self, task: Dict[str, Any]) -> None:
        req_id = task.get("id")
        limit = task.get("limit", 100)
        if not self.ai: return
        self.output_queue.put({
            "type": consts.IPC_DATA_RESPONSE,
            "req_id": req_id,
            "data": {"history": self.ai.chat_history[-limit:]}
        })

    def handle_get_all_memories(self, task: Dict[str, Any]) -> None:
        req_id = task.get("id")
        memories = []
        if self.ai and self.ai.memory_db:
            try: memories = self.ai.memory_db.get_all()
            except Exception: pass
        self.output_queue.put({"type": consts.IPC_DATA_RESPONSE, "req_id": req_id, "data": {"memories": memories}})

    def handle_get_memory_graph(self, task: Dict[str, Any]) -> None:
        req_id = task.get("id")
        data = {}
        if self.ai and self.ai.memory_db:
            try: data = self.ai.memory_db.get_all_embeddings()
            except Exception: pass
        self.output_queue.put({"type": consts.IPC_DATA_RESPONSE, "req_id": req_id, "data": data})

    def handle_get_facts_by_user(self, task: Dict[str, Any]) -> None:
        req_id = task.get("id")
        username = task.get("username", "")
        facts = []
        if self.ai and self.ai.memory_db and username:
            try: facts = self.ai.memory_db.get_facts_by_user(username)
            except Exception: pass
        self.output_queue.put({"type": consts.IPC_DATA_RESPONSE, "req_id": req_id, "data": facts})

    def handle_delete_memory(self, task: Dict[str, Any]) -> None:
        mem_id = task.get("mem_id")
        if self.ai and self.ai.memory_db and mem_id:
            try: self.ai.memory_db.delete(mem_id)
            except Exception: pass

    def handle_update_history(self, task: Dict[str, Any]) -> None:
        role = task.get("role", "system")
        content = task.get("content", "")
        if self.ai:
            self.ai.update_history(role, content)
            self.output_queue.put({
                "type": consts.IPC_META,
                "req_id": None,
                "tps": getattr(self.ai, "last_tps", 0),
                "mem_usage": getattr(self.ai, "current_mem_usage", "0/0"),
                "prompt_log": getattr(self.ai, "last_prompt_log", "")
            })

    def handle_command(self, task: Dict[str, Any]) -> None:
        cmd = task.get("cmd")
        args = task.get("args")
        if not self.ai: return
        if cmd == "clearmem": self.ai.clear_memory()
        elif cmd == "flush_facts": self.ai.flush_facts()
        elif cmd == "sleep": self.ai.stop_server()
        elif cmd == "wake": self.ai.start_server()
        elif cmd == "set_profile":
            if args:
                self.ai.system_instruction = args
                print(f"System Prompt Updated.")
