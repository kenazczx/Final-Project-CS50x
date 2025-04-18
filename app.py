from flask import Flask, render_template, request, redirect, session, flash, jsonify
from flask_session import Session
from cs50 import SQL
''' from geopy.geocoders import Nominatim -> for location in the future '''
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
import calendar

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
        amount = request.form.get('amount')
        if not amount:
            flash("Please provide an amount!", "danger")
            return redirect('/transactions')
        try:
            amount = float(amount)
        except ValueError:
            flash("Enter a valid amount!", "danger")
            return redirect('/transactions')
        amount = float(amount)   
        if amount < 0:
            flash("Amount cannot be negative!", "danger")
            return redirect('/transactions')   
        category_initial = request.form.get('category')
        if not category_initial:
            flash("Please provide a category!", "danger")
            return redirect('/transactions')
        if category_initial == "others":
            category = request.form.get('custom_category')
        else:
            category = category_initial
        if not re.match("^[A-Za-z &-]+$", category.strip()):
            flash("Category can only include letters, spaces, dashes, and '&'.", "danger")
            return redirect('/transactions')
        transaction_type = request.form.get('transaction_type')
        if not transaction_type:
            flash("Please provide a transaction type!", "danger")
            return redirect('/transactions')
        date = request.form.get('date')
        if not date:
            flash("Please provide a date!", "danger")
            return redirect('/transactions')
        formatted_date = datetime.strptime(date, '%Y-%m-%d').date()
        formatted_month = formatted_date.month
        formatted_year = formatted_date.year
        db.execute("INSERT INTO transactions (user_id, amount, category, transaction_type, date) VALUES (?, ?, ?, ?, ?)", user_id, amount, category, transaction_type, date)
        if transaction_type == "income":
            db.execute("UPDATE user_totals SET total_income = total_income + ? WHERE user_id = ?", amount, user_id)
            db.execute("UPDATE user_totals SET balance = balance + ? WHERE user_id = ?", amount, user_id)
            # TODO: Add income amount for transaction's month, year into monthly totals
            # TODO: Check if exists
            rows = db.execute("SELECT * FROM monthly_totals WHERE user_id = ? AND month = ? and year = ?", user_id, formatted_month, formatted_year)
            if len(rows) != 1:
                db.execute("INSERT INTO monthly_totals (user_id, income, month, year) VALUES (?, ?, ?, ?)", user_id, amount, formatted_month, formatted_year)
            else:
                db.execute("UPDATE monthly_totals SET income = income + ? WHERE user_id = ? AND month = ? AND year = ?", amount, user_id, formatted_month, formatted_year)
        elif transaction_type == "expense":
            db.execute("UPDATE user_totals SET total_expenses = total_expenses + ? WHERE user_id = ?", amount, user_id)
            db.execute("UPDATE user_totals SET balance = balance - ? WHERE user_id = ?", amount, user_id)
            # TODO: Add expense amount for transaction's month, year into monthly totals
            # TODO: Check if exists
            rows = db.execute("SELECT * FROM monthly_totals WHERE user_id = ? AND month = ? and year = ?", user_id, formatted_month, formatted_year)
            if len(rows) != 1:
                db.execute("INSERT INTO monthly_totals (user_id, spent, month, year) VALUES (?, ?, ?, ?)", user_id, amount, formatted_month, formatted_year)
            else:
                db.execute("UPDATE monthly_totals SET spent = spent + ? WHERE user_id = ? AND month = ? AND year = ?", amount, user_id, formatted_month, formatted_year)
        flash("Transaction added successfully!", "success")
        return redirect('/transactions')
    else:
        return redirect('/transactions')

@app.route('/delete_transaction', methods=['GET', 'POST'])
@login_required
def delete_transaction():
    if request.method == 'POST':
        user_id = session.get("user_id")
        transaction_id = request.form.get('transaction_id')
        transaction = db.execute("SELECT * FROM transactions WHERE id = ?", transaction_id)
        if transaction:
            trans = transaction[0]
            trans_date = datetime.strptime(trans["date"], '%Y-%m-%d').date()
            trans_month = trans_date.month
            trans_year = trans_date.year
            amount = float(trans["amount"])
            t_type = trans["transaction_type"]
            if t_type == "income":
                db.execute("UPDATE user_totals SET total_income = total_income - ? WHERE user_id = ?", amount, user_id)
                db.execute("UPDATE user_totals SET balance = balance - ? WHERE user_id = ?", amount, user_id)
                # TODO: Remove amount from the transaction's month monthly totals
                db.execute("UPDATE monthly_totals SET income = income - ? WHERE user_id = ? AND month = ? AND year = ?", amount, user_id, trans_month, trans_year)
            elif t_type == "expense":
                db.execute("UPDATE user_totals SET total_expenses = total_expenses - ? WHERE user_id = ?", amount, user_id)
                db.execute("UPDATE user_totals SET balance = balance + ? WHERE user_id = ?", amount, user_id)
                # TODO: Remove amount from the transaction's month monthly totals
                db.execute("UPDATE monthly_totals SET spent = spent - ? WHERE user_id = ? AND month = ? AND year = ?", amount, user_id, trans_month, trans_year)
            db.execute("DELETE FROM transactions WHERE id = ?", transaction_id)
            flash("Transaction deleted successfully!", "success")
        return redirect('/transactions')
    else:
        return redirect('/transactions')
@app.route('/edit-transaction/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    user_id = session.get("user_id")
    amount = float(request.form.get('amount'))
    if not amount:
        flash("Please provide an amount!", "danger")
        return redirect('/transactions')
    if amount < 0:
        flash("Amount cannot be negative!", "danger")
        return redirect('/transactions')
    category = request.form.get('category')
    if not category:
        flash("Please provide a category!", "danger")
        return redirect('/transactions')
    transaction_type = request.form.get('transaction_type')
    if not transaction_type:
        flash("Please provide a transaction type!", "danger")
        return redirect('/transactions')
    transaction_id = request.form.get('edit_transaction_id')
    date = request.form.get('date')
    if not date:
        flash("Please provide a date!", "danger")
        return redirect('/transactions')
    current_transaction_dict = db.execute("SELECT * FROM transactions WHERE id = ? AND user_id = ?", transaction_id, user_id)
    current_transaction = current_transaction_dict[0]
    stored_date = datetime.strptime(current_transaction["date"], '%Y-%m-%d').date()
    stored_month = stored_date.month
    stored_year = stored_date.year
    new_date = datetime.strptime(date, '%Y-%m-%d').date()
    new_month = new_date.month
    new_year = new_date.year
    if request.method == 'POST':
        if current_transaction["amount"] != amount or current_transaction["category"] != category or current_transaction["transaction_type"] != transaction_type or current_transaction["date"] != date:
            db.execute("UPDATE transactions SET amount = ?, category = ?, transaction_type = ?, date= ? WHERE user_id = ? AND id = ?", amount, category, transaction_type, date, user_id, transaction_id)
            if transaction_type == "income":
                new = amount - current_transaction["amount"]
                db.execute("UPDATE user_totals SET total_income = total_income + ? WHERE user_id = ?", new, user_id)
                db.execute("UPDATE user_totals SET balance = balance + ? WHERE user_id = ?", new, user_id)
                if stored_date != new_date or stored_month != new_month or stored_year != stored_year:
                    # TODO: Remove from transaction from old month's total
                    db.execute("UPDATE monthly_totals SET income = income - ? WHERE user_id = ? AND month = ? AND year = ?", current_transaction["amount"], user_id, stored_month, stored_year)
                    # TODO: Add transaction to new month's total
                    # TODO: Check if monthly_totals for that month already exists
                    rows = db.execute("SELECT * FROM monthly_totals WHERE user_id = ? AND month = ? and year = ?", user_id, new_month, new_year)
                    if len(rows) != 1:
                        db.execute("INSERT INTO monthly_totals (user_id, income, month, year) VALUES (?, ?, ?, ?)", user_id, amount, new_month, new_year)
                    else:
                        db.execute("UPDATE monthly_totals SET income = income + ? WHERE user_id = ? AND month = ? AND year = ?", amount, user_id, new_month, new_year)
            elif transaction_type == "expense":
                new = amount - current_transaction["amount"]
                db.execute("UPDATE user_totals SET total_expenses = total_expenses + ? WHERE user_id = ?", new, user_id)
                db.execute("UPDATE user_totals SET balance = balance - ? WHERE user_id = ?", new, user_id)
                if stored_date != new_date or stored_month != new_month or stored_year != new_year:
                    # TODO: Remove from transaction from old month's total
                    db.execute("UPDATE monthly_totals SET spent = spent - ? WHERE user_id = ? AND month = ? AND year = ?", current_transaction["amount"], user_id, stored_month, stored_year)
                    # TODO: Add transaction to new month's total
                    # TODO: Check if monthly_totals for that month already exists
                    rows = db.execute("SELECT * FROM monthly_totals WHERE user_id = ? AND month = ? and year = ?", user_id, new_month, new_year)
                    if len(rows) != 1:
                        db.execute("INSERT INTO monthly_totals (user_id, spent, month, year) VALUES (?, ?, ?, ?)", user_id, amount, new_month, new_year)
                    else:
                        db.execute("UPDATE monthly_totals SET spent = spent + ? WHERE user_id = ? AND month = ? AND year = ?", amount, user_id, new_month, new_year)
            flash("Transaction edited successfully!", "success")
            return redirect('/transactions')
        else:
            flash("No changes made to transaction!", "success")
            return redirect('/transactions')
    else:
        return redirect('/transactions')

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
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_regex, email):
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
            flash("Submit a valid email", "danger")
            return redirect("/register")

    else:
        return render_template('register.html')

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
        email_dict = db.execute("SELECT email FROM users WHERE id = ?", user_id)
        email = email_dict[0]["email"]
        code = str(random.randint(100000, 999999))
        msg = Message('BudgetBuddy Verification Code', sender=formataddr(("BudgetBuddy", app.config['MAIL_USERNAME'])), recipients=[email])
        msg.body = f'Your verification code is: {code}'
        msg.html = render_template("reset_code.html", code=code)
        mail.send(msg)

        session["change_email"] = email
        session["new_password"] = new_password
        session["change_code"] = code
        session["change_mode"] = True
        session["change_time"] = time.time()        
        return redirect("/verify_code")
    else:
        return render_template("change_password.html")       
        
@app.route("/forget_password", methods=["GET", "POST"])
def forget_password():
    if request.method == 'POST':
        emails_dict = db.execute("SELECT email FROM users")
        current_emails = [email["email"] for email in emails_dict]
        email = request.form.get("email")
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_regex, email):
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
            flash("Invalid email format!", "danger")
            return redirect("/forget_password")
    else:
        return render_template('forget_password.html')


@app.route("/verify_code", methods=["GET", "POST"])
def verify_code():
    email = session.get("reset_email") or (session["pending_user"]["email"] if "pending_user" in session else None) or session.get("change_email")
    code = session.get("reset_code") or session.get("register_code") or session.get("change_code")
    count = 0
    is_register = session.get("register_mode")
    is_change = session.get("change_mode")
    if not email or not code:
        flash("Access denied." "danger")
        return redirect('/forget_password')
    register_time = session.get("register_time")
    reset_time = session.get("reset_time")
    change_time = session.get("change_time")
    if register_time and (time.time() - register_time > 600):
        session.clear()
        flash("Verification code expired. Please try registering again.", "danger")
        return redirect("/register")
    if reset_time and (time.time() - reset_time > 600):
        flash("Verification code expired. Please try request a new reset.", "danger")
        return redirect("/forget_password")
    if change_time and (time.time() - change_time > 600):
        cleanup_verification()
        flash("Verification code expired. Please request to change password again.", "danger")
        return redirect("/change_password")
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
            elif is_change:
                new_password = session.get("new_password")
                hash_password = generate_password_hash(new_password)
                user_id_dict = db.execute("SELECT id FROM users WHERE email = ?", email)
                user_id = user_id_dict[0]["id"]
                db.execute("UPDATE users SET hash = ? WHERE id = ?", hash_password, user_id)
                flash("Password changed successfully!", "success")
                return redirect("/")             
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

@app.route("/transactions")
@login_required
def transactions():
    user_id = session.get("user_id")

    start = request.args.get("start")
    end = request.args.get("end")
    trans_type = request.args.get("type")
    category = request.args.get("category")

    query = "SELECT id, amount, category, transaction_type, date FROM transactions WHERE user_id = ?"
    params = [user_id]

    if start:
        query += " AND date >= ?"
        params.append(start)
    if end:
        query += " AND date <= ?"
        params.append(end)
    if trans_type and trans_type != "all":
        query += " AND transaction_type = ?"
        params.append(trans_type)
    if category:
        query += " AND category LIKE ?"
        params.append(category)
    
    query += " ORDER BY date DESC"
    transactions = db.execute(query, *params)
    today_str = datetime.today().date().isoformat()
    today = datetime.today().date()
    year = today.year
    month = today.month
    _, last_day = calendar.monthrange(2025, 4) # _, means ignore the first value since calender returns (weekday of firstday, number of days in the month)
    start_of_month = today.replace(day=1)
    end_of_month = today.replace(day=last_day)
    return render_template("transactions.html", transactions=transactions, today=today_str, start_of_month=start_of_month, end_of_month=end_of_month)

    
@app.route('/transaction-analysis')
def transaction_analysis():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 403

    # Filters from query params
    start_date = request.args.get("start")
    end_date = request.args.get("end")
    trans_type = request.args.get("type")  # 'income', 'expense', or 'all'

    query = "SELECT * FROM transactions WHERE user_id = ?"
    params = [user_id]

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    if trans_type and trans_type != 'all':
        query += " AND transaction_type = ?"
        params.append(trans_type)

    transactions = db.execute(query, *params)
    df = pd.DataFrame(transactions)

    income_by_category = {}
    expense_by_category = {}
    income_by_month = {}
    expense_by_month = {}

    # Process transactions if they exist
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.to_period('M').astype(str)

        if trans_type != 'expense':
            income_df = df[df['transaction_type'] == 'income']
            income_by_category = income_df.groupby('category')['amount'].sum().to_dict()
            income_by_month = income_df.groupby('month')['amount'].sum().to_dict()

        if trans_type != 'income':
            expense_df = df[df['transaction_type'] == 'expense']
            expense_by_category = expense_df.groupby('category')['amount'].sum().to_dict()
            expense_by_month = expense_df.groupby('month')['amount'].sum().to_dict()

    return jsonify({
        "income_by_category": income_by_category,
        "expense_by_category": expense_by_category,
        "income_by_month": income_by_month,
        "expense_by_month": expense_by_month
    })