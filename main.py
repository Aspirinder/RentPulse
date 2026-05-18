import asyncio
from playwright.async_api import async_playwright
from ScraperEngine import ScraperEngine
from websites.OLXParser import OLXParser
from websites.OTODOMParser import OTODOMParser

OLX_URL = "https://www.olx.pl/nieruchomosci/mieszkania/wynajem/poznan/?page=1&search%5Bfilter_enum_furniture%5D%5B0%5D=yes&search%5Bfilter_enum_rooms%5D%5B0%5D=two&search%5Bfilter_float_price%3Ato%5D=3000"
OTODOM_URL = "https://www.otodom.pl/pl/wyniki/wynajem/mieszkanie,2-pokoje/wielkopolskie/poznan/poznan/poznan?limit=36&priceMax=3000&by=DEFAULT&direction=DESC&page=1"
OLX_OUTPUT_FILE = "CSV/olx_offers_data.csv"
OTODOM_OUTPUT_FILE = "CSV/otodom_offers_data.csv"
LIMIT = 5

async def main():
    
    engine = ScraperEngine(output_file=OLX_OUTPUT_FILE)
    await engine.start_browser(headless=False)

    page_number = 16

    olx = OLXParser()
    otodom = OTODOMParser()
    
    while(True):
        
        found_count = await engine.run_parser(olx, olx.change_page(OLX_URL, page_number))

        if found_count == 0:
            print(f"✅ All pages processed. Finished at page {page_number - 1}.")
            break

        page_number += 1
    engine.save_to_csv()

    engine.output_file = OTODOM_OUTPUT_FILE
    engine.results = []
    page_number = 15

    while(True):

        found_count, content = await engine.run_parser(otodom, otodom.change_page(OTODOM_URL, page_number))

        can_go_next = await otodom.has_next_page(content)

        if found_count == 0 or not can_go_next:
            print(f"✅ All pages processed. Finished at page {page_number}.")
            break
        
        page_number += 1

    engine.save_to_csv()
    await engine.stop_browser()

if __name__ == "__main__":
    asyncio.run(main())