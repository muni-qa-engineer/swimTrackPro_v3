import psycopg2
from config import DATABASE_URL

def get_pg_connection():
    return psycopg2.connect(DATABASE_URL)

# --- Make-Up Credit Helpers ---

def has_makeup_credit(booking_id, original_date):
    """Return True if a make-up credit already exists for this booking/date."""
    conn = get_pg_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 1
        FROM makeup_credits
        WHERE booking_id = %s
          AND original_date = %s
        LIMIT 1
    """, (str(booking_id), original_date))

    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def create_makeup_credit(booking_id, original_date, notes='Skipped session'):
    """
    Create a make-up credit for a skipped class.
    Returns True if a new credit was created, False if one already exists.
    """
    if has_makeup_credit(booking_id, original_date):
        return False

    conn = get_pg_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO makeup_credits (
            booking_id,
            original_date,
            status,
            notes
        ) VALUES (%s, %s, 'available', %s)
    """, (
        str(booking_id),
        original_date,
        notes
    ))

    conn.commit()
    conn.close()
    return True

# --- Make-Up Credit Query Helper ---
def get_available_makeup_credits(booking_id):
    """
    Return all available make-up credits for a booking.
    """
    conn = get_pg_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, original_date, notes, created_at
        FROM makeup_credits
        WHERE booking_id = %s
          AND status = 'available'
        ORDER BY original_date
    """, (str(booking_id),))

    rows = cursor.fetchall()
    conn.close()

    credits = []
    for row in rows:
        credits.append({
            'id': row[0],
            'original_date': str(row[1]),
            'notes': row[2] or '',
            'created_at': str(row[3]) if row[3] else ''
        })

    return credits
