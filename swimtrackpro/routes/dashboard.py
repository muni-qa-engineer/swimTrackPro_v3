"""Dashboard route."""

from flask import render_template, session

from services.dashboard_service import (
    get_admin_dashboard_data,
    get_trainer_dashboard_data,
    get_guest_dashboard_data,
    get_all_packages
)
from swimtrackpro.runtime import get_pg_connection, load_data
from swimtrackpro.routes.bookings import check_and_perform_auto_resumes

def index():
    if 'user_name' not in session:
        packages = get_all_packages()
        return render_template('login.html', pkg=packages)

    
    check_and_perform_auto_resumes()
    data = load_data()
    
    current_user = session.get('user_name')
    current_phone = session.get('phone')
    current_role = session.get('role', 'guest')

    welcome_text = f"Welcome Back, {current_user.title()}"

    if current_role == 'admin':
        admin_context = get_admin_dashboard_data(current_user, data)
        admin_context['welcome_text'] = welcome_text
        return render_template('admin_dashboard.html', **admin_context)

    # Fetch previous login for non-admin to customize welcome text
    try:
        conn = get_pg_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT previous_login
            FROM user_activity
            WHERE LOWER(user_name) = LOWER(%s)
              AND role = %s
            ''',
            (current_user, current_role)
        )
        row = cursor.fetchone()
        conn.close()

        if not row or row[0] is None:
            welcome_text = f"Hi {current_user.title()}, Welcome"
    except Exception:
        pass

    if current_role == 'trainer':
        trainer_username = session.get('trainer_username') or 'asdf'
        context = get_trainer_dashboard_data(trainer_username, data)
        context['welcome_text'] = welcome_text
        context['user_name'] = session['user_name']
        context['role'] = current_role
        return render_template('trainer_dashboard.html', **context)
    
    # Guest
    context = get_guest_dashboard_data(current_user, current_phone, data)
    context['welcome_text'] = welcome_text
    context['user_name'] = session['user_name']
    context['role'] = current_role
    return render_template('guest_dashboard.html', **context)

def register_dashboard_routes(app):
    app.add_url_rule('/', endpoint='index', view_func=index)
