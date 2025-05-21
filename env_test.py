import os
import sys
from dotenv import load_dotenv, find_dotenv

def test_dotenv():
    """Тестирует загрузку переменных окружения из .env файла"""
    
    print(f"Текущий рабочий каталог: {os.getcwd()}")
    
    # Проверяем существование файла .env
    env_path = os.path.join(os.getcwd(), '.env')
    print(f"Проверка, существует ли файл .env по пути {env_path}: {os.path.exists(env_path)}")
    
    # Пытаемся найти .env файл автоматически
    found_dotenv = find_dotenv()
    print(f"Результат find_dotenv(): {found_dotenv}")
    
    # Пробуем прочитать содержимое файла
    try:
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"Содержимое .env файла (без значений, только ключи):")
                for line in content.splitlines():
                    if '=' in line:
                        key, value = line.split('=', 1)
                        print(f"  {key}=***")
        else:
            print("Файл .env не существует в текущем каталоге")
    except Exception as e:
        print(f"Ошибка при чтении файла .env: {str(e)}")
    
    # Явно загружаем переменные окружения
    load_dotenv(dotenv_path=env_path, override=True)
    
    # Проверяем наличие ключевых переменных
    openai_key = os.getenv('OPENAI_API_KEY')
    suno_key = os.getenv('SUNOAI_API_KEY')
    
    print(f"OPENAI_API_KEY загружен: {'Да' if openai_key else 'Нет'}")
    print(f"SUNOAI_API_KEY загружен: {'Да' if suno_key else 'Нет'}")
    
    # Проверка кодировки
    try:
        if os.path.exists(env_path):
            import chardet
            with open(env_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                print(f"Обнаруженная кодировка файла .env: {result['encoding']} (уверенность: {result['confidence']})")
    except ImportError:
        print("Библиотека chardet не установлена. Установите ее с помощью: pip install chardet")
    except Exception as e:
        print(f"Ошибка при определении кодировки: {str(e)}")
    
    # Проверка альтернативной загрузки
    try:
        from dotenv import dotenv_values
        config = dotenv_values(env_path)
        print(f"Результат dotenv_values (только ключи): {list(config.keys())}")
    except Exception as e:
        print(f"Ошибка при использовании dotenv_values: {str(e)}")

if __name__ == "__main__":
    test_dotenv() 