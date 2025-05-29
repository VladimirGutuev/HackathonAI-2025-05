#!/usr/bin/env python3
import requests
import json
import time

def test_music_generation():
    """Тестирует генерацию музыки"""
    
    print("🎵 Тестирование генерации музыки...")
    
    # Данные для генерации музыки
    data = {
        'diary_text': 'Сегодня был тяжелый день на фронте. Потеряли многих товарищей. Но мы держимся и не сдаемся. Надеемся на лучшее.',
        'generation_types[]': ['music']
    }
    
    # 1. Отправляем запрос на генерацию
    print("📤 Отправляем запрос на генерацию музыки...")
    try:
        response = requests.post('http://localhost:5000/analyze', data=data, timeout=30)
        print(f"📊 Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Запрос принят!")
            
            if 'music_generation_status' in result:
                music_status = result['music_generation_status']
                print(f"🎼 Статус музыки: {music_status.get('status')}")
                
                if 'task_id' in music_status:
                    task_id = music_status['task_id']
                    print(f"🆔 Task ID: {task_id}")
                    
                    # 2. Проверяем статус каждые 15 секунд
                    max_checks = 8  # Максимум 2 минуты
                    for check in range(max_checks):
                        print(f"\n🔍 Проверка {check + 1}/{max_checks} (через 15 сек)")
                        time.sleep(15)
                        
                        try:
                            status_response = requests.get(f'http://localhost:5000/check_music_status?task_id={task_id}', timeout=30)
                            
                            if status_response.status_code == 200:
                                status_data = status_response.json()
                                print(f"📈 Статус: {status_data.get('status')}")
                                
                                if status_data.get('fallback_created'):
                                    print("🔄 FALLBACK: Создана новая задача!")
                                    new_task_id = status_data.get('task_id')
                                    if new_task_id and new_task_id != task_id:
                                        print(f"🆔 Новый Task ID: {new_task_id}")
                                        task_id = new_task_id  # Переключаемся на новую задачу
                                
                                if status_data.get('is_music_ready'):
                                    print("🎉 МУЗЫКА ГОТОВА!")
                                    
                                    if status_data.get('audio_url'):
                                        print(f"🔗 Аудио URL: {status_data['audio_url'][:50]}...")
                                        
                                    if status_data.get('proxy_url'):
                                        print(f"🔗 Прокси URL: {status_data['proxy_url']}")
                                        
                                    if status_data.get('music_description'):
                                        print(f"📝 Описание: {status_data['music_description']}")
                                    
                                    return True
                                    
                                elif status_data.get('status') == 'error':
                                    print(f"❌ Ошибка: {status_data.get('message', 'Неизвестная ошибка')}")
                                    return False
                                    
                                else:
                                    print(f"⏳ Обработка... ({status_data.get('message', 'В процессе')})")
                                    
                            else:
                                print(f"❌ Ошибка проверки статуса: {status_response.status_code}")
                                
                        except Exception as e:
                            print(f"❌ Ошибка при проверке статуса: {e}")
                    
                    print("⏰ Превышено время ожидания")
                    return False
                    
                else:
                    print("❌ Task ID не найден в ответе")
                    return False
                    
            else:
                print("❌ Музыкальная генерация не была запущена")
                print(f"📄 Ответ: {result}")
                return False
                
        else:
            print(f"❌ Ошибка запроса: {response.status_code}")
            print(f"📄 Ответ: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    success = test_music_generation()
    
    if success:
        print("\n✅ ТЕСТ ПРОЙДЕН: Музыка успешно сгенерирована!")
    else:
        print("\n❌ ТЕСТ НЕ ПРОЙДЕН: Генерация музыки не удалась")
        
    print("\n🔍 Для диагностики проверьте логи сервера...") 