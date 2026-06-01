import pandas as pd
import asyncio
import hashlib
import httpx
import os
import boto3
import json
import uuid
from dotenv import load_dotenv
from BaseParser import BaseParser
from playwright.async_api import async_playwright
from botocore.exceptions import ClientError

load_dotenv()

class ScraperEngine:
    def __init__(self, output_file="results.csv"):
        self.output_file = output_file
        self.results = []
        self.browser = None
        self.context = None
        self.playwright = None

        # AWS configuration    
        self.aws_region = 'us-east-1' 
        self.bucket_name = 'apartment-parser-storage-0506'
        self.sqs_queue_url = os.getenv('sqs_queue_url')
        
        aws_credentials = {
            'aws_access_key_id': os.getenv('aws_access_key_id'),
            'aws_secret_access_key': os.getenv('aws_secret_access_key'),
            'aws_session_token': os.getenv('aws_session_token'),
            'region_name': self.aws_region
        }
        
        print("🔧 S3 and SQS initialization...")
        self.s3_client = boto3.client('s3', **aws_credentials)
        self.sqs_client = boto3.client('sqs', **aws_credentials)
        
        # temp folder for 
        self.temp_dir = "./temp_images"
        os.makedirs(self.temp_dir, exist_ok=True)

    async def start_browser(self, headless=False):
        self.playwright = await async_playwright().start()

        SYSTEM_CHROMIUM_PATH = '/usr/bin/chromium-browser'
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            executable_path=SYSTEM_CHROMIUM_PATH,# only for Linux
            args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox', 
                '--disable-dev-shm-usage'
            ])
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        print("🚀 Browser start")

    # Download images by original URLs and upload to S3 bucket. Returns list of S3 paths.
    async def upload_images_to_s3(self,site_name, apartment_id, raw_image_urls):
        s3_urls = []
        
        # async iamges downloading with httpx
        async with httpx.AsyncClient() as client:
            for index, url in enumerate(raw_image_urls, start=1):
                try:
                    response = await client.get(url, timeout=10.0)
                    if response.status_code != 200:
                        print(f"⚠️ Failed to download image: {url} (Status: {response.status_code})")
                        continue
                    
                    ext = ".jpg"
                    if ".png" in url.lower(): 
                        ext = ".png"
                    
                    local_filename = f"temp_{apartment_id}_{index}{ext}"
                    local_path = os.path.join(self.temp_dir, local_filename)
                    
                    # sdaving image to local temp folder
                    with open(local_path, "wb") as f:
                        f.write(response.content)

                    s3_key = f"{site_name}/apartment_{apartment_id}/photo_{index}{ext}"
                    
                    # uploading to S3 via async wrapper around sync method (playwright is async, boto3 is sync)
                    print(f"☁️ Uploading to S3: {s3_key}")
                    await asyncio.to_thread(
                        self.s3_client.upload_file, 
                        local_path, 
                        self.bucket_name, 
                        s3_key
                    )
                    
                    # saving S3 URL 
                    s3_urls.append(f"s3://{self.bucket_name}/{s3_key}")
                    
                    # removing temp file
                    os.remove(local_path)
                    
                except Exception as e:
                    print(f"❌ Image processing error for {url}: {e}")
                    
        return s3_urls
    
    # Upload JSON data to S3 under a folder named after the apartment ID.
    async def upload_json_to_s3(self,site_name, apartment_id, data_dict):
        s3_key = f"{site_name}/apartment_{apartment_id}/data.json"
        
        try:
            json_string = json.dumps(data_dict, ensure_ascii=False, indent=4)
            
            print(f"☁️ Uploading JSON to S3: {s3_key}")
            
            # uploading to S3 via async wrapper around sync method (playwright is async, boto3 is sync)
            await asyncio.to_thread(
                self.s3_client.put_object,
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_string,
                ContentType='application/json; charset=utf-8' # Указываем тип контента для удобства просмотра в браузере
            )
            
        except Exception as e:
            print(f"❌ Error uploading JSON to S3 for ID {apartment_id}: {e}") 

    #sends message to SQS
    def send_task_to_sqs(self, site_name, apartment_id):
        s3_folder_prefix = f"{site_name}/apartment_{apartment_id}/"
        
        # s3 message schema
        task_payload = {
            "task_id": str(uuid.uuid4()),
            "site_name": site_name,
            "apartment_id": apartment_id,
            "s3_folder": s3_folder_prefix,
            "attempt": 1
        }
        
        try:
            self.sqs_client.send_message(
                QueueUrl=self.sqs_queue_url,
                MessageBody=json.dumps(task_payload)
            )
            print(f"📨 message sent to SQS (ID: {apartment_id})")
        except Exception as e:
            print(f"❌ failed to send message to SQS: {e}")

    # check if apartment is already in S3 (true for already parsed apartments, false for new ones)
    async def is_apartment_parsed(self, site_name, apartment_id):
        s3_key = f"{site_name}/apartment_{apartment_id}/data.json"
        
        try:
            await asyncio.to_thread(
                self.s3_client.head_object,
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
            
        except ClientError as e:
            # 404 error means object does not exist, so it's not parsed yet
            if e.response['Error']['Code'] == '404':
                return False
            else:
                print(f"⚠️ Error checking S3: {e}")
                return False

    async def run_parser(self, parser: BaseParser, start_url):
        page = await self.context.new_page()
        print(f"🔎 Scanning: {start_url}")

        await page.goto(start_url, wait_until="domcontentloaded")
        content = await page.content()

        basic_offers = await parser.parse_list(content)

        if not basic_offers:
            return 0
        
        for offer in basic_offers:
            source_url = offer['Link']

            if "olx" in source_url.lower():
                site_name = "olx"
            elif "otodom" in source_url.lower():
                site_name = "otodom"

            # building unique ID for apartment based on source URL via hashing
            apartment_id = hashlib.md5(source_url.encode('utf-8')).hexdigest()[:10]

            is_in_s3 = await self.is_apartment_parsed(site_name, apartment_id)
            if is_in_s3:
                print(f"⏭️ Already in S3: {offer['Title'][:20]}")
                continue

            print(f"  -> Opening details: {offer['Title'][:30]}")
            await page.goto(offer['Link'], wait_until="domcontentloaded")
            await asyncio.sleep(1)

            detail_content = await page.content()
            details = await parser.parse_details(detail_content, offer)

            combined_data = {**offer, **details}
            combined_data['generated_id'] = apartment_id
            combined_data['source_site'] = site_name

            raw_img_urls = details.get('Images', []) 
            
            if raw_img_urls:
                print(f"⚙️ Apartment get ID {apartment_id}. Pushing to S3...")
                
                s3_cloud_links = await self.upload_images_to_s3(site_name, apartment_id, raw_img_urls)
                
                details['s3_stored_links'] = s3_cloud_links
                details['generated_id'] = apartment_id

            await self.upload_json_to_s3(site_name, apartment_id, combined_data)
            self.send_task_to_sqs(site_name, apartment_id)
            self.results.append(combined_data)

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