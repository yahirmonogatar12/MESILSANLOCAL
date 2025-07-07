import json
import os
from functools import wraps
from flask import Flask, request, render_template, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'alguna_clave_secreta'  # Necesario para usar sesiones

def cargar_usuarios():
    ruta = os.path.join(os.path.dirname(__file__), 'database', 'usuarios.json')
    ruta = os.path.abspath(ruta)
    with open(ruta, 'r', encoding='utf-8') as f:
        return json.load(f)

def login_requerido(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        print("Verificando sesión:", session.get('usuario'))
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorada

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username', '').strip()
        pw = request.form.get('password', '')
        usuarios = cargar_usuarios()
        if user in usuarios and usuarios[user] == pw:
            session['usuario'] = user
            # Redirige según el usuario
            if user.startswith("Materiales") or user == "1111":
                return redirect(url_for('material'))
            elif user.startswith("Produccion") or user == "2222":
                return redirect(url_for('produccion'))
            # Puedes agregar más roles aquí si lo necesitas
        return render_template('login.html', error="Usuario o contraseña incorrectos. Por favor, intente de nuevo")
    return render_template('login.html')

@app.route('/Materiales')
@login_requerido
def material():
    usuario = session.get('usuario', 'Invitado')
    return render_template('MaterialTemplate.html', usuario=usuario)

@app.route('/produccion')
@login_requerido
def produccion():
    usuario = session.get('usuario', 'Invitado')
    return render_template('ProduccionTemplate.html', usuario=usuario)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))
