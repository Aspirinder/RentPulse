import pandas as pd
from playwright.async_api import async_playwright
from BaseParser import BaseParser
import asyncio

class ScraperEngine:
    def __init__(self, output_file="results.csv"):
        self.output_file = output_file
        self.results = []
        self.browser = None
        self.context = None
        self.playwright = None


    async def start_browser(self, headless=False):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        print("🚀 Browser start")


    async def run_parser(self, parser: BaseParser, start_url):
        page = await self.context.new_page()
        print(f"🔎 Scanning: {start_url}")

        await page.goto(start_url, wait_until="networkidle")
        content = await page.content()

        basic_offers = await parser.parse_list(content)

        if not basic_offers:
            return 0
        
        for offer in basic_offers:
            print(f"  -> Opening details: {offer['Title'][:30]}")
            await page.goto(offer['Link'], wait_until="domcontentloaded")
            await asyncio.sleep(1)

            detail_content = await page.content()
            details = await parser.parse_details(detail_content, offer)

            self.results.append({**offer, **details})
            i+=1

        await page.close()

        return len(basic_offers), content


    async def stop_browser(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("🛑 Browser stop")


    def save_to_csv(self):
        if self.results:
            df = pd.DataFrame(self.results)
            df.to_csv(self.output_file, index=False, sep=';', encoding='utf-8-sig')
            print(f"✅ Data saves: {self.output_file}")