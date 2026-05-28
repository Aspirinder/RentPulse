import ollama
import json
import os

APARTMENT_ID = "777"
# Закиньте сюда пути к фотографиям (лучше 2-4 фото, чтобы не перегрузить видеопамять)
#image_paths = ['pics/hata1.jpg', 'pics/hata2.jpg', 'pics/hata3.jpg', 'pics/hata4.jpg'] # Убедитесь, что эти файлы существуют в папке
#image_paths = ['pics/photo1.jpg', 'pics/photo2.jpg', 'pics/photo3.jpg'] 
#image_paths = ['pics/miez1.jpg', 'pics/miez2.jpg', 'pics/miez3.jpg', 'pics/miez4.jpg']
image_paths = ['pics/test1.jpg', 'pics/test2.jpg', 'pics/test3.jpg', 'pics/test4.jpg']

# Проверяем, существуют ли файлы
valid_images = [img for img in image_paths if os.path.exists(img)]
if not valid_images:
    print("❌ Ошибка: Фотографии не найдены!")
    exit()

# ПРОМПТ ДЛЯ МУЛЬТИ-КАДРОВОГО АНАЛИЗА
prompt = """
You are an expert real estate architect. I have provided you with MULTIPLE photos of the EXACT SAME apartment.
Your task is to analyze ALL photos together to determine if it is a "Euro-layout" (combined open-plan kitchen and living room).

CRITICAL LOGIC PRIORITIES:
1. PRIORITY 1 (The Golden Rule): If ANY SINGLE PHOTO shows BOTH living room furniture (sofa/bed/dining) AND kitchen elements (cabinets/oven/sink) together in the same shot without a solid wall between them, this is UNDENIABLE PROOF of a combined space.
2. PRIORITY 2 (Cross-Reference): If no single photo shows the full open space, look for visual overlaps between different photos (e.g., the edge of a kitchen cabinet in photo 1 is visible next to a sofa in photo 2).

Respond STRICTLY in JSON format:
{
  "photo_summaries": "Briefly describe what is in each of the provided photos.",
  "step1_single_photo_check": "Look at your summaries. Does ANY SINGLE PHOTO contain both a kitchen area AND a living area (sofa/bed) in the same frame? Answer Yes or No, and name the photo.",
  "step2_cross_reference": "If Step 1 is No, do you see any physical connections between different photos? If Step 1 is Yes, write 'Not needed'.",
  "is_combined": true (if Step 1 is Yes OR Step 2 finds a connection) or false,
  "reason_russian": "Детальное объяснение на русском языке: почему это евродвушка (на основе одного кадра или связей) или изолированная планировка."
}
"""

print(f"=== Запуск Мульти-кадрового анализа Qwen2.5-VL ===")
print(f"Загружаем {len(valid_images)} фото одновременно в мозг модели...")

try:
    # Отправляем ВСЕ картинки разом в одном сообщении!
    response = ollama.chat(
        model='qwen2.5vl', 
        format='json',
        messages=[{
            'role': 'user',
            'content': prompt,
            'images': valid_images # Передаем массив путей
        }]
    )
    
    res_json = json.loads(response['message']['content'])
    is_clue_found = res_json.get('is_combined', False)
    
    print("\n================ ВЫВОДЫ МОДЕЛИ ================")
    print(f"Опись фото: {res_json.get('photo_summaries')}")
    print(f"Связи между фото: {res_json.get('cross_image_connections')}")
    print(f"Вердикт ИИ: {res_json.get('reason_russian')}")
    print("===============================================")
    
    if is_clue_found:
        print("\nИТОГ: ❌ ЕВРОДВУШКА / СТУДИЯ (Связь подтверждена)")
    else:
        print("\nИТОГ: ✅ ОБЫЧНАЯ ПЛАНИРОВКА (Комнаты изолированы)")

except Exception as e:
    print(f"\n❌ Ошибка обработки: {e}")