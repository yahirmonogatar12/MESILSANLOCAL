from flask import render_template, redirect, url_for, Flask

app = Flask(__name__)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/material')
def material():
    return render_template('MaterialTemplate.html')
