#!/usr/bin/env python3
import requests
import json

def test_music_only():
    print("🎵 Простой тест музыкальной генерации...")
    
    data = {
        'diary_text': 'Тяжелый день на фронте. Держимся.',
        'generation_types[]': ['music']
    }
    
    print("📤 Отправляем запрос...")
    try:
        response = requests.post('http://localhost:5000/analyze', data=data, timeout=120)  # 2 минуты
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Ответ получен!")
            print(f"📄 Ключи ответа: {list(result.keys())}")
            
            if 'music_generation_status' in result:
                music = result['music_generation_status']
                print(f"🎼 Музыка статус: {music.get('status')}")
                print(f"🆔 Task ID: {music.get('task_id', 'НЕТ')}")
                return music.get('task_id')
            else:
                print("❌ Нет музыкального статуса")
                print(f"📋 Полный ответ: {json.dumps(result, ensure_ascii=False, indent=2)}")
        else:
            print(f"❌ Ошибка: {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    return None

if __name__ == "__main__":
    task_id = test_music_only()
    if task_id:
        print(f"\n✅ Получен task_id: {task_id}")
        print("🔍 Теперь можно проверить статус через /check_music_status")
    else:
        print("\n❌ Не удалось получить task_id") 