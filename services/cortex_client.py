import asyncio
import uuid
import multiprocessing
import queue
from typing import Any, Dict, Optional, Generator, Tuple, List
import consts
from services.event_bus import event_bus
from services.tracing import tracer

class CortexClient:
    def __init__(self, input_queue: multiprocessing.Queue, output_queue: multiprocessing.Queue):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.pending_requests: Dict[str, Any] = {}
        self.loop = asyncio.get_event_loop()

    def handle_response(self, msg: Dict[str, Any]):
        msg_type = msg.get("type")
        req_id = msg.get("req_id")

        if msg_type == consts.IPC_TRACE_EVENT:
            trace_id = msg.get("trace_id")
            event_name = msg.get("event")
            data = msg.get("data")
            if trace_id and event_name:
                tracer.log_event(trace_id, event_name, data)
        elif msg_type == consts.IPC_TOKEN:
            if req_id in self.pending_requests:
                asyncio.run_coroutine_threadsafe(
                    self.pending_requests[req_id]["queue"].put(msg["content"]),
                    self.loop
                )
        elif msg_type == consts.IPC_META:
            # Broadcast debug info globally
            asyncio.run_coroutine_threadsafe(
                event_bus.emit("cortex_meta", msg),
                self.loop
            )
        elif msg_type == consts.IPC_GEN_COMPLETE:
            if req_id in self.pending_requests:
                asyncio.run_coroutine_threadsafe(
                    self.pending_requests[req_id]["queue"].put(None),
                    self.loop
                )
        elif msg_type == consts.IPC_ENGAGEMENT_RESULT:
            if req_id in self.pending_requests:
                fut = self.pending_requests[req_id]["future"]
                if not fut.done():
                    self.loop.call_soon_threadsafe(
                        fut.set_result, (msg["should_reply"], msg["reason"])
                    )
        elif msg_type == consts.IPC_DATA_RESPONSE:
            if req_id in self.pending_requests:
                fut = self.pending_requests[req_id]["future"]
                if not fut.done():
                    self.loop.call_soon_threadsafe(
                        fut.set_result, msg["data"]
                    )
        elif msg_type == consts.IPC_HEARTBEAT_ACK:
            if req_id in self.pending_requests:
                fut = self.pending_requests[req_id]["future"]
                if not fut.done():
                    self.loop.call_soon_threadsafe(
                        fut.set_result, True
                    )

    async def ping(self, timeout: float = 5.0) -> bool:
        req_id = str(uuid.uuid4())
        fut = self.loop.create_future()
        self.pending_requests[req_id] = {"type": "heartbeat", "future": fut}
        
        self.input_queue.put({"type": consts.IPC_HEARTBEAT, "id": req_id})
        
        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            return False
        finally:
            if req_id in self.pending_requests:
                del self.pending_requests[req_id]

    async def ask_data(self, msg_type: str, timeout: float = 5.0, **kwargs) -> Any:
        req_id = str(uuid.uuid4())
        fut = self.loop.create_future()
        self.pending_requests[req_id] = {"type": "data_request", "future": fut}
        
        payload = {"type": msg_type, "id": req_id}
        payload.update(kwargs)
        self.input_queue.put(payload)
        
        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            if req_id in self.pending_requests:
                del self.pending_requests[req_id]

    async def ask_engagement(self, sender: str, text: str, trace_id: Optional[str] = None) -> Tuple[bool, str]:
        req_id = str(uuid.uuid4())
        fut = self.loop.create_future()
        self.pending_requests[req_id] = {"type": "engagement", "future": fut}
        
        self.input_queue.put({
            "type": consts.IPC_ENGAGEMENT,
            "id": req_id,
            "sender": sender,
            "text": text,
            "trace_id": trace_id
        })
        
        try:
            return await asyncio.wait_for(fut, timeout=10.0)
        except asyncio.TimeoutError:
            return False, "Timeout"
        finally:
            if req_id in self.pending_requests:
                del self.pending_requests[req_id]

    async def generate(self, sender: str, text: str, context: str = "", trace_id: Optional[str] = None) -> Generator[str, None, None]:
        req_id = str(uuid.uuid4())
        q = asyncio.Queue()
        self.pending_requests[req_id] = {"type": "generation", "queue": q}
        
        self.input_queue.put({
            "type": consts.IPC_GENERATE,
            "id": req_id,
            "sender": sender,
            "text": text,
            "context": context,
            "trace_id": trace_id
        })
        
        async def gen():
            while True:
                token = await q.get()
                if token is None:
                    break
                yield token
            if req_id in self.pending_requests:
                del self.pending_requests[req_id]
                
        return gen()

    def send_command(self, cmd: str, args: Any = None):
        self.input_queue.put({
            "type": consts.IPC_COMMAND,
            "cmd": cmd,
            "args": args
        })

    def update_history(self, role: str, content: str):
        self.input_queue.put({
            "type": consts.IPC_UPDATE_HISTORY,
            "role": role,
            "content": content
        })

    def add_memory(self, text: str, source: str = "unknown", user: str = "unknown"):
        self.input_queue.put({
            "type": consts.IPC_ADD_MEMORY,
            "text": text,
            "source": source,
            "user": user
        })

    def analyze_batch(self, text_block: str, users: list = None):
        self.input_queue.put({
            "type": consts.IPC_ANALYZE_BATCH,
            "text": text_block,
            "users": users or []
        })

    async def get_facts_by_user(self, username: str) -> List[str]:
        return await self.ask_data(consts.IPC_GET_FACTS_BY_USER, username=username)
