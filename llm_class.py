import ollama
import json
import os

class QwenAnalyzer:
    def __init__(self, model_name='qwen2.5vl'):
        """
        Инициализация анализатора.
        model_name: Имя модели в Ollama (обычно qwen2.5-vl или qwen2.5-vl:7b).
        """
        self.model_name = model_name
        self.system_prompt = """
            You are an expert real estate architect. I have provided you with MULTIPLE photos of the EXACT SAME apartment.
            Your task is to analyze ALL photos together to determine if it is a "Euro-layout" (combined open-plan kitchen and living room/bedroom).

            CRITICAL LOGIC PRIORITIES:
            1. PRIORITY 1 (The Golden Rule): If ANY SINGLE PHOTO shows BOTH living room/bedroom furniture (sofa/bed/dining table) AND kitchen elements (cabinets/oven/sink) together in the same shot without a solid floor-to-ceiling wall between them, this is UNDENIABLE PROOF of a combined space (Euro-layout).
            2. PRIORITY 2 (Cross-Reference): If no single photo shows the full open space, look for visual overlaps between different photos (e.g., the edge of a kitchen cabinet in photo 1 is visible next to a sofa in photo 2).

            Respond STRICTLY in JSON format:
            {
                "photo_summaries": "Briefly describe what is in each of the provided photos.",
                "step1_single_photo_check": "Look at your summaries. Does ANY SINGLE PHOTO contain both a kitchen area AND a living area (sofa/bed) in the same frame? Answer Yes or No.",
                "step2_cross_reference": "If Step 1 is No, do you see any physical connections between different photos? If Step 1 is Yes, write 'Not needed'.",
                "is_combined": true (if Step 1 is Yes OR Step 2 finds a connection) or false,
                "reason_russian": "Детальное объяснение на русском языке: почему это евродвушка (на основе одного кадра или связей) или изолированная планировка."
            }
         """

    def analyze_apartment(self, local_image_paths):
        """
        Принимает список путей к локальным файлам изображений.
        Возвращает словарь с результатами анализа или None в случае ошибки.
        """
        # 1. Валидация входных данных
        valid_images = [img for img in local_image_paths if os.path.exists(img)]
        
        if not valid_images:
            print("   ⚠️ [Qwen] Внимание: Не передано ни одной валидной фотографии для анализа.")
            return {
                "is_combined": False,
                "reason_russian": "Ошибка: Фотографии не найдены или повреждены при скачивании."
            }

        print(f"   🧠 [Qwen] Анализ {len(valid_images)} фотографий...")

        # 2. Вызов Ollama
        try:
            response = ollama.chat(
                model=self.model_name,
                format='json',
                options={
                    "temperature": 0.1,  # Низкая температура для строгой логики
                    "num_ctx": 4096      # Размер контекста, важный для мульти-картинок
                },
                messages=[{
                    'role': 'user',
                    'content': self.system_prompt,
                    'images': valid_images
                }]
            )
            
            # 3. Парсинг ответа
            raw_content = response['message']['content']
            result_dict = json.loads(raw_content)
            
            # Убедимся, что ключевое поле is_combined существует
            if 'is_combined' not in result_dict:
                result_dict['is_combined'] = False
                
            return result_dict

        except json.JSONDecodeError as e:
            print(f"   ❌ [Qwen] Ошибка: Модель вернула невалидный JSON. {e}")
            print(f"   Сырой ответ: {response['message'].get('content', 'Пусто')}")
            return None
            
        except Exception as e:
            print(f"   ❌ [Qwen] Системная ошибка при обращении к Ollama: {e}")
            return None


# --- БЛОК ДЛЯ ТЕСТИРОВАНИЯ ---
if __name__ == "__main__":
    # Этот блок запустится только если вы запустите файл QwenAnalyzer.py напрямую.
    # Если вы импортируете класс в воркер, этот код проигнорируется.
    
    print("=== Режим тестирования класса QwenAnalyzer ===")
    
    # Подставьте пути к тестовым картинкам
    test_pics = ['pics/test1.jpg', 'pics/test2.jpg', 'pics/test3.jpg', 'pics/test4.jpg']
    
    analyzer = QwenAnalyzer(model_name='qwen2.5vl') # Убедитесь, что имя совпадает с тем, как модель называется в ollama list
    result = analyzer.analyze_apartment(test_pics)
    
    if result:
        print("\n================ ВЫВОДЫ МОДЕЛИ ================")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("===============================================")
        
        if result.get('is_combined'):
            print("\nИТОГ: ❌ ЕВРОДВУШКА / СТУДИЯ")
        else:
            print("\nИТОГ: ✅ ОБЫЧНАЯ ПЛАНИРОВКА")