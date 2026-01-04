from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

from config import config
from models import db, User, Event, Category, Attachment, EventImage
from ics_parser import ICSParser
from calendar_service import CalendarService

app = Flask(__name__)
app.config.from_object(config['default'])

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'images'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'attachments'), exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

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
    category_id = request.args.get('category_id', type=int)
    source = request.args.get('source')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Event.query.filter_by(user_id=current_user.id)
    
    if category_id:
        query = query.join(Event.categories).filter(Category.id == category_id)
    if source:
        query = query.filter(Event.source == source)
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(Event.start_time >= start_dt)
        except:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(Event.end_time <= end_dt)
        except:
            pass
    
    events = query.all()
    
    result = []
    for e in events:
        event_color = e.color or '#3788d8'
        if e.categories:
            event_color = e.categories[0].color or event_color
        
        result.append({
            'id': e.id,
            'title': e.title,
            'start': e.start_time.isoformat(),
            'end': e.end_time.isoformat(),
            'allDay': e.all_day,
            'color': event_color,
            'location': e.location or '',
            'description': e.description or '',
            'source': e.source
        })
    
    return jsonify(result)


@app.route('/api/event', methods=['POST'])
@login_required
def create_event():
    data = request.json

    start = datetime.fromisoformat(data['start'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(data['end'].replace('Z', '+00:00'))

    event = Event(
        user_id=current_user.id,
        title=data.get('title', 'Untitled'),
        description=data.get('description', ''),
        location=data.get('location', ''),
        start_time=start,
        end_time=end,
        all_day=data.get('allDay', False),
        color=data.get('color', '#3788d8'),
        source='manual'
    )

    db.session.add(event)
    
    if 'category_ids' in data and data['category_ids']:
        categories = Category.query.filter(
            Category.id.in_(data['category_ids']),
            Category.user_id == current_user.id
        ).all()
        event.categories = categories
    
    db.session.commit()

    return jsonify({'message': 'Event created', 'id': event.id}), 201


@app.route('/api/event/<int:event_id>')
@login_required
def get_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    if event.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    images = EventImage.query.filter_by(event_id=event_id).order_by(EventImage.created_at.desc()).limit(7).all()
    
    attachments = Attachment.query.filter_by(event_id=event_id).all()
    
    categories = [{'id': c.id, 'name': c.name, 'color': c.color} for c in event.categories]
    
    return jsonify({
        'id': event.id,
        'title': event.title,
        'description': event.description or '',
        'location': event.location or '',
        'start': event.start_time.isoformat(),
        'end': event.end_time.isoformat(),
        'allDay': event.all_day,
        'color': event.color or '#3788d8',
        'source': event.source,
        'images': [{'id': img.id, 'path': url_for('serve_image', image_id=img.id)} for img in images],
        'attachments': [{'id': att.id, 'filename': att.filename, 'path': url_for('download_attachment', attachment_id=att.id)} for att in attachments],
        'categories': categories
    })


@app.route('/api/event/<int:event_id>', methods=['PUT'])
@login_required
def update_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    if event.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    
    if 'title' in data:
        event.title = data['title']
    if 'description' in data:
        event.description = data.get('description', '')
    if 'location' in data:
        event.location = data.get('location', '')
    if 'start' in data:
        event.start_time = datetime.fromisoformat(data['start'].replace('Z', '+00:00'))
    if 'end' in data:
        event.end_time = datetime.fromisoformat(data['end'].replace('Z', '+00:00'))
    if 'allDay' in data:
        event.all_day = data['allDay']
    if 'color' in data:
        event.color = data['color']
    
    if 'category_ids' in data:
        if data['category_ids']:
            categories = Category.query.filter(
                Category.id.in_(data['category_ids']),
                Category.user_id == current_user.id
            ).all()
            event.categories = categories
        else:
            event.categories = []
    
    db.session.commit()
    
    return jsonify({'message': 'Event updated'})


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


@app.route('/api/category', methods=['POST'])
@login_required
def create_category():
    data = request.json
    
    if not data.get('name'):
        return jsonify({'error': 'Category name required'}), 400
    
    category = Category(
        user_id=current_user.id,
        name=data['name'],
        color=data.get('color', '#3788d8')
    )
    
    db.session.add(category)
    db.session.commit()
    
    return jsonify({
        'message': 'Category created',
        'id': category.id,
        'name': category.name,
        'color': category.color
    }), 201

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


@app.route('/api/event/<int:event_id>/image', methods=['POST'])
@login_required
def upload_event_image(event_id):
    event = Event.query.get_or_404(event_id)
    
    if event.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    image_count = EventImage.query.filter_by(event_id=event_id).count()
    if image_count >= app.config['MAX_IMAGES_PER_EVENT']:
        return jsonify({'error': f'Maximum {app.config["MAX_IMAGES_PER_EVENT"]} images per event'}), 400
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
    filename = timestamp + filename
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'images', filename)
    file.save(filepath)
    
    event_image = EventImage(
        event_id=event_id,
        image_path=filepath
    )
    db.session.add(event_image)
    db.session.commit()
    
    return jsonify({
        'message': 'Image uploaded',
        'id': event_image.id,
        'path': url_for('serve_image', image_id=event_image.id)
    }), 201


@app.route('/api/image/<int:image_id>')
@login_required
def serve_image(image_id):
    image = EventImage.query.get_or_404(image_id)
    event = Event.query.get_or_404(image.event_id)
    
    if event.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return send_file(image.image_path)


@app.route('/api/event/<int:event_id>/attachment', methods=['POST'])
@login_required
def upload_attachment(event_id):
    event = Event.query.get_or_404(event_id)
    
    if event.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > app.config['MAX_ATTACHMENT_SIZE']:
        return jsonify({'error': 'File too large'}), 400
    
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
    filename = timestamp + filename
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'attachments', filename)
    file.save(filepath)
    
    attachment = Attachment(
        event_id=event_id,
        filename=file.filename, 
        file_path=filepath
    )
    db.session.add(attachment)
    db.session.commit()
    
    return jsonify({
        'message': 'Attachment uploaded',
        'id': attachment.id,
        'filename': attachment.filename
    }), 201


@app.route('/api/attachment/<int:attachment_id>')
@login_required
def download_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    event = Event.query.get_or_404(attachment.event_id)
    
    if event.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return send_file(attachment.file_path, as_attachment=True, download_name=attachment.filename)


@app.route('/api/event/<int:event_id>/export')
@login_required
def export_event_ics(event_id):
    event = Event.query.get_or_404(event_id)
    
    if event.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    ics_content = calendar_service.generate_ics_file(event)
    
    import tempfile
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.ics', delete=False)
    temp_file.write(ics_content)
    temp_file.close()
    
    return send_file(
        temp_file.name,
        as_attachment=True,
        download_name=f'event_{event.id}.ics',
        mimetype='text/calendar'
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
