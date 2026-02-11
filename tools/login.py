import asyncio
from playwright.async_api import async_playwright

OUTPUT_FILE = "state.json"

async def main():
    async with async_playwright() as p:
        print("Launching browser...")
        # Headless=False so you can see the window and type your password
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print("Navigating to Instagram...")
        await page.goto("https://www.instagram.com/")

        print("\n" + "="*50)
        print("ACTION REQUIRED: ")
        print("1. Go to the browser window.")
        print("2. Log in to Instagram manually.")
        print("3. Wait until your Feed or Inbox is fully loaded.")
        print("4. Come back here and PRESS ENTER to save the session.")
        print("="*50 + "\n")

        # Wait for user to tell us they are done
        input(">>> Press ENTER when you are logged in...")

        # Save the state (cookies, local storage, etc.)
        await context.storage_state(path=OUTPUT_FILE)
        
        print(f"\nSUCCESS: Session saved to '{OUTPUT_FILE}'")
        print("You can now run the bot script.")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())