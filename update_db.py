#!/usr/bin/env python3
# filepath: /Users/tshreek/miniProj/update_db.py

"""
Database migration script for adding the is_encrypted column to the Message model.
"""

from app import create_app, db
from app.models import Message
from sqlalchemy import text

app = create_app()

def add_encrypted_column():
    with app.app_context():
        try:
            # Check if column exists
            conn = db.engine.connect()
            result = conn.execute(text("PRAGMA table_info(message)"))
            columns = [row[1] for row in result]
            
            # Add column if it doesn't exist
            if 'is_encrypted' not in columns:
                print("Adding is_encrypted column to Message table...")
                conn.execute(text("ALTER TABLE message ADD COLUMN is_encrypted BOOLEAN DEFAULT TRUE"))
                print("Column added successfully!")
            else:
                print("is_encrypted column already exists in Message table.")
                
            conn.close()
        except Exception as e:
            print(f"Error updating database: {e}")

if __name__ == "__main__":
    add_encrypted_column()
