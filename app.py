from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_session import Session
from cs50 import SQL
from geopy.geocoders import Nominatim
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Route for the home page
@app.route('/')
def home():
    return render_template('index.html')