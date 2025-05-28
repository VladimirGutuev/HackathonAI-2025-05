from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, Response, send_from_directory
from war_diary_analyzer import WarDiaryAnalyzer
from forum import init_forum, db, User, Topic, Message, TopicVote, MessageVote, UserFeedback
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
import sys
from datetime import datetime
from dotenv import load_dotenv, find_dotenv, dotenv_values
import json
import requests
from urllib.parse import quote
import urllib.parse

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
            literary_work = analyzer.generate_literary_work(diary_text, base_emotions)
            print(f"Генерация текста завершена, длина: {len(literary_work)}")
            response_data['generated_literary_work'] = literary_work
        
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
            print("Начало генерации музыки")
            try:
                # Убедимся, что папка для музыки существует
                os.makedirs(os.path.join('static', 'generated_music'), exist_ok=True)
                
                # Используем внешний URL, если он указан, или request.host_url в противном случае
                base_url = os.environ.get('EXTERNAL_URL', request.host_url.rstrip('/'))
                print(f"Используется base_url для коллбэка: {base_url}")
                music_result = analyzer.generate_music(diary_text, base_emotions, base_url=base_url)
                print(f"Генерация музыки завершена: {music_result['success']}")
                
                if not music_result.get('success', False):
                    error_msg = music_result.get('error', 'Неизвестная ошибка при генерации музыки')
                    print(f"Ошибка генерации музыки: {error_msg}")
                    response_data['generated_music'] = {
                        'success': False,
                        'error': error_msg
                    }
                else:
                    response_data['generated_music'] = {
                        'success': True,
                        'music_description': music_result.get('music_description', ''),
                        'audio_url': music_result.get('audio_url', ''),
                        'stream_url': music_result.get('stream_url', ''),
                        'embed_url': music_result.get('embed_url', ''),
                        'task_id': music_result.get('task_id', ''),
                        'status': music_result.get('status', 'unknown'),
                        'local_path': music_result.get('local_path', '')
                    }
            except Exception as music_error:
                print(f"Исключение при генерации музыки: {str(music_error)}")
                import traceback
                traceback.print_exc()
                response_data['generated_music'] = {
                    'success': False,
                    'error': f"Ошибка: {str(music_error)}"
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
        diary_text = data.get('diary_text', '')
        emotion_analysis = data.get('emotion_analysis', '')
        generated_literary_work = data.get('generated_literary_work', '')
        
        if not diary_text or not emotion_analysis or not generated_literary_work:
            return jsonify({'error': 'Не все данные для публикации были предоставлены'}), 400
        
        # Создаем новую тему на форуме
        title = f"Анализ военного дневника - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        topic = Topic(title=title, author=current_user)
        db.session.add(topic)
        
        # Форматируем эмоциональный анализ
        emotions = emotion_analysis
        emotion_text = "### Эмоциональный анализ:\n"
        
        if isinstance(emotions, dict):
            if emotions.get('primary_emotions'):
                emotion_text += "\nОсновные эмоции:\n"
                for emotion in emotions['primary_emotions']:
                    emotion_text += f"- {emotion['emotion']}: {emotion['intensity']}/10\n"
            
            if emotions.get('emotional_tone'):
                emotion_text += f"\nОбщий тон: {emotions['emotional_tone']}\n"
            
            if emotions.get('hidden_motives'):
                emotion_text += f"\nСкрытые мотивы: {', '.join(emotions['hidden_motives'])}\n"
            
            if emotions.get('attitude'):
                emotion_text += f"\nОтношение: {emotions['attitude']}\n"
        else:
            emotion_text += str(emotions)
        
        # Формируем содержимое сообщения
        content = f"""### Оригинальный текст дневника:
{diary_text}

{emotion_text}

### Литературная интерпретация:
{generated_literary_work}"""
        
        # Создаем первое сообщение в теме
        message = Message(content=content, topic=topic, author=current_user)
        db.session.add(message)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'topic_id': topic.id,
            'redirect_url': url_for('view_topic', topic_id=topic.id)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    """
    Обработчик обратных вызовов от SUNO API для обновления статуса задач генерации музыки.
    Принимает уведомления о завершении генерации музыки.
    """
    try:
        # Получаем данные из запроса
        data = request.get_json()
        print(f"Получен callback от SUNO API: {json.dumps(data, ensure_ascii=False)[:500]}...")
        
        if not data:
            return jsonify({'success': False, 'error': 'Пустые данные'}), 400
        
        # Проверяем структуру данных
        if 'data' not in data:
            print("ВНИМАНИЕ: В callback отсутствует поле 'data', используем весь ответ как основные данные")
            callback_data = data
        else:
            callback_data = data.get('data', {})
        
        # Получаем тип обратного вызова и task_id
        callback_type = callback_data.get('callbackType')
        
        # Проверяем различные поля, где может быть task_id
        task_id = (callback_data.get('task_id') or 
                  callback_data.get('taskId') or 
                  data.get('task_id') or 
                  data.get('taskId'))
        
        if not task_id:
            print("КРИТИЧЕСКАЯ ОШИБКА: Не найден task_id в callback данных")
            # Попытка извлечь task_id из других возможных мест
            if isinstance(callback_data.get('data'), list) and len(callback_data.get('data', [])) > 0:
                # Иногда task_id может быть внутри первого элемента массива data
                first_item = callback_data['data'][0]
                task_id = first_item.get('task_id') or first_item.get('taskId')
                
            if not task_id:
                print(f"Полные данные callback: {json.dumps(data, ensure_ascii=False)}")
                return jsonify({'success': False, 'error': 'Не удалось определить task_id'}), 400
        
        print(f"Обработка callback для task_id: {task_id}, тип: {callback_type}")
        
        # Путь к файлу метаданных
        metadata_path = os.path.join('static', 'generated_music', f"music_metadata_{task_id}.json")
        
        # Проверяем существование файла метаданных
        if not os.path.exists(metadata_path):
            print(f"Файл метаданных не найден: {metadata_path}")
            # Если файл не существует, создаем новый с базовой информацией
            metadata = {
                'task_id': task_id,
                'status': 'unknown',
                'created_at': datetime.now().isoformat(),
                'last_update': datetime.now().isoformat(),
                'callback_received': True,
                'callback_data': callback_data
            }
        else:
            # Загружаем текущие метаданные
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        
        # Обновляем метаданные на основе типа callback
        if callback_type:
            metadata['status'] = callback_type
        else:
            # Если нет типа, смотрим на код ответа
            if data.get('code') == 200:
                metadata['status'] = 'complete'
            else:
                metadata['status'] = 'updated'
        
        metadata['last_update'] = datetime.now().isoformat()
        metadata['callback_received'] = True
        
        # Тщательно проверяем все возможные структуры данных в callback
        
        # Вариант 1: Структура с callbackType и массивом data
        if callback_type == 'complete' and 'data' in callback_data and isinstance(callback_data['data'], list):
            tracks_data = callback_data.get('data', [])
            print(f"Обнаружена структура callback type 1: массив треков в data")
            
            if tracks_data and isinstance(tracks_data, list) and len(tracks_data) > 0:
                process_track_data(metadata, tracks_data[0], task_id)
        
        # Вариант 2: Структура с tracks массивом напрямую
        elif 'tracks' in callback_data and isinstance(callback_data['tracks'], list):
            tracks_data = callback_data.get('tracks', [])
            print(f"Обнаружена структура callback type 2: массив в tracks")
            
            if tracks_data and len(tracks_data) > 0:
                process_track_data(metadata, tracks_data[0], task_id)
        
        # Вариант 3: Структура с data объектом, содержащим информацию о треке
        elif 'data' in callback_data and isinstance(callback_data['data'], dict):
            print(f"Обнаружена структура callback type 3: объект в data")
            process_track_data(metadata, callback_data['data'], task_id)
        
        # Вариант 4: Данные о треке находятся непосредственно в callback_data
        elif any(key in callback_data for key in ['audio_url', 'audioUrl', 'stream_url', 'streamUrl']):
            print(f"Обнаружена структура callback type 4: данные трека в корне callback_data")
            process_track_data(metadata, callback_data, task_id)
            
        # Вариант 5: Данные находятся в родительском объекте data
        elif any(key in data for key in ['audio_url', 'audioUrl', 'stream_url', 'streamUrl']):
            print(f"Обнаружена структура callback type 5: данные трека в корне data")
            process_track_data(metadata, data, task_id)
        
        # Если callback сообщает об ошибке, сохраняем информацию об ошибке
        if callback_type == 'error' or data.get('code') != 200:
            metadata['status'] = 'error'
            metadata['error'] = (callback_data.get('message') or 
                               callback_data.get('msg') or 
                               data.get('msg') or 
                               'Неизвестная ошибка')
            print(f"Получена ошибка для задачи {task_id}: {metadata['error']}")
        
        # Сохраняем оригинальные данные callback для отладки
        metadata['last_callback'] = data
        
        # Сохраняем обновленные метаданные
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
            
        return jsonify({'success': True, 'message': f'Callback обработан для task_id: {task_id}'}), 200
    
    except Exception as e:
        print(f"Ошибка при обработке callback: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({'success': False, 'error': str(e)}), 500

def process_track_data(metadata, track, task_id):
    """
    Обрабатывает данные трека и обновляет метаданные.
    
    Args:
        metadata (dict): Словарь метаданных для обновления
        track (dict): Данные трека из callback
        task_id (str): Идентификатор задачи
    """
    # Получаем URL-адреса аудио с проверкой разных возможных полей
    audio_url = (track.get('audio_url') or 
                track.get('audioUrl') or 
                track.get('url') or 
                '')
    
    stream_url = (track.get('stream_audio_url') or 
                 track.get('streamAudioUrl') or 
                 track.get('streamUrl') or 
                 track.get('stream_url') or 
                 '')
    
    image_url = (track.get('image_url') or 
                track.get('imageUrl') or 
                track.get('coverUrl') or 
                track.get('cover_url') or 
                '')
    
    embed_url = (track.get('embed_url') or 
                track.get('embedUrl') or 
                '')
    
    # Проверяем и логируем URL-адреса
    print(f"Audio URL: {audio_url}")
    print(f"Stream URL: {stream_url}")
    print(f"Image URL: {image_url}")
    print(f"Embed URL: {embed_url}")
    
    # Создаем ссылку для проксирования, если аудио URL существует
    proxy_url = ''
    if audio_url:
        proxy_url = f"/proxy_audio?url={quote(audio_url)}"
    
    # Переменные для отслеживания локальных путей и URL-адресов
    local_audio_path = ''
    local_audio_url = ''
    
    # Пытаемся скачать аудиофайл, если есть URL
    if audio_url or stream_url:
        # Создаем директорию для аудиофайлов, если она не существует
        audio_dir = os.path.join('static', 'generated_music', 'audio')
        os.makedirs(audio_dir, exist_ok=True)
        
        # Формируем имя файла и путь для сохранения
        audio_filename = f"music_{task_id}.mp3"
        full_audio_path = os.path.join(audio_dir, audio_filename)
        
        # Формируем URL для доступа из браузера (в любом случае)
        local_audio_url = f"/static/generated_music/audio/{audio_filename}"
        
        # URL для скачивания (предпочитаем audio_url, если есть)
        download_url = audio_url if audio_url else stream_url
        
        if download_url:
            try:
                print(f"Начинаем скачивание аудиофайла с URL: {download_url}")
                
                # Скачиваем с увеличенным таймаутом и обработкой ошибок
                session = requests.Session()
                session.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))
                
                response = session.get(download_url, stream=True, timeout=60)
                response.raise_for_status()  # Проверка на ошибки HTTP
                
                # Сохраняем файл
                with open(full_audio_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # Проверяем, что файл был скачан успешно
                if os.path.exists(full_audio_path) and os.path.getsize(full_audio_path) > 0:
                    print(f"Аудиофайл успешно скачан и сохранен: {full_audio_path}")
                    local_audio_path = full_audio_path
                    # URL установлен выше, проверяем что он соответствует пути
                    print(f"Сформирован URL для аудио: {local_audio_url}")
                else:
                    print(f"Ошибка: файл не был скачан или имеет нулевой размер")
                    
                    # Пробуем альтернативный способ скачивания
                    print("Пробуем альтернативный способ скачивания...")
                    import urllib.request
                    
                    try:
                        urllib.request.urlretrieve(download_url, full_audio_path)
                        
                        if os.path.exists(full_audio_path) and os.path.getsize(full_audio_path) > 0:
                            print(f"Аудиофайл успешно скачан альтернативным способом: {full_audio_path}")
                            local_audio_path = full_audio_path
                            # URL установлен выше
                        else:
                            print("Альтернативное скачивание тоже не удалось: файл имеет нулевой размер")
                    except Exception as e:
                        print(f"Альтернативное скачивание тоже не удалось: {str(e)}")
            except Exception as e:
                print(f"Ошибка при скачивании аудиофайла: {str(e)}")
                import traceback
                traceback.print_exc()
    
    # Скачиваем изображение обложки, если URL существует
    local_image_path = ''
    local_image_url = ''
    
    if image_url:
        try:
            # Создаем директорию для изображений
            image_dir = os.path.join('static', 'generated_music', 'covers')
            os.makedirs(image_dir, exist_ok=True)
            
            # Формируем имя файла и путь
            image_filename = f"cover_{task_id}.jpg"
            local_image_path = os.path.join(image_dir, image_filename)
            local_image_url = f"/static/generated_music/covers/{image_filename}"
            
            # Скачиваем изображение
            print(f"Начинаем скачивание обложки с URL: {image_url}")
            response = requests.get(image_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Сохраняем файл
            with open(local_image_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Проверяем результат
            if os.path.exists(local_image_path) and os.path.getsize(local_image_path) > 0:
                print(f"Обложка успешно скачана: {local_image_path}")
            else:
                print(f"Ошибка: изображение не было скачано или имеет нулевой размер")
                local_image_path = ''
                local_image_url = ''
        except Exception as e:
            print(f"Ошибка при скачивании обложки: {str(e)}")
            local_image_path = ''
            local_image_url = ''
    
    # Создаем описание музыки на основе метаданных
    music_description = ''
    if 'style' in metadata:
        music_description = f"Сгенерирована музыка в стиле {metadata.get('style', 'инструментальный')}"
        if 'mood' in metadata:
            music_description += f", настроение: {metadata.get('mood')}"
        if 'emotions' in metadata and metadata['emotions']:
            music_description += f". Отражает эмоции: {', '.join(metadata['emotions'])}"
    else:
        music_description = "Сгенерирована музыка на основе дневниковых записей"
    
    # Сохраняем информацию о треке
    metadata['status'] = 'complete'
    metadata['completed_at'] = datetime.now().isoformat()
    metadata['audio_url'] = audio_url
    metadata['stream_url'] = stream_url
    metadata['image_url'] = image_url
    metadata['embed_url'] = embed_url
    metadata['proxy_url'] = proxy_url
    metadata['local_audio_path'] = local_audio_path
    metadata['local_image_path'] = local_image_path
    metadata['local_audio_url'] = local_audio_url
    metadata['local_image_url'] = local_image_url
    metadata['duration'] = track.get('duration', 0)
    metadata['tags'] = track.get('tags', '')
    metadata['track_data'] = track  # Сохраняем все данные трека для отладки
    metadata['music_description'] = music_description
    
    print(f"Обновлены метаданные для задачи: {task_id}")
    
    # Важно! Устанавливаем флаг готовности музыки на основе наличия аудио-файла или URL
    if (local_audio_path and os.path.exists(local_audio_path) and os.path.getsize(local_audio_path) > 0) or audio_url or stream_url:
        metadata['is_music_ready'] = True
    else:
        metadata['is_music_ready'] = False

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
        # Получаем список всех треков
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
                            'file_size': os.path.getsize(metadata_path)
                        }
                        tracks.append(track_info)
                    except Exception as e:
                        print(f"Ошибка при чтении {filename}: {e}")
                        continue
        
        # Сортируем по дате создания (новые первыми)
        tracks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Статистика изображений
        images_dir = os.path.join('static', 'generated_images')
        image_count = 0
        if os.path.exists(images_dir):
            image_count = len([f for f in os.listdir(images_dir) if f.endswith(('.png', '.jpg', '.jpeg'))])
        
        return render_template('admin.html', 
                             tracks=tracks, 
                             track_count=len(tracks),
                             image_count=image_count)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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