from playwright.async_api import async_playwright
from playwright_stealth import Stealth


class BrowserManager:
    def __init__(self):
        self.stealth = None
        self.playwright = None
        self.context = None

    async def start(self):
        self.stealth = Stealth()
        self.playwright_cm = self.stealth.use_async(async_playwright())
        self.playwright = await self.playwright_cm.__aenter__()

        self.context = await self.playwright.chromium.launch_persistent_context(
            "./user_data",
            headless=False,
            viewport={"width": 1920, "height": 1080},
        )

    async def newPage(self):
        return await self.context.new_page()

    async def close(self):
        await self.context.close()
        await self.playwright.stop()
