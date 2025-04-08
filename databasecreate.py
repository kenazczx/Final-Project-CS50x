import sqlite3

# Path to the database file
db_file = 'budget_tracker.db'

# Connect to the database (it will create the file if it doesn't exist)
conn = sqlite3.connect(db_file)

# Create a cursor object to execute SQL queries
cursor = conn.cursor()

# SQL queries to create tables
create_users_table = '''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    hash TEXT NOT NULL,  
    email TEXT NOT NULL UNIQUE,  
    income REAL NOT NULL DEFAULT 0,
    name TEXT NOT NULL,  
    date_of_birth DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  
);
'''

create_income_table = '''
CREATE TABLE IF NOT EXISTS income (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
'''

create_expenses_table = '''
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
'''

create_user_totals_table = '''
CREATE TABLE IF NOT EXISTS user_totals (
    user_id INTEGER PRIMARY KEY,
    total_income REAL NOT NULL DEFAULT 0,
    total_expenses REAL NOT NULL DEFAULT 0,
    balance REAL NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
'''

# Execute the SQL queries to create the tables
cursor.execute(create_users_table)
cursor.execute(create_income_table)
cursor.execute(create_expenses_table)
cursor.execute(create_user_totals_table)

# Commit the transaction
conn.commit()

# Close the connection
conn.close()

print(f"Database {db_file} created with tables: users, income, expenses, user_totals")