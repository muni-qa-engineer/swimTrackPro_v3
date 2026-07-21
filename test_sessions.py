import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from swimtrackpro.runtime import get_pg_connection

def test():
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM bookings WHERE LOWER(trainer_username) = 'asdf' OR trainer_username IS NOT NULL")
    
    columns = [desc[0] for desc in cur.description]
    bookings = [dict(zip(columns, row)) for row in cur.fetchall()]
    print("Found", len(bookings), "bookings for trainers.")
    for b in bookings:
        print(f"Booking: {b['student']}, Dates: {b.get('calendar_dates', 'None')}, Time: {b.get('time', 'None')}")
    conn.close()

if __name__ == '__main__':
    test()
