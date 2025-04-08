from flask import Flask, render_template, request, redirect, session, flash, jsonify
from flask_session import Session
from cs50 import SQL
from geopy.geocoders import Nominatim
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required, cleanup_verification
from datetime import datetime
import pandas as pd
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import os, random, time
from dotenv import load_dotenv
from email.utils import formataddr
import re

load_dotenv()  # Load variables from .env file

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = True
app.config['DEBUG'] = True
app.config['ENV'] = 'development'

mail = Mail(app)
serailizer = URLSafeTimedSerializer(app.secret_key)

if __name__ == "__main__":
    app.run(debug=True)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


db = SQL("sqlite:///budget_tracker.db")

# Route for the home page
@app.route('/')
@login_required
def home():
    current_date = datetime.now()
    current_month = current_date.month
    current_year = current_date.year
    user_id = session.get("user_id")
    name = db.execute("SELECT name FROM users WHERE id = ?", user_id)
    budgets = db.execute("SELECT budget, spent, income FROM monthly_totals WHERE user_id = ? AND month = ? AND year = ?", user_id, current_month, current_year)
    if budgets:
        monthly_budget = float(budgets[0]["budget"])
        monthly_spent = float(budgets[0]["spent"])
        monthly_income = float(budgets[0]["income"])
        if monthly_budget > 0:
            progress_percentage = round((monthly_spent / monthly_budget) * 100, 2)
        else:
            progress_percentage = 0
    else:
        progress_percentage = 0
        monthly_budget = 0
        monthly_spent = 0
        monthly_income = 0
    if not user_id:
        return redirect("/login")
    total_income = db.execute("SELECT total_income FROM user_totals WHERE user_id = ?", user_id)
    total_expenses = db.execute("SELECT total_expenses FROM user_totals WHERE user_id = ?", user_id)
    balance = db.execute("SELECT balance FROM user_totals WHERE user_id = ?", user_id)
    transactions = db.execute("SELECT id, amount, category, transaction_type, date FROM transactions WHERE user_id = ? ORDER BY date DESC", user_id)
    # Current Date
    return render_template("index.html", total_income=total_income[0]["total_income"], total_expenses=total_expenses[0]["total_expenses"], balance=balance[0]["balance"], transactions=transactions, progress_percentage=progress_percentage, monthly_budget=monthly_budget, monthly_spent=monthly_spent, monthly_income=monthly_income, name=name)

@app.route("/get_categories")
@login_required
def get_categories():
    user_id = session.get("user_id")
    transaction_type = request.args.get("type")

    if transaction_type not in ["income", "expense"]:
        return jsonify([])

    db_categories = db.execute(
        "SELECT DISTINCT category FROM transactions WHERE user_id = ? AND transaction_type = ?",
        user_id, transaction_type
    )

    default_income = ["Salary", "Business", "Investment", "Rental"]
    default_expense = ["Food", "Transport", "Entertainment", "Utilities"]

    if transaction_type == "income":
        categories = default_income + [row["category"] for row in db_categories if row["category"] not in default_income]
    else:
        categories = default_expense + [row["category"] for row in db_categories if row["category"] not in default_expense]

    # Add "Others" at the end
    if "Others" not in categories:
        categories.append("Others")

    return jsonify(categories)    
@app.route('/get_time')
@login_required
def get_time():
    """Get current time"""
    current_datetime = datetime.now()
    today = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
    return today


@app.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        user_id = session.get("user_id")
        current_date = datetime.now()
        current_month = current_date.month
        current_year = current_date.year
        amount = float(request.form.get('amount'))
        if not amount:
            flash("Please provide an amount!", "danger")
            return redirect('/')
        if amount < 0:
            flash("Amount cannot be negative!", "danger")
            return redirect('/')
        category_initial = request.form.get('category')
        if not category_initial:
            flash("Please provide a category!", "danger")
            return redirect('/')
        if category_initial == "others":
            category = request.form.get('custom_category')
        else:
            category = category_initial
        if not re.match("^[A-Za-z &-]+$", category.strip()):
            flash("Category can only include letters, spaces, dashes, and '&'.", "danger")
            return redirect("/")
        transaction_type = request.form.get('transaction_type')
        if not transaction_type:
            flash("Please provide a transaction type!", "danger")
            return redirect('/')
        date = request.form.get('date')
        if not date:
            flash("Please provide a date!", "danger")
            return redirect('/')
        db.execute("INSERT INTO transactions (user_id, amount, category, transaction_type, date) VALUES (?, ?, ?, ?, ?)", user_id, amount, category, transaction_type, date)
        if transaction_type == "income":
            db.execute("UPDATE user_totals SET total_income = total_income + ? WHERE user_id = ?", amount, user_id)
            db.execute("UPDATE user_totals SET balance = balance + ? WHERE user_id = ?", amount, user_id)
            if current_month == datetime.strptime(date, '%Y-%m-%d').month and current_year == datetime.strptime(date, '%Y-%m-%d').year:
                        db.execute("UPDATE monthly_totals SET income = income + ? WHERE user_id = ? AND month = ? AND year = ?", amount, user_id, current_month, current_year)
        elif transaction_type == "expense":
            db.execute("UPDATE user_totals SET total_expenses = total_expenses + ? WHERE user_id = ?", amount, user_id)
            db.execute("UPDATE user_totals SET balance = balance - ? WHERE user_id = ?", amount, user_id)
            if current_month == datetime.strptime(date, '%Y-%m-%d').month and current_year == datetime.strptime(date, '%Y-%m-%d').year:
                db.execute("UPDATE monthly_totals SET spent = spent + ? WHERE user_id = ? AND month = ? AND year = ?", amount, user_id, current_month, current_year)
        flash("Transaction added successfully!", "success")
        return redirect('/')
    else:
        return redirect('/')

@app.route('/delete_transaction', methods=['GET', 'POST'])
@login_required
def delete_transaction():
    if request.method == 'POST':
        current_date = datetime.now()
        current_month = current_date.month
        current_year = current_date.year
        user_id = session.get("user_id")
        transaction_id = request.form.get('transaction_id')
        transaction = db.execute("SELECT * FROM transactions WHERE id = ?", transaction_id)
        if transaction:
            trans = transaction[0]
            amount = float(trans["amount"])
            t_type = trans["transaction_type"]
            date = trans["date"]
            if t_type == "income":
                db.execute("UPDATE user_totals SET total_income = total_income - ? WHERE user_id = ?", amount, user_id)
                db.execute("UPDATE user_totals SET balance = balance - ? WHERE user_id = ?", amount, user_id)
                if current_month == datetime.strptime(date, '%Y-%m-%d').month and current_year == datetime.strptime(date, '%Y-%m-%d').year:
                        db.execute("UPDATE monthly_totals SET income = income - ? WHERE user_id = ? AND month = ? AND year = ?", amount, user_id, current_month, current_year)
            elif t_type == "expense":
                db.execute("UPDATE user_totals SET total_expenses = total_expenses - ? WHERE user_id = ?", amount, user_id)
                db.execute("UPDATE user_totals SET balance = balance + ? WHERE user_id = ?", amount, user_id)
                if current_month == datetime.strptime(date, '%Y-%m-%d').month and current_year == datetime.strptime(date, '%Y-%m-%d').year:
                    db.execute("UPDATE monthly_totals SET spent = spent - ? WHERE user_id = ? AND month = ? AND year = ?", amount, user_id, current_month, current_year)
            db.execute("DELETE FROM transactions WHERE id = ?", transaction_id)
            flash("Transaction deleted successfully!", "success")
        return redirect('/')
    else:
        return redirect('/')
@app.route('/edit-transaction/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    current_date = datetime.now()
    current_month = current_date.month
    current_year = current_date.year
    user_id = session.get("user_id")
    amount = float(request.form.get('amount'))
    if not amount:
        flash("Please provide an amount!", "danger")
        return redirect('/')
    if amount < 0:
        flash("Amount cannot be negative!", "danger")
        return redirect('/')
    category = request.form.get('category')
    if not category:
        flash("Please provide a category!", "danger")
        return redirect('/')
    transaction_type = request.form.get('transaction_type')
    if not transaction_type:
        flash("Please provide a transaction type!", "danger")
        return redirect('/')
    transaction_id = request.form.get('edit_transaction_id')
    date = request.form.get('date')
    if not date:
        flash("Please provide a date!", "danger")
        return redirect('/')
    current_transaction_dict = db.execute("SELECT * FROM transactions WHERE id = ? AND user_id = ?", transaction_id, user_id)
    current_transaction = current_transaction_dict[0]
    if request.method == 'POST':
        if current_transaction["amount"] != amount or current_transaction["category"] != category or current_transaction["transaction_type"] != transaction_type or current_transaction["date"] != date:
            db.execute("UPDATE transactions SET amount = ?, category = ?, transaction_type = ?, date= ? WHERE user_id = ? AND id = ?", amount, category, transaction_type, date, user_id, transaction_id)
            if transaction_type == "income":
                new = amount - current_transaction["amount"]
                if new > 0:
                    db.execute("UPDATE user_totals SET total_income = total_income + ? WHERE user_id = ?", new, user_id)
                    db.execute("UPDATE user_totals SET balance = balance + ? WHERE user_id = ?", new, user_id)
                    if current_month == datetime.strptime(date, '%Y-%m-%d').month and current_year == datetime.strptime(date, '%Y-%m-%d').year:
                        db.execute("UPDATE monthly_totals SET income = income + ? WHERE user_id = ? AND month = ? AND year = ?", new, user_id, current_month, current_year)
                if new < 0:
                    db.execute("UPDATE user_totals SET total_income = total_income - ? WHERE user_id = ?",abs(new), user_id)
                    db.execute("UPDATE user_totals SET balance = balance - ? WHERE user_id = ?", abs(new), user_id)
                    if current_month == datetime.strptime(date, '%Y-%m-%d').month and current_year == datetime.strptime(date, '%Y-%m-%d').year:
                        db.execute("UPDATE monthly_totals SET income = income - ? WHERE user_id = ? AND month = ? AND year = ?", new, user_id, current_month, current_year)
            elif transaction_type == "expense":
                new = amount - current_transaction["amount"]
                if new > 0:
                    db.execute("UPDATE user_totals SET total_expenses = total_expenses + ? WHERE user_id = ?", new, user_id)
                    db.execute("UPDATE user_totals SET balance = balance - ? WHERE user_id = ?", new, user_id)
                    if current_month == datetime.strptime(date, '%Y-%m-%d').month and current_year == datetime.strptime(date, '%Y-%m-%d').year:
                        db.execute("UPDATE monthly_totals SET spent = spent + ? WHERE user_id = ? AND month = ? AND year = ?", new, user_id, current_month, current_year)
                if new < 0:
                    db.execute("UPDATE user_totals SET total_expenses = total_expenses - ? WHERE user_id = ?", abs(new), user_id)
                    db.execute("UPDATE user_totals SET balance = balance + ? WHERE user_id = ?", abs(new), user_id)
                    if current_month == datetime.strptime(date, '%Y-%m-%d').month and current_year == datetime.strptime(date, '%Y-%m-%d').year:
                        db.execute("UPDATE monthly_totals SET spent = spent - ? WHERE user_id = ? AND month = ? AND year = ?", new, user_id, current_month, current_year)
            return redirect('/')
        flash("Transaction edited successfully!", "success")
        return redirect('/')
    else:
        return redirect('/')

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Please provide an username!", "danger")
            return redirect("/")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Please provide an password!", "danger")
            return redirect("/")

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("Invalid Username/Password!", "danger")
            return redirect("/")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        flash("Successfully logged in!", "success")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    flash("Successfully logged out!", "success")
    return redirect("/")
    

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        if not name:
            flash("Please provide a name!", "danger")
            return redirect("/register")
        email = request.form.get("email")
        if not email:
            flash("Please provide a email!", "danger")
            return redirect("/register")
        existing_emails = db.execute("SELECT * FROM users WHERE email = ?", email)
        if existing_emails:
            flash("Email already registered", "danger")
            return redirect("/register")
        dob = request.form.get("dob")
        username = request.form.get("username")
        if not username:
            flash("Please provide an username!", "danger")
            return redirect("/register")
        existing_usernames = db.execute("SELECT * FROM users WHERE username = ?", username)
        if existing_usernames:
            flash("Username already taken", "danger")
            return redirect("/register")
        password = request.form.get("password")
        if not password:
            flash("Please provide a password!", "danger")
            return redirect("/register")
        balance = request.form.get("balance")
        code = str(random.randint(100000, 999999))
        msg = Message('BudgetBuddy Verification Code', sender=formataddr(("BudgetBuddy", app.config['MAIL_USERNAME'])), recipients=[email])
        msg.body = f'Your verification code is: {code}'
        msg.html = render_template("reset_code.html", code=code)
        mail.send(msg)

        session["pending_user"] = {"name": name, "email": email, "dob": dob, "username": username, "password": password, "balance": balance}
        session["register_code"] = code
        session["register_mode"] = True
        session["register_time"] = time.time()
        return redirect("/verify_code")

    else:
        return render_template('register.html')
    
@app.route('/analysis')
@login_required
def analysis():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")
    transactions = db.execute("SELECT amount, category, transaction_type, date FROM transactions WHERE user_id = ?", user_id)
    if not transactions:
        flash("No transactions found, cannot analyse!", "danger")
        return redirect('/')
    df = pd.DataFrame(transactions)
    df['date'] = pd.to_datetime(df['date'])

    income_by_category = df[df['transaction_type'] == 'income'].groupby('category')['amount'].sum()
    expense_by_category = df[df['transaction_type'] == 'expense'].groupby('category')['amount'].sum()

    income_categories = income_by_category.index.tolist()
    income_values = income_by_category.values.tolist()

    expense_categories = expense_by_category.index.tolist()
    expense_values = expense_by_category.values.tolist()

    return render_template("analysis.html", income_categories=income_categories, income_values=income_values, expense_categories=expense_categories, expense_values=expense_values)

@app.route('/budget', methods=['GET', 'POST'])
@login_required
def set_budget():
    if request.method == 'POST':
        if "set_budget" in request.form:
            current_date = datetime.now()
            current_month = current_date.month
            current_year = current_date.year
            user_id = session.get("user_id")
            budget = request.form.get('budget')
            try:
                budget = float(budget)
            except ValueError:
                flash("Please provide a valid budget!", "danger")
                return redirect('/')
            if not budget:
                flash("Please provide a valid budget!", "danger")
                return redirect('/')
            if budget < 0:
                flash("Budget cannot be negative!", "danger")
                return redirect('/')
            if db.execute("SELECT * FROM monthly_totals WHERE user_id = ? AND month = ? AND year = ?", user_id, current_month, current_year):
                db.execute("UPDATE monthly_totals SET budget = ? WHERE user_id = ? AND month = ? AND year = ?", budget, user_id, current_month, current_year)
            else:
                db.execute("INSERT INTO monthly_totals (budget, month, year, user_id) VALUES (?, ?, ?, ?)", budget, current_month, current_year, user_id)
            flash("Budget set successfully!", "success")
            return redirect('/')
        elif "reset_budget" in request.form:
            current_date = datetime.now()
            current_month = current_date.month
            current_year = current_date.year
            user_id = session.get("user_id")
            rows = db.execute("SELECT * FROM monthly_totals WHERE user_id = ? AND month = ? AND year = ?", user_id, current_month, current_year)
            if rows[0]["budget"] == 0:
                flash("No budget set for this month!", "danger")
                return redirect('/')
            db.execute("UPDATE monthly_totals SET budget = 0 WHERE user_id = ? AND month = ? AND year = ?", user_id, current_month, current_year)
            flash("Budget reset successfully!", "success")
            return redirect('/')
    else:
        return redirect('/')
    
@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        hash_password = generate_password_hash(new_password)
        user_id = session.get("user_id")
        if not old_password:
            flash("Please provide old password", "danger")
            return redirect("/change_password")
        if not new_password:
            flash("Please provide new password", "danger")
            return redirect("/change_password")
        if not confirm_password:
            flash("Please provide confirmation password", "danger")
            return redirect("/change_password")
        if new_password != confirm_password:
            flash("Passwords don't match!", "danger")
            return redirect("/change_password")
        if old_password == new_password:
            flash("Old password and new password is the same!", "danger")
            return redirect("/change_password")
        hash_db_dict = db.execute("SELECT hash FROM users WHERE id = ?", user_id)
        hash_db = hash_db_dict[0]["hash"]
        if not check_password_hash(hash_db, old_password):
            flash("Old password entered is wrong!", "danger")
            return redirect("/change_password")
        db.execute("UPDATE users SET hash = ? WHERE id = ?", hash_password, user_id)
        flash("Password changed successfully!", "success")
        return redirect("/")
    else:
        return render_template("change_password.html")       
        
@app.route("/forget_password", methods=["GET", "POST"])
def forget_password():
    if request.method == 'POST':
        emails_dict = db.execute("SELECT email FROM users")
        current_emails = emails_dict[0]["email"]
        email = request.form.get("email")
        if email in current_emails:
            code = str(random.randint(100000, 999999))
            msg = Message('BudgetBuddy Verification Code', sender=formataddr(("BudgetBuddy", app.config['MAIL_USERNAME'])), recipients=[email])
            msg.body = f'Your verification code is: {code}'
            msg.html = render_template("reset_code.html", code=code)
            mail.send(msg)

            session["reset_email"] = email
            session["reset_code"] = code
            session["reset_time"] = time.time()
            return redirect("/verify_code")
        else:
            flash("Email not in our database!", "danger")
            return redirect("/forget_password")
    else:
        return render_template('forget_password.html')


@app.route("/verify_code", methods=["GET", "POST"])
def verify_code():
    email = session.get("reset_email") or (session["pending_user"]["email"] if "pending_user" in session else None)
    code = session.get("reset_code") or session.get("register_code")
    count = 0
    is_register = session.get("register_mode")
    if not email or not code:
        flash("Access denied." "danger")
        return redirect('/forget_password')
    register_time = session.get("register_time")
    reset_time = session.get("reset_time")
    if register_time and (time.time() - register_time > 600):
        session.clear()
        flash("Verification code expired. Please try registering again.", "danger")
        return redirect("/register")
    if reset_time and (time.time() - reset_time > 600):
        flash("Verification code expired. Please try request a new reset.", "danger")
        return redirect("/forget_password")
    if request.method == "POST":
        form_code = request.form.get("verification")
        if code == form_code:
            if is_register:
                user = session["pending_user"]
                hashed_pw = generate_password_hash(user["password"])
                db.execute("INSERT INTO users (name, email, date_of_birth, username, hash) VALUES (?, ?, ?, ?, ?)",
                           user["name"], user["email"], user["dob"], user["username"], hashed_pw)
                user_id = db.execute("SELECT id FROM users WHERE username = ?", user["username"])[0]["id"]
                db.execute("INSERT INTO user_totals (balance, user_id) VALUES (?, ?)", user["balance"], user_id)

                session.clear()
                flash("Registration successful! Please log in.", "success")
                return redirect("/login")               
            else:
                session["reset_status"] = True
                return redirect("/reset_password")
        else:
            while count < 1:
                count += 1
                flash("Wrong verification code entered", "danger")
                return redirect("/verify_code")
            flash("Wrong verification code entered", "danger")
            cleanup_verification()
            return redirect("/forget_password")
            

    else:
        return render_template("verify_code.html")

@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    status = session.get("reset_status")
    email = session.get("reset_email")
    code = session.get("reset_code")
    if not email or not code or not status == True:
        flash("Access denied", "danger")
        return redirect("/")
    if request.method == "POST":
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        hash_password = generate_password_hash(new_password)
        if not new_password or not confirm_password:
            flash("Please input new and confirmation password!", "danger")
            return redirect("/reset_password")
        if new_password != confirm_password:
            flash("New and confirmation password is not the same!", "danger")
            return redirect("/reset_password")
        db.execute("UPDATE users SET hash = ? WHERE email = ?", hash_password, email)
        flash("Password resetted successfully!", "success")
        cleanup_verification()
        return redirect("/")
    else:
        return render_template("reset_password.html")

    
