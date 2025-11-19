import sqlite3
import json
from datetime import datetime

class ComicDatabase:
    """Comic Database Management Class"""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                age_group TEXT NOT NULL,
                steps TEXT NOT NULL,
                images TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_comic(self, topic, age_group, steps, images=None):
        """Save comic data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO comics (topic, age_group, steps, images)
            VALUES (?, ?, ?, ?)
        ''', (topic, age_group, json.dumps(steps), json.dumps(images) if images else None))
        
        comic_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return comic_id
    
    def get_comic(self, comic_id):
        """Get comic data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM comics WHERE id = ?', (comic_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'topic': result[1],
                'age_group': result[2],
                'steps': json.loads(result[3]),
                'images': json.loads(result[4]) if result[4] else None,
                'created_at': result[5]
            }
        return None