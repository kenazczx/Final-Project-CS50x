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
    session.pop("reset_email", None)
    session.pop("reset_code", None)
    session.pop("reset_status", None)