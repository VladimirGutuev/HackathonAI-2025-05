from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from war_diary_analyzer import WarDiaryAnalyzer
from forum import init_forum, db, User, Topic, Message, TopicVote, MessageVote
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

print("OPENAI_API_KEY:", os.environ.get("OPENAI_API_KEY"))

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
                    error_msg = image_result.get('error', 'Неизвестная ошибка при генерации изображения')
                    print(f"Ошибка генерации изображения: {error_msg}")
                    response_data['generated_image'] = {
                        'success': False,
                        'error': error_msg
                    }
            except Exception as img_error:
                print(f"Исключение при генерации изображения: {str(img_error)}")
                import traceback
                traceback.print_exc()
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
                        'embed_url': music_result.get('embed_url', ''),
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
        print(f"Генерация изображения завершена: {image_result['success']}")
        
        if not image_result.get('success', False):
            return jsonify({
                'success': False,
                'error': image_result.get('error', 'Не удалось сгенерировать изображение')
            }), 500
        
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
            'embed_url': music_result.get('embed_url', '')
        }
        
        print("=== Обработка запроса /generate_music успешно завершена ===")
        return jsonify(response_data)
    except Exception as e:
        print(f"Критическая ошибка в /generate_music: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

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