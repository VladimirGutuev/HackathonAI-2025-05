from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, Response, send_from_directory
from war_diary_analyzer import WarDiaryAnalyzer
from forum import init_forum, db, User, Topic, Message, TopicVote, MessageVote, UserFeedback, UserGeneration
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
import sys
from datetime import datetime
from dotenv import load_dotenv, find_dotenv, dotenv_values
import json
import requests
from urllib.parse import quote
import urllib.parse
import time

# Улучшенная загрузка переменных окружения
env_path = find_dotenv() 
if env_path:
    print(f"Найден файл .env: {env_path}")
    try:
        # Чтение файла для проверки его содержимого
        with open(env_path, 'r', encoding='utf-8') as f:
            env_content = f.read()
            print(f"Файл .env содержит {len(env_content.splitlines())} строк")
            
        # Загрузка переменных окружения
        load_dotenv(dotenv_path=env_path, override=True)
        
        # Альтернативный способ загрузки
        config = dotenv_values(env_path)
        for key, value in config.items():
            if key not in os.environ:
                os.environ[key] = value
                print(f"Установлена переменная окружения через dotenv_values: {key}")
    except Exception as e:
        print(f"Ошибка при загрузке .env файла: {str(e)}")
else:
    print("Файл .env не найден!")

# Проверка переменных окружения
print("OPENAI_API_KEY:", "Установлен" if os.environ.get("OPENAI_API_KEY") else "НЕ УСТАНОВЛЕН")
print("SUNOAI_API_KEY:", "Установлен" if os.environ.get("SUNOAI_API_KEY") else "НЕ УСТАНОВЛЕН")

# Попытка импорта RAG компонентов
try:
    from historical_rag import HistoricalRAG
    RAG_AVAILABLE = True
except ImportError:
    HistoricalRAG = None # Определяем как None, если импорт не удался
    RAG_AVAILABLE = False

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///forum.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация компонентов
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
init_forum(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    sort_by = request.args.get('sort', 'date')  # date, likes
    if sort_by == 'likes':
        topics = Topic.query.order_by((Topic.votes_up - Topic.votes_down).desc()).all()
    else:  # date
        topics = Topic.query.order_by(Topic.created_at.desc()).all()
    return render_template('index.html', topics=topics, current_sort=sort_by)

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        print("=== Начало обработки запроса /analyze ===")
        diary_text = request.form.get('diary_text', '')
        
        # Получаем типы генерации
        generation_types = request.form.getlist('generation_types[]')
        
        if not diary_text:
            print("Ошибка: пустой текст дневника")
            return jsonify({'error': 'Текст дневника не может быть пустым'}), 400
        
        # Проверяем, что типы генерации указаны
        if not generation_types:
            print("Ошибка: не выбраны типы генерации")
            return jsonify({'error': 'Выберите хотя бы один тип генерации'}), 400

        print(f"Получен текст дневника длиной {len(diary_text)} символов")
        print(f"Выбранные типы генерации: {generation_types}")
        
        # Создаем анализатор и проводим эмоциональный анализ
        analyzer = WarDiaryAnalyzer()
        
        # Проводим расширенный анализ эмоций с историческим контекстом
        print("Начало расширенного анализа с историческим контекстом...")
        emotions = analyzer.analyze_emotions_with_context(diary_text)
        print(f"Расширенный анализ завершен: {list(emotions.keys())}")
        
        # Извлекаем базовый анализ эмоций из результата
        base_emotions = emotions.get('emotion_analysis', emotions)
        
        # Проверяем наличие ошибки в анализе эмоций
        if 'error' in base_emotions and base_emotions['error']:
            print(f"Ошибка при анализе эмоций: {base_emotions['error']}")
            return jsonify({
                'error': base_emotions['error'],
                'emotion_analysis': base_emotions,
            }), 500
        
        # Формируем ответ, всегда включаем полный анализ (включая исторический контекст если есть)
        response_data = {
            'emotion_analysis': emotions,
        }
        
        # На основе эмоционального анализа генерируем выбранные типы контента
        if 'text' in generation_types:
            print("Начало генерации художественного произведения")
            user_id_to_pass = current_user.id if current_user.is_authenticated else None
            literary_work_result = analyzer.generate_literary_work(diary_text, base_emotions, user_id=user_id_to_pass)
            
            if literary_work_result and isinstance(literary_work_result, dict):
                response_data['generated_literary_work'] = literary_work_result.get('text')
                print(f"Генерация текста завершена, длина: {len(literary_work_result.get('text', ''))}")

                if current_user.is_authenticated:
                    try:
                        new_generation = UserGeneration(
                            user_id=current_user.id,
                            generation_type='text',
                            file_path_or_id=literary_work_result.get('filepath'), # Сохраняем имя файла
                            title="Художественное произведение", # Можно сделать более динамичным
                            snippet_or_description=literary_work_result.get('text', '')[:500] + "..." if literary_work_result.get('text', '') else None
                        )
                        db.session.add(new_generation)
                        db.session.commit()
                        print(f"Запись о генерации текста для пользователя {current_user.id} сохранена.")
                    except Exception as e:
                        db.session.rollback()
                        print(f"Ошибка сохранения UserGeneration для текста: {e}")
            else:
                response_data['generated_literary_work'] = "Ошибка при генерации текста."
                print("Ошибка или некорректный результат от generate_literary_work")
        
        if 'image' in generation_types:
            try:
                print("Начало генерации изображения")
                # Убедимся, что папка для изображений существует
                os.makedirs(os.path.join('static', 'generated_images'), exist_ok=True)
                
                image_result = analyzer.generate_image_from_diary(diary_text, base_emotions)
                print(f"Генерация изображения завершена: {image_result.get('success', False)}")
                
                if image_result.get('success', False):
                    # Преобразуем пути к изображениям в URL-адреса
                    local_path = image_result.get('local_path', '')
                    print(f"Локальный путь к изображению: {local_path}")
                    
                    if local_path and os.path.exists(local_path):
                        # Если путь начинается с 'static/', преобразуем его в URL
                        if local_path.startswith('static/'):
                            image_url = '/' + local_path
                        elif local_path.startswith('static\\'):
                            # Для Windows пути
                            image_url = '/' + local_path.replace('\\', '/')
                        else:
                            # Пытаемся преобразовать любой другой путь
                            image_url = '/' + local_path.replace('\\', '/')
                    else:
                        # Если локальный путь не существует, используем внешний URL
                        image_url = image_result.get('image_url', '')
                        print(f"Локальный путь не найден, используем внешний URL")
                    
                    print(f"URL изображения: {image_url}")
                    
                    response_data['generated_image'] = {
                        'success': True,
                        'image_url': image_url,
                        'external_url': image_result.get('image_url', '')
                    }

                    if current_user.is_authenticated and image_result.get('success'):
                        try:
                            # file_path_or_id будет URL, если это внешний URL, или относительный путь, если локальный
                            img_path_to_save = local_path if local_path and os.path.exists(local_path) else image_result.get('image_url', '')
                            # Если img_path_to_save это полный путь, нужно получить относительный от static/
                            if os.path.isabs(img_path_to_save) and 'static' in img_path_to_save:
                                img_path_to_save = os.path.relpath(img_path_to_save, 'static')

                            new_generation = UserGeneration(
                                user_id=current_user.id,
                                generation_type='image',
                                file_path_or_id=img_path_to_save, 
                                title="Сгенерированное изображение",
                                snippet_or_description=image_result.get('prompt_used', diary_text[:200] + "...") # Сохраняем промпт или начало текста дневника
                            )
                            db.session.add(new_generation)
                            db.session.commit()
                            print(f"Запись о генерации изображения для пользователя {current_user.id} сохранена.")
                        except Exception as e:
                            db.session.rollback()
                            print(f"Ошибка сохранения UserGeneration для изображения: {e}")

                else:
                    error_message = image_result.get('error', 'Неизвестная ошибка при генерации изображения')
                    print(f"Ошибка генерации изображения: {error_message}")
                    
                    # Проверяем, связана ли ошибка с политикой содержания
                    if 'type' in image_result and image_result['type'] == 'content_policy_violation':
                        # Если тип уже определен в image_result, используем его напрямую
                        response_data['generated_image'] = {
                            'success': False,
                            'error': error_message,
                            'type': 'content_policy_violation',
                            'can_regenerate_safe': image_result.get('can_regenerate_safe', True),
                            'technical_error': image_result.get('technical_error', '')
                        }
                    elif any(term in error_message.lower() for term in 
                          ["content_policy_violation", "policy", "violates", "content policy", "насилия", "насилие"]):
                        # Если ошибка похожа на нарушение политики содержания
                        response_data['generated_image'] = {
                            'success': False,
                            'error': "Текст содержит описания, которые невозможно визуализировать согласно политике OpenAI.",
                            'type': 'content_policy_violation',
                            'can_regenerate_safe': True,
                            'technical_error': error_message
                        }
                    else:
                        # Другие типы ошибок
                        response_data['generated_image'] = {
                            'success': False,
                            'error': error_message
                        }
            except Exception as img_error:
                print(f"Исключение при генерации изображения: {str(img_error)}")
                import traceback
                traceback.print_exc()
                
                error_message = str(img_error)
                # Проверяем, связана ли ошибка с политикой содержания
                if any(term in error_message.lower() for term in 
                      ["content_policy_violation", "policy", "violates", "content policy", "насилия", "насилие"]):
                    response_data['generated_image'] = {
                        'success': False,
                        'error': "Текст содержит описания, которые невозможно визуализировать согласно политике OpenAI.",
                        'type': 'content_policy_violation',
                        'can_regenerate_safe': True,
                        'technical_error': error_message
                    }
                else:
                    response_data['generated_image'] = {
                        'success': False,
                        'error': f"Ошибка: {str(img_error)}"
                    }
        
        if 'music' in generation_types:
            print("Начало запроса на генерацию музыки")
            base_url_for_music = request.host_url.rstrip('/') # Получаем базовый URL для коллбека
            music_data = analyzer.generate_music(diary_text, base_emotions, base_url=base_url_for_music)
            
            if music_data and music_data.get('success') and music_data.get('task_id'):
                response_data['generated_music'] = {
                    'success': True,
                    'task_id': music_data['task_id'],
                    'message': music_data.get('message', 'Запрос на генерацию музыки отправлен.'),
                    'status_check_url': music_data.get('status_check_url', url_for('check_music_status', task_id=music_data['task_id']))
                }
                print(f"Запрос на генерацию музыки успешно отправлен. Task ID: {music_data['task_id']}")
                
                if current_user.is_authenticated:
                    try:
                        new_generation = UserGeneration(
                            user_id=current_user.id,
                            generation_type='music',
                            file_path_or_id=music_data['task_id'], # Сохраняем task_id
                            title=music_data.get('title', "Музыкальный трек (в обработке)"), # Используем title если есть
                            snippet_or_description=music_data.get('prompt_used', "Запрошена генерация музыки по тексту дневника.")
                        )
                        db.session.add(new_generation)
                        db.session.commit()
                        print(f"Запись о запросе на генерацию музыки для пользователя {current_user.id} сохранена (Task ID: {music_data['task_id']}).")
                    except Exception as e:
                        db.session.rollback()
                        print(f"Ошибка сохранения UserGeneration для музыки (запрос): {e}")
            else:
                error_msg = music_data.get('error', 'Неизвестная ошибка при генерации музыки')
                print(f"Ошибка генерации музыки: {error_msg}")
                response_data['generated_music'] = {
                    'success': False,
                    'error': error_msg
                }
        
        print("=== Обработка запроса /analyze успешно завершена ===")
        return jsonify(response_data)
    except Exception as e:
        print(f"Критическая ошибка в /analyze: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Это имя пользователя уже занято')
            return redirect(url_for('register'))
        
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        
        flash('Неверное имя пользователя или пароль')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/topic/new', methods=['GET', 'POST'])
@login_required
def new_topic():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            flash('Заполните все поля')
            return redirect(url_for('new_topic'))
        
        topic = Topic(title=title, author=current_user)
        db.session.add(topic)
        
        message = Message(content=content, topic=topic, author=current_user)
        db.session.add(message)
        
        db.session.commit()
        return redirect(url_for('view_topic', topic_id=topic.id))
    
    return render_template('new_topic.html')

@app.route('/topic/<int:topic_id>')
def view_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    messages = Message.query.filter_by(topic_id=topic_id).order_by(Message.created_at).all()
    return render_template('topic.html', topic=topic, messages=messages)

@app.route('/topic/<int:topic_id>/reply', methods=['POST'])
@login_required
def reply(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    content = request.form.get('content')
    
    if not content:
        flash('Сообщение не может быть пустым')
        return redirect(url_for('view_topic', topic_id=topic_id))
    
    message = Message(content=content, topic=topic, author=current_user)
    db.session.add(message)
    db.session.commit()
    
    return redirect(url_for('view_topic', topic_id=topic_id))

@app.route('/message/<int:message_id>/delete', methods=['POST'])
@login_required
def delete_message(message_id):
    message = Message.query.get_or_404(message_id)
    topic_id = message.topic_id
    
    # Проверяем, является ли текущий пользователь автором сообщения
    if message.author != current_user:
        flash('У вас нет прав для удаления этого сообщения')
        return redirect(url_for('view_topic', topic_id=topic_id))
    
    # Удаляем сообщение
    db.session.delete(message)
    db.session.commit()
    
    flash('Сообщение было удалено')
    return redirect(url_for('view_topic', topic_id=topic_id))

@app.route('/topic/<int:topic_id>/vote', methods=['POST'])
@login_required
def vote_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    vote_type = int(request.form.get('vote_type', 0))
    
    if vote_type not in [-1, 0, 1]:
        return jsonify({'error': 'Неверный тип голоса'}), 400
        
    existing_vote = TopicVote.query.filter_by(
        topic_id=topic_id,
        user_id=current_user.id
    ).first()
    
    if existing_vote:
        if existing_vote.vote_type == vote_type:
            # Отмена голоса
            if existing_vote.vote_type == 1:
                topic.votes_up -= 1
            else:
                topic.votes_down -= 1
            db.session.delete(existing_vote)
        else:
            # Изменение голоса
            if vote_type == 0:
                if existing_vote.vote_type == 1:
                    topic.votes_up -= 1
                else:
                    topic.votes_down -= 1
                db.session.delete(existing_vote)
            else:
                if existing_vote.vote_type == 1:
                    topic.votes_up -= 1
                    topic.votes_down += 1
                else:
                    topic.votes_down -= 1
                    topic.votes_up += 1
                existing_vote.vote_type = vote_type
    elif vote_type != 0:
        # Новый голос
        vote = TopicVote(user_id=current_user.id, topic_id=topic_id, vote_type=vote_type)
        if vote_type == 1:
            topic.votes_up += 1
        else:
            topic.votes_down += 1
        db.session.add(vote)
    
    db.session.commit()
    return jsonify({
        'votes_up': topic.votes_up,
        'votes_down': topic.votes_down,
        'user_vote': vote_type
    })

@app.route('/message/<int:message_id>/vote', methods=['POST'])
@login_required
def vote_message(message_id):
    message = Message.query.get_or_404(message_id)
    vote_type = int(request.form.get('vote_type', 0))
    
    if vote_type not in [-1, 0, 1]:
        return jsonify({'error': 'Неверный тип голоса'}), 400
        
    existing_vote = MessageVote.query.filter_by(
        message_id=message_id,
        user_id=current_user.id
    ).first()
    
    if existing_vote:
        if existing_vote.vote_type == vote_type:
            # Отмена голоса
            if existing_vote.vote_type == 1:
                message.votes_up -= 1
            else:
                message.votes_down -= 1
            db.session.delete(existing_vote)
        else:
            # Изменение голоса
            if vote_type == 0:
                if existing_vote.vote_type == 1:
                    message.votes_up -= 1
                else:
                    message.votes_down -= 1
                db.session.delete(existing_vote)
            else:
                if existing_vote.vote_type == 1:
                    message.votes_up -= 1
                    message.votes_down += 1
                else:
                    message.votes_down -= 1
                    message.votes_up += 1
                existing_vote.vote_type = vote_type
    elif vote_type != 0:
        # Новый голос
        vote = MessageVote(user_id=current_user.id, message_id=message_id, vote_type=vote_type)
        if vote_type == 1:
            message.votes_up += 1
        else:
            message.votes_down += 1
        db.session.add(vote)
    
    db.session.commit()
    return jsonify({
        'votes_up': message.votes_up,
        'votes_down': message.votes_down,
        'user_vote': vote_type
    })

@app.route('/topic/<int:topic_id>/delete', methods=['POST'])
@login_required
def delete_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    
    # Проверяем, является ли текущий пользователь автором темы
    if topic.author != current_user:
        flash('У вас нет прав для удаления этой темы')
        return redirect(url_for('view_topic', topic_id=topic_id))
    
    # Удаляем тему (каскадное удаление удалит все связанные сообщения и голоса)
    db.session.delete(topic)
    db.session.commit()
    
    flash('Тема была успешно удалена')
    return redirect(url_for('index'))

@app.route('/share_analysis', methods=['POST'])
@login_required
def share_analysis():
    try:
        data = request.get_json()
        
        # Создаем запись обратной связи
        feedback = UserFeedback(
            content_type=data.get('content_type'),
            feedback_type=data.get('feedback_type'),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            timestamp=datetime.utcnow()
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        # Возвращаем общее количество для этого типа контента
        total_count = UserFeedback.query.filter_by(
            content_type=data.get('content_type'),
            feedback_type=data.get('feedback_type')
        ).count()
        
        return jsonify({
            'success': True,
            'message': 'Обратная связь сохранена',
            'total_count': total_count
        })
        
    except Exception as e:
        print(f"Ошибка при сохранении обратной связи: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Не удалось сохранить обратную связь'
        }), 500

@app.route('/introduction')
def introduction():
    return render_template('introduction.html')

@app.route('/documentation')
def documentation():
    return render_template('documentation.html')

@app.route('/generate_image', methods=['POST'])
def generate_image():
    try:
        print("=== Начало обработки запроса /generate_image ===")
        data = request.get_json()
        
        # Проверяем наличие текста
        text = data.get('text', '')
        if not text:
            return jsonify({'success': False, 'error': 'Текст не может быть пустым'}), 400
        
        # Проверяем наличие эмоционального анализа
        emotion_analysis = data.get('emotion_analysis', None)
        
        print(f"Получен текст длиной {len(text)} символов")
        analyzer = WarDiaryAnalyzer()
        
        # Генерация изображения
        image_result = analyzer.generate_image_from_diary(text, emotion_analysis)
        print(f"Генерация изображения завершена: {image_result.get('success', False)}")
        
        if not image_result.get('success', False):
            # Передаем все поля из image_result, включая type и can_regenerate_safe, если они есть
            response_data = {
                'success': False,
                'error': image_result.get('error', 'Не удалось сгенерировать изображение')
            }
            
            # Добавляем дополнительные поля, если они есть
            if 'type' in image_result:
                response_data['type'] = image_result['type']
            if 'can_regenerate_safe' in image_result:
                response_data['can_regenerate_safe'] = image_result['can_regenerate_safe']
            if 'technical_error' in image_result:
                response_data['technical_error'] = image_result['technical_error']
                
            return jsonify(response_data), 500
        
        # Преобразуем пути к изображениям в URL-адреса
        local_path = image_result.get('local_path', '')
        image_url = ''
        
        print(f"Локальный путь изображения: {local_path}")
        
        if local_path:
            # Нормализуем путь для разных ОС
            normalized_path = local_path.replace('\\', '/')
            
            # Убедимся, что путь начинается с static/
            if normalized_path.startswith('static/'):
                image_url = '/' + normalized_path
            elif 'static/' in normalized_path:
                # Находим часть пути начиная с static/
                static_index = normalized_path.find('static/')
                image_url = '/' + normalized_path[static_index:]
            else:
                # Если локального пути нет или он некорректный, используем внешний URL
                image_url = image_result.get('image_url', '')
        else:
            # Используем внешний URL, если локального пути нет
            image_url = image_result.get('image_url', '')
        
        print(f"Итоговый URL изображения: {image_url}")
        
        response_data = {
            'success': True,
            'image_url': image_url,
            'external_url': image_result.get('image_url', '')
        }
        
        print("=== Обработка запроса /generate_image успешно завершена ===")
        return jsonify(response_data)
    except Exception as e:
        print(f"Критическая ошибка в /generate_image: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/generate_safe_image', methods=['POST'])
def generate_safe_image():
    """
    Генерирует безопасную (символическую/метафорическую) версию изображения для 
    дневникового текста, который не прошел модерацию из-за упоминания насилия.
    
    Этот эндпоинт вызывается после того, как пользователь согласился 
    генерировать альтернативное изображение.
    """
    try:
        diary_text = request.form.get('diary_text', '')
        
        if not diary_text:
            return jsonify({'success': False, 'error': 'Текст дневника не указан'}), 400
        
        # Создаем анализатор
        analyzer = WarDiaryAnalyzer()
        
        # Проводим эмоциональный анализ для лучшей генерации
        emotions = analyzer.analyze_emotions(diary_text)
        
        # Логируем начало безопасной генерации
        print(f"Начинаем генерацию БЕЗОПАСНОГО символического изображения по запросу пользователя")
        
        # Генерируем символическое изображение
        result = analyzer.generate_safe_image_from_diary(diary_text, emotions)
        
        print(f"Результат генерации безопасного изображения: {result}")
        
        # Формируем ответ
        if result.get('success', False):
            # Получаем URL изображения
            image_url = result.get('image_url', '')
            local_path = result.get('local_path', '')
            
            # Используем локальный путь, если доступен, иначе внешний URL
            display_url = f"/{local_path}" if local_path else image_url
            
            # Если локальный путь не начинается с /, добавляем его
            if display_url and not display_url.startswith('/'):
                display_url = '/' + display_url
            
            print(f"Безопасное изображение - локальный путь: {local_path}")
            print(f"Безопасное изображение - итоговый URL: {display_url}")
                
            return jsonify({
                'success': True, 
                'image_url': display_url,
                'external_url': image_url,  # Сохраняем внешний URL как запасной вариант
                'is_safe_alternative': True,
                'message': 'Создано символическое изображение на основе дневникового текста вместо прямой иллюстрации'
            })
        else:
            # Если произошла ошибка
            error_message = result.get('error', 'Неизвестная ошибка при генерации изображения')
            return jsonify({
                'success': False,
                'error': error_message,
                'technical_error': result.get('technical_error', '')
            }), 500
            
    except Exception as e:
        print(f"Ошибка при генерации безопасного изображения: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': f"Ошибка при генерации безопасного изображения: {str(e)}"
        }), 500

@app.route('/generate_music', methods=['POST'])
def generate_music():
    try:
        print("=== Начало обработки запроса /generate_music ===")
        data = request.get_json()
        
        # Проверяем наличие текста
        text = data.get('text', '')
        if not text:
            return jsonify({'success': False, 'error': 'Текст не может быть пустым'}), 400
        
        # Проверяем наличие эмоционального анализа
        emotion_analysis = data.get('emotion_analysis', None)
        
        print(f"Получен текст длиной {len(text)} символов")
        analyzer = WarDiaryAnalyzer()
        
        # Генерация музыки (только отправка задачи, не ожидание результата)
        # Используем внешний URL, если он указан, или request.host_url в противном случае
        base_url = os.environ.get('EXTERNAL_URL', request.host_url.rstrip('/'))
        print(f"Используется base_url для коллбэка: {base_url}")
        music_result = analyzer.generate_music(text, emotion_analysis, base_url=base_url, wait_for_result=False)
        print(f"Генерация музыки: {music_result}")
        
        if not music_result.get('success', False):
            return jsonify({
                'success': False,
                'error': music_result.get('error', 'Не удалось сгенерировать музыку')
            }), 500
        
        # Сразу возвращаем task_id и статус ожидания
        response_data = {
            'success': True,
            'task_id': music_result.get('task_id', ''),
            'status': 'processing',
            'music_description': music_result.get('music_description', '')
        }
        print("=== Обработка запроса /generate_music завершена (асинхронно) ===")
        return jsonify(response_data)
    except Exception as e:
        print(f"Критическая ошибка в /generate_music: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/check_music_status')
def check_music_status():
    """
    Проверяет статус задачи генерации музыки.
    """
    try:
        # Получаем task_id из параметров запроса
        task_id = request.args.get('task_id')
        if not task_id:
            return jsonify({'success': False, 'error': 'Не указан task_id', 'status': 'error'}), 200
        print(f"Получен запрос на проверку статуса для задачи: {task_id}")
        metadata_path = os.path.join('static', 'generated_music', f"music_metadata_{task_id}.json")
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Проверка наличия локального аудиофайла
                local_audio_path = metadata.get('local_audio_path', '')
                local_audio_url = None
                
                if local_audio_path and os.path.exists(local_audio_path) and os.path.getsize(local_audio_path) > 0:
                    audio_filename = os.path.basename(local_audio_path)
                    local_audio_url = f"/static/generated_music/audio/{audio_filename}"
                    print(f"Локальный аудиофайл найден: {local_audio_url}")
                    
                    # Если файл существует, возвращаем успешный ответ с данными
                    return jsonify({
                        'success': True,
                        'status': 'complete',
                        'local_audio_url': local_audio_url,
                        'is_music_ready': True,
                        'music_description': metadata.get('music_description', 'Сгенерированная музыка'),
                        'style': metadata.get('style', ''),
                        'mood': metadata.get('mood', '')
                    }), 200
                
                # Проверяем наличие аудио URL в метаданных (которые могли быть обновлены callback'ом)
                audio_url = metadata.get('audio_url', '')
                stream_url = metadata.get('stream_url', '')
                embed_url = metadata.get('embed_url', '')
                
                # Если есть какой-либо URL аудио, считаем, что музыка готова
                if audio_url or stream_url or embed_url or metadata.get('status') == 'complete':
                    print(f"Найдены URL'ы аудио, но локальный файл отсутствует")
                    
                    # Формируем прокси URL для аудиофайла, если он не был скачан локально
                    proxy_url = f"/proxy_audio?url={urllib.parse.quote(audio_url)}" if audio_url else ""
                    
                    return jsonify({
                        'success': True,
                        'status': 'complete',
                        'is_music_ready': True,
                        'audio_url': audio_url,
                        'stream_url': stream_url,
                        'embed_url': embed_url,
                        'proxy_url': proxy_url,
                        'local_audio_url': local_audio_url,
                        'music_description': metadata.get('music_description', 'Сгенерированная музыка')
                    }), 200
                
                # Если файлов нет, но есть последние данные коллбэка, проверяем их
                if 'last_callback' in metadata and metadata['last_callback']:
                    callback_data = metadata['last_callback']
                    if isinstance(callback_data, dict):
                        # Проверяем данные из callback на наличие URL'ов
                        data_field = callback_data.get('data', {})
                        
                        # Извлекаем URL'ы аудио из разных возможных мест в callback данных
                        audio_url = data_field.get('audio_url') or callback_data.get('audio_url') or ''
                        stream_url = data_field.get('stream_url') or callback_data.get('stream_url') or ''
                        
                        if audio_url or stream_url:
                            print(f"Найдены URL'ы аудио в callback данных")
                            proxy_url = f"/proxy_audio?url={urllib.parse.quote(audio_url)}" if audio_url else ""
                            
                            return jsonify({
                                'success': True,
                                'status': 'complete',
                                'is_music_ready': True,
                                'audio_url': audio_url,
                                'stream_url': stream_url,
                                'proxy_url': proxy_url,
                                'music_description': metadata.get('music_description', 'Сгенерированная музыка')
                            }), 200
            except Exception as e:
                print(f"Ошибка при чтении метаданных: {str(e)}")
                # Продолжаем выполнение, чтобы проверить статус через API
        
        # Если не удалось получить данные из локального файла, проверяем через API
        analyzer = WarDiaryAnalyzer()
        status_response = analyzer._check_music_generation_status(task_id)
        
        # Если получен успешный статус от API, обновляем его
        if status_response.get('status') == 'complete' and (status_response.get('audio_url') or status_response.get('stream_url')):
            print(f"API вернул статус complete для задачи {task_id}")
            status_response['is_music_ready'] = True
            
            # Добавляем прокси URL для аудио
            if status_response.get('audio_url'):
                status_response['proxy_url'] = f"/proxy_audio?url={urllib.parse.quote(status_response['audio_url'])}"
        
        print(f"Возвращаем статус: {status_response.get('status')}")
        return jsonify(status_response), 200
    except Exception as e:
        print(f"Ошибка при проверке статуса музыки: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'status': 'error',
            'message': f"Ошибка при проверке статуса: {str(e)}",
        }), 200

@app.route('/music_callback', methods=['POST'])
def music_callback():
    data = request.json
    print(f"Получены данные коллбэка от Suno: {json.dumps(data, indent=2)}")

    # Извлекаем task_id из данных коллбэка (может быть в data или data[0])
    task_id = None
    processed_data = None
    if isinstance(data, list) and len(data) > 0:
        task_id = data[0].get('id')
        processed_data = data[0]
    elif isinstance(data, dict):
        task_id = data.get('id')
        processed_data = data

    if not task_id:
        print("Коллбэк от Suno не содержит task_id")
        return jsonify({'status': 'error', 'message': 'task_id is missing'}), 400

    print(f"Коллбэк для Task ID: {task_id}")

    # Проверяем, есть ли уже обработанные метаданные для этого task_id
    music_dir = os.path.join('static', 'generated_music')
    metadata_filename_pattern = f"music_metadata_{task_id}_*.json"
    
    # Ищем файл метаданных
    found_metadata_files = []
    if os.path.exists(music_dir):
        for filename in os.listdir(music_dir):
            if filename.startswith(f"music_metadata_{task_id}") and filename.endswith(".json"):
                found_metadata_files.append(filename)
    
    if found_metadata_files:
        print(f"Найдены существующие метаданные для task_id {task_id}: {found_metadata_files}. Коллбэк, вероятно, уже обработан.")
        # Можно вернуть success, так как данные уже есть, или обработать как дубликат
        # return jsonify({'status': 'success', 'message': 'Callback already processed or metadata exists'}), 200

    try:
        analyzer = WarDiaryAnalyzer() # Создаем экземпляр, если методы _process_callback_data или другие нужны
        # Сохранение трека и метаданных (эта функция должна быть в WarDiaryAnalyzer или здесь)
        # Предположим, что _process_callback_data возвращает словарь с информацией о треке,
        # включая 'local_path' для аудиофайла и 'title'.
        # ИЛИ, если _process_callback_data делает всю работу по сохранению, то это не нужно тут.
        
        # Пример того, как можно было бы получить информацию (если _process_callback_data возвращает ее):
        # track_info = analyzer._process_callback_data(processed_data) # Убедитесь, что метод доступен и правильно вызывается

        # Просто сохраним сырые данные коллбэка как JSON для этого task_id, если еще нет метаданных
        # Это позволит нам позже обработать их, если что-то пойдет не так с UserGeneration
        if not found_metadata_files and processed_data:
            raw_callback_dir = os.path.join(music_dir, 'raw_callbacks')
            os.makedirs(raw_callback_dir, exist_ok=True)
            raw_callback_path = os.path.join(raw_callback_dir, f"raw_callback_{task_id}_{int(time.time())}.json")
            with open(raw_callback_path, 'w', encoding='utf-8') as f_raw:
                json.dump(processed_data, f_raw, ensure_ascii=False, indent=4)
            print(f"Сырые данные коллбэка для task_id {task_id} сохранены в {raw_callback_path}")

        # --- Обновление UserGeneration ---
        # Ищем запись UserGeneration по task_id
        generation_entry = UserGeneration.query.filter_by(generation_type='music', file_path_or_id=task_id).first()

        if generation_entry:
            print(f"Найдена запись UserGeneration для task_id {task_id} (ID: {generation_entry.id})")
            # Пытаемся извлечь полезную информацию из processed_data
            # Путь к файлу и название нужно будет определить на основе того, как WarDiaryAnalyzer
            # обрабатывает и сохраняет музыку после коллбэка.
            # Сейчас мы этого точно не знаем, поэтому оставим file_path_or_id как task_id, 
            # но попытаемся обновить title, если он есть в коллбэке.

            new_title = generation_entry.title # Сохраняем старое название по умолчанию
            if processed_data and processed_data.get('title'):
                new_title = processed_data.get('title')
            elif processed_data and processed_data.get('audio_url'): # Пытаемся извлечь имя файла из URL
                try:
                    parsed_url = urllib.parse.urlparse(processed_data.get('audio_url'))
                    filename_from_url = os.path.basename(parsed_url.path)
                    if filename_from_url:
                        new_title = filename_from_url
                except Exception as e_parse:
                    print(f"Не удалось извлечь имя файла из audio_url: {e_parse}")
            
            # Предположим, что музыка уже сохранена где-то и `file_path_or_id` должен указывать на файл
            # Это сложная часть, так как имя файла не всегда очевидно из коллбэка.
            # Если WarDiaryAnalyzer._process_callback_data сохраняет файл и возвращает его путь, это было бы идеально.
            # Пока что оставим file_path_or_id как task_id, так как это надежный идентификатор.
            # В профиле пользователя мы сможем использовать этот task_id для поиска соответствующего трека.

            generation_entry.title = new_title
            generation_entry.snippet_or_description = json.dumps(processed_data) # Сохраняем весь коллбэк в описание для отладки/информации
            generation_entry.updated_at = datetime.utcnow() # Если есть поле updated_at в модели
            
            try:
                db.session.commit()
                print(f"Запись UserGeneration для task_id {task_id} обновлена (название: {new_title}).")
            except Exception as e_commit:
                db.session.rollback()
                print(f"Ошибка коммита при обновлении UserGeneration для task_id {task_id}: {e_commit}")
        else:
            print(f"Запись UserGeneration для task_id {task_id} не найдена. Возможно, генерация была не от пользователя.")
        
        # Здесь должен быть вызов функции, которая фактически скачивает аудио и сохраняет метаданные
        # Например, WarDiaryAnalyzer()._process_callback_data(processed_data)
        # Сейчас этот вызов закомментирован или отсутствует в предоставленном коде app.py, что может быть проблемой.
        # Если метод analyzer._process_callback_data(processed_data) есть и он вызывается где-то еще 
        # (например, в check_music_status после получения коллбэка), то логика здесь может быть избыточной.
        # Важно, чтобы _process_callback_data был вызван ОДИН РАЗ для каждого успешного коллбэка.

        # Если WarDiaryAnalyzer.process_track_data используется для обработки и сохранения:
        if processed_data and processed_data.get('status') == 'complete':
            print(f"Коллбэк для task_id {task_id} имеет статус 'complete'. Попытка обработки...")
            try:
                # process_track_data ожидает 'metadata' и 'track' как в API Suno
                # В нашем случае processed_data это и есть 'track' или 'metadata'
                # Мы передаем его как track, а metadata формируем минимально
                mock_metadata_for_processing = {
                    'id': task_id,
                    'title': processed_data.get('title', 'Untitled Track'),
                    'tags': processed_data.get('tags'),
                    'prompt': processed_data.get('metadata', {}).get('prompt', '') 
                    # ... другие поля, которые могут понадобиться process_track_data
                }
                # process_track_data(mock_metadata_for_processing, processed_data, task_id) # Вызов функции из app.py
                # Эта функция сама сохранит метаданные и аудио.
                # Важно: убедитесь, что process_track_data корректно обрабатывает данные и не конфликтует с UserGeneration.
                # Сейчас я не буду ее вызывать, чтобы избежать двойной обработки или ошибок, если она не готова.
                print(f"Предполагается, что process_track_data будет вызван для task_id {task_id} для сохранения аудио и метаданных.")
            except Exception as e_process_track:
                print(f"Ошибка при вызове process_track_data для task_id {task_id}: {e_process_track}")
        else:
            print(f"Коллбэк для task_id {task_id} не имеет статуса 'complete' (статус: {processed_data.get('status')}). Пропуск основной обработки.")

        return jsonify({'status': 'success', 'message': 'Callback received'}), 200

    except Exception as e:
        print(f"Ошибка при обработке коллбэка Suno для task_id {task_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'Internal server error: {str(e)}'}), 500

@app.route('/proxy_audio')
def proxy_audio():
    """
    Проксирование запросов к аудиофайлам для обхода CORS и других ограничений.
    """
    try:
        url = request.args.get('url')
        if not url:
            return "URL parameter is required", 400
        
        print(f"Проксирование аудио из URL: {url}")
        
        # Настройки запроса
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'audio/*, */*',
            'Connection': 'keep-alive'
        }
        timeout = 60  # Увеличиваем тайм-аут до 60 секунд
        
        # Используем requests для получения содержимого файла
        # Отключаем стриминг и получаем весь файл сразу - решение проблемы с потоком
        response = requests.get(url, headers=headers, timeout=timeout, stream=False)
        response.raise_for_status()
        
        # Получаем данные аудиофайла полностью в память
        audio_data = response.content
        
        # Определяем тип контента
        content_type = response.headers.get('Content-Type', 'audio/mpeg')
        if 'audio' not in content_type:
            content_type = 'audio/mpeg'  # Устанавливаем по умолчанию audio/mpeg
        
        # Формируем ответ с правильными заголовками
        flask_response = Response(audio_data)
        flask_response.headers['Content-Type'] = content_type
        flask_response.headers['Content-Length'] = str(len(audio_data))
        flask_response.headers['Content-Disposition'] = 'inline; filename="audio.mp3"'
        flask_response.headers['Accept-Ranges'] = 'bytes'
        flask_response.headers['X-Proxy-Status'] = 'Success'
        flask_response.headers['Access-Control-Allow-Origin'] = '*'
        
        print(f"Успешно получен аудиофайл, размер: {len(audio_data)} байт, тип: {content_type}")
        
        return flask_response
        
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при проксировании аудио: {str(e)}")
        error_message = f"Ошибка при получении аудио: {str(e)}"
        return jsonify({'error': error_message}), 500
    except Exception as e:
        print(f"Неизвестная ошибка при проксировании аудио: {str(e)}")
        return jsonify({'error': f"Неизвестная ошибка: {str(e)}"}), 500

@app.route('/forum')
def forum():
    return redirect(url_for('index'))

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    try:
        data = request.get_json()
        
        # Создаем запись обратной связи
        feedback = UserFeedback(
            content_type=data.get('content_type'),
            feedback_type=data.get('feedback_type'),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            timestamp=datetime.utcnow()
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        # Возвращаем общее количество для этого типа контента
        total_count = UserFeedback.query.filter_by(
            content_type=data.get('content_type'),
            feedback_type=data.get('feedback_type')
        ).count()
        
        return jsonify({
            'success': True,
            'message': 'Обратная связь сохранена',
            'total_count': total_count
        })
        
    except Exception as e:
        print(f"Ошибка при сохранении обратной связи: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Не удалось сохранить обратную связь'
        }), 500

@app.route('/submit_detailed_feedback', methods=['POST'])
def submit_detailed_feedback():
    try:
        data = request.get_json()
        
        # Валидация данных
        if not data.get('content_type') or not data.get('main_rating'):
            return jsonify({
                'success': False,
                'error': 'Не хватает обязательных данных'
            }), 400
        
        # Создаем запись детальной обратной связи
        feedback_data = {
            'content_type': data.get('content_type'),
            'main_rating': int(data.get('main_rating')),
            'criteria_ratings': data.get('criteria_ratings', {}),
            'feedback_text': data.get('feedback_text', ''),
            'session_id': data.get('session_id', ''),
            'timestamp': data.get('timestamp'),
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', '')
        }
        
        # Сохраняем в базу данных (можно создать отдельную таблицу для детальной обратной связи)
        # Пока сохраним как JSON в существующей таблице
        feedback = UserFeedback(
            content_type=data.get('content_type'),
            feedback_type='detailed_rating',
            feedback_data=json.dumps(feedback_data, ensure_ascii=False),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            timestamp=datetime.utcnow()
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Детальная оценка сохранена',
            'feedback_id': feedback.id
        })
        
    except Exception as e:
        print(f"Ошибка при сохранении детальной оценки: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Не удалось сохранить оценку: {str(e)}'
        }), 500

# Добавляем маршрут для обслуживания сгенерированных изображений
@app.route('/static/generated_images/<filename>')
def generated_image(filename):
    """Обслуживание сгенерированных изображений"""
    return send_from_directory(os.path.join(app.root_path, 'static', 'generated_images'), filename)

# Добавляем маршрут для обслуживания сгенерированной музыки
@app.route('/static/generated_music/<path:filename>')
def generated_music(filename):
    """Обслуживание сгенерированной музыки"""
    return send_from_directory(os.path.join(app.root_path, 'static', 'generated_music'), filename)

# Добавляем функцию для поиска завершенных музыкальных задач
def find_available_music_tasks():
    """
    Ищет завершенные музыкальные задачи в папке generated_music
    """
    try:
        music_dir = os.path.join('static', 'generated_music')
        if not os.path.exists(music_dir):
            return []
        
        available_tasks = []
        
        # Ищем все файлы метаданных
        for filename in os.listdir(music_dir):
            if filename.startswith('music_metadata_') and filename.endswith('.json'):
                try:
                    metadata_path = os.path.join(music_dir, filename)
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    # Проверяем, есть ли готовая музыка
                    if (metadata.get('status') == 'complete' and 
                        (metadata.get('audio_url') or metadata.get('stream_url') or 
                         metadata.get('local_audio_url') or metadata.get('local_audio_path'))):
                        
                        task_info = {
                            'task_id': metadata.get('task_id'),
                            'title': metadata.get('title', 'Без названия'),
                            'created_at': metadata.get('created_at'),
                            'audio_url': metadata.get('audio_url', ''),
                            'stream_url': metadata.get('stream_url', ''),
                            'local_audio_url': metadata.get('local_audio_url', ''),
                            'music_description': metadata.get('music_description', ''),
                            'style': metadata.get('style', ''),
                            'mood': metadata.get('mood', '')
                        }
                        available_tasks.append(task_info)
                        
                except Exception as e:
                    print(f"Ошибка при чтении {filename}: {e}")
                    continue
        
        # Сортируем по дате создания (новые первыми)
        available_tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return available_tasks
        
    except Exception as e:
        print(f"Ошибка при поиске завершенных задач: {e}")
        return []

# Добавляем endpoint для получения списка готовой музыки
@app.route('/available_music')
def available_music():
    """
    Возвращает список доступной готовой музыки
    """
    try:
        tasks = find_available_music_tasks()
        return jsonify({
            'success': True,
            'tasks': tasks,
            'count': len(tasks)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/delete_music_track/<task_id>', methods=['POST'])
def delete_music_track(task_id):
    """
    Удаляет музыкальный трек и связанные с ним файлы
    """
    try:
        print(f"Запрос на удаление трека: {task_id}")
        
        # Проверяем валидность task_id (только буквы, цифры и некоторые символы)
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', task_id):
            return jsonify({
                'success': False,
                'error': 'Некорректный идентификатор трека'
            }), 400
        
        deleted_files = []
        
        # Удаляем файл метаданных
        metadata_path = os.path.join('static', 'generated_music', f"music_metadata_{task_id}.json")
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
            deleted_files.append(f"music_metadata_{task_id}.json")
            print(f"Удален файл метаданных: {metadata_path}")
        
        # Удаляем аудиофайл
        audio_path = os.path.join('static', 'generated_music', 'audio', f"music_{task_id}.mp3")
        if os.path.exists(audio_path):
            os.remove(audio_path)
            deleted_files.append(f"music_{task_id}.mp3")
            print(f"Удален аудиофайл: {audio_path}")
        
        # Удаляем обложку
        cover_path = os.path.join('static', 'generated_music', 'covers', f"cover_{task_id}.jpg")
        if os.path.exists(cover_path):
            os.remove(cover_path)
            deleted_files.append(f"cover_{task_id}.jpg")
            print(f"Удалена обложка: {cover_path}")
        
        if not deleted_files:
            return jsonify({
                'success': False,
                'error': 'Трек не найден или уже удален'
            }), 404
        
        return jsonify({
            'success': True,
            'message': f'Трек {task_id} успешно удален',
            'deleted_files': deleted_files
        })
        
    except Exception as e:
        print(f"Ошибка при удалении трека {task_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Ошибка при удалении трека: {str(e)}'
        }), 500

@app.route('/cleanup_music_tracks', methods=['POST'])
def cleanup_music_tracks():
    """
    Очищает старые или незавершенные музыкальные треки
    """
    try:
        data = request.get_json() or {}
        cleanup_type = data.get('type', 'incomplete')  # 'incomplete', 'old', 'all'
        
        print(f"Запрос на очистку треков типа: {cleanup_type}")
        
        music_dir = os.path.join('static', 'generated_music')
        if not os.path.exists(music_dir):
            return jsonify({
                'success': True,
                'message': 'Папка с музыкой не найдена',
                'deleted_count': 0
            })
        
        deleted_tracks = []
        
        # Ищем все файлы метаданных
        for filename in os.listdir(music_dir):
            if filename.startswith('music_metadata_') and filename.endswith('.json'):
                try:
                    metadata_path = os.path.join(music_dir, filename)
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    task_id = metadata.get('task_id', '')
                    status = metadata.get('status', '')
                    created_at = metadata.get('created_at', '')
                    
                    should_delete = False
                    
                    if cleanup_type == 'incomplete':
                        # Удаляем незавершенные треки
                        if status in ['processing', 'timeout', 'error', 'unknown']:
                            should_delete = True
                    elif cleanup_type == 'old':
                        # Удаляем треки старше 7 дней
                        if created_at:
                            try:
                                from datetime import datetime, timedelta
                                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                                if datetime.now() - created_date > timedelta(days=7):
                                    should_delete = True
                            except:
                                pass
                    elif cleanup_type == 'all':
                        # Удаляем все треки
                        should_delete = True
                    
                    if should_delete and task_id:
                        # Удаляем трек
                        deleted_files = []
                        
                        # Удаляем метаданные
                        if os.path.exists(metadata_path):
                            os.remove(metadata_path)
                            deleted_files.append(filename)
                        
                        # Удаляем аудиофайл
                        audio_path = os.path.join(music_dir, 'audio', f"music_{task_id}.mp3")
                        if os.path.exists(audio_path):
                            os.remove(audio_path)
                            deleted_files.append(f"music_{task_id}.mp3")
                        
                        # Удаляем обложку
                        cover_path = os.path.join(music_dir, 'covers', f"cover_{task_id}.jpg")
                        if os.path.exists(cover_path):
                            os.remove(cover_path)
                            deleted_files.append(f"cover_{task_id}.jpg")
                        
                        deleted_tracks.append({
                            'task_id': task_id,
                            'status': status,
                            'deleted_files': deleted_files
                        })
                        
                        print(f"Удален трек {task_id} (статус: {status})")
                        
                except Exception as e:
                    print(f"Ошибка при обработке {filename}: {e}")
                    continue
        
        return jsonify({
            'success': True,
            'message': f'Очистка завершена. Удалено треков: {len(deleted_tracks)}',
            'deleted_count': len(deleted_tracks),
            'deleted_tracks': deleted_tracks
        })
        
    except Exception as e:
        print(f"Ошибка при очистке треков: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Ошибка при очистке: {str(e)}'
        }), 500

@app.route('/admin')
def admin():
    """Страница администрирования для управления треками и тестирования"""
    try:
        # --- Управление Музыкой --- #
        music_dir = os.path.join('static', 'generated_music')
        tracks = []
        if os.path.exists(music_dir):
            for filename in os.listdir(music_dir):
                if filename.startswith('music_metadata_') and filename.endswith('.json'):
                    try:
                        metadata_path = os.path.join(music_dir, filename)
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        track_info = {
                            'task_id': metadata.get('task_id', ''),
                            'title': metadata.get('title', 'Без названия'),
                            'status': metadata.get('status', 'unknown'),
                            'created_at': metadata.get('created_at', ''),
                            'style': metadata.get('style', ''),
                            'mood': metadata.get('mood', ''),
                            'has_audio': bool(metadata.get('local_audio_path') or metadata.get('audio_url')),
                            'file_size': os.path.getsize(metadata_path) if os.path.exists(metadata_path) else 0
                        }
                        tracks.append(track_info)
                    except Exception as e:
                        print(f"Ошибка при чтении метаданных музыки {filename}: {e}")
                        continue
        tracks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # --- Управление Изображениями --- #
        images_dir = os.path.join('static', 'generated_images')
        images_list = []
        if os.path.exists(images_dir):
            for img_filename in os.listdir(images_dir):
                if img_filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    try:
                        img_path = os.path.join(images_dir, img_filename)
                        img_stat = os.stat(img_path)
                        images_list.append({
                            'filename': img_filename,
                            'url': url_for('static', filename=f'generated_images/{img_filename}'),
                            'size': img_stat.st_size, # в байтах
                            'modified_date': datetime.fromtimestamp(img_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        })
                    except Exception as e:
                        print(f"Ошибка при чтении информации об изображении {img_filename}: {e}")
                        continue
        images_list.sort(key=lambda x: x.get('modified_date', ''), reverse=True)
        image_count = len(images_list)

        # --- Управление Литературными Произведениями --- #
        literary_works_dir = os.path.join('instance', 'generated_literary_works')
        literary_works_list = []
        if os.path.exists(literary_works_dir):
            for meta_filename in os.listdir(literary_works_dir):
                if meta_filename.endswith('.meta.json'):
                    try:
                        meta_path = os.path.join(literary_works_dir, meta_filename)
                        txt_filename = meta_filename.replace('.meta.json', '.txt')
                        txt_path = os.path.join(literary_works_dir, txt_filename)
                        
                        with open(meta_path, 'r', encoding='utf-8') as f_meta:
                            meta_data = json.load(f_meta)
                        
                        # Достаем сниппет текста для предпросмотра
                        text_snippet = "(Текст произведения не найден)"
                        if os.path.exists(txt_path):
                            with open(txt_path, 'r', encoding='utf-8') as f_txt:
                                text_snippet = f_txt.read(200) + ("..." if len(f_txt.read()) > 0 else "") # Показываем до 200 символов
                        
                        # Получаем имя пользователя, если user_id есть
                        username = "Анонимно"
                        if meta_data.get('user_id'):
                            user = User.query.get(meta_data['user_id'])
                            if user:
                                username = user.username
                            else:
                                username = f"Пользователь ID: {meta_data['user_id']} (удален?)"
                        
                        literary_works_list.append({
                            'file_id': meta_data.get('file_id', txt_filename.replace('.txt', '')),
                            'meta_filename': meta_filename,
                            'txt_filename': txt_filename,
                            'timestamp': meta_data.get('generation_timestamp', 'N/A'),
                            'user_id': meta_data.get('user_id'),
                            'username': username,
                            'source_snippet': meta_data.get('source_diary_text_snippet', 'N/A'),
                            'text_snippet': text_snippet
                        })
                    except Exception as e:
                        print(f"Ошибка при чтении метаданных произведения {meta_filename}: {e}")
                        continue
        literary_works_list.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        literary_works_count = len(literary_works_list)
        
        return render_template('admin.html', 
                             tracks=tracks, 
                             track_count=len(tracks),
                             images=images_list,
                             image_count=image_count,
                             literary_works=literary_works_list,
                             literary_works_count=literary_works_count
                             )
    except Exception as e:
        print(f"Ошибка в /admin: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/delete_image/<filename>', methods=['POST'])
@login_required # Рекомендуется защитить этот эндпоинт
def delete_image_admin(filename):
    # Проверка прав администратора (если необходимо, сейчас просто @login_required)
    # if not current_user.is_admin: # Предполагая, что у User есть поле is_admin
    #     flash('У вас нет прав для этого действия.', 'danger')
    #     return redirect(url_for('admin'))
    try:
        # Валидация имени файла, чтобы предотвратить выход из директории
        if '..' in filename or '/' in filename or '\\' in filename:
            flash('Некорректное имя файла.', 'danger')
            return redirect(url_for('admin'))

        image_path = os.path.join(app.root_path, 'static', 'generated_images', filename)
        if os.path.exists(image_path):
            os.remove(image_path)
            flash(f'Изображение {filename} успешно удалено.', 'success')
        else:
            flash(f'Изображение {filename} не найдено.', 'warning')
    except Exception as e:
        flash(f'Ошибка при удалении изображения {filename}: {str(e)}', 'danger')
        print(f"Ошибка при удалении изображения {filename}: {str(e)}")
    return redirect(url_for('admin'))

@app.route('/admin/delete_literary_work/<file_id>', methods=['POST'])
@login_required
def delete_literary_work_admin(file_id):
    # Добавьте проверку прав администратора, если необходимо
    try:
        # Валидация file_id (должен быть безопасным, например, UUID)
        if not file_id or '..' in file_id or '/' in file_id or '\\' in file_id:
            flash('Некорректный идентификатор файла произведения.', 'danger')
            return redirect(url_for('admin'))

        works_dir = os.path.join(app.root_path, 'instance', 'generated_literary_works')
        txt_path = os.path.join(works_dir, f"{file_id}.txt")
        meta_path = os.path.join(works_dir, f"{file_id}.meta.json")

        deleted_something = False
        if os.path.exists(txt_path):
            os.remove(txt_path)
            deleted_something = True
        if os.path.exists(meta_path):
            os.remove(meta_path)
            deleted_something = True

        if deleted_something:
            flash(f'Литературное произведение (ID: {file_id}) успешно удалено.', 'success')
        else:
            flash(f'Литературное произведение (ID: {file_id}) не найдено.', 'warning')
    except Exception as e:
        flash(f'Ошибка при удалении литературного произведения (ID: {file_id}): {str(e)}', 'danger')
        print(f"Ошибка при удалении литературного произведения {file_id}: {str(e)}")
    return redirect(url_for('admin'))

@app.route('/rag-stats')
def rag_stats():
    stats = {}
    # RAG_AVAILABLE is defined near the top of app.py based on HistoricalRAG import
    if RAG_AVAILABLE and HistoricalRAG is not None:
        try:
            rag_instance = HistoricalRAG()
            if hasattr(rag_instance, 'get_database_stats') and callable(getattr(rag_instance, 'get_database_stats')):
                stats = rag_instance.get_database_stats()
                # Ensure a status is present, even if get_database_stats() doesn't return one
                if 'rag_status' not in stats:
                    stats['rag_status'] = 'Доступна'
            else:
                stats['error'] = 'Метод get_database_stats() не найден в классе HistoricalRAG.'
                stats['rag_status'] = 'Ошибка конфигурации'
        except Exception as e:
            print(f"Ошибка при инициализации HistoricalRAG или вызове get_database_stats: {e}")
            stats['error'] = f"Ошибка при получении статистики RAG: {str(e)}"
            stats['rag_status'] = 'Ошибка инициализации'
    else:
        stats['rag_status'] = 'Недоступна'
        stats['error'] = 'Компонент HistoricalRAG не был загружен. Проверьте наличие файла historical_rag.py и его зависимости.'
            
    return render_template('rag_stats.html', stats=stats, rag_available=RAG_AVAILABLE)

@app.route('/admin/literary-work/<filename>')
@login_required # Опционально, если админка требует входа
def view_literary_work(filename):
    # Убедимся, что имя файла безопасное и не содержит ../ и т.д.
    # Werkzeug.utils.secure_filename можно использовать, если имя файла приходит из ненадежного источника
    # В данном случае, оно формируется на сервере, но осторожность не помешает.
    if '..' in filename or filename.startswith('/'):
        return "Недопустимое имя файла", 400

    file_path = os.path.join('instance', 'generated_literary_works', filename)
    
    if not filename.endswith('.txt'):
        return "Неверный тип файла. Ожидается .txt", 400

    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Простой способ показать текст - можно создать отдельный шаблон
            # return f"<pre>{content}</pre>" 
            return render_template('view_literary_work_full.html', title=filename, content=content)
        else:
            return "Файл не найден", 404
    except Exception as e:
        print(f"Error reading literary work {filename}: {e}")
        return "Ошибка при чтении файла", 500

# --- User Profile --- #
@app.route('/profile')
@login_required
def user_profile():
    user_generations = UserGeneration.query.filter_by(user_id=current_user.id).order_by(UserGeneration.created_at.desc()).all()
    
    # Дополнительно можно будет обогатить эти данные
    # Например, для музыки, если file_path_or_id это task_id, найти соответствующий трек
    # и получить его статус, URL и т.д.
    # Для изображений, если file_path_or_id это относительный путь, сформировать полный URL.
    
    generations_data = []
    for gen in user_generations:
        data = {
            'id': gen.id,
            'type': gen.generation_type,
            'title': gen.title,
            'snippet': gen.snippet_or_description,
            'created_at': gen.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'file_path_or_id': gen.file_path_or_id
        }
        if gen.generation_type == 'text':
            # Для текста file_path_or_id это имя файла в instance/generated_literary_works/
            # Мы можем создать ссылку на просмотр полного текста, если такая функциональность есть
            # или дать возможность скачать
            data['view_url'] = url_for('view_literary_work', filename=gen.file_path_or_id) if gen.file_path_or_id else None
            data['download_url'] = url_for('download_literary_work', filename=gen.file_path_or_id) if gen.file_path_or_id else None # Нужно будет создать этот маршрут
        elif gen.generation_type == 'image':
            # file_path_or_id может быть URL или относительным путем к static/
            if gen.file_path_or_id and (gen.file_path_or_id.startswith('http') or gen.file_path_or_id.startswith('/')):
                data['image_url'] = gen.file_path_or_id
            elif gen.file_path_or_id:
                 # Проверяем, существует ли файл локально
                image_full_path = os.path.join('static', gen.file_path_or_id)
                if os.path.exists(image_full_path):
                    data['image_url'] = url_for('static', filename=gen.file_path_or_id)
                else:
                    data['image_url'] = None # или placeholder
                    data['error'] = "Файл изображения не найден"
            else:
                data['image_url'] = None # placeholder
            data['download_url'] = data['image_url'] # Для простоты, пользователь может скачать по URL
        elif gen.generation_type == 'music':
            # file_path_or_id это task_id. Нужно найти актуальную информацию о треке.
            # Это может потребовать запроса к static/generated_music/music_metadata_{task_id}.json
            task_id = gen.file_path_or_id
            music_metadata_file = None
            music_dir = os.path.join('static', 'generated_music')
            if os.path.exists(music_dir):
                for fname in os.listdir(music_dir):
                    if fname.startswith(f"music_metadata_{task_id}") and fname.endswith('.json'):
                        music_metadata_file = os.path.join(music_dir, fname)
                        break
            
            if music_metadata_file and os.path.exists(music_metadata_file):
                with open(music_metadata_file, 'r', encoding='utf-8') as f_meta:
                    meta = json.load(f_meta)
                data['music_status'] = meta.get('status', 'unknown')
                data['music_title'] = meta.get('title', gen.title)
                data['local_audio_url'] = meta.get('local_audio_url')
                data['download_url'] = meta.get('local_audio_url') # Ссылка на скачивание
                if meta.get('status') != 'complete' and not meta.get('local_audio_url'):
                    data['check_status_url'] = url_for('check_music_status', task_id=task_id)
            else:
                data['music_status'] = 'pending_or_error'
                data['music_title'] = gen.title or "Трек в обработке"
                data['check_status_url'] = url_for('check_music_status', task_id=task_id)

        generations_data.append(data)

    return render_template('profile.html', generations=generations_data)

# Нужно будет добавить маршрут для скачивания литературных произведений, если его нет
@app.route('/download_literary_work/<filename>')
@login_required
def download_literary_work(filename):
    # Важно: Проверить, что пользователь имеет доступ к этому файлу!
    # Ищем генерацию по имени файла и ID пользователя
    generation_entry = UserGeneration.query.filter_by(user_id=current_user.id, file_path_or_id=filename, generation_type='text').first()
    if not generation_entry:
        flash("Файл не найден или у вас нет к нему доступа.", "danger")
        return redirect(url_for('user_profile'))

    directory = os.path.join(app.root_path, 'instance', 'generated_literary_works')
    try:
        # Убедимся, что имя файла безопасное
        safe_filename = os.path.basename(filename) # Простая защита, можно использовать secure_filename
        if '..' in safe_filename or '/' in safe_filename or '\\' in safe_filename:
            raise ValueError("Недопустимое имя файла")
            
        return send_from_directory(directory, safe_filename, as_attachment=True)
    except FileNotFoundError:
        flash("Файл не найден на сервере.", "danger")
        return redirect(url_for('user_profile'))
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for('user_profile'))
    except Exception as e:
        print(f"Ошибка при скачивании файла {filename}: {e}")
        flash("Произошла ошибка при скачивании файла.", "danger")
        return redirect(url_for('user_profile'))

if __name__ == '__main__':
    print("\n=== Запуск сервера ===")
    print(f"API ключ OpenAI: {'настроен' if os.environ.get('OPENAI_API_KEY') else 'НЕ НАСТРОЕН'}")
    print("=== Используйте http://localhost:5000 для доступа к приложению ===\n")
    
    # Увеличиваем таймаут для запросов
    from werkzeug.serving import run_simple
    # Используем расширенные настройки для поддержки длительных запросов
    run_simple('localhost', 5000, app, 
              use_reloader=True, 
              use_debugger=True, 
              threaded=True, 
              use_evalex=True,
              passthrough_errors=False,
              ssl_context=None)