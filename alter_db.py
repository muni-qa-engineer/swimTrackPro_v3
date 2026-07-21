import os
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')

def alter_db():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE students ADD COLUMN skill_level TEXT;")
        conn.commit()
        print("Successfully added skill_level column.")
    except Exception as e:
        print("Column may already exist:", e)
    finally:
        conn.close()

if __name__ == '__main__':
    alter_db()
