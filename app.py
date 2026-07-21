import psycopg2
from flask import Flask
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from services.booking_engine import generate_recurring_dates
from swimtrackpro import runtime
from swimtrackpro.routes.authentication import register_authentication_routes
from swimtrackpro.routes.bookings import register_bookings_routes
from swimtrackpro.routes.dashboard import register_dashboard_routes
from swimtrackpro.routes.deletions import register_deletions_routes
from swimtrackpro.routes.general import register_general_routes
from swimtrackpro.routes.makeup import register_makeup_routes
from swimtrackpro.routes.pages import register_page_routes
from swimtrackpro.routes.payments import register_payments_routes
from swimtrackpro.routes.swimmers import register_swimmer_routes

app = Flask(__name__)
from config import (
    ADMIN_USERNAME,
    ADMIN_PASSWORD,
    SECRET_KEY,
    DATABASE_URL
)
app.secret_key = SECRET_KEY
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.route('/service-worker.js')
def service_worker():
    return app.send_static_file('service-worker.js')

def get_pg_connection():
    return psycopg2.connect(DATABASE_URL)

# V0033.0 - Make-Up Class Management
def ensure_database_tables():
    """
    Creates and alters PostgreSQL tables required for core functionality, 
    makeup, multi-trainer support, and system defaults.
    """
    conn = get_pg_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id SERIAL PRIMARY KEY,
        student_name TEXT,
        owner_name TEXT,
        owner_phone TEXT,
        skill_level TEXT
    )
    """)
    
    try:
        cursor.execute("ALTER TABLE students ADD COLUMN skill_level TEXT;")
        conn.commit()
    except Exception:
        conn.rollback()

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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profile_pictures (
        id SERIAL PRIMARY KEY,
        id_number VARCHAR(50) UNIQUE NOT NULL,
        filename TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS makeup_credits (
        id SERIAL PRIMARY KEY,
        booking_id TEXT NOT NULL,
        original_date DATE NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'available',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        used_at TIMESTAMP,
        notes TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS makeup_requests (
        id SERIAL PRIMARY KEY,
        credit_id INTEGER NOT NULL REFERENCES makeup_credits(id) ON DELETE CASCADE,
        booking_id TEXT NOT NULL,
        original_date DATE NOT NULL,
        requested_date DATE NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        requested_by VARCHAR(100),
        approved_by VARCHAR(100),
        decision_notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        decided_at TIMESTAMP
    )
    """)

    # Multi-trainer tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trainers (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        experience TEXT,
        qualification TEXT,
        currently_working TEXT,
        residence_location TEXT,
        id_proof TEXT,
        consent_accepted BOOLEAN DEFAULT FALSE,
        rating NUMERIC(3,2) DEFAULT 5.00
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS coach_feedback (
        id SERIAL PRIMARY KEY,
        trainer_username TEXT NOT NULL REFERENCES trainers(username) ON DELETE CASCADE,
        guest_name TEXT NOT NULL,
        guest_phone TEXT NOT NULL,
        rating INTEGER NOT NULL,
        pros TEXT,
        cons TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Ensure columns exist if the table was created earlier without them
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS experience TEXT")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS qualification TEXT")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS currently_working TEXT")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS residence_location TEXT")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS id_proof TEXT")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS consent_accepted BOOLEAN DEFAULT FALSE")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS rating NUMERIC(3,2) DEFAULT 5.00")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS photos TEXT DEFAULT ''")
    
    # V0034.0 - Rich Trainer Profiles
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS bio TEXT")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS specialties TEXT")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS instagram TEXT")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS facebook TEXT")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS twitter TEXT")
    
    # Trainer Payment Settings
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS upi_id TEXT")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS qr_code TEXT")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS account_holder_name TEXT")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS youtube TEXT")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS notice TEXT DEFAULT ''")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS whatsapp TEXT DEFAULT ''")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS consent_version TEXT DEFAULT 'v1.0'")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS consent_accepted_at TIMESTAMP WITHOUT TIME ZONE")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS consent_ip TEXT")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS id_number TEXT")
    cursor.execute("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN DEFAULT FALSE")

    cursor.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN DEFAULT FALSE")

    # Pre-populate default admin trainer if not exists
    cursor.execute("SELECT username FROM trainers WHERE LOWER(username) = LOWER(%s)", (ADMIN_USERNAME,))
    if not cursor.fetchone():
        cursor.execute("""
        INSERT INTO trainers (username, password, name, phone, email, experience, qualification, currently_working, residence_location, id_proof, consent_accepted, rating, notice, is_approved)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (ADMIN_USERNAME, ADMIN_PASSWORD, 'Trainer', '', '', '5+ Years', 'Certified Swim Coach', 'SwimTrackPro Academy', 'Local Camp', 'UID-12345', True, 5.00, '💰 Monthly fees are due before 5 days of the package end date • 🏆 Special coaching sessions available • 📞 Contact the trainer for any schedule changes', True))
    else:
        # Update existing admin trainer with default values if they are null
        cursor.execute("""
        UPDATE trainers 
        SET experience = COALESCE(experience, '5+ Years'),
            qualification = COALESCE(qualification, 'Certified Swim Coach'),
            currently_working = COALESCE(currently_working, 'SwimTrackPro Academy'),
            residence_location = COALESCE(residence_location, 'Local Camp'),
            id_proof = COALESCE(id_proof, 'UID-12345'),
            consent_accepted = TRUE,
            rating = COALESCE(rating, 5.00),
            notice = COALESCE(notice, '💰 Monthly fees are due before 5 days of the package end date • 🏆 Special coaching sessions available • 📞 Contact the trainer for any schedule changes'),
            is_approved = TRUE
        WHERE LOWER(username) = LOWER(%s)
        """, (ADMIN_USERNAME,))

    # ID Number Assignment Logic
    cursor.execute("""
    UPDATE trainers 
    SET id_number = 'STPA0001' 
    WHERE LOWER(username) = LOWER(%s) AND id_number IS NULL
    """, (ADMIN_USERNAME,))

    cursor.execute("SELECT MAX(CAST(SUBSTRING(id_number FROM 5) AS INTEGER)) FROM trainers WHERE id_number LIKE 'STPC%'")
    max_coach_val = cursor.fetchone()[0] or 0

    cursor.execute("""
    WITH numbered AS (
        SELECT username, ROW_NUMBER() OVER (ORDER BY username) as rn
        FROM trainers
        WHERE LOWER(username) != LOWER(%s) AND id_number IS NULL
    )
    UPDATE trainers t
    SET id_number = 'STPC' || LPAD((nt.rn + %s)::TEXT, 4, '0')
    FROM numbered nt
    WHERE t.username = nt.username
    """, (ADMIN_USERNAME, max_coach_val))

    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS trainer_username TEXT")
    cursor.execute("UPDATE bookings SET trainer_username = %s WHERE trainer_username IS NULL", (ADMIN_USERNAME,))
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS pause_status TEXT DEFAULT 'ACTIVE'")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS pause_used BOOLEAN DEFAULT FALSE")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS pause_date TEXT")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS resume_date TEXT")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS auto_resume_date TEXT")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS pause_reason TEXT")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS pause_other_reason TEXT")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS paused_days INTEGER DEFAULT 0")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS package_status TEXT DEFAULT 'ACTIVE'")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS last_status_change TIMESTAMP WITHOUT TIME ZONE")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS calendar_dates_override TEXT")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS pause_count INTEGER DEFAULT 0")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS pause_request_status TEXT")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS pause_requested_on TEXT")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS pause_requested_by TEXT")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS pause_approved_by TEXT")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS pause_approved_on TEXT")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS pause_rejected_by TEXT")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS pause_rejected_on TEXT")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS rejection_reason TEXT")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS resume_type TEXT")
    cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS remaining_classes_at_pause INTEGER")
    cursor.execute("UPDATE bookings SET pause_count = 1 WHERE pause_used = TRUE AND (pause_count IS NULL OR pause_count = 0)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS package_pause_audit (
        id SERIAL PRIMARY KEY,
        booking_id TEXT NOT NULL,
        action TEXT NOT NULL,
        performed_by TEXT NOT NULL,
        pause_date TEXT,
        resume_date TEXT,
        is_auto_resume BOOLEAN DEFAULT FALSE,
        reason TEXT,
        ip_address TEXT,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("ALTER TABLE user_activity ADD COLUMN IF NOT EXISTS current_login TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP")
    cursor.execute("ALTER TABLE user_activity ADD COLUMN IF NOT EXISTS previous_login TIMESTAMP WITHOUT TIME ZONE")
    cursor.execute("ALTER TABLE user_activity ADD COLUMN IF NOT EXISTS id_number TEXT")

    cursor.execute("SELECT MAX(CAST(SUBSTRING(id_number FROM 5) AS INTEGER)) FROM user_activity WHERE id_number LIKE 'STPS%'")
    max_guest_val = cursor.fetchone()[0] or 0

    cursor.execute("""
    WITH numbered AS (
        SELECT id, ROW_NUMBER() OVER (ORDER BY id) as rn
        FROM user_activity
        WHERE role = 'guest' AND id_number IS NULL
    )
    UPDATE user_activity u
    SET id_number = 'STPS' || LPAD((nt.rn + %s)::TEXT, 4, '0')
    FROM numbered nt
    WHERE u.id = nt.id
    """, (max_guest_val,))

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS password_reset_otps (
        id SERIAL PRIMARY KEY,
        email TEXT NOT NULL,
        otp TEXT NOT NULL,
        expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def load_data():
    ensure_database_tables()
    conn = get_pg_connection()
    cursor = conn.cursor()

    # Load students
    cursor.execute('SELECT * FROM students')
    student_rows = cursor.fetchall()

    students = []
    for s in student_rows:
        students.append({
            'name': s[1],
            'owner_name': s[2],
            'owner_phone': s[3],
            'is_blocked': s[4] if len(s) > 4 else False
        })

    # Load bookings
    cursor.execute('SELECT * FROM bookings')
    booking_colnames = [desc[0].lower() for desc in cursor.description]
    booking_rows = cursor.fetchall()

    # -------------------------------------------------------
    # OPTIMIZATION: Bulk-fetch all makeup data in 2 queries
    # instead of opening a new connection per booking.
    # -------------------------------------------------------

    # All credits grouped by booking_id
    cursor.execute("""
        SELECT id, booking_id, original_date, status, created_at
        FROM makeup_credits
        ORDER BY original_date
    """)
    all_credits = cursor.fetchall()

    credits_by_booking = {}
    for row in all_credits:
        bid = str(row[1])
        credits_by_booking.setdefault(bid, []).append(row)

    # All requests grouped by booking_id
    cursor.execute("""
        SELECT id, credit_id, booking_id, original_date, requested_date, status
        FROM makeup_requests
        ORDER BY requested_date
    """)
    all_requests = cursor.fetchall()

    requests_by_booking = {}
    for row in all_requests:
        bid = str(row[2])
        requests_by_booking.setdefault(bid, []).append(row)

    # -------------------------------------------------------

    bookings = []

    for b_row in booking_rows:
        b = dict(zip(booking_colnames, b_row))
        calendar_override = b.get('calendar_dates_override')
        if calendar_override:
            calendar_dates = [d.strip() for d in calendar_override.split(',') if d.strip()]
        else:
            calendar_dates = generate_recurring_dates(
                str(b.get('start_date', '')),
                str(b.get('end_date', '')),
                b.get('selected_days', '')
            )

        # V0037.3 - Real-Time Class Progress Completion
        # A class is considered completed when the current time is
        # greater than or equal to the session start time + 1 hour.
        is_completed = False
        total_classes = len(calendar_dates)
        completed_classes = 0
        remaining_classes = total_classes

        try:
            if calendar_dates:
                current_datetime = datetime.now(
                    ZoneInfo('Asia/Kolkata')
                ).replace(tzinfo=None)
                booking_time = (b.get('time') or '06:00 AM').strip()

                for class_date in calendar_dates:
                    class_datetime = datetime.strptime(
                        f"{class_date} {booking_time}",
                        '%Y-%m-%d %I:%M %p'
                    )
                    # Each session duration is 1 hour.
                    class_end_datetime = class_datetime + timedelta(hours=1)

                    # Mark as completed immediately after session end time.
                    if current_datetime >= class_end_datetime:
                        completed_classes += 1

                remaining_classes = max(
                    total_classes - completed_classes,
                    0
                )

                if total_classes > 0 and completed_classes >= total_classes:
                    is_completed = True

        except Exception as e:
            is_completed = False
            completed_classes = 0
            remaining_classes = total_classes

        # V0052.0 - Restore correct class counts when package is paused
        pause_status_val = b.get('pause_status') or 'ACTIVE'
        if pause_status_val in ('Paused', 'PAUSED'):
            remaining_classes = b.get('remaining_classes_at_pause') or 0
            total_classes = completed_classes + remaining_classes
            is_completed = False

        booking = {
            'id': b.get('id'),
            'student': b.get('student_name'),
            'created_by': b.get('created_by'),
            'start_date': b.get('start_date'),
            'end_date': b.get('end_date'),
            'package': b.get('package'),
            'selected_days': b.get('selected_days'),
            'location': b.get('location'),
            'persons': b.get('persons'),
            'time': b.get('time'),
            'fee': b.get('fee'),
            'status': b.get('status'),
            'payment_request': b.get('payment_request'),
            'payment_status': b.get('payment_request'),
            'owner_name': b.get('owner_name'),
            'owner_phone': b.get('owner_phone'),
            'email': b.get('email') or '',
            'booking_code': b.get('booking_code') or '',
            'payment_reminder_sent': b.get('payment_reminder_sent', False),
            'payment_reminder_sent_at': b.get('payment_reminder_sent_at'),
            'delete_requested': b.get('delete_requested', False),
            'delete_requested_at': b.get('delete_requested_at'),
            'delete_requested_by': b.get('delete_requested_by'),
            'calendar_dates': calendar_dates,
            'is_completed': is_completed,
            'total_classes': total_classes,
            'completed_classes': completed_classes,
            'remaining_classes': remaining_classes,
            'trainer_username': b.get('trainer_username') or 'asdf',
            'pause_status': b.get('pause_status') or 'ACTIVE',
            'pause_used': b.get('pause_used', False),
            'pause_date': b.get('pause_date'),
            'resume_date': b.get('resume_date'),
            'auto_resume_date': b.get('auto_resume_date'),
            'pause_reason': b.get('pause_reason'),
            'pause_other_reason': b.get('pause_other_reason'),
            'paused_days': b.get('paused_days', 0),
            'package_status': b.get('package_status') or 'ACTIVE',
            'last_status_change': b.get('last_status_change'),
            # V0052.0 - New pause workflow properties
            'pause_count': b.get('pause_count', 0),
            'pause_request_status': b.get('pause_request_status'),
            'pause_requested_on': b.get('pause_requested_on'),
            'pause_requested_by': b.get('pause_requested_by'),
            'pause_approved_by': b.get('pause_approved_by'),
            'pause_approved_on': b.get('pause_approved_on'),
            'pause_rejected_by': b.get('pause_rejected_by'),
            'pause_rejected_on': b.get('pause_rejected_on'),
            'rejection_reason': b.get('rejection_reason'),
            'resume_type': b.get('resume_type'),
            'remaining_classes_at_pause': b.get('remaining_classes_at_pause'),
        }

        # -------------------------------------------------------
        # Map pre-fetched makeup data — no DB calls inside loop
        # -------------------------------------------------------
        bid = str(booking['id'])
        booking_credits = credits_by_booking.get(bid, [])
        booking_requests = requests_by_booking.get(bid, [])

        pending_request = next((r for r in booking_requests if r[5] == 'pending'), None)
        approved_request = next((r for r in booking_requests if r[5] == 'approved'), None)

        # Total credits created for this booking
        booking['makeup_credits_used'] = len(booking_credits)

        # First available credit
        available_credits = [
            r for r in booking_credits if r[3] == 'available'
        ]
        first_available = available_credits[0] if available_credits else None

        booking['available_makeup_credit_id'] = (
            first_available[0] if first_available else None
        )
        booking['has_available_makeup_credit'] = first_available is not None

        # Skipped dates
        booking['skipped_dates'] = [
            str(r[2]) for r in booking_credits
        ]

        # Dates where the credit was already used
        booking['used_makeup_dates'] = [
            str(r[2]) for r in booking_credits if r[3] == 'used'
        ]

        # Add new fields for Calendar UI make-up workflow state
        booking['pending_request_id'] = pending_request[0] if pending_request else None
        booking['approved_request_id'] = approved_request[0] if approved_request else None
        
        # New Rule: 1 skip allowed for every 6 sessions booked
        total_skips_allowed = booking.get('total_classes', 0) // 6
        skips_used = len(booking_credits)
        skip_remaining = max(0, total_skips_allowed - skips_used)
        
        booking['skip_remaining'] = skip_remaining
        booking['skip_eligible'] = skip_remaining > 0
        booking['valid_until'] = booking['end_date']
        booking['makeup_used'] = approved_request is not None

        # Makeup requests (expanded for Calendar UI)
        booking['makeup_requests'] = [
            {
                'id': r[0],
                'credit_id': r[1],
                'original_date': str(r[3]),
                'requested_date': str(r[4]),
                'status': r[5]
            }
            for r in booking_requests
        ]

        bookings.append(booking)

    conn.close()

    return {
        'students': students,
        'bookings': bookings
    }



# --- ROUTES ---
runtime.configure(
    get_pg_connection=get_pg_connection,
    load_data=load_data,
)
try:
    ensure_database_tables()
except Exception as e:
    print(f"Warning: Could not run ensure_database_tables on startup: {e}")

register_dashboard_routes(app)
register_page_routes(
    app,
    get_pg_connection=get_pg_connection,
    load_data=load_data,
)
register_authentication_routes(
    app,
    get_pg_connection=get_pg_connection,
    admin_username=ADMIN_USERNAME,
    admin_password=ADMIN_PASSWORD,
)
register_swimmer_routes(
    app,
    get_pg_connection=get_pg_connection,
    load_data=load_data,
)
register_bookings_routes(app)
register_payments_routes(app)
register_deletions_routes(app)
register_makeup_routes(app)
register_general_routes(app)

@app.after_request
def add_header(response):
    """
    Prevent caching of pages to ensure back button doesn't reveal logged-in state after logout
    """
    if 'text/html' in response.headers.get('Content-Type', ''):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
    return response

@app.errorhandler(psycopg2.OperationalError)
def handle_db_error(e):
    return """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Database Offline - SwimTrackPro</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            body {
                font-family: 'Poppins', sans-serif;
                background-color: #f8fafc;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
            }
            .error-card {
                background: white;
                border-radius: 24px;
                padding: 40px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
                max-width: 500px;
                text-align: center;
            }
            .error-icon {
                font-size: 64px;
                margin-bottom: 20px;
            }
        </style>
</head>
<body>
    <div class="error-card">
        <div class="error-icon">🔌</div>
        <h3 class="fw-bold text-dark mb-3">Database Connection Offline</h3>
        <p class="text-muted mb-4">
            SwimTrackPro is currently unable to connect to the database. This could be due to a temporary internet connection interruption or server maintenance.
        </p>
        <button class="btn btn-primary px-4 py-2.5 rounded-pill fw-bold" onclick="window.location.reload();">
            🔄 Retry Connection
        </button>
        <div class="mt-4 text-start bg-light p-3 rounded-3 small text-secondary" style="font-family: monospace; overflow-x: auto;">
            <strong>Diagnostic Error:</strong><br>
            Unable to resolve the database server host.
        </div>
    </div>
</body>
</html>
""", 503

if __name__ == '__main__':
    app.run(debug=True)
