from flask import Flask, request, render_template, redirect, url_for

app = Flask(__name__)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username', '').strip()
        pw = request.form.get('password', '')
        if (user == "Materiales01" and pw == "Materiales2025") or \
           (user == "1111" and pw == "1111"):
            return redirect(url_for('material'))
        return render_template('login.html', error="Usuario o contraseña incorrectos. Por favor, intente de nuevo")
    
    # ✅ Para método GET, simplemente mostrar el formulario:
    return render_template('login.html')

@app.route('/Materiales')
def material():
    return render_template('MaterialTemplate.html')
