from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, Response
from war_diary_analyzer import WarDiaryAnalyzer
from forum import init_forum, db, User, Topic, Message, TopicVote, MessageVote
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
import sys
from datetime import datetime
from dotenv import load_dotenv, find_dotenv, dotenv_values
import json
import requests
from urllib.parse import quote

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
        
        # Сначала всегда проводим эмоциональный анализ
        emotions = analyzer.analyze_emotions(diary_text)
        print(f"Эмоциональный анализ завершен: {list(emotions.keys())}")
        
        # Проверяем наличие ошибки в анализе эмоций
        if 'error' in emotions and emotions['error']:
            print(f"Ошибка при анализе эмоций: {emotions['error']}")
            return jsonify({
                'error': emotions['error'],
                'emotion_analysis': emotions,
            }), 500
        
        # Формируем ответ, всегда включаем анализ эмоций
        response_data = {
            'emotion_analysis': emotions,
        }
        
        # На основе эмоционального анализа генерируем выбранные типы контента
        if 'text' in generation_types:
            print("Начало генерации художественного произведения")
            literary_work = analyzer.generate_literary_work(diary_text, emotions)
            print(f"Генерация текста завершена, длина: {len(literary_work)}")
            response_data['generated_literary_work'] = literary_work
        
        if 'image' in generation_types:
            try:
                print("Начало генерации изображения")
                # Убедимся, что папка для изображений существует
                os.makedirs(os.path.join('static', 'generated_images'), exist_ok=True)
                
                image_result = analyzer.generate_image_from_diary(diary_text, emotions)
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
                
                music_result = analyzer.generate_music(diary_text, emotions)
                print(f"Генерация музыки завершена: {music_result.get('success', False)}")
                
                if music_result.get('success', False):
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
                else:
                    error_msg = music_result.get('error', 'Неизвестная ошибка при генерации музыки')
                    print(f"Ошибка генерации музыки: {error_msg}")
                    response_data['generated_music'] = {
                        'success': False,
                        'error': error_msg
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
        if local_path.startswith('static/'):
            image_url = '/' + local_path
        else:
            image_url = image_result.get('image_url', '')
        
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
        
        # Генерация музыки
        music_result = analyzer.generate_music(text, emotion_analysis)
        print(f"Генерация музыки завершена: {music_result['success']}")
        
        if not music_result.get('success', False):
            return jsonify({
                'success': False,
                'error': music_result.get('error', 'Не удалось сгенерировать музыку')
            }), 500
        
        response_data = {
            'success': True,
            'music_description': music_result.get('music_description', ''),
            'audio_url': music_result.get('audio_url', ''),
            'stream_url': music_result.get('stream_url', ''),
            'embed_url': music_result.get('embed_url', ''),
            'task_id': music_result.get('task_id', ''),
            'status': music_result.get('status', 'unknown'),
            'local_path': music_result.get('local_path', '')
        }
        
        print("=== Обработка запроса /generate_music успешно завершена ===")
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
            return jsonify({'success': False, 'error': 'Не указан task_id'}), 400
        
        print(f"Получен запрос на проверку статуса для задачи: {task_id}")
        
        # Проверяем наличие локального файла метаданных напрямую
        metadata_path = os.path.join('static', 'generated_music', f"music_metadata_{task_id}.json")
        
        if os.path.exists(metadata_path):
            try:
                # Загружаем метаданные
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Проверяем наличие уже скачанного аудио
                local_audio_path = metadata.get('local_audio_path', '')
                if local_audio_path and os.path.exists(local_audio_path) and os.path.getsize(local_audio_path) > 0:
                    # Формируем относительный URL для аудио
                    audio_filename = os.path.basename(local_audio_path)
                    local_audio_url = f"/static/generated_music/audio/{audio_filename}"
                    
                    # Возвращаем успешный статус
                    return jsonify({
                        'success': True,
                        'status': 'complete',
                        'local_audio_url': local_audio_url,
                        'is_music_ready': True,
                        'music_description': metadata.get('music_description', 'Сгенерированная музыка'),
                        'style': metadata.get('style', ''),
                        'mood': metadata.get('mood', '')
                    })
            except Exception as e:
                print(f"Ошибка при чтении метаданных: {str(e)}")
                # Продолжаем выполнение, чтобы проверить статус через API
        
        # Создаем экземпляр анализатора
        analyzer = WarDiaryAnalyzer()
        
        # Проверяем статус генерации музыки через API
        status_response = analyzer._check_music_generation_status(task_id)
        
        # Логируем результат для отладки
        print(f"Результат проверки статуса: {json.dumps(status_response, default=str)[:500]}")
        
        # Для завершенных задач добавляем ссылки для проксирования
        if status_response.get('success') and status_response.get('status') == 'complete':
            audio_url = status_response.get('audio_url')
            if audio_url:
                # Добавляем URL для проксирования аудио
                status_response['proxy_url'] = f"/proxy_audio?url={quote(audio_url)}"
            
            # Проверяем локальный аудио URL
            local_audio_url = status_response.get('local_audio_url', '')
            
            # Если локальный аудио URL не начинается с /, добавляем его
            if local_audio_url and not local_audio_url.startswith('/'):
                status_response['local_audio_url'] = f"/{local_audio_url}"
            
            # Проверяем наличие локального аудио-файла напрямую из пути
            if 'local_audio_path' in status_response and status_response['local_audio_path']:
                path = status_response['local_audio_path']
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    filename = os.path.basename(path)
                    status_response['local_audio_url'] = f"/static/generated_music/audio/{filename}"
                    status_response['is_music_ready'] = True
        
        # Добавляем время запроса для отладки
        status_response['request_time'] = datetime.now().isoformat()
        
        # Возвращаем статус
        return jsonify(status_response)
    except Exception as e:
        print(f"Ошибка при проверке статуса музыки: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': str(e),
            'status': 'error',
            'message': f"Ошибка при проверке статуса: {str(e)}",
        }), 500

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
        proxy_url = f"/proxy_audio?url={audio_url}"
    
    # Скачиваем аудиофайл и сохраняем его локально, если URL существует
    local_audio_path = ''
    local_audio_url = ''
    
    if audio_url or stream_url:
        # Создаем директорию для аудиофайлов, если она не существует
        audio_dir = os.path.join('static', 'generated_music', 'audio')
        os.makedirs(audio_dir, exist_ok=True)
        
        # Формируем имя файла и путь для сохранения
        audio_filename = f"music_{task_id}.mp3"
        full_audio_path = os.path.join(audio_dir, audio_filename)
        
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
                    # Корректный URL для веб-доступа
                    local_audio_url = f"/static/generated_music/audio/{audio_filename}"
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
                            local_audio_url = f"/static/generated_music/audio/{audio_filename}"
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
                local_image_url = f"/static/generated_music/covers/{image_filename}"
                print(f"Обложка успешно скачана: {local_image_path}")
            else:
                print(f"Ошибка: изображение не было скачано или имеет нулевой размер")
                local_image_path = ''
        except Exception as e:
            print(f"Ошибка при скачивании обложки: {str(e)}")
            local_image_path = ''
    
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
    
    print(f"Обновлены метаданные для задачи: {task_id}")
    
    # Важно! Устанавливаем флаг готовности музыки на основе наличия аудио-файла
    if local_audio_path and os.path.exists(local_audio_path) and os.path.getsize(local_audio_path) > 0:
        metadata['is_music_ready'] = True
    elif audio_url:
        # Если локальный путь не создан, но есть внешний URL, все равно отмечаем как готовую
        metadata['is_music_ready'] = True
    else:
        metadata['is_music_ready'] = False

@app.route('/proxy_audio')
def proxy_audio():
    """
    Проксирует аудио-содержимое из внешнего URL для обхода CORS-ограничений.
    Используйте этот маршрут при проблемах с прямым доступом к аудио.
    """
    try:
        url = request.args.get('url')
        if not url:
            return "URL не указан", 400
        
        print(f"Проксирование аудио с URL: {url}")
        
        # Проверка на валидный URL
        if not url.startswith('http'):
            return "Неверный формат URL", 400
        
        # Отправляем запрос к внешнему ресурсу
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Проверка на ошибки HTTP
        
        # Получаем тип контента
        content_type = response.headers.get('Content-Type', 'audio/mpeg')
        
        # Создаем поток данных
        def generate():
            for chunk in response.iter_content(chunk_size=8192):
                yield chunk
                
        # Возвращаем аудио как поток
        return Response(generate(), content_type=content_type)
        
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при проксировании аудио: {str(e)}")
        return f"Ошибка при получении аудио: {str(e)}", 500
    except Exception as e:
        print(f"Общая ошибка при проксировании аудио: {str(e)}")
        return f"Общая ошибка: {str(e)}", 500

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