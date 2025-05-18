from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from war_diary_analyzer import WarDiaryAnalyzer
from forum import init_forum, db, User, Topic, Message, TopicVote, MessageVote
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
from datetime import datetime

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
        diary_text = request.form.get('diary_text', '')
        if not diary_text:
            return jsonify({'error': 'Текст дневника не может быть пустым'}), 400

        analyzer = WarDiaryAnalyzer()
        results = analyzer.process_diary(diary_text)
        
        return jsonify({
            'emotion_analysis': results['emotion_analysis'],
            'generated_literary_work': results['generated_literary_work']
        })
    except Exception as e:
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

if __name__ == '__main__':
    app.run(debug=True) 