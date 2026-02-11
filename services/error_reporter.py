import os
import time
import json
import traceback

class ErrorReporter:
    def __init__(self, log_file: str = "error_log.jsonl"):
        self.log_file = log_file

    def report(self, error_msg: str, context: str = "General", notify_browser: bool = False) -> None:
        """
        Logs error to file and stdout.
        """
        # 1. Stdout
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\033[91m[ERROR] [{timestamp}] [{context}] {error_msg}\033[0m")
        
        # 2. File Log
        try:
            entry = {
                "timestamp": time.time(),
                "time_str": timestamp,
                "context": context,
                "error": error_msg,
                "trace": traceback.format_exc()
            }
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

error_reporter = ErrorReporter()
