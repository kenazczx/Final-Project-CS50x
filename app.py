from flask import Flask, render_template, request, redirect
from fetch_restaurants import fetch_restaurants

app = Flask(__name__)

# Route for the home page
@app.route('/')
def home():
    return render_template('index.html')