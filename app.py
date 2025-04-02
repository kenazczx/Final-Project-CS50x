from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_session import Session
from cs50 import SQL
from geopy.geocoders import Nominatim
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required
import sqlite3


app = Flask(__name__)
app.config['DEBUG'] = True
app.config['ENV'] = 'development'
if __name__ == "__main__":
    app.run(debug=True)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


db = SQL("sqlite:///healtheats.db")

# Route for the home page
@app.route('/')
@login_required
def home():
    return render_template('index.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")
    

@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')