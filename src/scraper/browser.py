from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import asyncio


class BrowserManager:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(5)
        self.detailsLock = asyncio.Lock()
        self.stealth = None
        self.playwright = None
        self.context = None

    async def start(self, headless=True):
        self.stealth = Stealth()
        self.playwright_cm = self.stealth.use_async(async_playwright())
        self.playwright = await self.playwright_cm.__aenter__()

        self.context = await self.playwright.chromium.launch_persistent_context(
            "./user_data",
            headless=headless,
            viewport={"width": 1920, "height": 1080},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",  # Evita crashes em containers/Linux
            ],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        )

    async def newPage(self):
        return await self.context.new_page()

    async def close(self):
        await self.context.close()
        await self.playwright.stop()


async def main():
    browser = BrowserManager()
    await browser.start(headless=False)
    await browser.newPage()
    await asyncio.sleep(5000)


if __name__ == "__main__":
    asyncio.run(main())
