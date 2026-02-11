import time
import uuid
import json
from typing import Dict, Any, List, Optional
from collections import deque

class TracingService:
    def __init__(self, log_file: str = "trace_logs.jsonl", max_history: int = 100):
        self.log_file = log_file
        self.active_traces: Dict[str, Dict[str, Any]] = {}
        self.history = deque(maxlen=max_history)

    def start_trace(self, source: str, metadata: Optional[Dict] = None) -> str:
        trace_id = str(uuid.uuid4())[:8] # Short ID for readability
        self.active_traces[trace_id] = {
            "trace_id": trace_id,
            "start_time": time.time(),
            "start_perf": time.perf_counter(),
            "source": source,
            "events": [],
            "metadata": metadata or {}
        }
        self.log_event(trace_id, "trace_started")
        return trace_id

    def log_event(self, trace_id: str, event_name: str, data: Optional[Dict] = None):
        if not trace_id or trace_id not in self.active_traces:
            return
        
        perf_now = time.perf_counter()
        start_perf = self.active_traces[trace_id]["start_perf"]
        
        # Calculate delta from last event using perf_counter
        last_perf = start_perf
        if self.active_traces[trace_id]["events"]:
            last_perf = self.active_traces[trace_id]["events"][-1]["perf_ts"]
        
        step_delta = perf_now - last_perf
        elapsed = perf_now - start_perf
        
        event = {
            "event": event_name,
            "timestamp": time.time(),
            "perf_ts": perf_now,
            "elapsed": elapsed,
            "delta": step_delta,
            "data": data or {}
        }
        self.active_traces[trace_id]["events"].append(event)

    def add_metadata(self, trace_id: str, key: str, value: Any):
        if not trace_id or trace_id not in self.active_traces:
            return
        self.active_traces[trace_id]["metadata"][key] = value

    def end_trace(self, trace_id: str):
        if trace_id not in self.active_traces:
            return
        
        trace_data = self.active_traces.pop(trace_id)
        trace_data["total_duration"] = time.perf_counter() - trace_data["start_perf"]
        
        # Add to memory history
        self.history.append(trace_data)
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(trace_data) + "\n")
        except Exception as e:
            print(f"Tracing Write Error: {e}")

    def get_history(self) -> List[Dict]:
        return list(self.history)

tracer = TracingService()
