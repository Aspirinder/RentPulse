from bs4 import BeautifulSoup
from BaseParser import BaseParser
import re

class OLXParser(BaseParser):

    # Get title, price, date, link of all offers on search page
    async def parse_list(self, content):
        soup = BeautifulSoup(content, 'html.parser')
        cards = soup.find_all('div', {'data-cy': 'l-card'})
        offers = []

        for card in cards:
            try:
                link_el = card.find('a')
                raw_link = link_el['href']
                full_link = raw_link if raw_link.startswith('http') else "https://www.olx.pl" + raw_link
                
                loc_el = card.find('p', {'data-testid': 'location-date'})
                loc_text = loc_el.text.strip() if loc_el else ""

                
                item = ({
                    'Title': card.find('h4').text.strip() if card.find('h4') else "N/A",
                    'Price': card.find('p', {'data-testid': 'ad-price'}).text.strip(),
                    'Date': loc_text.split(' - ')[1] if ' - ' in loc_text else "N/A",
                    'Link': full_link
                })

                if "olx.pl" in full_link:
                    offers.append(item)
            except Exception as e:
                print(f"⚠️ Error parsing: {e}")
        return offers


    # Get images & description on offer page
    async def parse_details(self, html, offer):

        soup = BeautifulSoup(html, 'html.parser')

        try:
            desc_div = soup.find('div', {'data-cy': 'ad_description'})
            offer['Description'] = " ".join(desc_div.get_text(separator=" ", strip=True).split()) if desc_div else "N/A"
            

            img_elements = soup.select('div[data-testid="ad-photo"] img')
            image_urls = []
            for img in img_elements:
                src = img.get('src') or img.get('data-src')
    
                if src and 'http' in src:
                    clean_src = src.split(';')[0] 
                    image_urls.append(clean_src)
                
                offer['Images'] = list(set(image_urls))
            
        except Exception as e:
            print(f"❌ Error on {offer['Link']}: {e}")
        return offer
    
    
    def change_page(self, url, number):
        new_url = re.sub(r'page=\d+', f'page={number}', url);
        return new_url