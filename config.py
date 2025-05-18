import os
from datetime import timedelta

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-goes-here'
    
    # SQLAlchemy
    # Flask config.py
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(BASE_DIR, "instance", "chat.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # Face Detection Settings
    FACE_VERIFICATION_REQUIRED = True  # Set to True to enforce face verification
    FACE_MATCH_THRESHOLD = 0.6  # Lower value = stricter matching (0.6 recommended)
    FACE_VERIFICATION_LOCK_THRESHOLD = 5  # Number of failed attempts before temporary lock
    FACE_VERIFICATION_LOCK_MINUTES = 15  # Lock duration in minutes
    
    # File upload settings for face images
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size
    FACE_MODELS_PATH = os.path.join('static', 'face-api-models')
    
    # Security settings
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    
    # SSL/TLS (recommended for production)
    # SSL_CERT = '/path/to/cert.pem'  # Uncomment and set in production
    # SSL_KEY = '/path/to/key.pem'    # Uncomment and set in production
