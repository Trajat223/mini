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
   ```bash
   git clone https://github.com/YOUR_USERNAME/securechatapp.git
   cd securechatapp

## Database Setup

1. Create the `instance` folder:
    ```bash
    mkdir instance
    ```

2. Initialize the database:
    ```bash
    sqlite3 instance/chat.db < schema.sql
    ```

3. Run the app:
    ```bash
    python run.py
    ```
