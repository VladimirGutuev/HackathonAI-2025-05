#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Простой тест для проверки создания базы данных
"""

import os
from dotenv import load_dotenv, find_dotenv

# Загружаем переменные окружения
env_path = find_dotenv()
if env_path:
    load_dotenv(dotenv_path=env_path, override=True)

# Импортируем Flask компоненты
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Создаем простое приложение
app = Flask(__name__)
app.config['SECRET_KEY'] = 'test'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_forum.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализируем базу данных
db = SQLAlchemy(app)

# Определяем модели прямо здесь
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    votes_up = db.Column(db.Integer, default=0)
    votes_down = db.Column(db.Integer, default=0)

def test_database():
    """Тестирует создание базы данных"""
    try:
        print("🔧 Тестирование создания базы данных...")
        
        with app.app_context():
            # Удаляем старые таблицы
            print("📋 Удаление старых таблиц...")
            db.drop_all()
            
            # Создаем новые таблицы  
            print("🏗️ Создание новых таблиц...")
            db.create_all()
            
            # Проверяем таблицы
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"✅ Созданы таблицы: {', '.join(tables)}")
            
            # Создаем тестового пользователя
            print("👤 Создание тестового пользователя...")
            user = User(username='testuser')
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            # Проверяем создание
            saved_user = User.query.filter_by(username='testuser').first()
            if saved_user:
                print(f"✅ Пользователь создан: {saved_user.username}")
            else:
                print("❌ Ошибка: пользователь не найден")
                return False
                
            print("🎉 Тест успешно пройден!")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=== Тест создания базы данных ===")
    
    success = test_database()
    
    if success:
        print("\n✅ Тест завершен успешно!")
        # Показываем созданный файл
        if os.path.exists('test_forum.db'):
            size = os.path.getsize('test_forum.db')
            print(f"📁 Создан файл test_forum.db размером {size} байт")
    else:
        print("\n❌ Тест не пройден!") 