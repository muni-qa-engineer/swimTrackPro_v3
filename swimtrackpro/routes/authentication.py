"""Authentication routes with legacy URL and endpoint compatibility."""

from flask import flash, redirect, request, render_template, session, url_for


def register_authentication_routes(
    app,
    *,
    get_pg_connection,
    admin_username,
    admin_password,
):
    def login():
        # Handle browser navigating to /login directly — redirect to home
        if request.method == 'GET':
            return redirect(url_for('index'))

        role = (request.form.get("role") or "").lower()
        name = (request.form.get("name") or "").strip()
        password = (request.form.get("password") or "").strip()
        phone = (request.form.get("phone") or "").strip()

        if role == "trainer":
            try:
                conn = get_pg_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT username, password, name, is_approved, is_blocked FROM trainers WHERE LOWER(username) = LOWER(%s)",
                    (name.lower(),)
                )
                trainer_row = cursor.fetchone()
                conn.close()
            except Exception as db_err:
                print("LOGIN DB ERROR (trainer):", db_err)
                flash("Unable to connect to the database. Please try again in a moment.", "danger")
                return redirect(url_for("index"))

            if trainer_row and trainer_row[1] == password:
                if trainer_row[4]:
                    flash("Your account has been suspended by the administrator.", "danger")
                    return redirect(url_for("index"))

                if not trainer_row[3]:
                    flash("Your trainer registration is pending admin approval.", "warning")
                    return redirect(url_for("index"))

                session["user_name"] = trainer_row[2]
                session["role"] = "trainer"
                session["trainer_username"] = trainer_row[0]

                try:
                    conn = get_pg_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT id_number FROM trainers WHERE username = %s", (trainer_row[0],))
                    id_row = cursor.fetchone()
                    if id_row and id_row[0]:
                        session["id_number"] = id_row[0]
                    else:
                        session["id_number"] = "STPC0000"
                    conn.close()
                except Exception as e:
                    pass

                try:
                    conn = get_pg_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id, current_login FROM user_activity WHERE LOWER(user_name) = LOWER(%s) AND role = %s",
                        (trainer_row[2], "trainer")
                    )
                    act_row = cursor.fetchone()
                    if act_row:
                        cursor.execute(
                            "UPDATE user_activity SET previous_login = %s, current_login = CURRENT_TIMESTAMP, phone = %s WHERE id = %s",
                            (act_row[1], "", act_row[0])
                        )
                    else:
                        cursor.execute(
                            "INSERT INTO user_activity (user_name, phone, role, current_login, previous_login) VALUES (%s, %s, %s, CURRENT_TIMESTAMP, NULL)",
                            (trainer_row[2], "", "trainer")
                        )
                    conn.commit()
                    conn.close()
                except Exception as db_err:
                    print("LOGIN DB ERROR (trainer activity):", db_err)
                    # Activity log failure should not block trainer login
                return redirect(url_for("index"))

            flash("Invalid trainer credentials")
            return redirect(url_for("index", role="trainer"))

        if role == "admin":
            if name == admin_username and password == admin_password:
                session["user_name"] = "Super Admin"
                session["role"] = "admin"
                session["admin_username"] = "admin"

                try:
                    conn = get_pg_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT id_number FROM trainers WHERE LOWER(username) = LOWER(%s)", (admin_username,))
                    id_row = cursor.fetchone()
                    if id_row and id_row[0]:
                        session["id_number"] = id_row[0]
                    else:
                        session["id_number"] = "STPA0001"
                except Exception as e:
                    pass

                try:
                    conn = get_pg_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id, current_login FROM user_activity WHERE LOWER(user_name) = 'super admin' AND role = 'admin'"
                    )
                    act_row = cursor.fetchone()
                    if act_row:
                        cursor.execute(
                            "UPDATE user_activity SET previous_login = %s, current_login = CURRENT_TIMESTAMP, phone = %s WHERE id = %s",
                            (act_row[1], "", act_row[0])
                        )
                    else:
                        cursor.execute(
                            "INSERT INTO user_activity (user_name, phone, role, current_login, previous_login) VALUES (%s, %s, %s, CURRENT_TIMESTAMP, NULL)",
                            ("Super Admin", "", "admin")
                        )
                    conn.commit()
                    conn.close()
                except Exception as db_err:
                    print("LOGIN DB ERROR (admin activity):", db_err)
                # Still allow login even if activity log fails
                return redirect(url_for("index"))

            flash("Invalid admin credentials")
            return redirect(url_for("index", role="admin"))

        if role == "guest" and name:
            normalized_name = name.lower()
            phone = "".join(character for character in phone if character.isdigit())

            if len(phone) != 10:
                flash("Please enter a valid 10-digit mobile number.")
                return redirect(url_for("index"))

            try:
                conn = get_pg_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT owner_name
                    FROM students
                    WHERE owner_phone = %s

                    UNION

                    SELECT owner_name
                    FROM bookings
                    WHERE owner_phone = %s

                    LIMIT 1
                    """,
                    (phone, phone),
                )
                existing_row = cursor.fetchone()
                conn.close()
            except Exception as db_err:
                print("LOGIN DB ERROR (guest lookup):", db_err)
                flash("Unable to connect to the database. Please try again in a moment.", "danger")
                return redirect(url_for("index"))

            try:
                conn = get_pg_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT is_blocked FROM students WHERE owner_phone = %s LIMIT 1", (phone,))
                block_row = cursor.fetchone()
                conn.close()
                if block_row and block_row[0]:
                    flash("Your account has been suspended by the administrator.", "danger")
                    return redirect(url_for("index"))
            except Exception as e:
                print("LOGIN DB ERROR (guest block check):", e)

            if existing_row:
                existing_name = (existing_row[0] or "").strip().lower()
                if existing_name != normalized_name:
                    flash("User already exists with this mobile number.")
                    return redirect(url_for("index"))

            session["role"] = "guest"
            session["user_name"] = normalized_name
            session["phone"] = phone

            try:
                conn = get_pg_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, current_login, id_number FROM user_activity WHERE LOWER(user_name) = LOWER(%s) AND role = %s",
                    (normalized_name, "guest")
                )
                act_row = cursor.fetchone()
                if act_row:
                    session["id_number"] = act_row[2] or "STPS0000"
                    cursor.execute(
                        "UPDATE user_activity SET previous_login = %s, current_login = CURRENT_TIMESTAMP, phone = %s WHERE id = %s",
                        (act_row[1], phone, act_row[0])
                    )
                else:
                    cursor.execute("SELECT MAX(CAST(SUBSTRING(id_number FROM 5) AS INTEGER)) FROM user_activity WHERE id_number LIKE 'STPS%'")
                    max_guest_val = cursor.fetchone()[0] or 0
                    new_id_number = f"STPS{max_guest_val + 1:04d}"
                    session["id_number"] = new_id_number

                    cursor.execute(
                        "INSERT INTO user_activity (user_name, phone, role, current_login, previous_login, id_number) VALUES (%s, %s, %s, CURRENT_TIMESTAMP, NULL, %s)",
                        (normalized_name, phone, "guest", new_id_number)
                    )
                conn.commit()
                conn.close()
            except Exception as db_err:
                print("LOGIN DB ERROR (guest activity):", db_err)
                # Activity log failure should not block login
            return redirect(url_for("index"))

        flash("Please enter all required fields.")
        return redirect(url_for("index", role=role))

    def register_page():
        return render_template("registration.html")

    def register_trainer():
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        name = (request.form.get("name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        email = (request.form.get("email") or "").strip()
        experience = (request.form.get("experience") or "").strip()
        qualification = (request.form.get("qualification") or "").strip()
        currently_working = (request.form.get("currently_working") or "").strip()
        residence_location = (request.form.get("residence_location") or "").strip()
        id_proof = (request.form.get("id_proof") or "").strip()
        whatsapp = (request.form.get("whatsapp") or "").strip()
        consent_accepted = request.form.get("consent_accepted") == "on"

        if not username or not password or not name or not phone or not email or not whatsapp:
            flash("Please fill in all mandatory fields (marked with *).")
            return redirect(url_for("register_page"))

        if not consent_accepted:
            flash("You must accept the Coach Terms & Agreement to register.")
            return redirect(url_for("register_page"))

        import random
        rating = round(random.uniform(4.5, 5.0), 1)

        conn = get_pg_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM trainers WHERE LOWER(username) = LOWER(%s)", (username.lower(),))
        if cursor.fetchone():
            conn.close()
            flash("Trainer username already exists.")
            return redirect(url_for("register_page"))

        from datetime import datetime
        consent_version = "v1.0"
        consent_accepted_at = datetime.now()
        consent_ip = request.remote_addr or ""

        cursor.execute("SELECT MAX(CAST(SUBSTRING(id_number FROM 5) AS INTEGER)) FROM trainers WHERE id_number LIKE 'STPC%'")
        max_coach_val = cursor.fetchone()[0] or 0
        new_id_number = f"STPC{max_coach_val + 1:04d}"

        cursor.execute(
            """
            INSERT INTO trainers (username, password, name, phone, email, experience, qualification, currently_working, residence_location, id_proof, consent_accepted, rating, is_approved, whatsapp, consent_version, consent_accepted_at, consent_ip, id_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (username.lower(), password, name, phone, email, experience, qualification, currently_working, residence_location, id_proof, True, rating, False, whatsapp, consent_version, consent_accepted_at, consent_ip, new_id_number)
        )
        conn.commit()
        conn.close()
        flash("Trainer registered successfully! Your account is pending Super Admin approval before you can log in.")
        return redirect(url_for("index"))

    def terms_agreement_page():
        return render_template("terms_agreement.html")

    def forgot_password():
        if request.method == "GET":
            return render_template("forgot_password.html")
            
        email = (request.form.get("email") or "").strip()
        if not email:
            flash("Please enter an email address.", "danger")
            return redirect(url_for("forgot_password"))
            
        conn = get_pg_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, name FROM trainers WHERE email = %s", (email,))
        trainer = cursor.fetchone()
        
        if not trainer:
            conn.close()
            flash("No trainer found with that email address.", "danger")
            return redirect(url_for("forgot_password"))
            
        import random
        from datetime import datetime, timedelta
        from services.email_service import send_email
        
        otp = str(random.randint(100000, 999999))
        expires_at = datetime.now() + timedelta(minutes=10)
        
        cursor.execute(
            "INSERT INTO password_reset_otps (email, otp, expires_at) VALUES (%s, %s, %s)",
            (email, otp, expires_at)
        )
        conn.commit()
        conn.close()
        
        html_content = f"""
        <h2>SwimTrack Password Reset</h2>
        <p>Hi {trainer[1]},</p>
        <p>You requested a password reset. Your OTP is: <strong>{otp}</strong></p>
        <p>This OTP will expire in 10 minutes.</p>
        <p>If you did not request this, please ignore this email.</p>
        """
        
        send_email(
            subject="SwimTrack Password Reset OTP",
            html_content=html_content,
            to_email=email,
            to_name=trainer[1]
        )
        
        flash("An OTP has been sent to your email address.", "success")
        return render_template("verify_otp.html", email=email)

    def verify_otp():
        email = (request.form.get("email") or "").strip()
        otp = (request.form.get("otp") or "").strip()
        new_password = (request.form.get("new_password") or "").strip()
        
        if not email or not otp or not new_password:
            flash("Missing required fields.", "danger")
            if email:
                return render_template("verify_otp.html", email=email)
            return redirect(url_for("forgot_password"))
            
        conn = get_pg_connection()
        cursor = conn.cursor()
        
        from datetime import datetime
        cursor.execute(
            "SELECT id FROM password_reset_otps WHERE email = %s AND otp = %s AND expires_at > %s ORDER BY created_at DESC LIMIT 1",
            (email, otp, datetime.now())
        )
        valid_otp = cursor.fetchone()
        
        if not valid_otp:
            conn.close()
            flash("Invalid or expired OTP. Please request a new one.", "danger")
            return render_template("verify_otp.html", email=email)
            
        cursor.execute("UPDATE trainers SET password = %s WHERE email = %s", (new_password, email))
        cursor.execute("DELETE FROM password_reset_otps WHERE email = %s", (email,))
        conn.commit()
        conn.close()
        
        flash("Password reset successfully! You can now login with your new password.", "success")
        return redirect(url_for("login"))

    app.add_url_rule(
        "/login",
        endpoint="login",
        view_func=login,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        "/forgot-password",
        endpoint="forgot_password",
        view_func=forgot_password,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        "/verify-otp",
        endpoint="verify_otp",
        view_func=verify_otp,
        methods=["POST"],
    )
    app.add_url_rule(
        "/register",
        endpoint="register_page",
        view_func=register_page,
        methods=["GET"],
    )
    app.add_url_rule(
        "/register_trainer",
        endpoint="register_trainer",
        view_func=register_trainer,
        methods=["POST"],
    )
    app.add_url_rule(
        "/terms-agreement",
        endpoint="terms_agreement_page",
        view_func=terms_agreement_page,
        methods=["GET"],
    )
