import hashlib
from datetime import datetime, timedelta

def generate_booking_id(student, start_date, time_str):
    return hashlib.md5(f"{student}{start_date}{time_str}".encode()).hexdigest()

def generate_booking_code(cursor):
    cursor.execute(
        '''
        SELECT booking_code
        FROM bookings
        WHERE booking_code IS NOT NULL
        ORDER BY CAST(REPLACE(booking_code, 'STP', '') AS INTEGER) DESC
        LIMIT 1
        '''
    )

    row = cursor.fetchone()

    if row and row[0]:
        next_number = int(row[0].replace('STP', '')) + 1
    else:
        next_number = 1

    return f"STP{next_number:06d}"

# --- Recurring Booking Engine ---
def parse_selected_days(days_string):
    if not days_string:
        return []

    return [d.strip()[:3].lower() for d in days_string.split(',') if d.strip()]

def generate_recurring_dates(start_date_str, end_date_str, selected_days):
    generated_dates = []

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except:
        return generated_dates

    weekday_map = {
        'mon': 0,
        'tue': 1,
        'wed': 2,
        'thu': 3,
        'fri': 4,
        'sat': 5,
        'sun': 6
    }

    valid_days = {
        weekday_map[d]
        for d in parse_selected_days(selected_days)
        if d in weekday_map
    }

    current = start_date

    while current <= end_date:

        # Single package fallback
        if not valid_days:
            generated_dates.append(current.strftime('%Y-%m-%d'))
            break

        if current.weekday() in valid_days:
            generated_dates.append(current.strftime('%Y-%m-%d'))

        current += timedelta(days=1)

    return generated_dates
