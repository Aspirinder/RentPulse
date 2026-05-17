import asyncio
import pandas as pd
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

class OLXParser:
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


    async def stop_browser(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("🛑 Browser stop")

    #Get title, price, date, link of all offers on search page
    async def get_main_page_data(self, url):
        page = await self.context.new_page()
        print(f"🔎 Open page...")
        await page.goto(url, wait_until="networkidle")
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        cards = soup.find_all('div', {'data-cy': 'l-card'})
        
        extracted_data = []
        for card in cards:
            try:
                title_container = card.find('div', {'data-testid': 'ad-card-title'})
                if not title_container: continue
                
                link_el = title_container.find('a')
                href = link_el['href']
                link = href if href.startswith('http') else "https://www.olx.pl" + href
                
                loc_el = card.find('p', {'data-testid': 'location-date'})
                loc_text = loc_el.text.strip() if loc_el else ""
                
                extracted_data.append({
                    'Title': link_el.find('h4').text.strip(),
                    'Price': card.find('p', {'data-testid': 'ad-price'}).text.strip(),
                    'Date': loc_text.split(' - ')[1] if ' - ' in loc_text else "N/A",
                    'Link': link
                })
            except Exception as e:
                print(f"⚠️ Error parsing: {e}")
        
        await page.close()
        return extracted_data

    #Get images & description on offer page
    async def fetch_details(self, offer):
        page = await self.context.new_page()
        try:
            print(f"📖 Open: {offer['Title'][:30]}...")
            await page.goto(offer['Link'], wait_until="domcontentloaded")
            await asyncio.sleep(1)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            

            desc_div = soup.find('div', {'data-cy': 'ad_description'})
            offer['Description'] = " ".join(desc_div.get_text(separator=" ", strip=True).split()) if desc_div else "N/A"
            

            img_elements = soup.select('div[data-testid="ad-photo"] img')
            image_urls = []
            for img in img_elements:
                src = img.get('src') or img.get('data-src')
    
                if src and 'http' in src:
                    clean_src = src.split(';')[0] 
                    image_urls.append(clean_src)
                    offer['Images'] = ", ".join(list(set(image_urls)))
            
        except Exception as e:
            print(f"❌ Error on {offer['Link']}: {e}")
        finally:
            await page.close()
        return offer

    def save_to_csv(self):
        if self.results:
            df = pd.DataFrame(self.results)
            df.to_csv(self.output_file, index=False, sep=';', encoding='utf-8-sig')
            print(f"✅ Data saves: {self.output_file}")