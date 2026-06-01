import asyncio
from ScraperEngine import ScraperEngine
from websites.OLXParser import OLXParser
from websites.OTODOMParser import OTODOMParser
import time

OLX_URL = "https://www.olx.pl/nieruchomosci/mieszkania/wynajem/poznan/?page=1&search%5Bfilter_enum_furniture%5D%5B0%5D=yes&search%5Bfilter_enum_rooms%5D%5B0%5D=two&search%5Bfilter_float_price%3Ato%5D=3000"
OTODOM_URL = "https://www.otodom.pl/pl/wyniki/wynajem/mieszkanie,2-pokoje/wielkopolskie/poznan/poznan/poznan?limit=36&priceMax=3000&by=DEFAULT&direction=DESC&page=1"
OLX_OUTPUT_FILE = "CSV/olx_offers_data.csv"
OTODOM_OUTPUT_FILE = "CSV/otodom_offers_data.csv"
LIMIT = 5

async def main():
    
    engine = ScraperEngine()
    await engine.start_browser(headless=False)

    start_time = time.perf_counter()

    olx = OLXParser()
    otodom = OTODOMParser()
    
    await olx.start_parse(engine, OLX_URL, OLX_OUTPUT_FILE, page_number=1)

    await otodom.start_parse(engine, OTODOM_URL, OTODOM_OUTPUT_FILE, page_number=1)

    await engine.stop_browser()

    end_time = time.perf_counter()
    total_time = end_time - start_time

    print(f"Browser stop. Time: {int(total_time // 60)}:{int(total_time % 60)}")

if __name__ == "__main__":
    asyncio.run(main())