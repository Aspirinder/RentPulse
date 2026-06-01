from bs4 import BeautifulSoup
from BaseParser import BaseParser
import re

class OLXParser(BaseParser):

    # Orchestrates the pagination loop and handles page parsing execution
    async def start_parse(self, engine, url, output, page_number):

        while(True):
            # Run the parser for the current page URL and get the count of discovered offers
            found_count, _ = await engine.run_parser(self, self.change_page(url, page_number))

            # If no offers are found on the page, assume it is the last page and exit the loop
            if found_count == 0: 
                break

            # Increment page counter to move to the next search page
            page_number += 1

        # Logging parsing completion details
        print(f"Stop parse OLX. Parse pages: {page_number - 1}\n")
        
        # Configure the engine to save collected items to the specified CSV file
        engine.output_file = output
        engine.save_to_csv()
        
        # Reset the engine results cache to prepare for future parsing tasks
        engine.results = []


    # Scrapes listing items from the main search page (Title, Price, Date, Link)
    async def parse_list(self, content):
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find all offer cards container elements using OLX custom data attribute
        cards = soup.find_all('div', {'data-cy': 'l-card'})
        offers = []

        for card in cards:
            try:
                # Extract the anchor tag to get the destination URL
                link_el = card.find('a')
                if not link_el:
                    continue
                raw_link = link_el['href']
                
                # Resolve relative paths into absolute URLs if necessary
                full_link = raw_link if raw_link.startswith('http') else "https://www.olx.pl" + raw_link
                
                # Extract the combined location and date text element
                loc_el = card.find('p', {'data-testid': 'location-date'})
                loc_text = loc_el.text.strip() if loc_el else ""

                # Construct the basic offer dictionary structure
                item = {
                    'Title': card.find('h4').text.strip() if card.find('h4') else "N/A",
                    'Price': card.find('p', {'data-testid': 'ad-price'}).text.strip() if card.find('p', {'data-testid': 'ad-price'}) else "N/A",
                    # Parse the date by splitting the location text (format: "Location - Date")
                    'Date': loc_text.split(' - ')[1] if ' - ' in loc_text else "N/A",
                    'Link': full_link
                }

                # Filter out standard external ads (e.g., promotional Otodom inserts)
                if "olx.pl" in full_link:
                    offers.append(item)
                    
            except Exception as e:
                print(f"⚠️ Error parsing list item card: {e}")
                
        return offers


    # Extracts deep elements on the specific ad details page (Description & Images)
    async def parse_details(self, html, offer):
        soup = BeautifulSoup(html, 'html.parser')
        try:
            # Extract the raw ad description text block
            desc_div = soup.find('div', {'data-cy': 'ad_description'})
            # Clean up excessive whitespaces and line breaks from description text
            offer['Description'] = " ".join(desc_div.get_text(separator=" ", strip=True).split()) if desc_div else "N/A"
            
            # Select all image elements inside the primary photo container layout
            img_elements = soup.select('div[data-testid="ad-photo"] img')
            image_urls = []
            
            for img in img_elements:
                # Fallback check for standard src or lazy-loaded data-src attributes
                src = img.get('src') or img.get('data-src')
    
                if src and 'http' in src:
                    # Clean the URL by stripping trailing parameters after semicolons
                    clean_src = src.split(';')[0] 
                    image_urls.append(clean_src)
                
            # Remove eventual duplicates by casting into a set and back to list
            offer['Images'] = list(set(image_urls))
            
        except Exception as e:
            print(f"❌ Error extracting details on {offer['Link']}: {e}")
            
        return offer
    
    
    # Modifies the 'page=X' query parameter inside the destination URL using regular expressions
    def change_page(self, url, number):
        new_url = re.sub(r'page=\d+', f'page={number}', url)
        return new_url