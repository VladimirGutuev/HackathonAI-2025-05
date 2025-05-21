import os
import sys

def fix_env_file():
    """
    Исправляет файл .env:
    1. Удаляет BOM маркер
    2. Проверяет наличие SUNOAI_API_KEY
    3. Преобразует в кодировку UTF-8 без BOM
    """
    env_path = os.path.join(os.getcwd(), '.env')
    
    if not os.path.exists(env_path):
        print(f"Файл .env не найден по пути: {env_path}")
        return False
    
    # Создаем резервную копию
    backup_path = env_path + '.backup'
    try:
        with open(env_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        print(f"Создана резервная копия .env: {backup_path}")
    except Exception as e:
        print(f"Ошибка при создании резервной копии: {str(e)}")
        return False
    
    # Чтение содержимого файла
    try:
        with open(env_path, 'rb') as f:
            content = f.read()
            
        # Удаление BOM, если он есть
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]
            print("BOM маркер удален")
        
        # Преобразование в текст
        text_content = content.decode('utf-8')
        
        # Проверка наличия SUNOAI_API_KEY
        lines = text_content.splitlines()
        has_suno_key = any(line.strip().startswith('SUNOAI_API_KEY=') for line in lines)
        
        # Добавление SUNOAI_API_KEY если его нет
        if not has_suno_key:
            suno_key = input("Введите значение для SUNOAI_API_KEY: ")
            if suno_key:
                lines.append(f'SUNOAI_API_KEY={suno_key}')
                print("Добавлен ключ SUNOAI_API_KEY")
        
        # Запись обновленного содержимого в файл
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print("Файл .env успешно обновлен с кодировкой UTF-8 без BOM")
        return True
    
    except Exception as e:
        print(f"Ошибка при обработке файла .env: {str(e)}")
        if os.path.exists(backup_path):
            try:
                # Восстанавливаем из резервной копии в случае ошибки
                with open(backup_path, 'rb') as src, open(env_path, 'wb') as dst:
                    dst.write(src.read())
                print("Восстановлена резервная копия .env из-за ошибки")
            except Exception as restore_error:
                print(f"Ошибка при восстановлении резервной копии: {str(restore_error)}")
        return False

if __name__ == "__main__":
    print("Утилита для исправления файла .env")
    if fix_env_file():
        print("Файл .env успешно исправлен!")
    else:
        print("Произошла ошибка при исправлении файла .env") 