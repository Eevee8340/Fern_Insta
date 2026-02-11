import json
import time
import asyncio
from typing import Optional, Dict, Any, Callable
from playwright.async_api import Page, Route, Request as PlaywrightRequest

class Colors:
    GREEN = "\033[92m"
    ENDC = "\033[0m"

class NetworkObserver:
    def __init__(self, log_callback: Callable[[str], None] = None):
        self.captured_app_id: Optional[str] = None
        self.current_thread_id: Optional[str] = None
        self.last_network_activity: float = time.time()
        self.last_fetch_time: float = 0.0
        self.log = log_callback if log_callback else self._default_log
        self.page: Optional[Page] = None

    async def _default_log(self, text: str) -> None:
        print(text)

    def attach_page(self, page: Page) -> None:
        self.page = page

    async def capture_headers(self, route: Route, request: PlaywrightRequest) -> None:
        if not self.captured_app_id:
            headers = request.headers
            if "x-ig-app-id" in headers:
                self.captured_app_id = headers["x-ig-app-id"]
                await self.log(f"{Colors.GREEN}[Network] App ID Captured: {self.captured_app_id}{Colors.ENDC}")
        await route.continue_()

    async def fetch_latest_message_secure(self) -> Optional[Dict[str, Any]]:
        if not self.captured_app_id or not self.current_thread_id or not self.page:
            return None
        
        try:
            js_code = f"""
                async () => {{
                    try {{
                        const response = await fetch(
                            "https://www.instagram.com/api/v1/direct_v2/threads/{self.current_thread_id}/",
                            {{ headers: {{ "x-ig-app-id": "{self.captured_app_id}" }} }}
                        );
                        if (response.status !== 200) return {{ "error": response.status }};
                        return await response.json();
                    }} catch (e) {{ 
                        return {{ "error": e.toString() }}; 
                    }}
                }}
            """
            result = await self.page.evaluate(js_code)
            if isinstance(result, dict) and "error" in result:
                return None
            
            self.last_network_activity = time.time()
            return result
        except Exception:
            return None
