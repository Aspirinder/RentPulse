import asyncio
from bs4 import BeautifulSoup
import pandas as pd
from playwright.async_api import async_playwright
from OLXParser import OLXParser

BASE_URL = "https://www.olx.pl/nieruchomosci/mieszkania/wynajem/poznan/?page=1&search%5Bfilter_enum_furniture%5D%5B0%5D=yes&search%5Bfilter_enum_rooms%5D%5B0%5D=two&search%5Bfilter_float_price%3Ato%5D=3000"
OUTPUT_FILE = "olx_offers_data.csv"
LIMIT = 5

async def main():
    
    parser = OLXParser(output_file=OUTPUT_FILE)
    
    try:
        await parser.start_browser(headless=False)

        for i in range(1, 17):
            # Get info about offers on search page
            corrent_url = BASE_URL.replace("page=1", f"page={i}")

            offers = await parser.get_main_page_data(corrent_url)
        
            # Open every offer and get data
            for offer in offers:
                offer_datails = await parser.fetch_details(offer)
                parser.results.append(offer_datails)

        
        parser.save_to_csv()
        
    finally:
        await parser.stop_browser()

if __name__ == "__main__":
    asyncio.run(main())