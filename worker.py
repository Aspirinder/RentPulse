import os
import json
import time
import modal

# modal (server) image configuration
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "transformers>=4.45.0", 
        "accelerate", 
        "torchvision", 
        "torch", 
        "boto3", 
        "requests", 
        "pillow"
    )
)

app = modal.App("apartment-qwen-worker")

#cloud worker class 
@app.cls(image=image, gpu="b200", secrets=[modal.Secret.from_dotenv()], timeout=14400)
class CloudApartmentAnalyzer:
    
    @modal.enter()
    def setup(self):
        print("☁️ Running Modal server...")
        import boto3
        import torch
        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
        
        # initing AWS 
        self.aws_region = 'us-east-1'
        self.queue_url = os.environ.get('sqs_queue_url')
        self.bucket_name = 'apartment-parser-storage-0506'
        
        aws_credentials = {
            'aws_access_key_id': os.environ.get('aws_access_key_id'),
            'aws_secret_access_key': os.environ.get('aws_secret_access_key'),
            'aws_session_token': os.environ.get('aws_session_token'),
            'region_name': self.aws_region
        }
        
        self.sqs_client = boto3.client('sqs', **aws_credentials)
        self.s3_client = boto3.client('s3', **aws_credentials)
        
        self.temp_dir = "/tmp/worker_temp"
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Downloading and loading Qwen2-VL-72B-Instruct 
        print("☁️Loading Qwen2-VL-72B-Instruct...")
        model_id = "Qwen/Qwen2-VL-72B-Instruct"
        
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            model_id,
            torch_dtype=torch.bfloat16,
            device_map="auto"
        )
        self.processor = AutoProcessor.from_pretrained(model_id)
        print("✅ Qwen2-VL-72B-Instruct loaded successfully.")

    # Dowload and return data from S3
    def get_original_data_from_s3(self, s3_folder_prefix):
        data_key = f"{s3_folder_prefix}data.json"
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=data_key)
            return json.loads(response['Body'].read().decode('utf-8'))
        except Exception:
            return None

    # Dowload images from S3 and save locally for processing. Returns list of local paths. 
    def download_s3_images(self, s3_folder_prefix):
        local_paths = []
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=s3_folder_prefix)
            if 'Contents' not in response:
                return []
            for obj in response['Contents']:
                file_key = obj['Key']
                if file_key.endswith('.jpg') or file_key.endswith('.png'):
                    file_name = os.path.basename(file_key)
                    local_path = os.path.join(self.temp_dir, file_name)
                    self.s3_client.download_file(self.bucket_name, file_key, local_path)
                    local_paths.append(local_path)
            local_paths.sort() 
            return local_paths
        except Exception:
            return []

    # Comprasing images for AI processing
    def compress_images_for_ai(self, image_paths, max_size=(640, 640)):
        from PIL import Image
        loaded_images = []
        for path in image_paths:
            try:
                img = Image.open(path).convert('RGB')
                if img.width > max_size[0] or img.height > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                loaded_images.append(img)
            except Exception as e:
                print(f"⚠️ Reading error {path}: {e}")
        return loaded_images

    # Saving result to S3 as JSON under the same folder
    def save_result_to_s3(self, s3_folder_prefix, final_data):
        result_key = f"{s3_folder_prefix}ai_verdict.json"
        try:
            json_string = json.dumps(final_data, ensure_ascii=False, indent=4)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=result_key,
                Body=json_string,
                ContentType='application/json; charset=utf-8'
            )
            print(f"💾 Result successfully saved to S3: {result_key}")
        except Exception as e:
            print(f"❌ Error saving to S3: {e}")

    def cleanup_local_files(self, file_paths):
        for path in set(file_paths):
            if os.path.exists(path):
                os.remove(path)

    # Main loop to process SQS messages
    @modal.method()
    def process_active_queue(self):
        import torch
        import gc
        import re
        
        print("\n🚀 Server looking for AWS queue messages...")
        while True:
            try:
                response = self.sqs_client.receive_message(
                    QueueUrl=self.queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=15
                )# polling SQS for new tasks
                
                if 'Messages' not in response:
                    continue 
                    
                message = response['Messages'][0]
                receipt_handle = message['ReceiptHandle']
                task_data = json.loads(message['Body'])
                
                apartment_id = task_data.get('apartment_id')
                s3_folder = task_data.get('s3_folder')
                
                print(f"\n📦 SQS Task: Apartment {apartment_id}")
                
                original_data = self.get_original_data_from_s3(s3_folder)
                if not original_data:
                    continue

                # Parsing main data
                title = original_data.get("Title", "No title")
                desc = original_data.get("Description", "No description")
                offer_link = original_data.get("Link", "Ссылка не найдена")

                print(f"📝 {title[:50]}...")
                print(f"🔗 {offer_link}")

                print("⬇️ Downloading images from S3...")
                downloaded_image_paths = self.download_s3_images(s3_folder)
                
                if not downloaded_image_paths:
                    print("⚠️ No images found. Task will be deleted.")
                    self.sqs_client.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)
                    continue
                    
                # Processing images for AI (resizing/compressing)
                paths_to_analyze = downloaded_image_paths[:8]
                pil_images = self.compress_images_for_ai(paths_to_analyze)


                print("👁️ Qwen is analyzing...")
                start_time = time.time()
                
                # System prompt for Qwen2-VL with clear instructions and reasoning steps. Emphasizing that photos take precedence over text in case of contradictions.
                system_text = """You are a Senior Real Estate Data Analyst. 
Your task is to analyze apartment listings (photos and text) to accurately classify the kitchen layout.
- "COMBINED" (true): The kitchen shares the same open space with the living area (e.g., aneks kuchenny).
- "ISOLATED" (false): The kitchen is a completely separate room enclosed by walls/doors (e.g., osobna kuchnia).

CRITICAL INSTRUCTION: You must cross-reference the text with the visual evidence. Real estate agents often use inaccurate terms in the text to attract buyers. If the text contradicts the photographic evidence, the photos MUST always take precedence."""

                # User prompt with clear instructions and the data to analyze. Asking for step-by-step reasoning in the answer to ensure the model explains how it arrived at the conclusion, especially in cases of conflicting information. Requesting output in a strict JSON format for easy parsing.
                user_text = f"""Title: {title}
Description: {desc}

Analyze the photos and text carefully. 
Output ONLY a JSON object in this exact format:
{{
  "reasoning": "Step 1: Visual evidence. Step 2: Textual evidence. Step 3: Conflict resolution (if any) and final conclusion.",
  "is_combined": true or false
}}"""
                
                # Building the content block for Qwen2-VL
                content_block = [{"type": "image"} for _ in pil_images]
                content_block.append({"type": "text", "text": user_text})
                messages = [
                    {"role": "system", "content": system_text},
                    {"role": "user", "content": content_block}
                ]

                try:
                    input_text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True) # Tokenizing the prompt for Qwen2-VL
                    inputs = self.processor(
                        text=[input_text], 
                        images=pil_images, 
                        padding=True, 
                        return_tensors="pt"
                    ).to(self.model.device) # Sending to gpu

                    # Generating response
                    output = self.model.generate(**inputs, max_new_tokens=512)
                    
                    # Processing model output to extract the generated text
                    generated_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs.input_ids, output)]
                    response_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
                    raw_text = response_text.strip()
                    
                    # Generating JSON for response
                    json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                    if json_match:
                        raw_text = json_match.group(0)

                    try:
                        ai_verdict = json.loads(raw_text)
                    except json.JSONDecodeError:
                        print(f"❌ JSON error. Raw model response:\n{response_text}")
                        self.cleanup_local_files(downloaded_image_paths)
                        #self.sqs_client.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)
                        continue
                    
                    # Logs for fast evaluating results
                    print("\n" + "="*60)
                    print(f"🔗 Checked apartment: {offer_link}")
                    print(f"🎯 Model verdict ({round(time.time() - start_time, 1)} sec):")
                    print(json.dumps(ai_verdict, indent=2, ensure_ascii=False))
                    print("="*60 + "\n")
                    
                    # Saving final result to S3
                    final_combined_result = {
                        **original_data,
                        "ai_verdict": ai_verdict,
                        "classified_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    self.save_result_to_s3(s3_folder, final_combined_result)
                    
                except Exception as e:
                    print(f"❌ Error generating response: {e}")

                # Cleaning up local files and GPU memory
                self.cleanup_local_files(downloaded_image_paths)
                torch.cuda.empty_cache()
                gc.collect()
                
                # Deleting completed task from SQS
                self.sqs_client.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)
                print("✅ Task completed.")
                
            except Exception as e:
                print(f"🚨 Error in main loop: {e}")
                time.sleep(5)

@app.local_entrypoint()
def main():
    print("🚀 Starting Modal server...")
    worker = CloudApartmentAnalyzer()
    worker.process_active_queue.remote()