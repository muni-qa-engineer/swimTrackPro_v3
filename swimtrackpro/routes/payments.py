"""Payment mutation routes."""

from flask import flash, redirect, request, session, url_for

from swimtrackpro.runtime import get_pg_connection


def update_payment_status(booking_id):
    if 'user_name' not in session:
        return redirect(url_for('index'))

    new_status = (request.form.get('status') or '').strip()
    print('=' * 60)
    print('PAYMENT UPDATE REQUEST')
    print('Booking ID:', booking_id)
    print('Role:', session.get('role'))
    print('Requested Status:', new_status)
    print('=' * 60)

    allowed_statuses = [
        'Not Paid',
        'Pending Verification',
        'Paid'
    ]

    if new_status not in allowed_statuses:
        flash('Invalid payment status selected')
        return redirect(url_for('index'))

    conn = get_pg_connection()
    cursor = conn.cursor()

    role = session.get('role')

    # -------------------------
    # TRAINER VERIFICATION FLOW
    # -------------------------
    if role == 'trainer':

        print('TRAINER FLOW')
        print('Saving status:', new_status)
        cursor.execute('''
        UPDATE bookings
        SET
            status = %s,
            payment_request = %s
        WHERE id = %s
        ''', (
            new_status,
            'Paid' if new_status == 'Paid' else 'Not Paid',
            booking_id
        ))

    # -------------------------
    # GUEST PAYMENT REQUEST FLOW
    # -------------------------
    else:

        # Guest selecting Paid means:
        # Request trainer verification.
        if new_status == 'Paid':
            actual_status = 'Pending Verification'
            actual_request = 'Paid'
        else:
            actual_status = 'Not Paid'
            actual_request = 'Not Paid'

        print('GUEST FLOW')
        print('Actual Status:', actual_status)
        print('Actual Request:', actual_request)
        print('Owner Name:', session.get('user_name'))
        print('Owner Phone:', session.get('phone'))
        print('SESSION USER:', repr(session.get('user_name')))
        print('SESSION PHONE:', repr(session.get('phone')))
        cursor.execute(
            '''
            SELECT owner_name, owner_phone, status, payment_request
            FROM bookings
            WHERE id = %s
            ''',
            (booking_id,)
        )

        booking_row = cursor.fetchone()

        print('DB Booking Row:', booking_row)
        if booking_row:
            print('DB OWNER NAME:', repr(booking_row[0]))
            print('DB OWNER PHONE:', repr(booking_row[1]))
        cursor.execute('''
        UPDATE bookings
        SET
            status = %s,
            payment_request = %s
        WHERE id = %s
        ''', (
            actual_status,
            actual_request,
            booking_id
        ))
        print('ROWS UPDATED:', cursor.rowcount)

    conn.commit()
    cursor.execute(
        '''
        SELECT status, payment_request
        FROM bookings
        WHERE id = %s
        ''',
        (booking_id,)
    )

    saved_row = cursor.fetchone()

    print('DB Saved Values:', saved_row)
    conn.close()

    flash('Payment status updated successfully')
    return redirect(url_for('index'))

def register_payments_routes(app):
    app.add_url_rule('/update_payment_status/<booking_id>', endpoint='update_payment_status', view_func=update_payment_status, methods=['POST'])
