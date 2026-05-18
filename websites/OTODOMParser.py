from bs4 import BeautifulSoup
from BaseParser import BaseParser
import json
import re

class OTODOMParser(BaseParser):

    # Get title, price, date, link of all offers on search page
    async def parse_list(self, content):
        soup = BeautifulSoup(content, 'html.parser')
        offers =[]

        script_tag = soup.find('script', id='__NEXT_DATA__')
        if not script_tag:
            print("❌ No JSON data on Otodom")
            return []

        try:
            data = json.loads(script_tag.string)
            
            items = data.get('props', {}).get('pageProps', {}).get('data', {}).get('searchAds', {}).get('items', [])
                
            for item in items:
                slug = item.get('slug')
                if not slug: continue

                offers.append({
                    'Title': item.get('title', 'N/A'),
                    'Price': f"{item.get('totalPrice', {}).get('value', 'N/A')} {item.get('totalPrice', {}).get('currency', '')}",
                    'Date': item.get('pushedUpAt', 'N/A'),
                    'Link': f"https://www.otodom.pl/pl/oferta/{slug}"
                })

        except Exception as e:
            print(f"⚠️ Error parsing: {e}")

        return offers


    # Get images & description on offer page
    async def parse_details(self, html, offer):

        soup = BeautifulSoup(html, 'html.parser')
        
        script_tag = soup.find('script', id='__NEXT_DATA__')
        if script_tag:
            try:
                data = json.loads(script_tag.string)
                ad_data = data.get('props', {}).get('pageProps', {}).get('ad', {})
            
                if ad_data:
                    raw_description = ad_data.get('description', 'N/A')
                    if raw_description and raw_description != 'N/A':
                        clean_description = BeautifulSoup(raw_description, 'html.parser').get_text(separator=" ", strip=True)
                        offer['Description'] = " ".join(clean_description.split())
                    else:
                        offer['Description'] = 'N/A'
                    
                    characteristics = ad_data.get('characteristics', [])
                    characteristics_list = []

                    label_mapping = {
                        'rent': 'Czynsz',
                        'm': 'Powierzchnia',
                        'rooms_num': 'Liczba pokoi',
                        'floor_no': 'Piętro',
                        'deposit': 'Kaucja',
                        'ready_since': 'Dostępne od'
                    }

                    for c in characteristics:
                        key = c.get('key')
                        label = c.get('label')
                        value = c.get('localizedValue')

                        if label and label != "None":
                            display_label = label
                        elif key in label_mapping:
                            display_label = label_mapping[key]
                        else:
                            display_label = key if key else "Param"
                        
                        characteristics_list.append(f"{display_label}: {value}")

                    characteristics_text = " | ".join(characteristics_list)
                
                    features = ad_data.get('features', [])
                    features_text = ", ".join(features) if isinstance(features, list) else ""

                    created_at = ad_data.get('createdAt', 'N/A')
                    updated_at = ad_data.get('pushedUpAt')

                    if updated_at != None:
                        offer['Date'] = updated_at.split('T')[0]
                    else:
                        offer['Date'] = created_at.split('T')[0]

                    full_info = []
                    if characteristics_text: full_info.append(f"CHARACTERISTICS: {characteristics_text}")
                    if features_text: full_info.append(f"FEATURES: {features_text}")
                    if offer['Description']: full_info.append(f"DESCRIPTION: {offer['Description']}")
                
                    offer['Description'] = " ".join(full_info)
                
                    images = ad_data.get('images', [])
                    image_urls = [img.get('large') for img in images if img.get('large')]
                    if image_urls:
                        offer['Images'] = ", ".join(image_urls)
                
            except Exception as e:
                print(f"⚠️ JSON Error: {e}")
        return offer
    
    # Check if there is next page
    async def has_next_page(self, content):
        soup = BeautifulSoup(content, 'html.parser')
    
        next_button = soup.find('button', {'title': 'Go to next Page'})
    

        if not next_button:
            return False
    
        if next_button.has_attr('disabled'):
            return False
        
        return True
    

    def change_page(self ,url, number):
        new_url = re.sub(r'page=\d+', f'page={number}', url);
        return new_url