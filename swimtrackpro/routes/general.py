"""General authenticated pages and session routes."""

from flask import flash, redirect, render_template, request, session, url_for, jsonify

from services.settings_service import get_setting, set_setting
from swimtrackpro.auth import login_required, trainer_required, admin_required
from swimtrackpro.runtime import get_pg_connection, load_data


@login_required
def about_trainer():
    current_user = session.get("user_name")
    current_phone = session.get("phone")
    current_role = session.get("role", "guest")

    conn = get_pg_connection()
    cursor = conn.cursor()

    if current_role == "trainer":
        assigned_usernames = []
        trainer_user = session.get("trainer_username") or "asdf"
        cursor.execute("""
            SELECT username, name, phone, email, experience, qualification, currently_working, residence_location, rating, photos, whatsapp 
            FROM trainers WHERE username = %s
        """, (trainer_user,))
        trainers = cursor.fetchall()
    else:
        # Swimmer/Guest: find trainer usernames from bookings
        data = load_data()
        bookings = [
            b for b in data.get("bookings", [])
            if (b.get("owner_name") or "").strip().lower() == current_user
            and b.get("owner_phone") == current_phone
        ]
        assigned_usernames = list(set([b.get("trainer_username") for b in bookings if b.get("trainer_username")]))
        
        trainers = []
        if assigned_usernames:
            placeholders = ", ".join(["%s"] * len(assigned_usernames))
            cursor.execute(f"""
                SELECT username, name, phone, email, experience, qualification, currently_working, residence_location, rating, photos, whatsapp 
                FROM trainers WHERE username IN ({placeholders}) AND is_approved = TRUE
            """, tuple(assigned_usernames))
            trainers = cursor.fetchall()

    coaches_list = []
    for r in trainers:
        username = r[0]
        cursor.execute("""
            SELECT guest_name, rating, pros, cons, created_at 
            FROM coach_feedback 
            WHERE trainer_username = %s 
            ORDER BY created_at DESC
        """, (username,))
        feedbacks = []
        for f in cursor.fetchall():
            feedbacks.append({
                "guest_name": f[0],
                "rating": f[1],
                "pros": f[2] or "",
                "cons": f[3] or "",
                "created_at": f[4].strftime('%Y-%m-%d') if f[4] else '--'
            })

        coaches_list.append({
            "username": username,
            "name": r[1],
            "phone": r[2] or "",
            "email": r[3] or "",
            "experience": r[4] or "5+ Years",
            "qualification": r[5] or "Certified Swim Coach",
            "currently_working": r[6] or "SwimTrackPro Academy",
            "residence_location": r[7] or "Local Camp",
            "rating": float(r[8]) if r[8] is not None else 5.0,
            "photos": [p.strip() for p in (r[9] or "").split(",") if p.strip()],
            "whatsapp": r[10] or "",
            "feedbacks": feedbacks
        })

    conn.close()

    return render_template("about_trainer.html", coaches=coaches_list, role=current_role, assigned_usernames=assigned_usernames, admin_phone=get_setting("trainer_phone", ""))


@login_required
def help_page():
    return render_template("help.html", role=session.get("role", "guest"))

@login_required
def about_swimming():
    return render_template("about_swimming.html", role=session.get("role", "guest"))


@trainer_required("Only trainer can update the Notice Board.")
def update_notice():
    notice_message = request.form.get("notice_message", "").strip()

    if not notice_message:
        flash("Notice Board message cannot be empty.", "warning")
        return redirect(url_for("index"))

    trainer_user = session.get("trainer_username") or "asdf"
    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE trainers SET notice = %s WHERE username = %s", (notice_message, trainer_user))
    conn.commit()
    conn.close()

    flash("Notice Board updated successfully.", "success")
    return redirect(url_for("index"))


@login_required
def profile_page():
    current_role = session.get("role", "guest")
    if current_role != "trainer":
        flash("Only trainers have a profile page.", "error")
        return redirect(url_for("index"))

    trainer_user = session.get("trainer_username") or "asdf"
    conn = get_pg_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        email = request.form.get("email")
        experience = request.form.get("experience")
        qualification = request.form.get("qualification")
        currently_working = request.form.get("currently_working")
        residence_location = request.form.get("residence_location")
        whatsapp = request.form.get("whatsapp")

        cursor.execute("""
            UPDATE trainers 
            SET name = %s, phone = %s, email = %s, experience = %s, qualification = %s, currently_working = %s, residence_location = %s, whatsapp = %s
            WHERE username = %s
        """, (name, phone, email, experience, qualification, currently_working, residence_location, whatsapp, trainer_user))
        conn.commit()

        # Update session so the dashboard card reflects the new name immediately
        if name:
            session["user_name"] = name

        flash("Profile updated successfully!", "success")

    cursor.execute("""
        SELECT username, name, phone, email, experience, qualification, currently_working, residence_location, id_proof, rating, whatsapp 
        FROM trainers WHERE username = %s
    """, (trainer_user,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        flash("Trainer not found.", "error")
        return redirect(url_for("index"))

    trainer_data = {
        "username": row[0],
        "name": row[1],
        "phone": row[2] or "",
        "email": row[3] or "",
        "experience": row[4] or "",
        "qualification": row[5] or "",
        "currently_working": row[6] or "",
        "residence_location": row[7] or "",
        "id_proof": row[8] or "",
        "rating": float(row[9]) if row[9] is not None else 5.0,
        "whatsapp": row[10] or ""
    }

    return render_template("profile.html", trainer=trainer_data, role=current_role)


@login_required
def profile_upload_photo():
    import os
    import time
    from werkzeug.utils import secure_filename

    current_role = session.get("role", "guest")
    if current_role != "trainer":
        flash("Only trainers can upload photos.", "error")
        return redirect(url_for("index"))

    trainer_user = session.get("trainer_username") or "asdf"

    if "training_pic" not in request.files:
        flash("No file part in the request.", "error")
        return redirect(url_for("profile_page"))

    file = request.files["training_pic"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("profile_page"))

    if file:
        filename = secure_filename(file.filename)
        filename = f"{trainer_user}_{int(time.time())}_{filename}"

        album_dir = os.path.join("static", "images", "Album")
        os.makedirs(album_dir, exist_ok=True)

        filepath = os.path.join(album_dir, filename)
        file.save(filepath)

        conn = get_pg_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT photos FROM trainers WHERE username = %s", (trainer_user,))
        row = cursor.fetchone()

        current_photos = row[0] if (row and row[0]) else ""
        if current_photos:
            new_photos = f"{current_photos},{filename}"
        else:
            new_photos = filename

        cursor.execute("UPDATE trainers SET photos = %s WHERE username = %s", (new_photos, trainer_user))
        conn.commit()
        conn.close()

        flash("Photo uploaded and added to your album successfully!", "success")

    return redirect(url_for("profile_page"))


def logout():
    session.clear()
    return redirect(url_for("index"))


@admin_required("Only super admin can approve trainers.")
def approve_trainer(username):
    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE trainers SET is_approved = TRUE WHERE username = %s", (username,))
    conn.commit()
    conn.close()
    flash(f"Trainer '{username}' approved successfully.", "success")
    return redirect(url_for("index"))


@admin_required("Only super admin can reject trainers.")
def reject_trainer(username):
    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trainers WHERE username = %s", (username,))
    conn.commit()
    conn.close()
    flash(f"Trainer '{username}' rejected and registration deleted.", "success")
    return redirect(url_for("index"))


@admin_required("Only super admin can delete bookings.")
def admin_delete_booking(booking_id):
    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookings WHERE id = %s", (booking_id,))
    conn.commit()
    conn.close()
    flash(f"Booking ID {booking_id} deleted successfully.", "success")
    return redirect(url_for("index"))


@admin_required("Only super admin can assign coaches.")
def assign_coach(booking_id):
    trainer_username = request.form.get("trainer_username")
    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE bookings SET trainer_username = %s WHERE id = %s", (trainer_username, booking_id))
    conn.commit()
    conn.close()
    flash(f"Coach assigned successfully for Booking #{booking_id}.", "success")
    return redirect(url_for("index"))


@login_required
def submit_coach_feedback(trainer_username):
    current_role = session.get("role", "guest")
    if current_role != "guest":
        flash("Only guests/swimmers can leave feedback.", "error")
        return redirect(url_for("about_trainer"))

    rating = request.form.get("rating")
    pros = request.form.get("pros", "").strip()
    cons = request.form.get("cons", "").strip()

    if not rating:
        flash("Please provide a rating.", "warning")
        return redirect(url_for("about_trainer"))

    try:
        rating_val = int(rating)
        if rating_val < 1 or rating_val > 5:
            raise ValueError()
    except ValueError:
        flash("Rating must be an integer between 1 and 5.", "warning")
        return redirect(url_for("about_trainer"))

    guest_name = session.get("user_name")
    guest_phone = session.get("phone")

    # Verify that the coach is assigned to the guest via active bookings
    data = load_data()
    bookings = [
        b for b in data.get("bookings", [])
        if (b.get("owner_name") or "").strip().lower() == guest_name.lower()
        and b.get("owner_phone") == guest_phone
    ]
    assigned_usernames = [b.get("trainer_username") for b in bookings if b.get("trainer_username")]
    if trainer_username not in assigned_usernames:
        flash("You can only submit feedback for a coach assigned to you.", "error")
        return redirect(url_for("about_trainer"))

    conn = get_pg_connection()
    cursor = conn.cursor()

    # Check if trainer exists and is approved
    cursor.execute("SELECT username FROM trainers WHERE username = %s AND is_approved = TRUE", (trainer_username,))
    if not cursor.fetchone():
        conn.close()
        flash("Coach not found or not approved.", "error")
        return redirect(url_for("about_trainer"))

    # Check if guest already submitted feedback for this trainer
    cursor.execute("""
        SELECT id FROM coach_feedback 
        WHERE trainer_username = %s AND LOWER(guest_name) = LOWER(%s) AND guest_phone = %s
    """, (trainer_username, guest_name.lower(), guest_phone))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
            UPDATE coach_feedback 
            SET rating = %s, pros = %s, cons = %s, created_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (rating_val, pros, cons, existing[0]))
    else:
        cursor.execute("""
            INSERT INTO coach_feedback (trainer_username, guest_name, guest_phone, rating, pros, cons)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (trainer_username, guest_name, guest_phone, rating_val, pros, cons))

    conn.commit()

    # Recalculate and update the trainer's overall rating
    cursor.execute("""
        SELECT AVG(rating) FROM coach_feedback WHERE trainer_username = %s
    """, (trainer_username,))
    avg_rating_row = cursor.fetchone()
    if avg_rating_row and avg_rating_row[0] is not None:
        new_rating = round(float(avg_rating_row[0]), 2)
        cursor.execute("""
            UPDATE trainers SET rating = %s WHERE username = %s
        """, (new_rating, trainer_username))
        conn.commit()

    conn.close()
    flash("Feedback submitted successfully!", "success")
    return redirect(url_for("about_trainer"))


@admin_required("Only admin can block trainers.")
def toggle_block_trainer(username):
    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_blocked FROM trainers WHERE username = %s", (username,))
    row = cursor.fetchone()
    if row:
        new_status = not row[0]
        cursor.execute("UPDATE trainers SET is_blocked = %s WHERE username = %s", (new_status, username))
        conn.commit()
        if new_status:
            flash(f"Trainer {username} has been blocked and suspended.", "danger")
        else:
            flash(f"Trainer {username} has been unblocked.", "success")
    conn.close()
    return redirect(url_for("index"))

@admin_required("Only admin can block students.")
def toggle_block_student(phone):
    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_blocked FROM students WHERE owner_phone = %s", (phone,))
    row = cursor.fetchone()
    if row:
        new_status = not row[0]
        cursor.execute("UPDATE students SET is_blocked = %s WHERE owner_phone = %s", (new_status, phone))
        conn.commit()
        if new_status:
            flash(f"Student with phone {phone} has been blocked and suspended.", "danger")
        else:
            flash(f"Student with phone {phone} has been unblocked.", "success")
    else:
        # Create student record if not found just to block them based on phone
        cursor.execute("INSERT INTO students (owner_phone, owner_name, is_blocked) VALUES (%s, %s, %s)", (phone, 'Unknown', True))
        conn.commit()
        flash(f"Student with phone {phone} has been blocked and suspended.", "danger")
    conn.close()
    return redirect(url_for("index"))


@admin_required("Only admin can edit students.")
def edit_student(phone):
    if request.method == "POST":
        new_name = request.form.get("name")
        new_owner = request.form.get("owner_name")
        new_phone = request.form.get("owner_phone")
        
        conn = get_pg_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE students SET name = %s, owner_name = %s, owner_phone = %s WHERE owner_phone = %s",
            (new_name, new_owner, new_phone, phone)
        )
        # also update bookings that might use the old phone
        cursor.execute(
            "UPDATE bookings SET owner_phone = %s WHERE owner_phone = %s",
            (new_phone, phone)
        )
        conn.commit()
        conn.close()
        flash("Student details updated successfully.", "success")
        return redirect(url_for("index"))

@admin_required("Only admin can edit trainers.")
def edit_trainer(username):
    if request.method == "POST":
        conn = get_pg_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE trainers 
            SET name = %s, phone = %s, email = %s, experience = %s, 
                qualification = %s, currently_working = %s, residence_location = %s, rating = %s
            WHERE username = %s
            """,
            (
                request.form.get("name"),
                request.form.get("phone"),
                request.form.get("email"),
                request.form.get("experience"),
                request.form.get("qualification"),
                request.form.get("currently_working"),
                request.form.get("residence_location"),
                request.form.get("rating"),
                username
            )
        )
        conn.commit()
        conn.close()
        flash("Trainer details updated successfully.", "success")
        return redirect(url_for("index"))

@admin_required("Only admin can delete trainer images.")
def delete_trainer_image(username, filename):
    import os
    if request.method == "POST":
        conn = get_pg_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT photos FROM trainers WHERE username = %s", (username,))
        row = cursor.fetchone()
        
        if row and row[0]:
            photos = row[0].split(",")
            if filename in photos:
                photos.remove(filename)
                new_photos_str = ",".join(photos)
                
                # Delete from database
                cursor.execute("UPDATE trainers SET photos = %s WHERE username = %s", (new_photos_str, username))
                
                # Delete file from disk
                album_dir = os.path.join("static", "images", "Album")
                filepath = os.path.join(album_dir, filename)
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except Exception as e:
                    print(f"Error removing file {filepath}: {e}")
                
                conn.commit()
                flash("Image deleted successfully.", "success")
            else:
                flash("Image not found in trainer's album.", "warning")
        
        conn.close()
        return redirect(url_for("index"))

def register_general_routes(app):
    """Register routes with their legacy endpoint names unchanged."""

    app.add_url_rule(
        "/about-trainer",
        endpoint="about_trainer",
        view_func=about_trainer,
    )
    app.add_url_rule(
        "/help",
        endpoint="help_page",
        view_func=help_page,
    )
    app.add_url_rule(
        "/about-swimming",
        endpoint="about_swimming",
        view_func=about_swimming,
    )
    app.add_url_rule(
        "/update_notice",
        endpoint="update_notice",
        view_func=update_notice,
        methods=["POST"],
    )
    def profile_update_password():
        current_role = session.get("role")
        trainer_user = session.get("trainer_username")
        if current_role != "trainer" or not trainer_user:
            return redirect(url_for("index"))

        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if new_password != confirm_password:
            flash("New passwords do not match.", "danger")
            return redirect(url_for("profile_page"))

        conn = get_pg_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM trainers WHERE username = %s", (trainer_user,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            flash("Trainer account not found.", "danger")
            return redirect(url_for("profile_page"))

        cursor.execute("UPDATE trainers SET password = %s WHERE username = %s", (new_password, trainer_user))
        conn.commit()
        conn.close()

        flash("Password updated successfully!", "success")
        return redirect(url_for("profile_page"))

    @app.route('/api/my_id_card')
    def api_my_id_card():
        if 'user_name' not in session:
            return jsonify({'error': 'Not logged in'}), 401
            
        role = session.get('role', 'guest')
        user_name = session.get('user_name', '')
        id_number = session.get('id_number', '')
        
        conn = get_pg_connection()
        cursor = conn.cursor()
        
        photo = None
        title = "SwimTrackPro Guest"
        phone = session.get('phone', '')
        email = ""
        address = ""
        
        if role == 'admin':
            title = "SwimTrackPro Admin"
            cursor.execute("SELECT phone, email, residence_location FROM trainers WHERE LOWER(username) = LOWER(%s)", (session.get('admin_username', 'admin'),))
            row = cursor.fetchone()
            if row:
                phone, email, address = row[0], row[1], row[2]
        elif role == 'trainer':
            title = "SwimTrackPro Coach"
            cursor.execute("SELECT phone, email, residence_location FROM trainers WHERE username = %s", (session.get('trainer_username'),))
            row = cursor.fetchone()
            if row:
                phone, email, address = row[0], row[1], row[2]
        else:
            title = "SwimTrackPro Student"
            
        # Fetch from profile_pictures table
        cursor.execute("SELECT filename FROM profile_pictures WHERE id_number = %s", (id_number,))
        pic_row = cursor.fetchone()
        if pic_row and pic_row[0]:
            photo = url_for('static', filename='profile_pictures/' + pic_row[0])
            
        conn.close()

        return jsonify({
            'name': user_name.title(),
            'title': title,
            'id_number': id_number,
            'phone': phone,
            'email': email,
            'address': address,
            'photo': photo
        })

    @app.route('/api/upload_id_card_photo', methods=['POST'])
    def api_upload_id_card_photo():
        if 'user_name' not in session or 'id_number' not in session:
            return jsonify({'error': 'Not logged in'}), 401

        if 'profile_pic' not in request.files:
            return jsonify({'error': 'No file part in the request.'}), 400

        file = request.files['profile_pic']
        if file.filename == '':
            return jsonify({'error': 'No file selected.'}), 400

        if file:
            import os
            from werkzeug.utils import secure_filename
            id_number = session.get('id_number', 'UNKNOWN')
            original_ext = os.path.splitext(file.filename)[1]
            original_base = os.path.splitext(file.filename)[0]
            # Use original name with ID appended as requested
            new_filename = secure_filename(f"{original_base}_{id_number}{original_ext}")

            profile_dir = os.path.join("static", "profile_pictures")
            os.makedirs(profile_dir, exist_ok=True)
            filepath = os.path.join(profile_dir, new_filename)
            file.save(filepath)

            conn = get_pg_connection()
            cursor = conn.cursor()
            
            # Upsert into profile_pictures
            cursor.execute("""
                INSERT INTO profile_pictures (id_number, filename, updated_at) 
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (id_number) 
                DO UPDATE SET filename = EXCLUDED.filename, updated_at = EXCLUDED.updated_at
            """, (id_number, new_filename))
            conn.commit()
            conn.close()

            return jsonify({'success': True, 'photo': url_for('static', filename='profile_pictures/' + new_filename)})
            
        return jsonify({'error': 'Upload failed'}), 500

    @app.route('/api/remove_id_card_photo', methods=['POST'])
    def api_remove_id_card_photo():
        if 'user_name' not in session or 'id_number' not in session:
            return jsonify({'error': 'Not logged in'}), 401
            
        id_number = session.get('id_number')
        
        conn = get_pg_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT filename FROM profile_pictures WHERE id_number = %s", (id_number,))
        row = cursor.fetchone()
        
        if row:
            import os
            filename = row[0]
            filepath = os.path.join("static", "profile_pictures", filename)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass
            
            cursor.execute("DELETE FROM profile_pictures WHERE id_number = %s", (id_number,))
            conn.commit()
        
        conn.close()
        
        return jsonify({'success': True})

    app.add_url_rule(
        "/profile",
        endpoint="profile_page",
        view_func=profile_page,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        "/profile/update_password",
        endpoint="profile_update_password",
        view_func=profile_update_password,
        methods=["POST"],
    )
    app.add_url_rule(
        "/profile/upload-photo",
        endpoint="profile_upload_photo",
        view_func=profile_upload_photo,
        methods=["POST"],
    )
    app.add_url_rule(
        "/logout",
        endpoint="logout",
        view_func=logout,
    )
    app.add_url_rule(
        "/admin/approve_trainer/<username>",
        endpoint="approve_trainer",
        view_func=approve_trainer,
        methods=["POST"],
    )
    app.add_url_rule(
        "/admin/reject_trainer/<username>",
        endpoint="reject_trainer",
        view_func=reject_trainer,
        methods=["POST"],
    )
    app.add_url_rule(
        "/admin/delete_booking/<booking_id>",
        endpoint="admin_delete_booking",
        view_func=admin_delete_booking,
        methods=["POST"],
    )
    app.add_url_rule(
        "/admin/assign_coach/<booking_id>",
        endpoint="assign_coach",
        view_func=assign_coach,
        methods=["POST"],
    )
    app.add_url_rule(
        "/coach/feedback/<trainer_username>",
        endpoint="submit_coach_feedback",
        view_func=submit_coach_feedback,
        methods=["POST"],
    )
    app.add_url_rule(
        "/admin/toggle_block_trainer/<username>",
        endpoint="toggle_block_trainer",
        view_func=toggle_block_trainer,
        methods=["POST"],
    )
    app.add_url_rule(
        "/admin/toggle_block_student/<phone>",
        endpoint="toggle_block_student",
        view_func=toggle_block_student,
        methods=["POST"],
    )
    app.add_url_rule(
        "/admin/edit_student/<phone>",
        endpoint="edit_student",
        view_func=edit_student,
        methods=["POST"],
    )
    app.add_url_rule(
        "/admin/edit_trainer/<username>",
        endpoint="edit_trainer",
        view_func=edit_trainer,
        methods=["POST"],
    )
    app.add_url_rule(
        "/admin/delete_trainer_image/<username>/<filename>",
        endpoint="delete_trainer_image",
        view_func=delete_trainer_image,
        methods=["POST"],
    )
