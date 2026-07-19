"""Skipped-session and make-up request routes."""

from datetime import datetime

from flask import flash, redirect, render_template, request, session, url_for

from services.booking_engine import generate_recurring_dates
from services.makeup_service import create_makeup_credit, get_available_makeup_credits
from swimtrackpro.runtime import get_pg_connection


def skip_session(booking_id, session_date):
    """
    V0033.0 Step 2 - Skip a scheduled class and create a make-up credit.

    session_date format: YYYY-MM-DD
    """
    if 'user_name' not in session:
        flash('Please log in first')
        return redirect(url_for('index'))

    # Validate that the booking exists directly from PostgreSQL.
    # Avoid calling load_data() here because load_data() may trigger
    # logic that rewrites existing bookings and causes duplicate
    # primary key errors.
    conn = get_pg_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        student_name,
        owner_name,
        owner_phone,
        email,
        start_date,
        end_date,
        selected_days,
        time
    FROM bookings
    WHERE id = %s
    LIMIT 1
    """, (str(booking_id),))

    row = cursor.fetchone()
    conn.close()

    if row:
        booking = {
            'id': row[0],
            'student': row[1],
            'owner_name': row[2],
            'owner_phone': row[3],
            'email': row[4] or '',
            'time': row[8] or '06:00 AM',
            'calendar_dates': generate_recurring_dates(
                str(row[5]),
                str(row[6]),
                row[7]
            )
        }
    else:
        booking = None

    if not booking:
        flash('Booking not found')
        return redirect(url_for('calendar_page'))

    # Guests may skip only their own bookings.
    if session.get('role') != 'trainer':
        if (
            booking.get('owner_name') != session.get('user_name')
            or booking.get('owner_phone') != session.get('phone')
        ):
            flash('Unauthorized action')
            return redirect(url_for('calendar_page'))

    # Validate that the selected date belongs to this booking schedule.
    calendar_dates = booking.get('calendar_dates', [])
    if session_date not in calendar_dates:
        flash('Invalid session date')
        return redirect(url_for('calendar_page'))
        
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo
    from datetime import timedelta
        
    # Enforce 6-hour rule
    try:
        session_datetime = datetime.strptime(f"{session_date} {booking['time']}", '%Y-%m-%d %I:%M %p')
        session_datetime = session_datetime.replace(tzinfo=ZoneInfo('Asia/Kolkata'))
        now_ist = datetime.now(ZoneInfo('Asia/Kolkata'))
        
        if session_datetime <= now_ist:
            flash('You cannot skip a class that has already started or ended.')
            return redirect(url_for('calendar_page', booking=booking_id))
            
        time_diff = (session_datetime - now_ist).total_seconds()
        if time_diff < 6 * 3600:
            flash('You can only skip a session at least 6 hours before it starts.')
            return redirect(url_for('calendar_page', booking=booking_id))
    except Exception as e:
        print("Error validating 6 hour rule:", e)

    # Create one make-up credit for this skipped session.
    created = create_makeup_credit(
        booking_id,
        session_date,
        f"Skipped session for {booking.get('student', '')}"
    )

    if created:
        flash(
            f"Session on {session_date} marked as skipped. "
            "One make-up credit has been created."
        )
    else:
        flash('A make-up credit already exists for this session.')

    return redirect(
        url_for(
            'calendar_page',
            booking=booking_id,
            date=session_date
        )
    )

def undo_skip_session(booking_id, session_date):
    """
    Remove a skipped-session credit when no make-up request has been created.

    This allows a swimmer to reverse an accidental skip before the credit
    is used to submit a pending or approved make-up request.
    """
    if 'user_name' not in session:
        flash('Please log in first')
        return redirect(url_for('index'))

    conn = get_pg_connection()
    cursor = conn.cursor()

    # Load the booking to verify ownership.
    cursor.execute("""
    SELECT owner_name, owner_phone
    FROM bookings
    WHERE id = %s
    LIMIT 1
    """, (str(booking_id),))

    booking_row = cursor.fetchone()

    if not booking_row:
        conn.close()
        flash('Booking not found.')
        return redirect(url_for('calendar_page'))

    # Guests may undo only their own skipped sessions.
    if session.get('role') != 'trainer':
        if (
            booking_row[0] != session.get('user_name')
            or booking_row[1] != session.get('phone')
        ):
            conn.close()
            flash('Unauthorized action')
            return redirect(url_for('calendar_page'))

    # Find an available make-up credit for this skipped date.
    cursor.execute("""
    SELECT id
    FROM makeup_credits
    WHERE booking_id = %s
      AND original_date = %s
      AND status = 'available'
    LIMIT 1
    """, (
        str(booking_id),
        session_date
    ))

    credit_row = cursor.fetchone()

    if not credit_row:
        conn.close()
        flash('This skipped session cannot be undone.')
        return redirect(url_for('calendar_page'))

    credit_id = credit_row[0]

    # Safety check: do not allow undo if any make-up request already exists.
    cursor.execute("""
    SELECT 1
    FROM makeup_requests
    WHERE credit_id = %s
    LIMIT 1
    """, (credit_id,))

    if cursor.fetchone():
        conn.close()
        flash('Cannot undo because a make-up request already exists.')
        return redirect(url_for('calendar_page'))

    # Delete the unused make-up credit.
    cursor.execute("""
    DELETE FROM makeup_credits
    WHERE id = %s
    """, (credit_id,))

    conn.commit()
    conn.close()

    flash('Skipped session has been restored.')
    return redirect(
        url_for(
            'calendar_page',
            booking=booking_id,
            date=session_date
        )
    )

def makeup_request_form(booking_id):
    """
    Display the make-up request form for all available credits.
    """
    if 'user_name' not in session:
        flash('Please log in first')
        return redirect(url_for('index'))

    conn = get_pg_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT student_name, owner_name, owner_phone
    FROM bookings
    WHERE id = %s
    LIMIT 1
    """, (str(booking_id),))

    row = cursor.fetchone()
    conn.close()

    if not row:
        flash('Booking not found')
        return redirect(url_for('index'))

    # Guests may access only their own bookings.
    if session.get('role') != 'trainer':
        if row[1] != session.get('user_name') or row[2] != session.get('phone'):
            flash('Unauthorized action')
            return redirect(url_for('index'))

    credits = get_available_makeup_credits(booking_id)

    if not credits:
        flash('No available make-up credits.')
        return redirect(url_for('index'))

    return render_template(
        'makeup_request.html',
        booking_id=booking_id,
        student_name=row[0],
        credits=credits
    )

def submit_makeup_request():
    """
    Create a make-up request for a selected credit and replacement date.
    """
    if 'user_name' not in session:
        flash('Please log in first')
        return redirect(url_for('index'))

    booking_id = (request.form.get('booking_id') or '').strip()
    credit_id = (request.form.get('credit_id') or '').strip()
    requested_date = (request.form.get('requested_date') or '').strip()

    if not booking_id or not credit_id or not requested_date:
        flash('All fields are required.')
        return redirect(url_for('calendar_page'))

    conn = get_pg_connection()
    cursor = conn.cursor()

    # Validate the selected credit.
    cursor.execute("""
    SELECT original_date
    FROM makeup_credits
    WHERE id = %s
      AND booking_id = %s
      AND status = 'available'
    LIMIT 1
    """, (credit_id, str(booking_id)))

    row = cursor.fetchone()

    if not row:
        conn.close()
        flash('Selected make-up credit is no longer available.')
        return redirect(url_for('calendar_page'))

    original_date = row[0]

    # --------------------------------------
    # V0033.1 Step 1 - Prevent Same-Day Selection
    # Users can only request a replacement on a future date.
    # The requested date must be strictly greater than the skipped date.
    # --------------------------------------
    try:
        requested_dt = datetime.strptime(
            requested_date,
            '%Y-%m-%d'
        ).date()

        original_dt = original_date

        if requested_dt <= original_dt:
            conn.close()
            flash(
                'Replacement date must be after the skipped session date.'
            )
            return redirect(url_for('calendar_page'))

    except Exception:
        conn.close()
        flash('Invalid replacement date.')
        return redirect(url_for('calendar_page'))

    # Prevent duplicate pending requests for the same credit.
    cursor.execute("""
    SELECT 1
    FROM makeup_requests
    WHERE credit_id = %s
      AND status IN ('pending', 'approved')
    LIMIT 1
    """, (credit_id,))

    if cursor.fetchone():
        conn.close()
        flash('A make-up request already exists for this skipped session.')
        return redirect(url_for('calendar_page'))

    # Create pending request.
    cursor.execute("""
    INSERT INTO makeup_requests (
        credit_id,
        booking_id,
        original_date,
        requested_date,
        status,
        requested_by
    ) VALUES (%s, %s, %s, %s, 'pending', %s)
    """, (
        int(credit_id),
        str(booking_id),
        original_date,
        requested_date,
        session.get('user_name')
    ))

    conn.commit()
    conn.close()

    flash('Make-up request submitted successfully for admin approval.')
    return redirect(
        url_for(
            'calendar_page',
            booking=booking_id,
            date=str(original_date)
        )
    )

def approve_makeup_request(request_id):
    """
    Approve a pending make-up request and consume the related credit.
    """
    if session.get('role') != 'trainer':
        flash('Unauthorized action')
        return redirect(url_for('index'))

    conn = get_pg_connection()
    cursor = conn.cursor()

    # Load the pending request and its credit.
    cursor.execute("""
    SELECT credit_id
    FROM makeup_requests
    WHERE id = %s
      AND status = 'pending'
    LIMIT 1
    """, (request_id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        flash('Pending make-up request not found.')
        return redirect(url_for('calendar_page'))

    credit_id = row[0]

    # Mark the request as approved.
    cursor.execute("""
    UPDATE makeup_requests
    SET
        status = 'approved',
        approved_by = %s,
        decided_at = CURRENT_TIMESTAMP
    WHERE id = %s
    """, (
        session.get('user_name', 'Admin'),
        request_id
    ))

    # Mark the associated credit as used.
    cursor.execute("""
    UPDATE makeup_credits
    SET
        status = 'used',
        used_at = CURRENT_TIMESTAMP
    WHERE id = %s
    """, (credit_id,))

    conn.commit()
    conn.close()

    flash('Make-up request approved successfully.')
    return redirect(url_for('calendar_page'))

def reject_makeup_request(request_id):
    """
    Reject or undo a pending make-up request.

    Behavior:
    - Delete the pending record from makeup_requests.
    - Restore the related makeup_credits row to status = 'available'.
    """
    if session.get('role') not in ('trainer', 'guest'):
        flash('Unauthorized action')
        return redirect(url_for('index'))

    conn = get_pg_connection()
    cursor = conn.cursor()

    # Load the pending request and related credit.
    cursor.execute("""
    SELECT credit_id
    FROM makeup_requests
    WHERE id = %s
      AND status = 'pending'
    LIMIT 1
    """, (request_id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        flash('Pending make-up request not found.')
        return redirect(url_for('calendar_page'))

    credit_id = row[0]

    # Restore the make-up credit so it can be used again.
    cursor.execute("""
    UPDATE makeup_credits
    SET
        status = 'available',
        used_at = NULL
    WHERE id = %s
    """, (credit_id,))

    # Remove the pending request completely.
    cursor.execute("""
    DELETE FROM makeup_requests
    WHERE id = %s
    """, (request_id,))

    conn.commit()
    conn.close()

    flash('Pending make-up request has been revoked.')
    return redirect(url_for('calendar_page'))

def register_makeup_routes(app):
    app.add_url_rule('/skip_session/<booking_id>/<session_date>', endpoint='skip_session', view_func=skip_session, methods=['POST'])
    app.add_url_rule('/undo_skip_session/<booking_id>/<session_date>', endpoint='undo_skip_session', view_func=undo_skip_session, methods=['POST'])
    app.add_url_rule('/makeup_request/<booking_id>', endpoint='makeup_request_form', view_func=makeup_request_form)
    app.add_url_rule('/submit_makeup_request', endpoint='submit_makeup_request', view_func=submit_makeup_request, methods=['POST'])
    app.add_url_rule('/approve_makeup_request/<int:request_id>', endpoint='approve_makeup_request', view_func=approve_makeup_request, methods=['POST'])
    app.add_url_rule('/reject_makeup_request/<int:request_id>', endpoint='reject_makeup_request', view_func=reject_makeup_request, methods=['POST'])
