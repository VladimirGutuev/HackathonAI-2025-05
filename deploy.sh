#!/bin/bash

# Скрипт для деплоя приложения на хостинг

echo "==== Начинаем процесс деплоя ===="

# 1. Создаем .env файл с необходимыми переменными окружения
echo "Создаем .env файл..."
cat > .env << EOL
OPENAI_API_KEY=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
SUNOAI_API_KEY=a8aebe65c6c9a1bdda12b0406024d469
DB_HOST=localhost
DB_USER=v133295_dbuser
DB_PASSWORD=K>%SKrMcu#.qrTpD
DB_NAME=v133295_db
USE_MYSQL=True
DEBUG=False
EOL

echo "Файл .env создан."

# 2. Подготовка файлов для загрузки
echo "Подготавливаем файлы для загрузки..."

# Создаем директории
mkdir -p deploy/static
mkdir -p deploy/static/generated_images
mkdir -p deploy/static/generated_music
mkdir -p deploy/static/css
mkdir -p deploy/templates

# Копируем файлы
cp -r static/* deploy/static/
cp -r templates/* deploy/templates/
cp app.py config.py forum.py war_diary_analyzer.py wsgi.py passenger_wsgi.py .htaccess requirements.txt deploy/
cp mysql_schema.sql init_mysql_db.py deploy/
cp .env deploy/

echo "Файлы подготовлены."

# 3. Загрузка файлов на сервер с помощью FTP
echo "Для загрузки файлов на сервер используйте FTP-клиент (например, FileZilla)"
echo "Сервер: v133295.hostde42.fornex.host"
echo "Логин: v133295"
echo "Пароль: (ваш пароль)"
echo "Порт: 21"
echo "Загрузите содержимое папки deploy/ в ~/public_html/diaryofwar.ru/"

# 4. Инструкции по настройке
echo "==== После загрузки файлов: ===="
echo "1. Подключитесь к серверу по SSH"
echo "2. Перейдите в директорию ~/public_html/diaryofwar.ru/"
echo "3. Создайте виртуальное окружение: python -m venv env"
echo "4. Активируйте виртуальное окружение: source env/bin/activate"
echo "5. Установите зависимости: pip install -r requirements.txt"
echo "6. Инициализируйте базу данных: python init_mysql_db.py"
echo "7. Запустите приложение с помощью Gunicorn: gunicorn -b 127.0.0.1:8000 wsgi:app"

echo "==== Деплой завершен ====" 