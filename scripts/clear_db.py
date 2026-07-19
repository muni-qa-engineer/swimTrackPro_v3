from app import get_pg_connection

conn = get_pg_connection()
cursor = conn.cursor()

cursor.execute("DELETE FROM bookings")
cursor.execute("DELETE FROM students")

conn.commit()

cursor.close()
conn.close()

print("Database cleared successfully ✅")