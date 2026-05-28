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

    # --- НАСТРОЙКИ AMAZON S3 (AWS ACADEMY) ---
        self.aws_region = 'us-east-1'  # Проверьте ваш регион в Learner Lab
        self.bucket_name = 'apartment-parser-storage-0506'  # Имя вашего бакета
        self.sqs_queue_url = os.getenv('sqs_queue_url')  # URL вашей SQS очереди для задач (если нужно)
        
        # Данные авторизации из вкладки AWS Details (обновляются каждую сессию)
        aws_credentials = {
            'aws_access_key_id': os.getenv('aws_access_key_id'),  # Обязательно для студентов!
            'aws_secret_access_key': os.getenv('aws_secret_access_key'),
            'aws_session_token': os.getenv('aws_session_token'),  # Обязательно для студентов!
            'region_name': self.aws_region
        }
        
        print("🔧 Инициализация подключения к Amazon S3...")
        self.s3_client = boto3.client('s3', **aws_credentials)
        self.sqs_client = boto3.client('sqs', **aws_credentials)
        
        # Создаем временную локальную папку для промежуточного сохранения картинок
        self.temp_dir = "./temp_images"
        os.makedirs(self.temp_dir, exist_ok=True)

    async def start_browser(self, headless=False):
        self.playwright = await async_playwright().start()

        SYSTEM_CHROMIUM_PATH = '/usr/bin/chromium-browser'

        self.browser = await self.playwright.chromium.launch(
            headless=headless,# Принудительно используем системный браузер
            args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox', 
                '--disable-dev-shm-usage' # Спасает от падений из-за нехватки памяти на серверах
            ])
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        print("🚀 Browser start")

    async def upload_images_to_s3(self,site_name, apartment_id, raw_image_urls):
        """
        Скачивает картинки по оригинальным URL и загружает их в бакет S3.
        Возвращает список внутренних путей S3 (s3://...).
        """
        s3_urls = []
        
        # Используем httpx для асинхронного скачивания файлов
        async with httpx.AsyncClient() as client:
            for index, url in enumerate(raw_image_urls, start=1):
                try:
                    # 1. Скачиваем картинку во временный файл
                    response = await client.get(url, timeout=10.0)
                    if response.status_code != 200:
                        print(f"      ⚠️ Не удалось скачать фото: {url} (Status: {response.status_code})")
                        continue
                    
                    # Определяем расширение файла (.jpg или .png)
                    ext = ".jpg"
                    if ".png" in url.lower(): 
                        ext = ".png"
                    
                    local_filename = f"temp_{apartment_id}_{index}{ext}"
                    local_path = os.path.join(self.temp_dir, local_filename)
                    
                    # Записываем байты на диск
                    with open(local_path, "wb") as f:
                        f.write(response.content)
                        
                    # 2. Формируем красивое имя (ключ) файла для S3
                    s3_key = f"{site_name}/apartment_{apartment_id}/photo_{index}{ext}"
                    
                    # Загружаем файл в бакет S3. 
                    # Так как boto3 синхронный, оборачиваем его в asyncio.to_thread, 
                    # чтобы он не блокировал весь асинхронный парсер.
                    print(f"   ☁️ Отправка в S3: {s3_key}")
                    await asyncio.to_thread(
                        self.s3_client.upload_file, 
                        local_path, 
                        self.bucket_name, 
                        s3_key
                    )
                    
                    # Сохраняем финальный S3 путь
                    s3_urls.append(f"s3://{self.bucket_name}/{s3_key}")
                    
                    # 3. Сразу удаляем временный файл с локального диска
                    os.remove(local_path)
                    
                except Exception as e:
                    print(f"      ❌ Ошибка при обработке изображения {url}: {e}")
                    
        return s3_urls
    
    async def upload_json_to_s3(self,site_name, apartment_id, data_dict):
        """
        Превращает словарь Python в JSON-строку и загружает напрямую в S3 
        в папку квартиры под именем data.json.
        """
        s3_key = f"{site_name}/apartment_{apartment_id}/data.json"
        
        try:
            # Превращаем словарь в строку JSON. 
            # ensure_ascii=False важен, чтобы польский/русский текст не превратился в коды типа \u0430
            json_string = json.dumps(data_dict, ensure_ascii=False, indent=4)
            
            print(f"   ☁️ Отправка текстовых данных в S3: {s3_key}")
            
            # Используем put_object для отправки строки из памяти
            await asyncio.to_thread(
                self.s3_client.put_object,
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_string,
                ContentType='application/json; charset=utf-8' # Указываем тип контента для удобства просмотра в браузере
            )
            
        except Exception as e:
            print(f"      ❌ Ошибка при загрузке JSON в S3 для ID {apartment_id}: {e}") 

    def send_task_to_sqs(self, site_name, apartment_id):
        """
        Формирует JSON-контракт задачи и отправляет его в очередь SQS.
        """
        
        # Формируем путь, по которому воркер найдет файлы в S3
        s3_folder_prefix = f"{site_name}/apartment_{apartment_id}/"
        
        # Строгий контракт задачи
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
            print(f"   📨 ЗАДАЧА ОТПРАВЛЕНА В ОЧЕРЕДЬ SQS (ID: {apartment_id})")
        except Exception as e:
            print(f"   ❌ Ошибка при отправке в SQS: {e}")

    async def is_apartment_parsed(self, site_name, apartment_id):
        """
        Проверяет, существует ли уже папка с этой квартирой в S3.
        Возвращает True, если квартира уже спарсена, и False, если она новая.
        """
        s3_key = f"{site_name}/apartment_{apartment_id}/data.json"
        
        try:
            # head_object просто проверяет существование файла, не скачивая его
            await asyncio.to_thread(
                self.s3_client.head_object,
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True # Ошибки нет -> файл найден -> квартира уже есть!
            
        except ClientError as e:
            # Ошибка 404 означает, что файла нет
            if e.response['Error']['Code'] == '404':
                return False
            else:
                # Если произошла другая ошибка (например, с токеном), выводим её
                print(f"      ⚠️ Ошибка проверки S3: {e}")
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
            print(f"  -> Opening details: {offer['Title'][:30]}")
            await page.goto(offer['Link'], wait_until="domcontentloaded")
            await asyncio.sleep(1)

            detail_content = await page.content()
            details = await parser.parse_details(detail_content, offer)

            if "olx" in source_url.lower():
                site_name = "olx"
            elif "otodom" in source_url.lower():
                site_name = "otodom"

            # --- ГЕНЕРАЦИЯ СОБСТВЕННОГО УМНОГО ID ---
            # Берем ссылку, кодируем и превращаем в хэш. 
            # [:10] - отрезаем первые 10 символов, чтобы ID был коротким и красивым
            apartment_id = hashlib.md5(source_url.encode('utf-8')).hexdigest()[:10]

            is_in_s3 = await self.is_apartment_parsed(site_name, apartment_id)
            if is_in_s3:
                print(f"  ⏭️ Пропуск (уже есть в базе S3): {offer['Title'][:20]}")
                continue
            
            await page.goto(source_url, wait_until="domcontentloaded")
            await asyncio.sleep(1)

            detail_content = await page.content()
            details = await parser.parse_details(detail_content, offer)

            combined_data = {**offer, **details}
            combined_data['generated_id'] = apartment_id
            combined_data['source_site'] = site_name

            # --- ИНТЕГРАЦИЯ С S3 ПАЙПЛАЙНОМ ---
            raw_img_urls = details.get('Images', []) 
            
            if raw_img_urls:
                print(f"   ⚙️ Квартире присвоен ID {apartment_id}. Обработка S3...")
                
                # Запускаем наш метод загрузки в S3 с новым сгенерированным ID
                s3_cloud_links = await self.upload_images_to_s3(site_name, apartment_id, raw_img_urls)
                
                details['s3_stored_links'] = s3_cloud_links
                # Сохраняем сгенерированный ID в общие результаты, чтобы он был и в CSV
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