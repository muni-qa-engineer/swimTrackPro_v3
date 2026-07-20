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

# PACKAGES TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS packages (
    id SERIAL PRIMARY KEY,
    category TEXT,
    package_name TEXT,
    base_price INTEGER,
    discount_percentage INTEGER DEFAULT 0,
    UNIQUE(category, package_name)
)
""")

# Seed default packages if empty
cursor.execute("SELECT COUNT(*) FROM packages")
if cursor.fetchone()[0] == 0:
    default_packages = [
        ('individual', 'demo', 0, 0),
        ('individual', 'single', 750, 0),
        ('individual', 'monthly', 6000, 0),
        ('individual', '3_months', 27000, 17),
        ('individual', '6_months', 54000, 22),
        ('individual', '9_months', 81000, 28),
        ('individual', '12_months', 108000, 33),
        ('group', 'demo', 0, 0),
        ('group', 'single', 2500, 0),
        ('group', 'monthly', 20000, 0),
        ('group', '3_months', 60000, 10),
        ('group', '6_months', 120000, 20),
        ('group', '9_months', 180000, 25),
        ('group', '12_months', 240000, 30)
    ]
    cursor.executemany(
        "INSERT INTO packages (category, package_name, base_price, discount_percentage) VALUES (%s, %s, %s, %s)",
        default_packages
    )

conn.commit()
cursor.close()
conn.close()

print("PostgreSQL tables created successfully ✅")