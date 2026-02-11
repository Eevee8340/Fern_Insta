import asyncio
from playwright.async_api import async_playwright, Page, BrowserContext, Browser
import config
import os
import json

class BrowserManager:
    def __init__(self):
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self.current_url = config.DIRECT_LINK
        
        # Load persistence
        if os.path.exists("session_state.json"):
            try:
                with open("session_state.json", "r") as f:
                    data = json.load(f)
                    self.current_url = data.get("last_direct_link", config.DIRECT_LINK)
            except: pass

    async def launch(self):
        print("1. Launching Browser (Async)...")
        p = await async_playwright().start()
        
        self.browser = await p.chromium.launch(
            headless=config.HEADLESS, 
            slow_mo=config.BROWSER_SLOW_MO
        )

        try:
            self.context = await self.browser.new_context(
                storage_state=config.STATE_FILE,
                user_agent=config.USER_AGENT,
            )
        except FileNotFoundError:
            print(f"No {config.STATE_FILE} found. Please login first.")
            raise

        self.page = await self.context.new_page()
        print(f"   [+] Resuming last thread: {self.current_url}")
        await self.page.goto(self.current_url)
        return self.page

    async def handle_popups(self):
        print("4. Handling popups...")
        try:
            not_now = self.page.locator('button:has-text("Not Now")')
            if await not_now.count() > 0:
                await not_now.click(timeout=2000)
        except Exception as e:
            # Safe to ignore timeout here
            pass

    async def switch_thread(self, thread_id):
        new_url = f"https://www.instagram.com/direct/t/{thread_id}/"
        print(f"Switching thread to: {new_url}")
        try:
            await self.page.goto(new_url)
            self.current_url = new_url
            
            # Persist
            with open("session_state.json", "w") as f:
                json.dump({"last_direct_link": new_url}, f)
                
            return True
        except Exception as e:
            print(f"   [!] Navigation error: {e}")
            return False

    async def close(self):
        try:
            if self.context: await self.context.close()
        except: pass
        try:
            if self.browser: await self.browser.close()
        except: pass
