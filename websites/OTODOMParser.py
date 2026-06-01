from bs4 import BeautifulSoup
from BaseParser import BaseParser
import json
import re

class OTODOMParser(BaseParser):

    # Orchestrates the multi-page parsing lifecycle specific to Otodom's data architecture
    async def start_parse(self, engine, url, output, page_number):
         
        # Execute an initial baseline request to fetch the raw script data and establish page parameters
        _, content = await engine.run_parser(self, self.change_page(url, page_number))

        # Dynamically extract total available pages from the internal Next.js state payload
        max_page_number = await self.get_total_pages(content)
        print(f"Found max pages: {max_page_number}")
        
        # Iterate sequentially up to and including the absolute upper bound page index
        for page_number in range(page_number, max_page_number + 1):
            _, _ = await engine.run_parser(self, self.change_page(url, page_number))

        # Logging parsing sequence completion parameters
        print(f"Stop parse OTODOM. Parse pages: {page_number}\n")
        
        # Point the scraper engine file targets to the requested output path
        engine.output_file = output
        engine.save_to_csv()
        
        # Flush the runtime results cache array memory to prevent cross-contamination
        engine.results = []

    # Extracts basic item listings natively out of the Next.js hydration script tag bounds
    async def parse_list(self, content):
        soup = BeautifulSoup(content, 'html.parser')
        offers = []

        # Find the script tag containing the initial state hydration data dictionary
        script_tag = soup.find('script', id='NEXT_DATA')
        if not script_tag:
            print("❌ No JSON data on Otodom")
            return []

        try:
            # Parse the inner text string value of the node directly into a Python object tree
            data = json.loads(script_tag.string)
            
            # Navigate nested keys to isolate target organic listing objects array block
            items = data.get('props', {}).get('pageProps', {}).get('data', {}).get('searchAds', {}).get('items', [])
                
            for item in items:
                slug = item.get('slug')
                if not slug: 
                    continue

                # Append clean standard dictionary maps for downstream engine ingestion
                offers.append({
                    'Title': item.get('title', 'N/A'),
                    # Combine pricing numeric values with their corresponding currency symbol fields
                    'Price': f"{item.get('totalPrice', {}).get('value', 'N/A')} {item.get('totalPrice', {}).get('currency', '')}",
                    'Date': item.get('pushedUpAt', 'N/A'),
                    'Link': f"https://www.otodom.pl/pl/oferta/{slug}"
                })

        except Exception as e:
            print(f"⚠️ Error parsing list context frame: {e}")

        return offers
    # Extracts details, features, and high-resolution images out of an active listing item node
    async def parse_details(self, html, offer):
        soup = BeautifulSoup(html, 'html.parser')
        
        # Leverage the inner JSON state store script to bypass messy runtime DOM trees entirely
        script_tag = soup.find('script', id='NEXT_DATA')
        if script_tag:
            try:
                data = json.loads(script_tag.string)
                ad_data = data.get('props', {}).get('pageProps', {}).get('ad', {})
            
                if ad_data:
                    # Clean up descriptions containing embed structures or raw HTML string fragments
                    raw_description = ad_data.get('description', 'N/A')
                    if raw_description and raw_description != 'N/A':
                        clean_description = BeautifulSoup(raw_description, 'html.parser').get_text(separator=" ", strip=True)
                        offer['Description'] = " ".join(clean_description.split())
                    else:
                        offer['Description'] = 'N/A'
                    
                    # Process tabular technical data specifications array matrices
                    characteristics = ad_data.get('characteristics', [])
                    characteristics_list = []

                    # Internal localization fallbacks mapping schema keys into Polish human-readable definitions
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

                        # Determine the highest priority display name tag label string
                        if label and label != "None":
                            display_label = label
                        elif key in label_mapping:
                            display_label = label_mapping[key]
                        else:
                            display_label = key if key else "Param"
                        
                        characteristics_list.append(f"{display_label}: {value}")

                    # Concatenate specification string vectors with clean programmatic separator characters
                    characteristics_text = " | ".join(characteristics_list)
                
                    # Extract unstructured listing perk tags strings array (e.g., "balcony", "elevator")
                    features = ad_data.get('features', [])
                    features_text = ", ".join(features) if isinstance(features, list) else ""

                    # Isolate strict ISO timestamp strings for listing chronological tracking metrics
                    created_at = ad_data.get('createdAt', 'N/A')
                    updated_at = ad_data.get('pushedUpAt')

                    # Prioritize push-up adjustments over the baseline nodes creation date parameter
                    if updated_at != None:
                        offer['Date'] = updated_at.split('T')[0]
                    else:
                        offer['Date'] = created_at.split('T')[0]
                    # Aggregate text layers to create a highly informative summary blob
                    full_info = []
                    if characteristics_text: full_info.append(f"CHARACTERISTICS: {characteristics_text}")
                    if features_text: full_info.append(f"FEATURES: {features_text}")
                    if offer['Description']: full_info.append(f"DESCRIPTION: {offer['Description']}")
                
                    offer['Description'] = " ".join(full_info)
                
                    # Map all unique available high-resolution media URLs into a unique collection set
                    images = ad_data.get('images', [])
                    image_urls = [img.get('large') for img in images if img.get('large')]
                    if image_urls:
                        offer['Images'] = list(set(image_urls))
                
            except Exception as e:
                print(f"⚠️ Deep node deserialization error: {e}")
                
        return offer
    
    # Interrogates the active tracking framework layout object layer to fetch the listing size index limits
    async def get_total_pages(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        script = soup.find('script', id='NEXT_DATA')
    
        if script:
            try:
                data = json.loads(script.string)
                listing_stats = data.get('props', {}).get('pageProps', {}).get('tracking', {}).get('listing', {})
            
                # Retrieve the concrete page count integer natively declared inside the platform metrics
                total_pages = listing_stats.get('page_count', 1)
                print(f"📊 СOtodom: There are {total_pages} pages.")
                return total_pages
            except Exception as e:
                print(f"⚠️ Failed to parse dynamic layout stats tracker: {e}")
            
        return 1
    
    # Mutates target query parameters dynamically to enable precise index page routing steps
    def change_page(self ,url, number):
        new_url = re.sub(r'page=\d+', f'page={number}', url)
        return new_url