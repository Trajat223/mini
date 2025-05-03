import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user, logout_user
from flask_socketio import emit
from werkzeug.utils import secure_filename

from . import socketio

# Constants
MAX_MESSAGE_LENGTH = 500
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif"}

# State
user_sid_map = {}  # { username: sid }
online_users = set()
messages = {}

# Blueprint setup
main = Blueprint('main', __name__)

# Utility Functions
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes
@main.route("/")
def home():
    return redirect(url_for("auth.register"))

@main.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out successfully.")
    return redirect(url_for("auth.login"))

@main.route("/chat")
@login_required
def chat():
    return render_template("chat.html", username=current_user.username)


@main.route("/upload_public", methods=["POST"])
def upload_public_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    sender = request.form.get("sender")

    if not sender or file.filename == "":
        return jsonify({"error": "Missing sender or filename"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    filename = secure_filename(file.filename)
    file_url = url_for("static", filename=f"uploads/{filename}", _external=True)

    try:
        # Emit to all connected clients (no need for 'broadcast=True')
        socketio.emit("receive_file", {
            "sender": sender,
            "fileName": filename,
            "fileUrl": file_url
        })

        return jsonify({"fileName": filename, "fileUrl": file_url}), 200

    except Exception as e:
        print(f"Error during file upload: {str(e)}")
        return jsonify({"error": f"Failed to broadcast file: {str(e)}"}), 500

        return jsonify({"error": f"Failed to broadcast file: {str(e)}"}), 500


@main.route("/upload_private", methods=["POST"])
def upload_private_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    sender = request.form.get("sender")
    recipient = request.form.get("recipient")

    if not sender or not recipient or file.filename == "":
        return jsonify({"error": "Missing sender, recipient, or filename"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    filename = secure_filename(file.filename)
    
    try:
        # Instead of saving the file, we will send it directly in memory
        file_url = url_for("static", filename=f"uploads/{filename}", _external=True)

        # Send the file privately to the recipient
        if recipient in user_sid_map:
            recipient_sid = user_sid_map[recipient]
            socketio.emit("private_file", {"sender": sender, "fileName": filename, "fileUrl": file_url}, to=recipient_sid)
            return jsonify({"fileName": filename, "fileUrl": file_url}), 200
        else:
            return jsonify({"error": f"{recipient} is not online. File not delivered."}), 400

    except Exception as e:
        return jsonify({"error": f"Failed to send private file: {str(e)}"}), 500

# Socket.IO Events
@socketio.on("connect")
def handle_connect():
    username = request.args.get("username")
    if not username or username in user_sid_map:
        emit("error", {"message": "Invalid or duplicate username."}, to=request.sid)
        return

    user_sid_map[username] = request.sid
    online_users.add(username)
    emit("user_list", list(online_users), broadcast=True)


@socketio.on("disconnect")
def handle_disconnect():
    disconnected_user = next((u for u, sid in user_sid_map.items() if sid == request.sid), None)
    if disconnected_user:
        online_users.discard(disconnected_user)
        user_sid_map.pop(disconnected_user, None)
        emit("user_list", list(online_users), broadcast=True)  # Corrected the typo `eemit` -> `emit`


@socketio.on("send_message")
def handle_message(data):
    message = data.get("message", "").strip()
    if not message or len(message) > MAX_MESSAGE_LENGTH:
        emit("receive_message", {"sender": "System", "message": "Message is invalid or too long."}, to=request.sid)
        return

    emit("receive_message", {
        "sender": data["sender"],
        "message": message,
        "timestamp": data["timestamp"]
    }, broadcast=True)

@socketio.on("private_message")
def handle_private_message(data):
    sender, recipient = data["sender"], data["recipient"]
    message, timestamp, message_id = data["message"], data["timestamp"], data["message_id"]

    messages[message_id] = {
        "sender": sender,
        "recipient": recipient,
        "message": message,
        "timestamp": timestamp,
        "read_by": []
    }

    if recipient in user_sid_map:
        emit("private_message", {
            "sender": sender,
            "message": message,
            "timestamp": timestamp,
            "message_id": message_id
        }, to=user_sid_map[recipient])
    else:
        emit("private_message", {
            "sender": "System",
            "message": f"{recipient} is not online.",
            "timestamp": timestamp
        }, to=request.sid)

@socketio.on("typing")
def handle_typing(data):
    sender = data.get("sender")
    print(f"{sender} is typing...")
    emit("typing", {"sender": sender}, broadcast=True)

@socketio.on("stop_typing")
def handle_stop_typing(data):
    sender = data.get("sender")
    print(f"{sender} stopped typing.")
    emit("stop_typing", {"sender": sender}, broadcast=True)

@socketio.on("message_read")
def handle_message_read(data):
    message_id = data.get("message_id")
    sender = data.get("sender")
    reader = data.get("reader")

    if not all([message_id, sender, reader]):
        print("Invalid data for message_read:", data)
        return

    print(f"[READ RECEIPT] Message {message_id} read by {reader}")

    if message_id in messages:
        if reader not in messages[message_id]["read_by"]:
            messages[message_id]["read_by"].append(reader)

        if sender in user_sid_map:
            emit("message_read", {"message_id": message_id, "reader": reader}, to=user_sid_map[sender])
