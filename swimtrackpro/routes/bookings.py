"""Booking creation and editing routes."""

from datetime import datetime, timedelta

from flask import flash, redirect, render_template, request, session, url_for, jsonify
from zoneinfo import ZoneInfo
from services.settings_service import get_setting
from services.booking_engine import parse_selected_days
from swimtrackpro.auth import login_required

from services.booking_engine import (
    generate_booking_code,
    generate_booking_id,
    generate_recurring_dates,
)
from services.email_service import send_booking_confirmation_email
from services.pricing_service import calculate_discounted_fee
from swimtrackpro.runtime import get_pg_connection, load_data


def book():
    if session.get('role') == 'trainer':
        flash('Trainer cannot create bookings directly')
        return redirect(url_for('index'))
    data = load_data()
    # Enhanced validation and logic for booking
    student = request.form['student']
    date_str = request.form['date']
    time_str = (request.form.get('time') or '').strip()

    if not time_str:
        print('DEBUG BOOK FORM KEYS:', list(request.form.keys()))
        flash('Please select a valid time slot before confirming booking.', 'warning')
        return redirect('/booking')
    email = (request.form.get('email') or '').strip()
    package = request.form.get('package', 'Single')
    end_date = request.form.get('end_date', date_str)
    persons = request.form.get('persons', 1)

    # Default fee based on package and group discount.
    session_count = None

    if package == 'Monthly':
        selected_days = request.form.get('selected_days', '')
        session_count = len([
            day.strip()
            for day in selected_days.split(',')
            if day.strip()
        ])

    elif package == 'Custom':
        session_count = len(
            generate_recurring_dates(
                date_str,
                end_date,
                request.form.get('selected_days', '')
            )
        )

    fee = calculate_discounted_fee(package, persons, session_count)

    if package == 'Demo':
        fee = 0

    # V0044.0 - Custom package fee is calculated by the frontend fee engine.
    if package == 'Custom':
        try:
            fee = int(float(request.form.get('fee', 0) or 0))
        except Exception:
            fee = 0

    # Allow manual fee override only for admin users.
    # Guest users always use the system-calculated fee.
    if session.get('role') == 'trainer':
        manual_fee = (request.form.get('fee') or '').strip()
        if manual_fee:
            try:
                fee = int(float(manual_fee))
            except ValueError:
                pass

    # Normalize end date based on package
    if package in ('Single', 'Demo'):
        end_date = date_str
    elif package == 'Monthly':
        start_dt = datetime.strptime(date_str, '%Y-%m-%d').date()
        next_month = start_dt + timedelta(days=31)
        end_date = (next_month - timedelta(days=1)).strftime('%Y-%m-%d')
    # Validate that end date is not earlier than start date
    try:
        start_dt = datetime.strptime(date_str, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

        if end_dt < start_dt:
            flash('End date cannot be earlier than start date')
            return redirect(url_for('index'))
    except Exception:
        flash('Invalid start or end date')
        return redirect(url_for('index'))

    # Validate past date
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        if selected_date < datetime.today().date():
            flash("Cannot book past dates")
            return redirect(url_for('index'))
    except:
        flash("Invalid date")
        return redirect(url_for('index'))

    booking_id = generate_booking_id(student, date_str, time_str)

    conn = get_pg_connection()
    cursor = conn.cursor()
    booking_code = generate_booking_code(cursor)
    print('GENERATED BOOKING CODE:', booking_code)

    # Prevent overlapping bookings within 1 hour
    try:
        booking_time = datetime.strptime(time_str, '%I:%M %p')
    except Exception:
        flash('Invalid time format')
        return redirect(url_for('index'))

    new_booking_dates = generate_recurring_dates(
        date_str,
        end_date,
        request.form.get('selected_days', '')
    )

    # -------------------------------------------------
    # Recurring-date Trainer Location Conflict Check & Group Swimmer Handling
    # -------------------------------------------------
    # 1. Duplicate Booking Check (same student, same time)
    for b in data['bookings']:
        try:
            same_student = (b.get('student', '').strip().lower() == student.strip().lower() and 
                            b.get('owner_name') == session.get('user_name'))
            if not same_student:
                continue
            
            existing_start = str(b.get('start_date', ''))
            existing_end = str(b.get('end_date', b.get('start_date', '')))
            existing_days = b.get('selected_days', '')
            existing_booking_dates = generate_recurring_dates(existing_start, existing_end, existing_days)
            
            overlapping_dates = set(new_booking_dates) & set(existing_booking_dates)
            if not overlapping_dates:
                continue
                
            existing_time_str = b.get('time')
            if not existing_time_str: continue
            
            existing_time = datetime.strptime(existing_time_str, '%I:%M %p')
            time_diff = abs((booking_time - existing_time).total_seconds()) / 60
            
            if time_diff < 60:
                flash('Duplicate booking already exists.', 'warning')
                return redirect('/booking?booking_conflict=true')
        except Exception:
            continue

    # 2. Coach Availability & Group Swimming Check
    group_swimmers = set()
    for b in data['bookings']:
        try:
            if b.get('trainer_username', '').strip().lower() != trainer_username:
                continue
                
            existing_start = str(b.get('start_date', ''))
            existing_end = str(b.get('end_date', b.get('start_date', '')))
            existing_days = b.get('selected_days', '')
            existing_booking_dates = generate_recurring_dates(existing_start, existing_end, existing_days)
            
            overlapping_dates = set(new_booking_dates) & set(existing_booking_dates)
            if not overlapping_dates:
                continue
                
            existing_time_str = b.get('time')
            if not existing_time_str: continue
            
            existing_time = datetime.strptime(existing_time_str, '%I:%M %p')
            time_diff = abs((booking_time - existing_time).total_seconds()) / 60
            
            if time_diff < 60:
                existing_location = b.get('location', '').strip().lower()
                if existing_location != new_location:
                    suggested_time = (existing_time + timedelta(hours=1)).strftime('%I:%M %p')
                    flash(f'The slot is already booked in other location. Please change timing, coach or location. Suggested time for this coach: {suggested_time}', 'warning')
                    return redirect('/booking?location_conflict=true')
                else:
                    group_swimmer_name = b.get('student')
                    if group_swimmer_name and group_swimmer_name.strip().lower() != student.strip().lower():
                        group_swimmers.add(group_swimmer_name)
        except Exception:
            continue
            
    if group_swimmers:
        swimmer_names = ", ".join(group_swimmers)
        flash(f'You will swim along with a swimmer: {swimmer_names}', 'info')



    payment_choice = request.form.get('payment_status', 'Not Paid')

    if payment_choice == 'Paid':
        status = 'Pending'
    else:
        status = 'Not Paid'

    trainer_username = request.form.get('trainer_username', 'asdf').strip().lower()

    new_booking = {
        "id": booking_id,
        "booking_code": booking_code,
        "student": student,
        "created_by": session.get('user_name'),
        "start_date": date_str,
        "end_date": end_date,
        "package": package,
        "selected_days": request.form.get('selected_days', ''),
        "location": request.form.get('location', '').strip(),
        "email": email,
        "persons": persons,
        "time": time_str,
        "fee": fee,
        "status": status,
        "payment_request": payment_choice,
        "owner_name": session.get('user_name'),
        "owner_phone": session.get('phone'),
        "trainer_username": trainer_username,
    }

    # V0037.1 - Automatically create the swimmer if it does not already exist.
    existing_swimmer = next(
        (
            s for s in data['students']
            if isinstance(s, dict)
            and (s.get('name') or '').strip().lower() == student.strip().lower()
            and s.get('owner_name') == session.get('user_name')
            and s.get('owner_phone') == session.get('phone')
        ),
        None
    )

    if not existing_swimmer:
        swimmer_conn = get_pg_connection()
        swimmer_cursor = swimmer_conn.cursor()

        swimmer_cursor.execute('''
        INSERT INTO students (
            student_name,
            owner_name,
            owner_phone,
            skill_level
        ) VALUES (%s, %s, %s, %s)
        ''', (
            student.strip(),
            session.get('user_name'),
            session.get('phone'),
            request.form.get('skill_level', 'Beginner')
        ))

        swimmer_conn.commit()
        swimmer_conn.close()

    # Convert group_swimmers set to sorted list for deterministic indexing
    group_swimmers = sorted(group_swimmers)
    # Flash group swimmer info if needed
    if group_swimmers:
        if len(group_swimmers) == 1:
            flash(f'You are swimming along with {group_swimmers[0]}.', 'info')
        else:
            name1 = group_swimmers[0]
            name2 = group_swimmers[1] if len(group_swimmers) > 1 else ''
            others_count = len(group_swimmers) - 2
            if others_count > 0:
                flash(f'You are swimming along with {name1}, {name2} and {others_count} others.', 'info')
            else:
                flash(f'You are swimming along with {name1}, {name2}.', 'info')

    cursor.execute('''
    INSERT INTO bookings (
        id,
        booking_code,
        student_name,
        created_by,
        start_date,
        end_date,
        package,
        selected_days,
        location,
        persons,
        time,
        fee,
        status,
        payment_request,
        owner_name,
        owner_phone,
        email,
        trainer_username
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        new_booking['id'],
        new_booking['booking_code'],
        new_booking['student'],
        new_booking['created_by'],
        new_booking['start_date'],
        new_booking['end_date'],
        new_booking['package'],
        new_booking['selected_days'],
        new_booking['location'],
        int(new_booking['persons']),
        new_booking['time'],
        int(new_booking['fee']),
        new_booking['status'],
        new_booking['payment_request'],
        new_booking['owner_name'],
        new_booking['owner_phone'],
        new_booking['email'],
        new_booking['trainer_username']
    ))

    conn.commit()
    conn.close()

    # The confirmation email will be sent after payment options are confirmed.
    return redirect(f'/payment_options/{booking_id}')

def edit_booking(booking_id):
    data = load_data()

    # Find booking
    booking = next((b for b in data['bookings'] if b['id'] == booking_id), None)

    if not booking:
        flash("Booking not found")
        return redirect(url_for('index'))

    # Trainer check
    if session.get('role') == 'trainer':
        trainer_user = session.get('trainer_username') or 'asdf'
        if (booking.get('trainer_username') or 'asdf').strip().lower() != trainer_user.strip().lower():
            flash("Unauthorized action")
            return redirect(url_for('index'))

    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, name FROM trainers ORDER BY name")
    trainers = [{"username": row[0], "name": row[1]} for row in cursor.fetchall()]
    conn.close()

    # Render edit page with booking data and user role
    return render_template(
        'editBooking.html',
        booking=booking,
        role=session.get('role', 'guest'),
        trainers=trainers
    )

def update_booking(booking_id):
    data = load_data()

    # Find booking
    booking = next((b for b in data['bookings'] if b['id'] == booking_id), None)

    if not booking:
        flash("Booking not found")
        return redirect(url_for('index'))

    # Trainer check
    if session.get('role') == 'trainer':
        trainer_user = session.get('trainer_username') or 'asdf'
        if (booking.get('trainer_username') or 'asdf').strip().lower() != trainer_user.strip().lower():
            flash("Unauthorized action")
            return redirect(url_for('index'))

    old_values = {
        'student': booking.get('student', ''),
        'start_date': booking.get('start_date', ''),
        'end_date': booking.get('end_date', ''),
        'package': booking.get('package', ''),
        'selected_days': booking.get('selected_days', ''),
        'location': booking.get('location', ''),
        'time': booking.get('time', ''),
        'fee': booking.get('fee', ''),
        'persons': booking.get('persons', '')
    }

    # Get updated values
    student = request.form['student']
    date_str = request.form['date']
    time_str = (request.form.get('time') or '').strip()

    if not time_str:
        print('DEBUG UPDATE FORM KEYS:', list(request.form.keys()))
        flash('Please select a valid time slot before saving changes.', 'warning')
        return redirect(url_for('edit_booking', booking_id=booking_id))

    package = request.form.get('package', 'Single')
    end_date = request.form.get('end_date', date_str)
    persons = request.form.get('persons', 1)

    # Default fee based on package and group discount.
    session_count = None
    selected_days = request.form.getlist('selected_days')
    selected_days_str = ', '.join(selected_days)

    if package == 'Monthly':
        session_count = len([
            day.strip()
            for day in selected_days
            if day.strip()
        ])

    elif package == 'Custom':
        session_count = len(
            generate_recurring_dates(
                date_str,
                end_date,
                selected_days_str
            )
        )

    fee = calculate_discounted_fee(package, persons, session_count)
    if package == 'Demo':
        fee = 0

    # V0044.0 - Custom package fee is calculated by the frontend fee engine.
    if package == 'Custom':
        try:
            fee = int(float(request.form.get('fee', 0) or 0))
        except Exception:
            fee = 0

    # Fee was already calculated above using calculate_discounted_fee().
    # Do not recalculate here, otherwise Edit Booking can overwrite the
    # correct pricing engine result (for example Monthly 2-days becoming ₹9000).
    # Trainer can still manually override the fee.
    # Only the old package/day-based recalculation was removed.
    if session.get('role') == 'trainer':
        manual_fee = (request.form.get('fee') or '').strip()

        if manual_fee:
            try:
                fee = int(float(manual_fee))
            except ValueError:
                pass

    # Normalize end date based on package
    if package in ('Single', 'Demo'):
        end_date = date_str
    elif package == 'Monthly':
        start_dt = datetime.strptime(date_str, '%Y-%m-%d').date()
        next_month = start_dt + timedelta(days=31)
        end_date = (next_month - timedelta(days=1)).strftime('%Y-%m-%d')
    # Validate that end date is not earlier than start date
    try:
        start_dt = datetime.strptime(date_str, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

        if end_dt < start_dt:
            flash('End date cannot be earlier than start date')
            return redirect(url_for('edit_booking', booking_id=booking_id))
    except Exception:
        flash('Invalid start or end date')
        return redirect(url_for('edit_booking', booking_id=booking_id))

    # Get selected class days
    selected_days = request.form.getlist('selected_days')

    # Convert selected days list to comma-separated string
    selected_days_str = ', '.join(selected_days)

    # Prevent overlapping bookings when editing
    try:
        booking_time = datetime.strptime(time_str, '%I:%M %p')
    except Exception:
        flash('Invalid time format')
        return redirect(url_for('edit_booking', booking_id=booking_id))

    new_booking_dates = generate_recurring_dates(
        date_str,
        end_date,
        selected_days_str
    )

    # --- Recurring-date Trainer Location Conflict Check (same as in book()) ---
    new_location = (request.form.get('location') or '').strip().lower()
    
    # 1. Duplicate Booking Check (same student, same time)
    for b in data['bookings']:
        try:
            # Skip the booking currently being edited
            if str(b.get('id')) == str(booking_id):
                continue
                
            same_student = (b.get('student', '').strip().lower() == student.strip().lower() and 
                            b.get('owner_name') == session.get('user_name'))
            if not same_student:
                continue
            
            existing_start = str(b.get('start_date', ''))
            existing_end = str(b.get('end_date', b.get('start_date', '')))
            existing_days = b.get('selected_days', '')
            existing_booking_dates = generate_recurring_dates(existing_start, existing_end, existing_days)
            
            overlapping_dates = set(new_booking_dates) & set(existing_booking_dates)
            if not overlapping_dates:
                continue
                
            existing_time_str = b.get('time')
            if not existing_time_str: continue
            
            existing_time = datetime.strptime(existing_time_str, '%I:%M %p')
            time_diff = abs((booking_time - existing_time).total_seconds()) / 60
            
            if time_diff < 60:
                flash('Duplicate booking already exists.', 'warning')
                return redirect(url_for('edit_booking', booking_id=booking_id))
        except Exception:
            continue

    # 2. Coach Availability & Group Swimming Check
    group_swimmers = set()
    for b in data['bookings']:
        try:
            # Skip the booking currently being edited
            if str(b.get('id')) == str(booking_id):
                continue
                
            trainer_username = booking.get('trainer_username', 'asdf').strip().lower()
            if b.get('trainer_username', '').strip().lower() != trainer_username:
                continue
                
            existing_start = str(b.get('start_date', ''))
            existing_end = str(b.get('end_date', b.get('start_date', '')))
            existing_days = b.get('selected_days', '')
            existing_booking_dates = generate_recurring_dates(existing_start, existing_end, existing_days)
            
            overlapping_dates = set(new_booking_dates) & set(existing_booking_dates)
            if not overlapping_dates:
                continue
                
            existing_time_str = b.get('time')
            if not existing_time_str: continue
            
            existing_time = datetime.strptime(existing_time_str, '%I:%M %p')
            time_diff = abs((booking_time - existing_time).total_seconds()) / 60
            
            if time_diff < 60:
                existing_location = b.get('location', '').strip().lower()
                new_location = request.form.get('location', '').strip().lower()
                if existing_location != new_location:
                    suggested_time = (existing_time + timedelta(hours=1)).strftime('%I:%M %p')
                    flash(f'The slot is already booked in other location. Please change timing, coach or location. Suggested time for this coach: {suggested_time}', 'warning')
                    return redirect(url_for('edit_booking', booking_id=booking_id))
                else:
                    group_swimmer_name = b.get('student')
                    if group_swimmer_name and group_swimmer_name.strip().lower() != student.strip().lower():
                        group_swimmers.add(group_swimmer_name)
        except Exception:
            continue
            
    if group_swimmers:
        swimmer_names = ", ".join(group_swimmers)
        flash(f'You will swim along with a swimmer: {swimmer_names}', 'info')

    # Update values
    booking['student'] = student
    booking['start_date'] = date_str
    booking['end_date'] = end_date
    booking['package'] = package
    booking['selected_days'] = selected_days_str
    booking['location'] = request.form.get('location', '').strip()
    booking['time'] = time_str
    booking['fee'] = fee

    booking['persons'] = persons

    payment_choice = request.form.get('payment_status', 'Not Paid')
    booking['payment_request'] = payment_choice

    role = session.get('role')

    # Guest payment request flow
    if role != 'trainer':

        if payment_choice == 'Paid':
            booking['status'] = 'Pending'
        else:
            booking['status'] = 'Not Paid'

    # Trainer edit flow
    else:

        # Trainer uses same edit dropdown
        if payment_choice == 'Paid':
            booking['status'] = 'Paid'
        else:
            booking['status'] = 'Not Paid'

    trainer_username = request.form.get('trainer_username', booking.get('trainer_username', 'asdf')).strip().lower()
    booking['trainer_username'] = trainer_username

    conn = get_pg_connection()
    cursor = conn.cursor()

    cursor.execute('''
    UPDATE bookings
    SET
        student_name = %s,
        start_date = %s,
        end_date = %s,
        package = %s,
        selected_days = %s,
        location = %s,
        time = %s,
        fee = %s,
        persons = %s,
        status = %s,
        payment_request = %s,
        trainer_username = %s
    WHERE id = %s
    ''', (
        booking['student'],
        booking['start_date'],
        booking['end_date'],
        booking['package'],
        booking['selected_days'],
        booking['location'],
        booking['time'],
        int(booking['fee']),
        int(booking['persons']),
        booking['status'],
        booking['payment_request'],
        booking['trainer_username'],
        booking_id
    ))

    changes = []

    field_labels = {
        'student': 'Swimmer',
        'start_date': 'Start Date',
        'end_date': 'End Date',
        'package': 'Package',
        'selected_days': 'Selected Days',
        'location': 'Location',
        'time': 'Time',
        'fee': 'Fee',
        'persons': 'Persons'
    }

    for field, label in field_labels.items():
        old_value = str(old_values.get(field, ''))
        new_value = str(booking.get(field, ''))

        if old_value != new_value:
            changes.append({
                'field': label,
                'old': old_value,
                'new': new_value
            })

    conn.commit()
    conn.close()

    if changes:
        print('BOOKING UPDATED:', changes)

    # flash("Booking updated successfully")
    return redirect('/my-bookings')

def is_date_holiday_or_closed(date_str):
    holidays = get_setting("public_holidays", ["2026-08-15", "2026-10-02", "2026-12-25"])
    closures = get_setting("pool_closures", [])
    return (date_str in holidays) or (date_str in closures)

def check_single_date_conflict(*, booking_id, trainer_username, student, owner_name, time_str, location, date_str, existing_bookings):
    for b in existing_bookings:
        if str(b.get("id")) == str(booking_id):
            continue
        if str(b.get("status")).strip().lower() == "cancelled":
            continue
        
        # Check trainer conflict (same trainer, same time, different location)
        if str(b.get("trainer_username", "")).strip().lower() == str(trainer_username).strip().lower():
            if date_str in b.get("calendar_dates", []):
                if b.get("time") == time_str:
                    if b.get("location", "").strip().lower() != location.strip().lower():
                        conflict_dt = datetime.strptime(date_str, '%Y-%m-%d')
                        conflict_date_str = conflict_dt.strftime('%d %b %Y')
                        return f"Trainer already has a session with {b.get('student', 'another swimmer')} at {b.get('location', '')} on {conflict_date_str} at {time_str}."
        
        # Check duplicate booking check for same student/owner within 1 hour
        if b.get("student") == student and b.get("owner_name") == owner_name:
            if date_str in b.get("calendar_dates", []):
                try:
                    t1 = datetime.strptime(time_str, '%I:%M %p')
                    t2 = datetime.strptime(b.get("time"), '%I:%M %p')
                    if abs((t1 - t2).total_seconds()) / 60 < 60:
                        conflict_dt = datetime.strptime(date_str, '%Y-%m-%d')
                        conflict_date_str = conflict_dt.strftime('%d %b %Y')
                        return f"Duplicate booking conflict: Student already has a session at {b.get('time')} on {conflict_date_str}."
                except Exception:
                    pass
    return None

@login_required
def pause_booking():
    current_role = session.get("role", "guest")
    if current_role == "trainer":
        return jsonify({"success": False, "error": "Coaches cannot pause bookings."}), 403

    booking_id = request.form.get("booking_id")
    reason = (request.form.get("reason") or "").strip()
    other_reason = (request.form.get("other_reason") or "").strip()
    comments = (request.form.get("comments") or "").strip()
    
    if not booking_id or not reason:
        return jsonify({"success": False, "error": "Booking ID and reason are required."}), 400
        
    if reason == "Other" and not other_reason:
        return jsonify({"success": False, "error": "Please specify the other reason."}), 400
        
    data = load_data()
    booking = next((b for b in data.get("bookings", []) if str(b["id"]) == str(booking_id)), None)
    
    if not booking:
        return jsonify({"success": False, "error": "Booking not found."}), 404
        
    if booking.get("owner_name") != session.get("user_name"):
        return jsonify({"success": False, "error": "Unauthorized action."}), 403
        
    if booking.get("is_completed") or booking.get("delete_requested") or str(booking.get("status")).strip().lower() == "cancelled":
        return jsonify({"success": False, "error": "Completed, cancelled, or delete-requested bookings cannot be paused."}), 400
        
    if booking.get("package") not in ("Monthly", "Custom"):
        return jsonify({"success": False, "error": "Only Monthly and Custom packages can be paused."}), 400
        
    if int(booking.get("remaining_classes", 0)) <= 0:
        return jsonify({"success": False, "error": "No remaining classes left to pause."}), 400
        
    if booking.get("pause_status") == "Paused" or booking.get("pause_status") == "PAUSED":
        return jsonify({"success": False, "error": "Booking is already paused."}), 400

    if booking.get("pause_request_status") == "Pending" or booking.get("pause_status") == "Approval Pending":
        return jsonify({"success": False, "error": "A pause approval request is already pending."}), 400
        
    today_str = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
    today_date = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    
    calendar_dates = booking.get("calendar_dates", [])
    completed_count = int(booking.get("completed_classes", 0))
    completed_dates = calendar_dates[:completed_count]
    
    if len(completed_dates) >= len(calendar_dates):
         return jsonify({"success": False, "error": "All classes are already completed."}), 400

    pause_count = int(booking.get("pause_count", 0))

    if pause_count == 0:
        # First Free Pause: Allowed immediately!
        auto_resume_date = (today_date + timedelta(days=7)).strftime("%Y-%m-%d")
        
        conn = get_pg_connection()
        cursor = conn.cursor()
        remaining_classes_val = len(calendar_dates) - completed_count
        cursor.execute("""
            UPDATE bookings
            SET pause_status = 'Paused',
                pause_used = TRUE,
                pause_count = 1,
                pause_date = %s,
                auto_resume_date = %s,
                pause_reason = %s,
                pause_other_reason = %s,
                package_status = 'Paused',
                last_status_change = CURRENT_TIMESTAMP,
                calendar_dates_override = %s,
                end_date = %s,
                remaining_classes_at_pause = %s
            WHERE id = %s
        """, (
            today_str,
            auto_resume_date,
            reason,
            other_reason,
            ",".join(completed_dates) if completed_dates else "",
            completed_dates[-1] if completed_dates else today_str,
            remaining_classes_val,
            booking_id
        ))
        
        ip_address = request.remote_addr or ""
        cursor.execute("""
            INSERT INTO package_pause_audit (booking_id, action, performed_by, pause_date, reason, ip_address)
            VALUES (%s, 'PAUSE', %s, %s, %s, %s)
        """, (
            booking_id,
            session.get("user_name"),
            today_str,
            f"{reason}: {other_reason}" if other_reason else reason,
            ip_address
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True, 
            "message": f"⏸️ Package paused successfully. Your package will automatically resume on {datetime.strptime(auto_resume_date, '%Y-%m-%d').strftime('%d %b %Y')} if no action is taken."
        })
    else:
        # Subsequent pause: Approval Required workflow!
        conn = get_pg_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE bookings
            SET pause_status = 'Approval Pending',
                package_status = 'Approval Pending',
                pause_request_status = 'Pending',
                pause_requested_on = CURRENT_TIMESTAMP,
                pause_requested_by = %s,
                pause_reason = %s,
                pause_other_reason = %s,
                rejection_reason = NULL,
                last_status_change = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (
            session.get("user_name"),
            reason,
            f"{other_reason} | Comments: {comments}" if (other_reason and comments) else (other_reason or comments),
            booking_id
        ))
        
        ip_address = request.remote_addr or ""
        cursor.execute("""
            INSERT INTO package_pause_audit (booking_id, action, performed_by, pause_date, reason, ip_address)
            VALUES (%s, 'PAUSE_REQUESTED', %s, %s, %s, %s)
        """, (
            booking_id,
            session.get("user_name"),
            today_str,
            f"Reason: {reason}. Comments: {comments}",
            ip_address
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "📩 Your package pause request has been submitted successfully and is awaiting Trainer/Admin approval."
        })

@login_required
def resume_booking():
    current_role = session.get("role", "guest")
    if current_role == "trainer":
        return jsonify({"success": False, "error": "Coaches cannot resume bookings."}), 403

    booking_id = request.form.get("booking_id")
    if not booking_id:
        return jsonify({"success": False, "error": "Booking ID is required."}), 400
        
    data = load_data()
    booking = next((b for b in data.get("bookings", []) if str(b["id"]) == str(booking_id)), None)
    
    if not booking:
        return jsonify({"success": False, "error": "Booking not found."}), 404
        
    if booking.get("owner_name") != session.get("user_name"):
        return jsonify({"success": False, "error": "Unauthorized action."}), 403
        
    if booking.get("pause_status") not in ("PAUSED", "Paused"):
        return jsonify({"success": False, "error": "Package is not paused."}), 400
        
    today_str = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
    current_date = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    
    calendar_dates = booking.get("calendar_dates", [])
    completed_count = int(booking.get("completed_classes", 0))
    completed_dates = calendar_dates[:completed_count]
    
    total_classes = int(booking.get("total_classes", len(calendar_dates)))
    remaining_count = max(total_classes - completed_count, 0)
    
    if remaining_count <= 0:
        return jsonify({"success": False, "error": "No remaining sessions to reschedule."}), 400
        
    weekday_map = {
        'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6
    }
    selected_days = booking.get("selected_days", "")
    valid_days = {
        weekday_map[d]
        for d in parse_selected_days(selected_days)
        if d in weekday_map
    }
    
    standard_candidate_dates = []
    temp_date = current_date
    while len(standard_candidate_dates) < remaining_count:
        if (not valid_days) or (temp_date.weekday() in valid_days):
            date_candidate_str = temp_date.strftime('%Y-%m-%d')
            if not is_date_holiday_or_closed(date_candidate_str):
                standard_candidate_dates.append(date_candidate_str)
        temp_date += timedelta(days=1)
        
    conflict_msg = None
    for date_candidate_str in standard_candidate_dates:
        conflict_msg = check_single_date_conflict(
            booking_id=booking_id,
            trainer_username=booking.get("trainer_username", "asdf"),
            student=booking.get("student"),
            owner_name=booking.get("owner_name"),
            time_str=booking.get("time"),
            location=booking.get("location"),
            date_str=date_candidate_str,
            existing_bookings=data.get("bookings", [])
        )
        if conflict_msg:
            break
            
    if conflict_msg:
        return jsonify({
            "success": False, 
            "error": f"reschedule_required: {conflict_msg}"
        }), 400
        
    new_calendar = completed_dates + standard_candidate_dates
    new_end_date = new_calendar[-1]
    
    paused_days_count = 0
    if booking.get("pause_date"):
        try:
            p_dt = datetime.strptime(booking["pause_date"], "%Y-%m-%d").date()
            paused_days_count = (current_date - p_dt).days
        except Exception:
            pass
            
    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE bookings
        SET pause_status = 'ACTIVE',
            resume_date = %s,
            paused_days = %s,
            package_status = 'ACTIVE',
            last_status_change = CURRENT_TIMESTAMP,
            calendar_dates_override = %s,
            end_date = %s,
            remaining_classes_at_pause = NULL
        WHERE id = %s
    """, (
        today_str,
        paused_days_count,
        ",".join(new_calendar),
        new_end_date,
        booking_id
    ))
    
    ip_address = request.remote_addr or ""
    cursor.execute("""
        INSERT INTO package_pause_audit (booking_id, action, performed_by, resume_date, is_auto_resume, ip_address)
        VALUES (%s, 'RESUME', %s, %s, FALSE, %s)
    """, (
        booking_id,
        session.get("user_name"),
        today_str,
        ip_address
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        "success": True, 
        "message": "Package resumed successfully. Your remaining sessions have been rescheduled."
    })

def check_and_perform_auto_resumes():
    try:
        today_str = datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%Y-%m-%d')
        conn = get_pg_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, trainer_username, time, location, student_name, owner_name, selected_days, auto_resume_date, pause_date
            FROM bookings
            WHERE pause_status = 'PAUSED' AND auto_resume_date <= %s
        """, (today_str,))
        paused_bookings = cursor.fetchall()
        
        if not paused_bookings:
            conn.close()
            return
            
        cursor.execute("SELECT id, student_name, owner_name, start_date, end_date, selected_days, time, location, status, trainer_username, calendar_dates_override FROM bookings")
        all_booking_rows = cursor.fetchall()
        
        existing_bookings_mapped = []
        for b in all_booking_rows:
            cal_override = b[10]
            if cal_override:
                dates = [d.strip() for d in cal_override.split(',') if d.strip()]
            else:
                dates = generate_recurring_dates(str(b[3]), str(b[4]), b[5])
            existing_bookings_mapped.append({
                'id': b[0],
                'student': b[1],
                'owner_name': b[2],
                'time': b[6],
                'location': b[7],
                'status': b[8],
                'trainer_username': b[9] or 'asdf',
                'calendar_dates': dates
            })
            
        for row in paused_bookings:
            booking_id = row[0]
            trainer_username = row[1] or 'asdf'
            time_str = row[2]
            location = row[3]
            student = row[4]
            owner = row[5]
            selected_days = row[6]
            auto_resume_date_str = row[7]
            pause_date_str = row[8]
            
            cursor.execute("SELECT calendar_dates_override, start_date, end_date, selected_days, remaining_classes_at_pause FROM bookings WHERE id = %s", (booking_id,))
            b_info = cursor.fetchone()
            if not b_info:
                continue
                
            cal_override = b_info[0]
            if cal_override:
                calendar_dates = [d.strip() for d in cal_override.split(',') if d.strip()]
            else:
                calendar_dates = generate_recurring_dates(str(b_info[1]), str(b_info[2]), b_info[3])
                
            completed_dates = calendar_dates
            completed_count = len(completed_dates)
            
            remaining_count = b_info[4]
            if remaining_count is None:
                orig_dates = generate_recurring_dates(str(b_info[1]), str(b_info[2]), b_info[3])
                total_classes = len(orig_dates) if orig_dates else 12
                remaining_count = max(total_classes - completed_count, 0)
            
            if remaining_count <= 0:
                cursor.execute("""
                    UPDATE bookings
                    SET pause_status = 'ACTIVE',
                        resume_date = %s,
                        package_status = 'ACTIVE',
                        last_status_change = CURRENT_TIMESTAMP,
                        remaining_classes_at_pause = NULL
                    WHERE id = %s
                """, (auto_resume_date_str, booking_id))
                continue
                
            rescheduled_dates = []
            weekday_map = {
                'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6
            }
            valid_days = {
                weekday_map[d]
                for d in parse_selected_days(selected_days)
                if d in weekday_map
            }
            
            temp_date = datetime.strptime(auto_resume_date_str, '%Y-%m-%d').date()
            while len(rescheduled_dates) < remaining_count:
                if (not valid_days) or (temp_date.weekday() in valid_days):
                    date_candidate_str = temp_date.strftime('%Y-%m-%d')
                    if not is_date_holiday_or_closed(date_candidate_str):
                        conflict_msg = check_single_date_conflict(
                            booking_id=booking_id,
                            trainer_username=trainer_username,
                            student=student,
                            owner_name=owner,
                            time_str=time_str,
                            location=location,
                            date_str=date_candidate_str,
                            existing_bookings=existing_bookings_mapped
                        )
                        if not conflict_msg:
                            rescheduled_dates.append(date_candidate_str)
                temp_date += timedelta(days=1)
                if (temp_date - datetime.strptime(auto_resume_date_str, '%Y-%m-%d').date()).days > 365:
                    break
                    
            new_calendar = completed_dates + rescheduled_dates
            new_end_date = new_calendar[-1] if new_calendar else auto_resume_date_str
            
            paused_days_count = 7
            
            cursor.execute("""
                UPDATE bookings
                SET pause_status = 'ACTIVE',
                    resume_date = %s,
                    paused_days = %s,
                    package_status = 'ACTIVE',
                    last_status_change = CURRENT_TIMESTAMP,
                    calendar_dates_override = %s,
                    end_date = %s,
                    remaining_classes_at_pause = NULL
                WHERE id = %s
            """, (
                auto_resume_date_str,
                paused_days_count,
                ",".join(new_calendar),
                new_end_date,
                booking_id
            ))
            
            cursor.execute("""
                INSERT INTO package_pause_audit (booking_id, action, performed_by, resume_date, is_auto_resume, reason, ip_address)
                VALUES (%s, 'AUTO_RESUME', 'SYSTEM', %s, TRUE, 'Auto resume after maximum pause period.', '127.0.0.1')
            """, (
                booking_id,
                auto_resume_date_str
            ))
            
        conn.commit()
        conn.close()
    except Exception as exc:
        print("AUTO RESUME BACKGROUND CHECK ERROR:", exc)

def register_bookings_routes(app):
    app.add_url_rule('/book', endpoint='book', view_func=book, methods=['POST'])
    app.add_url_rule('/edit/<booking_id>', endpoint='edit_booking', view_func=edit_booking)
    app.add_url_rule('/update/<booking_id>', endpoint='update_booking', view_func=update_booking, methods=['POST'])
    app.add_url_rule('/booking/pause', endpoint='pause_booking', view_func=pause_booking, methods=['POST'])
    app.add_url_rule('/booking/resume', endpoint='resume_booking', view_func=resume_booking, methods=['POST'])
    app.add_url_rule('/booking/approve_pause', endpoint='approve_pause', view_func=approve_pause, methods=['POST'])
    app.add_url_rule('/booking/reject_pause', endpoint='reject_pause', view_func=reject_pause, methods=['POST'])
    app.add_url_rule('/booking/confirm_paylater/<booking_id>', endpoint='confirm_paylater', view_func=confirm_paylater, methods=['POST'])

def confirm_paylater(booking_id):
    if not session.get('user_name'):
        flash("Unauthorized action", "danger")
        return redirect('/booking')
        
    data = load_data()
    booking = next((b for b in data.get('bookings', []) if str(b['id']) == str(booking_id)), None)
    
    if not booking:
        flash("Booking not found", "danger")
        return redirect('/booking')
        
    if booking.get('owner_name') != session.get('user_name') and session.get('role') != 'admin':
        flash("Unauthorized action", "danger")
        return redirect('/booking')
        
    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE bookings SET payment_request = 'Not Paid', status = 'Not Paid' WHERE id = %s", (booking_id,))
    conn.commit()
    conn.close()
    
    # Update dict so email has correct status
    booking['payment_request'] = 'Not Paid'
    booking['status'] = 'Not Paid'
    
    send_booking_confirmation_email(booking)
    
    return redirect('/my-bookings?booking_success=true')

@login_required
def approve_pause():
    current_role = session.get("role")
    if current_role not in ("trainer", "admin"):
        return jsonify({"success": False, "error": "Unauthorized action."}), 403

    booking_id = request.form.get("booking_id")
    if not booking_id:
        return jsonify({"success": False, "error": "Booking ID is required."}), 400

    data = load_data()
    booking = next((b for b in data.get("bookings", []) if str(b["id"]) == str(booking_id)), None)

    if not booking:
        return jsonify({"success": False, "error": "Booking not found."}), 404

    if booking.get("pause_request_status") != "Pending":
        return jsonify({"success": False, "error": "No pending pause request found for this booking."}), 400

    today_str = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
    today_date = datetime.now(ZoneInfo("Asia/Kolkata")).date()

    calendar_dates = booking.get("calendar_dates", [])
    completed_count = int(booking.get("completed_classes", 0))
    completed_dates = calendar_dates[:completed_count]

    auto_resume_date = (today_date + timedelta(days=7)).strftime("%Y-%m-%d")
    new_pause_count = int(booking.get("pause_count", 0)) + 1

    conn = get_pg_connection()
    cursor = conn.cursor()
    remaining_classes_val = len(calendar_dates) - completed_count
    cursor.execute("""
        UPDATE bookings
        SET pause_status = 'Paused',
            pause_used = TRUE,
            pause_count = %s,
            pause_date = %s,
            auto_resume_date = %s,
            package_status = 'Paused',
            last_status_change = CURRENT_TIMESTAMP,
            calendar_dates_override = %s,
            end_date = %s,
            pause_request_status = 'Approved',
            pause_approved_by = %s,
            pause_approved_on = CURRENT_TIMESTAMP,
            remaining_classes_at_pause = %s
        WHERE id = %s
    """, (
        new_pause_count,
        today_str,
        auto_resume_date,
        ",".join(completed_dates) if completed_dates else "",
        completed_dates[-1] if completed_dates else today_str,
        session.get("user_name"),
        remaining_classes_val,
        booking_id
    ))

    ip_address = request.remote_addr or ""
    cursor.execute("""
        INSERT INTO package_pause_audit (booking_id, action, performed_by, pause_date, reason, ip_address)
        VALUES (%s, 'PAUSE_APPROVED', %s, %s, 'Additional pause approved.', %s)
    """, (
        booking_id,
        session.get("user_name"),
        today_str,
        ip_address
    ))

    cursor.execute("""
        INSERT INTO package_pause_audit (booking_id, action, performed_by, pause_date, reason, ip_address)
        VALUES (%s, 'PAUSE', 'SYSTEM', %s, 'Package paused after approval.', %s)
    """, (
        booking_id,
        today_str,
        ip_address
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "✅ Your additional package pause request has been approved."
    })

@login_required
def reject_pause():
    current_role = session.get("role")
    if current_role not in ("trainer", "admin"):
        return jsonify({"success": False, "error": "Unauthorized action."}), 403

    booking_id = request.form.get("booking_id")
    rejection_reason = (request.form.get("rejection_reason") or "").strip()

    if not booking_id:
        return jsonify({"success": False, "error": "Booking ID is required."}), 400
    if not rejection_reason:
        return jsonify({"success": False, "error": "Rejection reason is required."}), 400

    data = load_data()
    booking = next((b for b in data.get("bookings", []) if str(b["id"]) == str(booking_id)), None)

    if not booking:
        return jsonify({"success": False, "error": "Booking not found."}), 404

    if booking.get("pause_request_status") != "Pending":
        return jsonify({"success": False, "error": "No pending pause request found for this booking."}), 400

    today_str = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")

    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE bookings
        SET pause_status = 'Active',
            package_status = 'ACTIVE',
            last_status_change = CURRENT_TIMESTAMP,
            pause_request_status = 'Rejected',
            pause_rejected_by = %s,
            pause_rejected_on = CURRENT_TIMESTAMP,
            rejection_reason = %s
        WHERE id = %s
    """, (
        session.get("user_name"),
        rejection_reason,
        booking_id
    ))

    ip_address = request.remote_addr or ""
    cursor.execute("""
        INSERT INTO package_pause_audit (booking_id, action, performed_by, pause_date, reason, ip_address)
        VALUES (%s, 'PAUSE_REJECTED', %s, %s, %s, %s)
    """, (
        booking_id,
        session.get("user_name"),
        today_str,
        f"Rejected: {rejection_reason}",
        ip_address
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "❌ Your package pause request has been declined. Please contact your trainer for further assistance."
    })
