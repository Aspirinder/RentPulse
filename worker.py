import boto3
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

# --- НАСТРОЙКИ AWS ACADEMY (Внесите свежие данные из AWS Details) ---
aws_region = 'us-east-1'  # Проверьте ваш регион в Learner Lab
bucket_name = 'apartment-parser-storage-0506'  # Имя вашего бакета
sqs_queue_url = os.getenv('sqs_queue_url')  # URL вашей SQS очереди для задач (если нужно)
        
        # Данные авторизации из вкладки AWS Details (обновляются каждую сессию)
aws_credentials = {
    'aws_access_key_id': os.getenv('aws_access_key_id'),  # Обязательно для студентов!
    'aws_secret_access_key': os.getenv('aws_secret_access_key'),
    'aws_session_token': os.getenv('aws_session_token'),  # Обязательно для студентов!
    'region_name':aws_region
}

# Инициализируем клиенты для работы с облаком
sqs_client = boto3.client('sqs', **aws_credentials)
s3_client = boto3.client('s3', **aws_credentials)

print("🚀 Локальный воркер запущен и готов к обработке задач...")

def process_active_queue():
    while True:
        try:
            print("\n🔎 Опрашиваю очередь SQS в поиске новых квартир...")
            
            # 1. Запрашиваем 1 сообщение из очереди
            response = sqs_client.receive_message(
                QueueUrl=sqs_queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20 # Long Polling: ждем до 20 сек, если очередь пуста, чтобы не спамить запросами
            )
            
            # Если сообщений в очереди нет, цикл просто начнется заново
            if 'Messages' not in response:
                print("📭 Очередь пуста. Повторный опрос через несколько секунд...")
                time.sleep(5)
                continue
                
            # Извлекаем первое доступное сообщение
            message = response['Messages'][0]
            receipt_handle = message['ReceiptHandle'] # Квитанция для последующего удаления
            
            # Десериализуем JSON-контракт задачи, который прислал парсер
            task_data = json.loads(message['Body'])
            
            apartment_id = task_data['apartment_id']
            site_name = task_data['site_name']
            s3_folder = task_data['s3_folder']
            
            print(f"📦 Найдена задача! Сайт: {site_name.upper()}, ID Квартиры: {apartment_id}")
            print(f"📂 Путь к данным в S3: {s3_folder}")
            
            # -------------------------------------------------------------
            # НА СЛЕДУЮЩЕМ ЭТАПЕ ЗДЕСЬ БУДЕТ:
            # 1. Скачивание картинок и data.json из S3 по пути s3_folder
            # 2. Запуск Ollama (Qwen2.5-VL)
            # 3. Сохранение вердикта в DynamoDB
            # -------------------------------------------------------------
            
            # Эмулируем работу ИИ (пока для теста)
            print("🤖 [Тест] Имитация работы Qwen2.5-VL...")
            time.sleep(3) 
            
            # 2. Удаляем задачу из очереди, так как она успешно выполнена
            sqs_client.delete_message(
                QueueUrl=sqs_queue_url,
                ReceiptHandle=receipt_handle
            )
            print(f"✅ Задача {apartment_id} успешно обработана и удалена из SQS.")
            
        except Exception as e:
            print(f"❌ Ошибка в цикле воркера: {e}")
            time.sleep(5)

if __name__ == "__main__":
    process_active_queue()