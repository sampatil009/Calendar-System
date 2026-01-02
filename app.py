from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

from config import config
from models import db, User, Event, Category
from ics_parser import ICSParser
from calendar_service import CalendarService

app = Flask(__name__)
app.config.from_object(config['default'])

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

ics_parser = ICSParser()
calendar_service = CalendarService()

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('calendar_view', view='month'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(
            username=request.form.get('username')
        ).first()

        if user and check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            return redirect(url_for('calendar_view', view='month'))

        flash('Invalid username or password', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if User.query.filter_by(username=request.form.get('username')).first():
            flash('Username already exists', 'error')
            return render_template('register.html')

        if User.query.filter_by(email=request.form.get('email')).first():
            flash('Email already exists', 'error')
            return render_template('register.html')

        user = User(
            username=request.form.get('username'),
            email=request.form.get('email'),
            password_hash=generate_password_hash(request.form.get('password'))
        )

        db.session.add(user)
        db.session.commit()

        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))


@app.route('/calendar/<view>')
@login_required
def calendar_view(view):
    if view not in ['month', 'week', 'day']:
        view = 'month'

    today = datetime.now()

    return render_template(
        'calendar.html',
        view=view,
        year=today.year,
        month=today.month,
        day=today.day
    )


@app.route('/api/events')
@login_required
def get_events():
    events = Event.query.filter_by(user_id=current_user.id).all()

    return jsonify([{
        'id': e.id,
        'title': e.title,
        'start': e.start_time.isoformat(),
        'end': e.end_time.isoformat(),
        'allDay': e.all_day,
        'color': e.color or '#3788d8'
    } for e in events])


@app.route('/api/event', methods=['POST'])
@login_required
def create_event():
    data = request.json

    start = datetime.fromisoformat(data['start'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(data['end'].replace('Z', '+00:00'))

    event = Event(
        user_id=current_user.id,
        title=data.get('title', 'Untitled'),
        start_time=start,
        end_time=end,
        all_day=data.get('allDay', False),
        color=data.get('color', '#3788d8'),
        source='manual'
    )

    db.session.add(event)
    db.session.commit()

    return jsonify({'message': 'Event created'}), 201


@app.route('/api/event/<int:event_id>', methods=['DELETE'])
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)

    if event.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    db.session.delete(event)
    db.session.commit()

    return jsonify({'message': 'Event deleted'})

@app.route('/api/categories')
@login_required
def get_categories():
    categories = Category.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'color': c.color
    } for c in categories])

@app.route('/api/upload/ics', methods=['POST'])
@login_required
def upload_ics():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.lower().endswith('.ics'):
        return jsonify({'error': 'Only .ics files allowed'}), 400

    try:
        events = ics_parser.parse_ics_file(file, current_user.id)
        return jsonify({
            'message': f'Successfully imported {len(events)} events',
            'count': len(events)
        })
    except Exception as e:
        print("ICS UPLOAD ERROR:", str(e))
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
