from app import get_pg_connection

conn = get_pg_connection()
cursor = conn.cursor()

# STUDENTS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    student_name TEXT,
    owner_name TEXT,
    owner_phone TEXT
)
""")

# BOOKINGS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS bookings (
    id TEXT PRIMARY KEY,
    student_name TEXT,
    created_by TEXT,
    start_date TEXT,
    end_date TEXT,
    package TEXT,
    selected_days TEXT,
    location TEXT,
    persons INTEGER,
    time TEXT,
    fee INTEGER,
    status TEXT,
    payment_request TEXT,
    owner_name TEXT,
    owner_phone TEXT
)
""")

# PROFILE PICTURES TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS profile_pictures (
    id SERIAL PRIMARY KEY,
    id_number VARCHAR(50) UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
cursor.close()
conn.close()

print("PostgreSQL tables created successfully ✅")