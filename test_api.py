#!/usr/bin/env python3
import requests
import json

def test_api():
    url = "http://localhost:5000/analyze"
    
    data = {
        'diary_text': 'Сегодня был тяжелый день на фронте. Потеряли многих товарищей. Но мы держимся и не сдаемся.',
        'generation_types[]': ['text'],
        'literary_type': 'poem'
    }
    
    print("🧪 Тестирование API генерации текста...")
    print(f"📤 URL: {url}")
    print(f"📝 Данные: {data}")
    
    try:
        response = requests.post(url, data=data, timeout=60)
        print(f"📊 Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Успешный ответ!")
            
            if 'emotion_analysis' in result:
                print("📈 Анализ эмоций получен")
                emotions = result['emotion_analysis']
                if 'primary_emotions' in emotions:
                    print(f"🎭 Основные эмоции: {[e['emotion'] for e in emotions['primary_emotions']]}")
            
            if 'generated_literary_work' in result:
                print("📖 Литературное произведение сгенерировано!")
                work = result['generated_literary_work']
                print(f"📝 Длина: {len(work)} символов")
                print("🔍 Превью:")
                print(work[:200] + "..." if len(work) > 200 else work)
            else:
                print("❌ Литературное произведение НЕ сгенерировано")
                
        else:
            print(f"❌ Ошибка: {response.status_code}")
            print(f"📄 Ответ: {response.text}")
            
    except requests.exceptions.ConnectıonError:
        print("❌ Ошибка подключения к серверу. Убедитесь что Flask работает на localhost:5000")
    except requests.exceptions.Timeout:
        print("❌ Таймаут запроса")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_api() 