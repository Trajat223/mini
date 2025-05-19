import os
import base64
from flask import request, session, current_app
from flask_socketio import emit, join_room, leave_room
from app import socketio, db
from app.models import User, Message
from flask_login import current_user
from datetime import datetime

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        join_room(f'user_{current_user.id}')
        emit('status', {'msg': f'{current_user.username} connected'})

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        leave_room(f'user_{current_user.id}')
        emit('status', {'msg': f'{current_user.username} disconnected'})

@socketio.on('send_message')
def handle_send_message(data):
    if not current_user.is_authenticated:
        return

    sender_id = current_user.id
    recipient_id = data.get('recipient_id')
    content = data.get('content')
    is_face_locked = data.get('is_face_locked', False)
    is_encrypted = data.get('is_encrypted', False)

    print(f"[SocketIO] Message from {sender_id} to {recipient_id} (locked: {is_face_locked}, encrypted: {is_encrypted})")

    if sender_id and recipient_id and content:
        message = Message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            content=content,
            is_face_locked=is_face_locked
        )
        db.session.add(message)
        db.session.commit()

        message_data = {
            'id': message.id,
            'user_id': sender_id,
            'recipient_id': recipient_id,
            'content': content,
            'is_face_locked': is_face_locked,
            'is_encrypted': is_encrypted,
            'timestamp': message.timestamp.isoformat(),
            'author': {
                'id': current_user.id,
                'username': current_user.username
            }
        }

        room = f"user_{recipient_id}"
        emit('new_message', message_data, room=room)

@socketio.on('get_messages')
def handle_get_messages(data):
    if not current_user.is_authenticated:
        return

    other_user_id = data.get('user_id')
    if not other_user_id:
        return

    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == other_user_id)) |
        ((Message.sender_id == other_user_id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.timestamp).all()

    message_list = []
    for msg in messages:
        sender = db.session.get(User, msg.sender_id)
        message_list.append({
            'id': msg.id,
            'user_id': msg.sender_id,
            'recipient_id': msg.recipient_id,
            'content': msg.content,
            'file_path': msg.file_path,
            'is_face_locked': msg.is_face_locked,
            'is_encrypted': True,  # Assume all messages are encrypted
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'author': {
                'id': sender.id,
                'username': sender.username
            }
        })

    emit('message_history', {'messages': message_list})

@socketio.on('join_room')
def on_join(user_id):
    room = f"user_{user_id}"
    join_room(room)
    print(f"User {user_id} joined room: {room}")
