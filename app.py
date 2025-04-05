from flask import Flask, render_template, request, redirect, session, flash, jsonify
from flask_session import Session
from cs50 import SQL
from geopy.geocoders import Nominatim
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required
from datetime import datetime
import pandas as pd
import time

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['ENV'] = 'development'
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
    default_income_categories = ["Salary", "Business", "Investment", "Rental"]
    default_expense_categories = ["Food", "Transport", "Entertainment", "Utilities"]
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")
    total_income = db.execute("SELECT total_income FROM user_totals WHERE user_id = ?", user_id)
    total_expenses = db.execute("SELECT total_expenses FROM user_totals WHERE user_id = ?", user_id)
    balance = db.execute("SELECT balance FROM user_totals WHERE user_id = ?", user_id)
    transactions = db.execute("SELECT id, amount, category, transaction_type, date FROM transactions WHERE user_id = ? ORDER BY date DESC", user_id)
    transaction_type = request.args.get("transaction_type", None)
    categories = []
    if transaction_type == "income":
        income_categories = db.execute("SELECT DISTINCT category FROM transactions WHERE user_id = ? AND transaction_type = 'income'", user_id)
        categories = default_income_categories + [row["category"] for row in income_categories]
    elif transaction_type == "expense":
        expense_categories = db.execute("SELECT DISTINCT category FROM transactions WHERE user_id = ? AND transaction_type = 'expense'", user_id)
        categories = default_expense_categories + [row["category"] for row in expense_categories]
    # Current Date
    return render_template("index.html", total_income=total_income[0]["total_income"], total_expenses=total_expenses[0]["total_expenses"], balance=balance[0]["balance"], transactions=transactions, transaction_type=transaction_type, categories=categories)
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
        amount = float(request.form.get('amount'))
        if not amount:
            flash("Please provide an amount!", "danger")
            return redirect('/')
        category_initial = request.form.get('category')
        if not category_initial:
            flash("Please provide a category!", "danger")
            return redirect('/')
        if category_initial == "others":
            category = request.form.get('custom_category')
        else:
            category = category_initial
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
        elif transaction_type == "expense":
            db.execute("UPDATE user_totals SET total_expenses = total_expenses + ? WHERE user_id = ?", amount, user_id)
            db.execute("UPDATE user_totals SET balance = balance - ? WHERE user_id = ?", amount, user_id)
        flash("Transaction added successfully!", "success")
        return redirect('/')
    else:
        return redirect('/')

@app.route('/delete_transaction', methods=['GET', 'POST'])
@login_required
def delete_transaction():
    if request.method == 'POST':
        user_id = session.get("user_id")
        transaction_id = request.form.get('transaction_id')
        transaction = db.execute("SELECT * FROM transactions WHERE id = ?", transaction_id)
        if transaction:
            trans = transaction[0]
            amount = float(trans["amount"])
            t_type = trans["transaction_type"]
            if t_type == "income":
                db.execute("UPDATE user_totals SET total_income = total_income - ? WHERE user_id = ?", amount, user_id)
                db.execute("UPDATE user_totals SET balance = balance - ? WHERE user_id = ?", amount, user_id)
            elif t_type == "expense":
                db.execute("UPDATE user_totals SET total_expenses = total_expenses - ? WHERE user_id = ?", amount, user_id)
                db.execute("UPDATE user_totals SET balance = balance + ? WHERE user_id = ?", amount, user_id)
            db.execute("DELETE FROM transactions WHERE id = ?", transaction_id)
            flash("Transaction deleted successfully!", "success")
        return redirect('/')
    else:
        return redirect('/')
@app.route('/edit-transaction/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    user_id = session.get("user_id")
    amount = float(request.form.get('amount'))
    if not amount:
        flash("Please provide an amount!", "danger")
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
                if new < 0:
                    db.execute("UPDATE user_totals SET total_income = total_income - ? WHERE user_id = ?",abs(new), user_id)
                    db.execute("UPDATE user_totals SET balance = balance - ? WHERE user_id = ?", abs(new), user_id)
            elif transaction_type == "expense":
                new = amount - current_transaction["amount"]
                if new > 0:
                    db.execute("UPDATE user_totals SET total_expenses = total_expenses + ? WHERE user_id = ?", new, user_id)
                    db.execute("UPDATE user_totals SET balance = balance - ? WHERE user_id = ?", new, user_id)
                if new < 0:
                    db.execute("UPDATE user_totals SET total_expenses = total_expenses - ? WHERE user_id = ?", abs(new), user_id)
                    db.execute("UPDATE user_totals SET balance = balance + ? WHERE user_id = ?", abs(new), user_id)
            return redirect('/')
        flash("Transaction edited successfully!", "success")
        return redirect('/')
    else:
        return redirect('/')

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id

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
        try:
            email = request.form.get("email")
            if not email:
                flash("Please provide a email!", "danger")
                return redirect("/register")
        except ValueError:
            return flash("Email already registered", "danger")
        dob = request.form.get("dob")
        try:
            username = request.form.get("username")
            if not username:
                flash("Please provide an username!", "danger")
                return redirect("/register")
        except ValueError:
                flash("Username already taken!", "danger")
                return redirect("/register")
        password = request.form.get("password")
        if not password:
            return flash("Please provide a password!", "danger")
        hash = generate_password_hash(password)
        balance = request.form.get("balance")
        db.execute("INSERT INTO users (name, email, date_of_birth, username, hash) VALUES (?, ?, ?, ?, ?)", name, email, dob, username, hash)
        user = db.execute("SELECT id FROM users WHERE username = ?", username)
        user_id = user[0]["id"]
        db.execute("INSERT INTO user_totals (balance, user_id) VALUES (?, ?)", balance, user_id)
        return redirect("/")

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