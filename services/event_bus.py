import asyncio
from typing import Any, Callable, Dict, List, Coroutine, Tuple

class EventBus:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            # listeners[event_name] = List[Tuple[priority, callback]]
            cls._instance.listeners = {}
            cls._instance.error_handler = None
        return cls._instance

    def set_error_handler(self, handler: Callable[..., Coroutine[Any, Any, Any]]):
        self.error_handler = handler

    def subscribe(self, event_name: str, callback: Callable[..., Coroutine[Any, Any, Any]], priority: int = 50):
        if event_name not in self.listeners:
            self.listeners[event_name] = []
        self.listeners[event_name].append((priority, callback))
        # Sort by priority descending (higher priority first)
        self.listeners[event_name].sort(key=lambda x: x[0], reverse=True)

    async def emit(self, event_name: str, *args, **kwargs) -> List[Any]:
        results = []
        if event_name in self.listeners:
            for priority, callback in self.listeners[event_name]:
                try:
                    res = await callback(*args, **kwargs)
                    results.append(res)
                    # If any handler returns False, we stop propagation (event consumed)
                    if res is False:
                        break
                except Exception as e:
                    print(f"   [!] Event Error ({event_name} @ {priority}): {e}")
                    if self.error_handler:
                        try: await self.error_handler(f"Event Error ({event_name}): {e}")
                        except: pass
                    results.append(e)
        return results

# Singleton
event_bus = EventBus()

# Singleton
event_bus = EventBus()
