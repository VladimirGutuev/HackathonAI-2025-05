from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    topics = db.relationship('Topic', backref='author', lazy=True)
    messages = db.relationship('Message', backref='author', lazy=True)
    topic_votes = db.relationship('TopicVote', backref='user', lazy=True)
    message_votes = db.relationship('MessageVote', backref='user', lazy=True)

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
    messages = db.relationship('Message', backref='topic', lazy=True, cascade='all, delete-orphan')
    votes = db.relationship('TopicVote', backref='topic', lazy=True, cascade='all, delete-orphan')

    def get_vote_from_user(self, user):
        if not user.is_authenticated:
            return 0
        vote = TopicVote.query.filter_by(topic_id=self.id, user_id=user.id).first()
        return vote.vote_type if vote else 0

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    votes_up = db.Column(db.Integer, default=0)
    votes_down = db.Column(db.Integer, default=0)
    votes = db.relationship('MessageVote', backref='message', lazy=True, cascade='all, delete-orphan')

    def get_vote_from_user(self, user):
        if not user.is_authenticated:
            return 0
        vote = MessageVote.query.filter_by(message_id=self.id, user_id=user.id).first()
        return vote.vote_type if vote else 0

class TopicVote(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), primary_key=True)
    vote_type = db.Column(db.Integer, nullable=False)  # 1 for upvote, -1 for downvote
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MessageVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=False)
    vote_type = db.Column(db.String(10), nullable=False)  # 'like' или 'dislike'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserFeedback(db.Model):
    """Модель для хранения обратной связи пользователей о генерируемом контенте"""
    id = db.Column(db.Integer, primary_key=True)
    content_type = db.Column(db.String(50), nullable=False)  # 'literary_work', 'generated_image', 'generated_music', 'emotion_analysis'
    feedback_type = db.Column(db.String(20), nullable=False)  # 'like', 'dislike', 'detailed_rating'
    feedback_data = db.Column(db.Text, nullable=True)  # JSON данные для детальной обратной связи
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # может быть анонимным
    user_ip = db.Column(db.String(45), nullable=True)  # для защиты от спама (старое поле)
    ip_address = db.Column(db.String(45), nullable=True)  # IP адрес (новое поле)
    user_agent = db.Column(db.String(500), nullable=True)  # User Agent браузера
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    user = db.relationship('User', backref=db.backref('feedback', lazy=True))
    
    def __repr__(self):
        return f'<UserFeedback {self.content_type}:{self.feedback_type}>'

# Определение модели UserGeneration 
class UserGeneration(db.Model):
    __tablename__ = 'user_generations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Corrected ForeignKey to 'user.id'
    generation_type = db.Column(db.String(50), nullable=False)  # 'text', 'image', 'music'
    file_path_or_id = db.Column(db.String(512), nullable=True) 
    title = db.Column(db.String(255), nullable=True) 
    snippet_or_description = db.Column(db.Text, nullable=True) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('generations', lazy='dynamic')) 

    def __repr__(self):
        return f'<UserGeneration id={self.id} user_id={self.user_id} type={self.generation_type}>'

class UserActivity(db.Model):
    """Модель для отслеживания активности пользователей"""
    __tablename__ = 'user_activity'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Может быть анонимным
    ip_address = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.String(500), nullable=True)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    page_visited = db.Column(db.String(200), nullable=True)
    
    user = db.relationship('User', backref=db.backref('activity_records', lazy=True))
    
    def __repr__(self):
        return f'<UserActivity user_id={self.user_id} ip={self.ip_address}>'

def init_forum(app):
    db.init_app(app)
    with app.app_context():
        db.create_all() 