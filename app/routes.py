from flask import Flask, request, render_template, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'alguna_clave_secreta'  # Necesario para usar sesiones

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
            session['usuario'] = user  # Guardar usuario en sesión
            return redirect(url_for('material'))
        # Verificar credenciales para Producción
        if (user == "Produccion01" and pw == "Produccion2025") or \
           (user == "2222" and pw == "2222"):
            session['usuario'] = user  # Guardar usuario en sesión
            return redirect(url_for('produccion'))
        
        return render_template('login.html', error="Usuario o contraseña incorrectos. Por favor, intente de nuevo")
    
    return render_template('login.html')

@app.route('/Materiales')
def material():
    usuario = session.get('usuario', 'Invitado')
    return render_template('MaterialTemplate.html', usuario=usuario)

@app.route('/produccion')
def produccion():
    usuario = session.get('usuario', 'Invitado')
    return render_template('ProduccionTemplate.html', usuario=usuario)
