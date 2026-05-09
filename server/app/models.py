from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib
import os
import json

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

db = SQLAlchemy()


class Class(db.Model):
    __tablename__ = 'classes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    class_number = db.Column(db.Integer, unique=True, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    after_class_send_time = db.Column(db.String(5), default='19:50')
    created_at = db.Column(db.DateTime, default=datetime.now)

    teacher = db.relationship('User', backref='managed_class', foreign_keys=[teacher_id])
    schedules = db.relationship('Schedule', backref='class_', lazy='dynamic', cascade='all, delete-orphan')
    students = db.relationship('Student', backref='class_', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'class_number': self.class_number,
            'teacher_id': self.teacher_id,
            'after_class_send_time': self.after_class_send_time,
            'teacher_name': self.teacher.display_name if self.teacher else None
        }


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='student')
    display_name = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime, nullable=True)

    @property
    def password(self):
        raise AttributeError('password is not readable')

    @password.setter
    def password(self, password):
        if HAS_BCRYPT:
            self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        else:
            salt = os.urandom(32)
            key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
            self.password_hash = f'pbkdf2:{salt.hex()}:{key.hex()}'

    def set_password(self, password):
        if HAS_BCRYPT:
            self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        else:
            salt = os.urandom(32)
            key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
            self.password_hash = f'pbkdf2:{salt.hex()}:{key.hex()}'

    def verify_password(self, password):
        if not self.password_hash:
            return False
        if HAS_BCRYPT:
            return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
        else:
            if self.password_hash.startswith('pbkdf2:'):
                parts = self.password_hash.split(':')
                salt = bytes.fromhex(parts[1])
                key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
                return key.hex() == parts[2]
            return False

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'display_name': self.display_name,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    client_id = db.Column(db.String(100), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=True)
    is_online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, nullable=True)
    config_data = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'class_id': self.class_id,
            'client_id': self.client_id,
            'display_name': self.display_name,
            'is_online': self.is_online,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None
        }


class Schedule(db.Model):
    __tablename__ = 'schedules'

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)
    period = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.String(5), nullable=False)
    end_time = db.Column(db.String(5), nullable=False)
    subject = db.Column(db.String(50), nullable=True)
    is_holiday = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'class_id': self.class_id,
            'day_of_week': self.day_of_week,
            'period': self.period,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'subject': self.subject,
            'is_holiday': self.is_holiday
        }


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='normal')
    is_urgent = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='pending')
    scheduled_time = db.Column(db.DateTime, nullable=True)
    sent_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    sender = db.relationship('User', backref='sent_messages')
    class_ = db.relationship('Class', backref='messages')
    read_records = db.relationship('ReadRecord', backref='message', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'sender_name': self.sender.display_name if self.sender else None,
            'class_id': self.class_id,
            'title': self.title,
            'content': self.content,
            'priority': self.priority,
            'is_urgent': self.is_urgent,
            'status': self.status,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'sent_time': self.sent_time.isoformat() if self.sent_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_count': self.read_records.count()
        }


class DelayedQueue(db.Model):
    __tablename__ = 'delayed_queue'

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(200), nullable=True)
    is_processed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    message = db.relationship('Message', backref='delayed_entries')
    class_ = db.relationship('Class')

    def to_dict(self):
        return {
            'id': self.id,
            'message_id': self.message_id,
            'class_id': self.class_id,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'reason': self.reason,
            'is_processed': self.is_processed
        }


class ReadRecord(db.Model):
    __tablename__ = 'read_records'

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    read_time = db.Column(db.DateTime, default=datetime.now)

    student = db.relationship('Student', backref='read_records')

    def to_dict(self):
        return {
            'id': self.id,
            'message_id': self.message_id,
            'student_id': self.student_id,
            'read_time': self.read_time.isoformat() if self.read_time else None
        }


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(50), nullable=True)
    target_id = db.Column(db.Integer, nullable=True)
    detail = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref='audit_logs')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'detail': self.detail,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Config(db.Model):
    __tablename__ = 'config'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
