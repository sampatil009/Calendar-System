from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    events = db.relationship(
        'Event',
        backref='user',
        cascade='all, delete-orphan'
    )

    categories = db.relationship(
        'Category',
        backref='user',
        cascade='all, delete-orphan'
    )


class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )

    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default='')
    location = db.Column(db.String(255), default='')

    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)

    all_day = db.Column(db.Boolean, default=False)
    color = db.Column(db.String(7), default='#3788d8')
    source = db.Column(db.String(50), default='manual')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    attachments = db.relationship(
        'Attachment',
        backref='event',
        cascade='all, delete-orphan'
    )

    images = db.relationship(
        'EventImage',
        backref='event',
        cascade='all, delete-orphan'
    )

    categories = db.relationship(
        'Category',
        secondary='event_categories',
        backref=db.backref('events', lazy='dynamic')
    )

class Attachment(db.Model):
    __tablename__ = 'attachments'

    id = db.Column(db.Integer, primary_key=True)

    event_id = db.Column(
        db.Integer,
        db.ForeignKey('events.id'),
        nullable=False
    )

    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class EventImage(db.Model):
    __tablename__ = 'event_images'

    id = db.Column(db.Integer, primary_key=True)

    event_id = db.Column(
        db.Integer,
        db.ForeignKey('events.id'),
        nullable=False
    )

    image_path = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )

    name = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(7), default='#3788d8')


event_categories = db.Table(
    'event_categories',
    db.Column(
        'event_id',
        db.Integer,
        db.ForeignKey('events.id'),
        primary_key=True
    ),
    db.Column(
        'category_id',
        db.Integer,
        db.ForeignKey('categories.id'),
        primary_key=True
    )
)
