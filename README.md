# BudgetBuddy
#### Video Demo:  <URL HERE>
#### Description:

## Features 

- 🔐 **User Authentication**
  - Secure registration and login
  - Password hashing with Flask’s `werkzeug.security`
  - Email-based verification for registration, password reset, and password change

- 📊 **Financial Dashboard**
  - View **lifetime income**, **expenses**, and **current balance**
  - Track **monthly income, spending, and budget**
  - Dynamic progress bar to visualize budget usage
  - Real-time clock display using `/get_time`

- 💸 **Transaction Management**
  - Add, edit, and delete transactions
  - Income and expense categorization (with default and custom categories)
  - Smart UI toggle for custom category input
  - Filter transactions by start/end date, transaction type and category

- 📈 **Spending Analysis**
  - **Interactive charts powered by Chart.js**
  - Income & Expense breakdown by category 
  - Income & Expense break down by month
  - Filter data shown by month, start/end date and transaction type
  - Data processed and grouped using `pandas`

- 💰 **Monthly Budget Control**
  - Set/reset monthly budgets
  - Automatically shows remaining amount vs total

- 📧 **Email Integration**
  - Email verification and password reset via `Flask-Mail`
  - Code-based 2-step password change mechanism

- 🔐 **Security and Session Management**
  - Session-based login using Flask sessions
  - Time-limited verification codes via `itsdangerous`
  - Form validation and basic input sanitation (e.g., regex for categories)

- 🧰 **Tech Stack**
  - **Backend:** Flask, CS50 SQL (SQLite), Python
  - **Frontend:** HTML, Bootstrap, Jinja2, JavaScript, Chart.js
  - **Libraries:** Flask-Mail, dotenv, pandas, itsdangerous, datetime, os, calender, re
 
## Screenshots

- Coming soon
