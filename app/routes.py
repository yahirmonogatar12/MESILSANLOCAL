import json
import os
from functools import wraps
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from .db import get_db_connection, init_db
import sqlite3

app = Flask(__name__)
app.secret_key = 'alguna_clave_secreta'  # Necesario para usar sesiones
init_db()  # Esto crea la tabla si no existe

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


# A continuación se definen las rutas para manejar las entradas de materiales aéreos
@app.route('/guardar_entrada_aereo', methods=['POST'])
def guardar_entrada_aereo():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO entrada_aereo (
            forma_material, cliente, codigo_material, fecha_fabricacion,
            origen_material, cantidad_actual, fecha_recibo, lote_material,
            codigo_recibido, numero_parte, propiedad
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (
            data.get('formaMaterial'),
            data.get('cliente'),
            data.get('codigoMaterial'),
            data.get('fechaFab'),
            data.get('origenMaterial'),
            data.get('cantidadActual'),
            data.get('fechaRecibo'),
            data.get('loteMaterial'),
            data.get('codRecibido'),
            data.get('numParte'),
            data.get('propiedad')
        )
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/listar_entradas_aereo')
def listar_entradas_aereo():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM entrada_aereo ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    resultado = [dict(r) for r in rows]
    return jsonify(resultado)

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'database', 'ISEMM_MES.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
