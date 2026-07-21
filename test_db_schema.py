import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from swimtrackpro.runtime import get_pg_connection

def test():
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'students'")
    print("STUDENTS COLUMNS:", [r[0] for r in cur.fetchall()])
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'bookings'")
    print("BOOKINGS COLUMNS:", [r[0] for r in cur.fetchall()])
    conn.close()

if __name__ == '__main__':
    test()
