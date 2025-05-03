import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev_secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(os.path.abspath(os.path.dirname(__file__)), "instance", "chat.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

