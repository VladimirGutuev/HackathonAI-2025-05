#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для инициализации базы данных приложения.
Создает все необходимые таблицы для форума и других компонентов.
"""

import os
import sys
from dotenv import load_dotenv, find_dotenv

# Загружаем переменные окружения
env_path = find_dotenv()
if env_path:
    load_dotenv(dotenv_path=env_path, override=True)

# Импортируем компоненты приложения
from app import app, db
from forum import User, Topic, Message, TopicVote, MessageVote, UserFeedback

def init_database():
    """Инициализирует базу данных с созданием всех таблиц"""
    try:
        print("🔧 Инициализация базы данных...")
        
        # Создаем контекст приложения
        with app.app_context():
            # Удаляем существующие таблицы (если есть)
            print("📋 Удаление старых таблиц...")
            db.drop_all()
            
            # Создаем новые таблицы
            print("🏗️ Создание новых таблиц...")
            db.create_all()
            
            # Проверяем, что таблицы созданы
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"✅ Созданы таблицы: {', '.join(tables)}")
            
            # Создаем тестового пользователя (опционально)
            test_user = User.query.filter_by(username='admin').first()
            if not test_user:
                print("👤 Создание тестового пользователя 'admin'...")
                admin_user = User(username='admin')
                admin_user.set_password('X-,y*t)Lg%Xl6Yzn')
                admin_user.is_admin = True
                db.session.add(admin_user)
                db.session.commit()
                print("✅ Тестовый пользователь создан (admin/X-,y*t)Lg%Xl6Yzn)")
            
            print("🎉 База данных успешно инициализирована!")
            
    except Exception as e:
        print(f"❌ Ошибка при инициализации базы данных: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    print("=== Инициализация базы данных ===")
    
    success = init_database()
    
    if success:
        print("\n✅ Инициализация завершена успешно!")
        print("🚀 Теперь можно запускать приложение: python app.py")
    else:
        print("\n❌ Инициализация не удалась!")
        sys.exit(1) 