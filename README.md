# SecureChatApp

A secure real-time chat application built with Flask, Socket.IO, and SQLite.  
Supports user registration, login, chat rooms, and file sharing.

---

## 🚀 Features

- User registration & login
- Password hashing for secure storage
- Real-time public/private messaging with Socket.IO
- **End-to-End Encryption** for all messages
- Face recognition authentication
- Face-locked message security
- File upload & sharing
- SQLite backend (local database)

---

## 🔒 Security Features

### End-to-End Encryption
All messages are encrypted on the sender's device before transmission and can only be decrypted by the intended recipient. This ensures:

- The server cannot read message contents
- Messages remain secure even if the database is compromised
- Only the intended recipient can decrypt and read messages

### Face Authentication
- Users can register their face for biometric authentication
- Face-locked messages require facial verification to view
- Failed face verification attempts are logged

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
# miniproject
# minip_latest
