# --- [same imports as you provided] ---
from flask import (
    render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
)
from flask import current_app as app
from app.models import LoginForm, User, Message, FaceVerificationLog, MessageForm
from app import db, socketio
from flask_login import login_required, login_user, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect
from flask_socketio import join_room, leave_room
import os
import base64
import json
import cv2
import numpy as np
from datetime import datetime
import face_recognition
from sqlalchemy import or_
import logging
import re

csrf = CSRFProtect(app)
logging.basicConfig(level=logging.INFO)

UPLOADS_FOLDER = os.path.join(app.static_folder, 'uploads')
FACE_VERIFICATION_REQUIRED = app.config.get('FACE_VERIFICATION_REQUIRED', False)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    filename = secure_filename(filename)
    return send_from_directory(UPLOADS_FOLDER, filename, as_attachment=True)

@app.route('/')
def index():
    return redirect(url_for('chat')) if current_user.is_authenticated else redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            if user.face_data and FACE_VERIFICATION_REQUIRED:
                session['temp_user_id'] = user.id
                return redirect(url_for('face_verification'))
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            logging.info(f"User {username} logged in.")
            return redirect(url_for('chat'))
        flash('Invalid username or password')
        logging.warning(f"Failed login for {username}")
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        face_data = request.form.get('faceData')

        if not all([username, password, confirm_password]):
            flash('All fields are required')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('register.html')

        password_policy = re.compile(r'''
            ^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#^()_\-+=]).{8,}$
        ''', re.VERBOSE)
        if not password_policy.match(password):
            flash('Password must be strong: min 8 chars, with upper, lower, digit, special char.')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return render_template('register.html')

        hashed_password = generate_password_hash(password)
        user = User(username=username, password=hashed_password)

        if face_data:
            user.face_data = face_data.split(',')[1] if ',' in face_data else face_data

        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/face_verification')
def face_verification():
    if 'temp_user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['temp_user_id'])
    if not user:
        return redirect(url_for('login'))
    return render_template('face_verification.html', username=user.username)

@app.route('/verify_face', methods=['POST'])
def verify_face():
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Invalid request format'})

    data = request.json
    face_image = data.get('faceImage')
    username = data.get('username')

    user = User.query.get(session.get('temp_user_id')) or User.query.filter_by(username=username).first()
    if not user or not user.face_data:
        return jsonify({'success': False, 'message': 'User not found or face data missing'})

    try:
        input_image = base64.b64decode(face_image.split(',')[1] if ',' in face_image else face_image)
        input_np = cv2.imdecode(np.frombuffer(input_image, np.uint8), cv2.IMREAD_COLOR)

        stored_image = base64.b64decode(user.face_data)
        stored_np = cv2.imdecode(np.frombuffer(stored_image, np.uint8), cv2.IMREAD_COLOR)

        input_encoding = face_recognition.face_encodings(cv2.cvtColor(input_np, cv2.COLOR_BGR2RGB))[0]
        stored_encoding = face_recognition.face_encodings(cv2.cvtColor(stored_np, cv2.COLOR_BGR2RGB))[0]

        results = face_recognition.compare_faces([stored_encoding], input_encoding)
        distance = face_recognition.face_distance([stored_encoding], input_encoding)[0]
        match_percentage = round((1 - distance) * 100, 2)

        if results[0]:
            login_user(user)
            session.pop('temp_user_id', None)
            user.last_login = datetime.utcnow()
            db.session.commit()

            log = FaceVerificationLog(user_id=user.id)
            db.session.add(log)
            db.session.commit()

            return jsonify({'success': True, 'matchPercentage': match_percentage})
        return jsonify({'success': False, 'message': f'Face mismatch ({match_percentage:.1f}%)'})

    except Exception as e:
        logging.error(f"Face verification error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/chat')
@login_required
def chat():
    recipient_id = request.args.get('recipient_id', type=int)
    users = User.query.with_entities(User.id, User.username).filter(User.id != current_user.id).all()
    form = MessageForm()
    return render_template('chat.html', users=users, recipient_id=recipient_id, form=form)

@app.route('/get_messages', methods=['GET'])
@login_required
def get_messages():
    recipient_id = request.args.get('recipient_id', type=int)
    messages = Message.query.filter(
        or_(
            (Message.sender_id == current_user.id) & (Message.recipient_id == recipient_id),
            (Message.sender_id == recipient_id) & (Message.recipient_id == current_user.id)
        )
    ).order_by(Message.timestamp).all()

    return jsonify({'messages': [{
        'id': m.id,
        'user_id': m.sender_id,
        'recipient_id': m.recipient_id,
        'content': m.content,
        'timestamp': m.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'is_face_locked': m.is_face_locked,
        'author': {
            'id': m.sender_id,
            'username': User.query.get(m.sender_id).username
        }
    } for m in messages]})

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    content = request.form.get('content')
    recipient_id = request.form.get('recipient_id', type=int)
    is_face_locked = request.form.get('is_face_locked', 'false') == 'true'

    if not content or not recipient_id:
        return jsonify({'success': False, 'message': 'Missing content or recipient'}), 400

    recipient = User.query.get(recipient_id)
    if not recipient:
        return jsonify({'success': False, 'message': 'Recipient not found'}), 404

    message = Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        content=content,
        is_face_locked=is_face_locked,
        timestamp=datetime.utcnow()
    )
    db.session.add(message)
    db.session.commit()

    message_data = {
        'id': message.id,
        'user_id': message.sender_id,
        'recipient_id': message.recipient_id,
        'content': message.content,
        'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'is_face_locked': message.is_face_locked,
        'author': {
            'id': current_user.id,
            'username': current_user.username
        }
    }

    socketio.emit('new_message', message_data, room=str(recipient_id))
    socketio.emit('new_message', message_data, room=str(current_user.id))
    return jsonify({'success': True, 'message': 'Message sent'})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()  # Ensures full logout
    return redirect(url_for('login'))

# --- Socket.IO Events ---

@socketio.on('join_room')
def handle_join_room(room_id):
    if current_user.is_authenticated and str(current_user.id) == str(room_id):
        join_room(room_id)
        logging.info(f"{current_user.username} joined room {room_id}")

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        join_room(str(current_user.id))
        logging.info(f"{current_user.username} connected to room {current_user.id}")

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        leave_room(str(current_user.id))
        logging.info(f"{current_user.username} disconnected")

@socketio.on('send_message')
def handle_send_message(data):
    if not current_user.is_authenticated:
        return {'success': False, 'message': 'Authentication required'}

    content = data.get('content')
    recipient_id = data.get('recipient_id')
    is_face_locked = data.get('is_face_locked', False)

    if not content or not recipient_id:
        return {'success': False, 'message': 'Missing content or recipient'}

    recipient = User.query.get(recipient_id)
    if not recipient:
        return {'success': False, 'message': 'Recipient not found'}

    message = Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        content=content,
        timestamp=datetime.utcnow(),
        is_face_locked=is_face_locked
    )
    db.session.add(message)
    db.session.commit()

    message_data = {
        'id': message.id,
        'user_id': message.sender_id,
        'recipient_id': message.recipient_id,
        'content': message.content,
        'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'is_face_locked': is_face_locked,
        'author': {
            'id': current_user.id,
            'username': current_user.username
        }
    }

    socketio.emit('new_message', message_data, room=str(recipient_id))
    socketio.emit('new_message', message_data, room=str(current_user.id))
    return {'success': True, 'message': 'Message sent'}
