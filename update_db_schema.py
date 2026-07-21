import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app import get_db_connection

def update():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE students ADD COLUMN skill_level TEXT;")
        conn.commit()
        print("Column skill_level added successfully.")
    except Exception as e:
        print("Could not add column, maybe it exists:", e)
        conn.rollback()
    conn.close()

if __name__ == '__main__':
    update()
