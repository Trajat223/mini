from flask import render_template, request, redirect, url_for, flash, jsonify, session
from flask import current_app as app
from app import db
from app.models import User, Message
from flask_login import login_required, login_user, logout_user

from werkzeug.security import check_password_hash, generate_password_hash, secure_filename
import os
import base64
import json
import cv2
import numpy as np
from datetime import datetime
import face_recognition

# Home route
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            # Check if user has face data and if face verification is required
            if user.face_data and app.config.get('FACE_VERIFICATION_REQUIRED', False):
                session['temp_user_id'] = user.id
                return redirect(url_for('face_verification'))
            
            # Regular login if face verification not required or no face data
            login_user(user)
            return redirect(url_for('chat'))
        
        flash('Invalid username or password')
    
    return render_template('login.html')

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        face_data = request.form.get('faceData')
        
        # Validate input
        if not username or not password:
            flash('Username and password are required')
            return render_template('register.html')
            
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('register.html')
            
        # Check if username exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists')
            return render_template('register.html')
        
        # Create new user
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        
        # Save face data if provided
        if face_data:
            # Remove the data URL prefix to get the base64 data
            face_data = face_data.split(',')[1] if ',' in face_data else face_data
            new_user.face_data = face_data
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
        
    return render_template('register.html')

# Face verification route - renders the face verification page
@app.route('/face_verification')
def face_verification():
    if 'temp_user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['temp_user_id'])
    if not user:
        return redirect(url_for('login'))
    
    return render_template('face_verification.html', username=user.username)

# API endpoint for face verification
@app.route('/verify_face', methods=['POST'])
def verify_face():
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Invalid request format'})
    
    data = request.json
    face_image = data.get('faceImage')
    username = data.get('username')
    
    # Get user from session or username
    user_id = session.get('temp_user_id')
    user = None
    
    if user_id:
        user = User.query.get(user_id)
    elif username:
        user = User.query.filter_by(username=username).first()
    
    if not user or not user.face_data:
        return jsonify({'success': False, 'message': 'User not found or no face data registered'})
    
    try:
        # Process the incoming face image
        face_image_data = face_image.split(',')[1] if ',' in face_image else face_image
        decoded_image = base64.b64decode(face_image_data)
        
        # Convert to numpy array for face_recognition library
        nparr = np.frombuffer(decoded_image, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Process the stored face data
        stored_face_data = base64.b64decode(user.face_data)
        stored_nparr = np.frombuffer(stored_face_data, np.uint8)
        stored_img = cv2.imdecode(stored_nparr, cv2.IMREAD_COLOR)
        
        # Convert to RGB (face_recognition uses RGB)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        stored_img_rgb = cv2.cvtColor(stored_img, cv2.COLOR_BGR2RGB)
        
        # Find face encodings
        face_locations = face_recognition.face_locations(img_rgb)
        if not face_locations:
            return jsonify({'success': False, 'message': 'No face detected in the image'})
        
        face_encoding = face_recognition.face_encodings(img_rgb, face_locations)[0]
        
        # Find stored face encodings
        stored_face_locations = face_recognition.face_locations(stored_img_rgb)
        if not stored_face_locations:
            return jsonify({'success': False, 'message': 'No face in stored reference image'})
        
        stored_face_encoding = face_recognition.face_encodings(stored_img_rgb, stored_face_locations)[0]
        
        # Compare faces
        results = face_recognition.compare_faces([stored_face_encoding], face_encoding, tolerance=0.6)
        face_distance = face_recognition.face_distance([stored_face_encoding], face_encoding)[0]
        match_percentage = (1 - face_distance) * 100
        
        if results[0]:
            # Log successful verification
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Complete login process
            login_user(user)
            if 'temp_user_id' in session:
                session.pop('temp_user_id')
                
            return jsonify({
                'success': True, 
                'message': f'Face verified with {match_percentage:.1f}% confidence',
                'matchPercentage': match_percentage
            })
        else:
            # Log failed verification attempt
            return jsonify({
                'success': False, 
                'message': f'Face verification failed ({match_percentage:.1f}% match, 80% required)'
            })
    
    except Exception as e:
        print(f"Face verification error: {str(e)}")
        return jsonify({'success': False, 'message': f'Error processing face: {str(e)}'})

# Chat route (protected)
@app.route('/chat')
@login_required
def chat():
    recipient_id = request.args.get('recipient_id', type=int)

    users = User.query.filter(User.id != current_user.id).all()
    messages = []

    if recipient_id:
        messages = Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.recipient_id == recipient_id)) |
            ((Message.sender_id == recipient_id) & (Message.recipient_id == current_user.id))
        ).order_by(Message.timestamp).all()

    return render_template('chat.html', users=users, messages=messages, recipient_id=recipient_id)

# Send message API
@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    content = request.form.get('message')
    recipient_id = int(request.form.get('recipient_id'))
    file = request.files.get('file')

    file_path = None
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.static_folder, 'uploads', filename)
        file.save(file_path)
        file_path = f'static/uploads/{filename}'

    message = Message(
        content=content,
        sender_id=current_user.id,
        recipient_id=recipient_id,
        file_path=file_path
    )
    db.session.add(message)
    db.session.commit()
    return redirect(url_for('chat', recipient_id=recipient_id))


# Logout route
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))
