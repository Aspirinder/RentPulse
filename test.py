import os
import ollama
import json
from ultralytics import YOLO


APARTMENT_ID = "777"

#image_paths = ['pics/hata1.jpg', 'pics/hata2.jpg', 'pics/hata3.jpg', 'pics/hata4.jpg'] # Убедитесь, что эти файлы существуют в папке
#image_paths = ['pics/photo1.jpg', 'pics/photo2.jpg', 'pics/photo3.jpg'] 
#image_paths = ['pics/miez1.jpg', 'pics/miez2.jpg', 'pics/miez3.jpg', 'pics/miez4.jpg']
image_paths = ['pics/test1.jpg', 'pics/test2.jpg', 'pics/test3.jpg', 'pics/test4.jpg']

prompt = """
You are an expert real estate architect. Analyze this photo to determine if the apartment has an open-plan "Euro-layout" (where the kitchen is combined with the living room or bedroom).

RULES FOR OPEN-PLAN:
1. You must see BOTH kitchen elements (cabinets, sink, oven) AND living elements (sofa, bed, or a continuous large living space) in this EXACT SAME photo.
2. There must be NO solid walls or standard doorways separating them. They must share the same continuous open space.
3. If the photo only shows a kitchen, it is NOT proof of an open plan (return false).
4. If you see a kitchen, but it is viewed through a standard narrow doorway from a hallway, it is an isolated room (return false).

Respond STRICTLY in JSON format:
{
  "observed_objects": "List the main furniture and appliances visible.",
  "walls_and_doors": "Describe any separating walls, doorways, or arches between different functional zones.",
  "is_combined": true (only if kitchen and living/bedroom clearly share one open space without walls) or false,
  "reason_russian": "Короткое обоснование на русском языке: почему это изолированная комната или совмещенное пространство."
}
"""

apartment_report = {
    "apartment_id": APARTMENT_ID,
    "status": "PROCESSED",
    "is_combined": False,
    "trigger_photo": None,
    "logs": []
}

print(f"=== Запуск Qwen-анализа по заданному списку ({len(image_paths)} фото) ===")

for index, img_path in enumerate(image_paths, start=1):
    print(f"\n[Анализ фото {index}/{len(image_paths)}: {img_path}] ...")
    
    if not os.path.exists(img_path):
        print(f"   ❌ Ошибка: Файл {img_path} не найден. Пропускаем.")
        continue
        
    try:
        response = ollama.chat(
            model='qwen2.5vl', # Используем зрячую модель Qwen
            format='json',
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [img_path]
            }]
        )
        
        res_json = json.loads(response['message']['content'])
        is_clue_found = res_json.get('is_combined', False)
        
        print(f"   • Объекты: {res_json.get('observed_objects')}")
        print(f"   • Стены/двери: {res_json.get('walls_and_doors')}")
        print(f"   • Вердикт ИИ: {res_json.get('reason_russian')}")
        
        apartment_report["logs"].append({
            "file": img_path,
            "is_combined": is_clue_found,
            "reason": res_json.get('reason_russian')
        })
        
        # Правило "одного прокола": если хоть на одном фото есть совмещение — бракуем всю квартиру
        if is_clue_found is True and apartment_report["is_combined"] is False:
            apartment_report["is_combined"] = True
            apartment_report["trigger_photo"] = img_path
            print("   🚨 ВНИМАНИЕ: Найдено совмещенное пространство!")

    except Exception as e:
        print(f"   ❌ Ошибка обработки: {e}")

print("\n" + "="*50)
if apartment_report["is_combined"]:
    print(f"ИТОГ: ❌ ЕВРОДВУШКА / СТУДИЯ (Улика найдена на фото: {apartment_report['trigger_photo']})")
else:
    print("ИТОГ: ✅ ОБЫЧНАЯ ПЛАНИРОВКА (Все зоны на фото изолированы)")
print("="*50)