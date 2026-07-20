from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import calendar

from swimtrackpro.runtime import get_pg_connection
from services.settings_service import get_setting

def get_admin_dashboard_data(current_user, data):
    """Fetch and process data specifically for the Admin dashboard."""
    conn = get_pg_connection()
    cursor = conn.cursor()
    
    # Fetch trainers
    cursor.execute("SELECT username, name, phone, email, experience, qualification, currently_working, residence_location, rating, is_approved, is_blocked, photos FROM trainers ORDER BY name")
    trainers_list = []
    for row in cursor.fetchall():
        photos_str = row[11] if row[11] else ""
        photos_list = [p for p in photos_str.split(",") if p]
        trainers_list.append({
            'username': row[0],
            'name': row[1],
            'phone': row[2],
            'email': row[3],
            'experience': row[4],
            'qualification': row[5],
            'currently_working': row[6],
            'residence_location': row[7],
            'rating': float(row[8]) if row[8] else 5.0,
            'is_approved': row[9],
            'is_blocked': row[10],
            'photos': photos_list
        })
        
    # Fetch user activities
    cursor.execute("SELECT user_name, phone, role, current_login, previous_login FROM user_activity ORDER BY current_login DESC")
    activities_list = []
    for row in cursor.fetchall():
        activities_list.append({
            'user_name': row[0],
            'phone': row[1],
            'role': row[2],
            'current_login': row[3].strftime('%Y-%m-%d %H:%M:%S') if row[3] else '--',
            'previous_login': row[4].strftime('%Y-%m-%d %H:%M:%S') if row[4] else '--'
        })
        
    # Fetch package pause audit logs
    cursor.execute("SELECT id, booking_id, action, performed_by, pause_date, resume_date, is_auto_resume, reason, ip_address, created_at FROM package_pause_audit ORDER BY created_at DESC")
    audit_rows = cursor.fetchall()
    audit_logs = []
    for r in audit_rows:
        audit_logs.append({
            'id': r[0],
            'booking_id': r[1],
            'action': r[2],
            'performed_by': r[3],
            'pause_date': r[4],
            'resume_date': r[5],
            'is_auto_resume': r[6],
            'reason': r[7],
            'ip_address': r[8],
            'created_at': r[9].strftime('%Y-%m-%d %H:%M:%S') if r[9] else '--'
        })
        


    # Calculate today's sessions and weekly distribution from full bookings data
    today_str = datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%Y-%m-%d')
    today_sessions = []
    
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_counts = {d: 0 for d in days_of_week}
    
    for b in data.get('bookings', []):
        if today_str in b.get('calendar_dates', []):
            today_sessions.append({
                'time': b.get('time', '06:00 AM'),
                'student': b.get('student', '--'),
                'package': b.get('package', '--'),
                'trainer_username': b.get('trainer_username', 'asdf'),
                'booking_id': b.get('id')
            })
        sel_days = b.get('selected_days', '')
        if sel_days:
            for day in days_of_week:
                if day.lower() in sel_days.lower():
                    day_counts[day] += 1
                    
    paused_bookings = [b for b in data.get('bookings', []) if str(b.get('pause_status')).upper() == 'PAUSED']
    paused_packages_count = len(paused_bookings)
    
    today_date = datetime.now(ZoneInfo('Asia/Kolkata')).date()
    auto_resume_today_count = sum(1 for b in paused_bookings if b.get('auto_resume_date') == today_str)
    
    paused_this_week_count = 0
    for b in paused_bookings:
        p_date_str = b.get('pause_date')
        if p_date_str:
            try:
                p_date = datetime.strptime(p_date_str, '%Y-%m-%d').date()
                if 0 <= (today_date - p_date).days <= 7:
                    paused_this_week_count += 1
            except ValueError:
                pass
                
    resume_pending_count = sum(1 for b in data.get('bookings', []) if b.get('pause_status') == 'Approval Pending')
    chart_data = [day_counts[d] for d in days_of_week]
    
    # Fetch Packages
    cursor.execute("SELECT id, category, package_name, base_price, discount_percentage FROM packages ORDER BY id")
    packages_list = []
    for row in cursor.fetchall():
        packages_list.append({
            'id': row[0],
            'category': row[1],
            'package_name': row[2],
            'base_price': row[3],
            'discount_percentage': row[4]
        })
        
    conn.close()

    return {
        'trainers': trainers_list,
        'bookings': data.get('bookings', []),
        'students': data.get('students', []),
        'today_sessions': today_sessions,
        'activities': activities_list,
        'chart_data': chart_data,
        'paused_packages_count': paused_packages_count,
        'auto_resume_today_count': auto_resume_today_count,
        'paused_this_week_count': paused_this_week_count,
        'resume_pending_count': resume_pending_count,
        'audit_logs': audit_logs,
        'packages': packages_list
    }

def get_all_packages():
    """Fetch all packages for the landing page."""
    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, category, package_name, base_price, discount_percentage FROM packages")
    packages = []
    for row in cursor.fetchall():
        bp = row[3]
        dp = row[4]
        final_price = int(bp - (bp * dp / 100.0)) if dp > 0 else bp
        packages.append({
            'id': row[0],
            'category': row[1],
            'package_name': row[2],
            'base_price': bp,
            'discount_percentage': dp,
            'final_price': final_price
        })
    conn.close()
    
    # Convert to a dictionary for easier access in Jinja
    pkg_dict = {}
    for p in packages:
        if p['category'] not in pkg_dict:
            pkg_dict[p['category']] = {}
        pkg_dict[p['category']][p['package_name']] = p
        
    return pkg_dict

def get_trainer_dashboard_data(trainer_username, data):
    """Fetch and process data specifically for the Trainer dashboard."""
    trainer_user_lower = (trainer_username or 'asdf').strip().lower()
    
    user_bookings = [
        b for b in data.get('bookings', [])
        if (b.get('trainer_username') or 'asdf').strip().lower() == trainer_user_lower
    ]
    
    assigned_student_keys = set(
        ((b.get('owner_name') or '').strip().lower(), b.get('owner_phone'))
        for b in user_bookings
    )
    user_students = [
        s for s in data.get('students', [])
        if isinstance(s, dict)
        and ((s.get('owner_name') or '').strip().lower(), s.get('owner_phone')) in assigned_student_keys
    ]
    base_data = _process_common_dashboard_data(user_bookings, user_students, 'trainer', trainer_username)
    
    # Custom Trainer Metrics
    # 1. Pending Approvals
    pending_pauses = [b for b in user_bookings if b.get('pause_status') == 'Approval Pending']
    pending_payments = [b for b in user_bookings if str(b.get('status', '')).lower() != 'paid']
    
    # 2. Earnings and Trends (Monthly)
    ist_now = datetime.now(ZoneInfo('Asia/Kolkata'))
    current_year = ist_now.year
    current_month = ist_now.month
    
    monthly_earnings = [0] * 12
    for b in user_bookings:
        if str(b.get('status', '')).lower() == 'paid':
            start_date_str = b.get('start_date')
            if start_date_str:
                try:
                    dt = datetime.strptime(start_date_str, '%Y-%m-%d')
                    if dt.year == current_year:
                        fee = int(b.get('fee', 0) or 0)
                        monthly_earnings[dt.month - 1] += fee
                except ValueError:
                    pass
                    
    students_this_month = 0
    students_last_month = 0
    for b in user_bookings:
        start_date_str = b.get('start_date')
        if start_date_str:
            try:
                dt = datetime.strptime(start_date_str, '%Y-%m-%d')
                if dt.year == current_year and dt.month == current_month:
                    students_this_month += 1
                elif (dt.year == current_year and dt.month == current_month - 1) or (current_month == 1 and dt.year == current_year - 1 and dt.month == 12):
                    students_last_month += 1
            except ValueError:
                pass
                
    trend_growth = students_this_month - students_last_month

    # 3. Feedback and Ratings
    feedbacks = []
    avg_rating = 0.0
    try:
        from swimtrackpro.runtime import get_pg_connection
        conn = get_pg_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT rating FROM trainers WHERE LOWER(username) = LOWER(%s)", (trainer_username,))
        row = cursor.fetchone()
        if row and row[0]:
            avg_rating = float(row[0])
            
        cursor.execute("""
            SELECT guest_name, rating, pros, cons, created_at 
            FROM coach_feedback 
            WHERE LOWER(trainer_username) = LOWER(%s)
            ORDER BY created_at DESC LIMIT 10
        """, (trainer_username,))
        
        for f in cursor.fetchall():
            feedbacks.append({
                'guest_name': f[0],
                'rating': f[1],
                'pros': f[2],
                'cons': f[3],
                'created_at': f[4].strftime('%b %d, %Y') if f[4] else ''
            })
        conn.close()
    except Exception as e:
        print(f"Error fetching feedback: {e}")

    base_data.update({
        'pending_pauses': pending_pauses,
        'pending_payments': pending_payments,
        'monthly_earnings': monthly_earnings,
        'trend_growth': trend_growth,
        'students_this_month': students_this_month,
        'lifetime_students': len(assigned_student_keys),
        'avg_rating': avg_rating,
        'feedbacks': feedbacks
    })
    
    return base_data

def get_guest_dashboard_data(current_user, current_phone, data):
    """Fetch and process data specifically for the Guest dashboard."""
    user_bookings = [
        b for b in data.get('bookings', [])
        if (b.get('owner_name') or '').strip().lower() == current_user
        and b.get('owner_phone') == current_phone
    ]
    user_students = [
        s for s in data.get('students', [])
        if isinstance(s, dict)
        and (s.get('owner_name') or '').strip().lower() == current_user
        and s.get('owner_phone') == current_phone
    ]
    return _process_common_dashboard_data(user_bookings, user_students, 'guest', current_user)

def _process_common_dashboard_data(user_bookings, user_students, current_role, current_user):
    """Shared metrics and analytics logic for Trainer and Guest dashboards."""
    ist_now = datetime.now(ZoneInfo('Asia/Kolkata'))
    current_year = ist_now.year
    current_month = ist_now.month
    today_day = ist_now.day
    today_date = ist_now.date()
    current_month_name = ist_now.strftime('%B %Y')

    total_swimmers = len(user_students)
    active_bookings = sum(1 for b in user_bookings if not b.get('is_completed', False))
    completed_bookings = sum(1 for b in user_bookings if b.get('is_completed', False))

    monthly_revenue = sum(int(b.get('fee', 0) or 0) for b in user_bookings if str(b.get('status', '')).lower() == 'paid')
    pending_payments = sum(int(b.get('fee', 0) or 0) for b in user_bookings if str(b.get('status', '')).lower() != 'paid')

    total_sessions = sum(int(b.get('total_classes', 0) or 0) for b in user_bookings)
    completed_sessions = sum(int(b.get('completed_classes', 0) or 0) for b in user_bookings)
    remaining_sessions = sum(int(b.get('remaining_classes', 0) or 0) for b in user_bookings)
    makeup_sessions = sum(1 for b in user_bookings if b.get('has_available_makeup_credit', False))
    total_skips_remaining = sum(int(b.get('skip_remaining', 0) or 0) for b in user_bookings)

    booked_dates = set()
    makeup_dates = set()

    for booking in user_bookings:
        booking_time = (booking.get('time') or '06:00 AM').strip()
        for session_date in booking.get('calendar_dates', []):
            try:
                dt = datetime.strptime(session_date, '%Y-%m-%d')
                session_datetime = datetime.strptime(f"{session_date} {booking_time}", '%Y-%m-%d %I:%M %p')
                session_end = session_datetime + timedelta(hours=1)
                if dt.year == current_year and dt.month == current_month and session_end > ist_now.replace(tzinfo=None):
                    booked_dates.add(dt.day)
            except Exception:
                pass

        for makeup_date in booking.get('used_makeup_dates', []):
            try:
                dt = datetime.strptime(str(makeup_date), '%Y-%m-%d')
                if dt.year == current_year and dt.month == current_month:
                    makeup_dates.add(dt.day)
            except Exception:
                pass

    cal = calendar.Calendar(firstweekday=0)
    calendar_days = []
    for week in cal.monthdayscalendar(current_year, current_month):
        for day in week:
            if day == 0:
                calendar_days.append({'day': None, 'is_today': False, 'is_booked': False, 'is_makeup': False})
            else:
                calendar_days.append({
                    'day': day,
                    'is_today': day == today_day,
                    'is_booked': day in booked_dates,
                    'is_makeup': day in makeup_dates
                })

    current_date_display = ist_now.strftime('%A, %d %b %Y')
    
    if current_role == 'trainer':
        hero_message = f'Manage {len(user_students)} swimmers and {len(user_bookings)} bookings from one place.'
    else:
        hero_message = 'Track sessions, bookings, payments and swimmer progress from one place.'

    next_session_name = '--'
    next_session_date = '--'
    next_session_time = '--'
    guest_upcoming_sessions = []
    trainer_upcoming_slots = []
    trainer_remaining_slots = 0
    upcoming_sessions = []
    all_future_sessions = []

    for booking in user_bookings:
        booking_time = (booking.get('time') or '').strip()
        for session_date in booking.get('calendar_dates', []):
            try:
                session_datetime = datetime.strptime(f"{session_date} {booking_time}", '%Y-%m-%d %I:%M %p')
                current_time = ist_now.replace(tzinfo=None)
                if session_datetime >= current_time:
                    session_info = {'datetime': session_datetime, 'student': booking.get('student', '--'), 'time': booking_time, 'booking_id': booking.get('id'), 'raw_date': session_date}
                    all_future_sessions.append(session_info)
            except Exception:
                continue

    all_future_sessions.sort(key=lambda x: x['datetime'])
    upcoming_sessions = all_future_sessions

    if current_role == 'trainer':
        slot_counts = {}
        for session in upcoming_sessions:
            date_text = session['datetime'].strftime('%d %b')
            time_text = session['datetime'].strftime('%I:%M %p')
            slot_key = (date_text, time_text)
            if slot_key not in slot_counts:
                slot_counts[slot_key] = {'count': 0, 'swimmers': []}
            slot_counts[slot_key]['count'] += 1
            slot_counts[slot_key]['swimmers'].append(session.get('student', '--'))
            
        sorted_slots = sorted(slot_counts.items(), key=lambda x: datetime.strptime(f"{x[0][0]} {x[0][1]}", "%d %b %I:%M %p"))
        trainer_remaining_slots = max(len(sorted_slots) - 3, 0)
        trainer_upcoming_slots = [
            {
                'date': date_text,
                'slot': time_text,
                'count': slot_data['count'],
                'swimmer_names': ', '.join(slot_data['swimmers'][:2]) + (f" +{len(slot_data['swimmers']) - 2} More" if len(slot_data['swimmers']) > 2 else '')
            }
            for (date_text, time_text), slot_data in sorted_slots[:3]
        ]
    elif upcoming_sessions:
        sorted_sessions = sorted(upcoming_sessions, key=lambda x: x['datetime'])
        guest_upcoming_sessions = [{'name': s['student'], 'date': s['datetime'].strftime('%d %b'), 'time': s['time'], 'booking_id': s['booking_id'], 'raw_date': s['raw_date']} for s in sorted_sessions[:5]]
        next_session = sorted_sessions[0]
        next_session_name = next_session['student']
        next_session_date = next_session['datetime'].strftime('%d %b')
        next_session_time = next_session['time']
        
    guest_all_future = [{'name': s['student'], 'date': s['datetime'].strftime('%d %b %Y'), 'time': s['time'], 'booking_id': s['booking_id'], 'raw_date': s['raw_date']} for s in all_future_sessions[:15]]

    total_packages = len(user_bookings)
    active_packages = active_bookings
    completed_packages = completed_bookings
    active_package_name = 'No Package'
    active_package_valid_till = '--'
    package_status = 'Active'

    active_booking = None
    for booking in sorted(user_bookings, key=lambda b: str(b.get('end_date', '')), reverse=True):
        if not booking.get('is_completed', False):
            active_booking = booking
            break

    if active_booking:
        active_package_name = active_booking.get('package', 'No Package')
        valid_till = active_booking.get('end_date')
        if valid_till:
            try:
                active_package_valid_till = datetime.strptime(str(valid_till), '%Y-%m-%d').strftime('%d %b %Y')
            except Exception:
                active_package_valid_till = str(valid_till)
        try:
            expiry_date = datetime.strptime(str(active_booking.get('end_date')), '%Y-%m-%d').date()
            if expiry_date < ist_now.date():
                package_status = 'Expired'
        except Exception:
            pass

    enriched_students = []
    for swimmer in user_students:
        swimmer_name = (swimmer.get('name') or '').strip()
        swimmer_bookings = [b for b in user_bookings if (b.get('student') or '').strip().lower() == swimmer_name.lower()]
        
        completed_total = sum(int(b.get('completed_classes', 0) or 0) for b in swimmer_bookings)
        sessions_total = sum(int(b.get('total_classes', 0) or 0) for b in swimmer_bookings)
        
        next_session_dt = ''
        future_dates = []
        for booking in swimmer_bookings:
            for session_date in booking.get('calendar_dates', []):
                try:
                    dt = datetime.strptime(session_date, '%Y-%m-%d').date()
                    if dt >= ist_now.date():
                        future_dates.append(dt)
                except Exception:
                    pass
        if future_dates:
            next_session_dt = min(future_dates).strftime('%d %b %Y')
            
        active_pkg = ''
        active_bkg = None
        for b in sorted(swimmer_bookings, key=lambda b: str(b.get('end_date', '')), reverse=True):
            if not b.get('is_completed', False):
                active_bkg = b
                break
        if active_bkg:
            active_pkg = active_bkg.get('package', '')
            
        swimmer_copy = dict(swimmer)
        swimmer_copy['completed_sessions'] = completed_total
        swimmer_copy['total_sessions'] = sessions_total
        swimmer_copy['next_session'] = next_session_dt
        swimmer_copy['package'] = active_pkg
        enriched_students.append(swimmer_copy)
        
    user_students = enriched_students

    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT location FROM bookings WHERE location IS NOT NULL AND TRIM(location) <> '' ORDER BY location")
    location_suggestions = [row[0] for row in cursor.fetchall() if row[0]]

    # Notifications & Notices
    notification_list = []
    notice_message = ""
    
    if current_role == 'trainer':
        cursor.execute("SELECT notice FROM trainers WHERE username = %s", (current_user,))
        row_notice = cursor.fetchone()
        notice_message = row_notice[0] if (row_notice and row_notice[0]) else "Welcome to SwimTrackPro! Use • to separate multiple announcements."
        
        for b in user_bookings:
            if str(b.get('status', '')).lower() == 'pending verification':
                notification_list.append(f"💰 Payment verification needed for {b.get('student', 'Swimmer')}'s {b.get('package')} package.")
            if b.get('delete_requested'):
                notification_list.append(f"🗑️ Deletion requested by {b.get('student', 'Swimmer')} for booking #{b.get('id')}.")
            for req in b.get('makeup_requests', []):
                if req.get('status') == 'pending':
                    notification_list.append(f"⏳ Pending Make-up request for {b.get('student', 'Swimmer')} on {req.get('requested_date')}.")
    else:
        assigned_usernames = list(set([b.get("trainer_username", "asdf") for b in user_bookings if b.get("trainer_username")]))
        if not assigned_usernames:
            assigned_usernames = ["asdf"]
        placeholders = ", ".join(["%s"] * len(assigned_usernames))
        cursor.execute(f"SELECT name, notice FROM trainers WHERE username IN ({placeholders})", tuple(assigned_usernames))
        rows_notice = cursor.fetchall()
        announcements_list = []
        for name, notice in rows_notice:
            if notice:
                for ann in notice.split("•"):
                    ann_text = ann.strip()
                    if ann_text:
                        announcements_list.append(f"Coach {name.title()}: {ann_text}")
        if announcements_list:
            notice_message = " • ".join(announcements_list)
            for ann in announcements_list:
                notification_list.append(f"📢 Notice: {ann}")
                
        for b in user_bookings:
            if str(b.get('status', '')).lower() != 'paid':
                notification_list.append(f"💰 Payment due: Please complete payment of ₹{b.get('fee')} for {b.get('student')}'s {b.get('package')} package.")
            if b.get('has_available_makeup_credit'):
                notification_list.append(f"🔄 Make-up credit available for {b.get('student')} (Valid until {b.get('valid_until')}).")
                
    notification_count = len(notification_list)
    conn.close()

    return {
        'bookings': user_bookings,
        'students': user_students,
        'total_swimmers': total_swimmers,
        'active_bookings': active_bookings,
        'completed_bookings': completed_bookings,
        'monthly_revenue': monthly_revenue,
        'pending_payments': pending_payments,
        'total_sessions': total_sessions,
        'completed_sessions': completed_sessions,
        'remaining_sessions': remaining_sessions,
        'makeup_sessions': makeup_sessions,
        'total_skips_remaining': total_skips_remaining,
        'location_suggestions': location_suggestions,
        'current_month_name': current_month_name,
        'today_day': today_day,
        'booked_dates': booked_dates,
        'makeup_dates': makeup_dates,
        'calendar_days': calendar_days,
        'notification_count': notification_count,
        'notification_list': notification_list,
        'hero_message': hero_message,
        'current_date_display': current_date_display,
        'next_session_name': next_session_name,
        'next_session_date': next_session_date,
        'next_session_time': next_session_time,
        'guest_upcoming_sessions': guest_upcoming_sessions,
        'guest_all_future': guest_all_future,
        'trainer_upcoming_slots': trainer_upcoming_slots,
        'trainer_remaining_slots': trainer_remaining_slots,
        'upcoming_sessions': upcoming_sessions,
        'active_package_name': active_package_name,
        'active_package_valid_till': active_package_valid_till,
        'package_status': package_status,
        'total_packages': total_packages,
        'active_packages': active_packages,
        'completed_packages': completed_packages,
        'received_amount': monthly_revenue,
        'pending_amount': pending_payments,
        'notice_message': notice_message,
        'account_holder_name': get_setting("account_holder_name", ""),
        'trainer_phone': get_setting("trainer_phone", ""),
        'upi_id': get_setting("upi_id", "")
    }
