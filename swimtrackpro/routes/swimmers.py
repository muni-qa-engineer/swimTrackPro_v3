"""Swimmer management routes."""

from flask import flash, redirect, request, session, url_for


def register_swimmer_routes(app, *, get_pg_connection, load_data):
    def add_swimmer():
        if session.get("role") == "trainer":
            flash("Trainer cannot add swimmers directly")
            return redirect(url_for("index"))

        data = load_data()
        name = (request.form.get("name") or "").strip()

        if not name:
            flash("Swimmer name required")
            return redirect(url_for("index"))

        existing_swimmer = next(
            (
                swimmer
                for swimmer in data["students"]
                if isinstance(swimmer, dict)
                and swimmer.get("name") == name
                and swimmer.get("owner_name") == session.get("user_name")
                and swimmer.get("owner_phone") == session.get("phone")
            ),
            None,
        )

        if existing_swimmer:
            return redirect(url_for("index", swimmer_exists="true"))

        conn = get_pg_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO students (student_name, owner_name, owner_phone)
            VALUES (%s, %s, %s)
            """,
            (name, session.get("user_name"), session.get("phone")),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("booking_page"))

    def delete_swimmer(name):
        current_user = session.get("user_name")
        current_phone = session.get("phone")

        conn = get_pg_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM students
            WHERE student_name = %s
              AND owner_name = %s
              AND owner_phone = %s
            """,
            (name, current_user, current_phone),
        )
        cursor.execute(
            """
            DELETE FROM bookings
            WHERE student_name = %s
              AND owner_name = %s
              AND owner_phone = %s
            """,
            (name, current_user, current_phone),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("booking_page"))

    app.add_url_rule(
        "/add_swimmer",
        endpoint="add_swimmer",
        view_func=add_swimmer,
        methods=["POST"],
    )
    app.add_url_rule(
        "/delete_swimmer/<name>",
        endpoint="delete_swimmer",
        view_func=delete_swimmer,
        methods=["POST"],
    )
