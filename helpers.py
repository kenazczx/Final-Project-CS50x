import requests

from flask import redirect, render_template, session
from functools import wraps


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def cleanup_verification():
    if session.get("reset_email"):
        session.pop("reset_email", None)
    if session.get("reset_code"):
        session.pop("reset_code", None)
    if session.get("reset_status"):
        session.pop("reset_status", None)
    if session.get("pending_user"):
        session.pop("pending_user", None)
    if session.get("register_code"):
        session.pop("register_code", None)
    if session.get("register_mode"):
        session.pop("register_mode", None)