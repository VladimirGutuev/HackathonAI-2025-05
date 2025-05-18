# Установка и настройка

## Требования
- Python 3.7.1 или выше
- pip (менеджер пакетов Python)

## Шаги установки

1. Создайте виртуальное окружение:
```bash
python -m venv env
```

2. Активируйте виртуальное окружение:

Для Windows (PowerShell):
```powershell
.\env\Scripts\Activate.ps1
```

Для Windows (Command Prompt):
```cmd
env\Scripts\activate.bat
```

Для Linux/MacOS:
```bash
source env/bin/activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` в корневой директории проекта и добавьте ваш API ключ OpenAI:
```
OPENAI_API_KEY=ваш_ключ_api
```

## Проверка установки

Для проверки корректности установки запустите:
```bash
python war_diary_analyzer.py
```

Если все настроено правильно, вы увидите сообщение об успешном анализе и сгенерированный текст будет сохранен в файл `output.txt`.

## Возможные проблемы

1. Если возникает ошибка с `python-dotenv`:
   ```bash
   pip install python-dotenv --upgrade
   ```

2. Если возникает ошибка с OpenAI API:
   - Проверьте правильность API ключа в файле `.env`
   - Убедитесь, что у вас есть доступ к API OpenAI
   - Проверьте баланс на вашем аккаунте OpenAI

3. Если возникают проблемы с виртуальным окружением:
   - Удалите папку `env`
   - Создайте новое окружение
   - Повторите шаги установки 