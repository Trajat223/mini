from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config
from flask_socketio import SocketIO
from flask_wtf import CSRFProtect
import os

# Initialize Flask extensions
csrf = CSRFProtect()
db = SQLAlchemy()
socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")  # <- Updated
login_manager = LoginManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.db'
    app.config['FACE_VERIFICATION_REQUIRED'] = True

    # Initialize extensions with app
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")  # <- Ensure proper init
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = 'login'

    # Ensure instance and upload folders exist
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    os.makedirs(os.path.join(app.static_folder, 'face-api-models'), exist_ok=True)
    os.makedirs(os.path.join(app.static_folder, 'uploads'), exist_ok=True)

    with app.app_context():
        from app import routes, models, socket_events
        from app.models import User

        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))

        db.create_all()

    return app
