"""Reusable access-control decorators for Flask views."""

from functools import wraps

from flask import flash, redirect, session, url_for


def login_required(view):
    """Redirect anonymous users to the existing index/login endpoint."""

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_name" not in session:
            return redirect(url_for("index"))
        return view(*args, **kwargs)

    return wrapped_view


def trainer_required(message="Only trainer can perform this action."):
    """Restrict a view to authenticated trainer sessions."""

    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if "user_name" not in session:
                return redirect(url_for("index"))
            if session.get("role") != "trainer":
                flash(message, "danger")
                return redirect(url_for("index"))
            return view(*args, **kwargs)

        return wrapped_view

    return decorator


def admin_required(message="Only admin can perform this action."):
    """Restrict a view to super admin sessions."""

    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if "user_name" not in session:
                return redirect(url_for("index"))
            if session.get("role") != "admin":
                flash(message, "danger")
                return redirect(url_for("index"))
            return view(*args, **kwargs)

        return wrapped_view

    return decorator
