# SecureChatApp

A secure real-time chat application built with Flask, Socket.IO, and SQLite.  
Supports user registration, login, chat rooms, and file sharing.

---

## 🚀 Features

- User registration & login
- Password hashing for secure storage
- Real-time public/private messaging with Socket.IO
- File upload & sharing
- SQLite backend (local database)

---

## 📦 Requirements

- Python 3.x
- Virtualenv (recommended)

---

## ⚙️ Setup Instructions

1. **Clone the repository**
   
   git clone https://github.com/RachitNaveen/securechatapp.git
   cd securechatapp

## Database Setup

1. Create the `instance` folder:
    
    mkdir instance
    
2. Set up the virtual environment:

   python -m venv venv
   source venv/bin/activate # Linux/macOS
   venv\Scripts\activate # Windows
   pip install -r requirements.txt

3. Initialize the database:

    mkdir instance
    sqlite3 instance/chat.db < schema.sql
    

3. Run the app:
    
    python run.py
    


## Notes

- The `.gitignore` excludes unnecessary files like `chat.db` and `venv/`.

# miniproject
# miniproject
