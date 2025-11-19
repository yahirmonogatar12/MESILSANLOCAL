import json
import os
import re
import traceback
import tempfile
import subprocess
import threading
import socket
import time

# Intentar importar MySQLdb, si no está disponible usar PyMySQL como alternativa
try:
    import MySQLdb
except ImportError:
    import pymysql
    pymysql.install_as_MySQLdb()
    import MySQLdb

from datetime import datetime, date, time as dt_time, timedelta
from functools import wraps

def obtener_fecha_hora_mexico():
    """Obtener fecha y hora actual en zona horaria de México (GMT-6)"""
    try:
        # Calcular hora de México Central (GMT-6)
        utc_now = datetime.utcnow()
        mexico_time = utc_now - timedelta(hours=6)
        return mexico_time
    except Exception as e:
        # Fallback a hora local
        return datetime.now()

from flask import Flask, request, render_template, redirect, url_for, session, jsonify, send_file, send_from_directory
from .db import (get_db_connection, init_db, test_database_connection,
                agregar_entrada_aereo, obtener_entradas_aereo,
                agregar_control_material_almacen, obtener_control_material_almacen,
                migrar_datos_sqlite)
from .db_mysql import (
    execute_query, obtener_materiales, guardar_material,
    obtener_inventario, actualizar_inventario,
    obtener_bom_por_modelo, guardar_bom_item, obtener_modelos_bom as obtener_modelos_bom_db,
    listar_bom_por_modelo, insertar_bom_desde_dataframe,
    guardar_configuracion, cargar_configuracion, actualizar_material_completo
)
import pandas as pd
from werkzeug.utils import secure_filename

# Importar sistema de autenticación mejorado
from .auth_system import AuthSystem
from .user_admin import user_admin_bp
from .admin_api import admin_bp

# Importar modelos y funciones PO → WO
from .po_wo_models import (
    crear_tablas_po_wo, validar_codigo_po, validar_codigo_wo,
    generar_codigo_po, generar_codigo_wo, verificar_po_existe, verificar_wo_existe,
    obtener_po_por_codigo, obtener_wo_por_codigo, listar_pos_por_estado, listar_pos_con_filtros, listar_wos_por_po, listar_wos_con_filtros
)
from .api_po_wo import registrar_rutas_po_wo
from .api_raw_modelos import api_raw
from .smd_inventory_api import register_smd_inventory_routes

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback_key_for_development_only')  # Necesario para usar sesiones

# Registrar rutas SMD Inventory después de crear la app
register_smd_inventory_routes(app)

# Registrar rutas API PO → WO
# registrar_rutas_po_wo(app)  # Comentado para evitar conflicto con run.py

# Registrar API RAW (modelos desde tabla raw) si no está ya registrado
try:
    if 'api_raw' not in app.blueprints:
        app.register_blueprint(api_raw)
        print(" API RAW (part_no) registrado en app.routes")
except Exception as e:
    print(f"Error registrando API RAW en app.routes: {e}")

# Inicializar base de datos original
init_db()  # Esto crea la tabla si no existe

# Inicializar sistema de autenticación
auth_system = AuthSystem()
auth_system.init_database()

# Registrar Blueprints de administración

# SMT Routes Simple
try:
    from .smt_routes_date_fixed import smt_bp
    app.register_blueprint(smt_bp)
    print(" SMT Routes Simple registradas")
except Exception as e:
    print(f"❌ Error importando SMT Routes Simple: {e}")

@app.route("/smt-simple")
def smt_simple():
    """Página SMT simple sin filtros complicados"""
    return render_template("smt_simple.html")

app.register_blueprint(user_admin_bp, url_prefix='/admin')
app.register_blueprint(admin_bp)

def requiere_permiso_dropdown(pagina, seccion, boton):
    """Decorador para verificar permisos específicos de dropdowns"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario' not in session:
                return jsonify({'error': 'Usuario no autenticado', 'redirect': '/login'}), 401
            
            try:
                username = session['usuario']
                print(f"🔐 Verificando permisos para usuario: {username}, página: {pagina}, sección: {seccion}, botón: {boton}")
                
                # Obtener roles del usuario
                query_rol = '''
                    SELECT r.nombre
                    FROM usuarios_sistema u
                    JOIN usuario_roles ur ON u.id = ur.usuario_id
                    JOIN roles r ON ur.rol_id = r.id
                    WHERE u.username = %s AND u.activo = 1 AND r.activo = 1
                    ORDER BY r.nivel DESC
                    LIMIT 1
                '''
                
                usuario_rol = execute_query(query_rol, (username,), fetch='one')
                print(f"🔍 Resultado query_rol: {usuario_rol}, tipo: {type(usuario_rol)}")
                
                if not usuario_rol:
                    print("❌ Usuario sin roles asignados")
                    return jsonify({'error': 'Usuario sin roles asignados'}), 403
                
                # Manejar tanto diccionarios como tuplas
                if isinstance(usuario_rol, dict):
                    rol_nombre = usuario_rol['nombre']
                else:
                    rol_nombre = usuario_rol[0]
                    
                print(f"👤 Rol del usuario: {rol_nombre}")
                
                # AHORA TODOS LOS ROLES (incluido superadmin) verifican permisos en base de datos
                # Verificar permiso específico
                query_permiso = '''
                    SELECT COUNT(*) FROM usuarios_sistema u
                    JOIN usuario_roles ur ON u.id = ur.usuario_id
                    JOIN rol_permisos_botones rpb ON ur.rol_id = rpb.rol_id
                    JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
                    WHERE u.username = %s AND pb.pagina = %s AND pb.seccion = %s AND pb.boton = %s
                    AND u.activo = 1 AND pb.activo = 1
                '''
                
                result = execute_query(query_permiso, (username, pagina, seccion, boton), fetch='one')
                print(f"🔍 Resultado query_permiso: {result}, tipo: {type(result)}")
                
                # Manejar tanto diccionarios como tuplas
                if isinstance(result, dict):
                    count_value = result.get('COUNT(*)', 0) or result.get('count', 0) or list(result.values())[0] if result else 0
                else:
                    count_value = result[0] if result else 0
                    
                tiene_permiso = count_value > 0
                print(f" Tiene permiso: {tiene_permiso} (count: {count_value})")
                
                if not tiene_permiso:
                    print(f"❌ Sin permisos para: {pagina} > {seccion} > {boton}")
                    # Respuesta diferente para AJAX vs navegación directa
                    if request.headers.get('Content-Type') == 'application/json' or request.is_json:
                        return jsonify({
                            'error': f'No tienes permisos para acceder a: {boton}',
                            'permiso_requerido': f'{pagina} > {seccion} > {boton}'
                        }), 403
                    else:
                        # Para carga AJAX de HTML, devolver mensaje de error
                        return f"""
                        <div style="
                            display: flex; 
                            flex-direction: column; 
                            align-items: center; 
                            justify-content: center; 
                            height: 400px; 
                            background: #2c2c2c; 
                            color: #e0e0e0; 
                            border-radius: 10px; 
                            margin: 20px;
                            text-align: center;
                        ">
                            <i class="fas fa-lock" style="font-size: 3rem; color: #dc3545; margin-bottom: 20px;"></i>
                            <h3>Acceso Denegado</h3>
                            <p>No tienes permisos para acceder a: <strong>{boton}</strong></p>
                            <p style="font-size: 0.9rem; opacity: 0.7;">Permiso requerido: {pagina} > {seccion} > {boton}</p>
                        </div>
                        """, 403
                
                print(f" Permisos verificados correctamente, ejecutando función...")
                return f(*args, **kwargs)
                
            except Exception as e:
                print(f"❌ Error verificando permisos: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'error': 'Error interno del servidor'}), 500
        
        return decorated_function
    return decorator

# Filtros de Jinja2 para permisos de botones
@app.template_filter('tiene_permiso_boton')
def tiene_permiso_boton(nombre_boton):
    """Filtro para verificar si el usuario actual tiene permiso para un botón específico"""
    try:
        # Obtener el usuario de la sesión actual
        if 'username' not in session:
            return False
        
        username = session['username']
        
        # Verificar si el usuario es superadmin (acceso total)
        query_usuario = 'SELECT departamento FROM usuarios_sistema WHERE username = %s'
        usuario = execute_query(query_usuario, (username,), fetch='one')
        
        if not usuario:
            return False
            
        if usuario[0] == 'superadmin':
            return True
        
        # Verificar permiso específico del botón
        query_permiso = '''
            SELECT 1 FROM usuarios_sistema u
            JOIN usuario_roles ur ON u.id = ur.usuario_id
            JOIN roles r ON ur.rol_id = r.id
            JOIN rol_permisos_botones rpb ON r.id = rpb.rol_id
            JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
            WHERE u.username = %s AND pb.boton = %s AND pb.activo = 1
            LIMIT 1
        '''
        
        resultado = execute_query(query_permiso, (username, nombre_boton), fetch='one')
        
        return resultado is not None
        
    except Exception as e:
        print(f"Error verificando permiso de botón '{nombre_boton}': {e}")
        return False

@app.template_filter('permisos_botones_pagina')
def permisos_botones_pagina(usuario, pagina):
    """Filtro para obtener todos los permisos de botones de una página"""
    if not usuario:
        return {}
    return auth_system.obtener_permisos_botones_usuario(usuario, pagina)

# DEPRECADO: Función antigua para compatibilidad temporal
def cargar_usuarios():
    """Función deprecada - se mantiene para compatibilidad"""
    ruta = os.path.join(os.path.dirname(__file__), 'database', 'usuarios.json')
    ruta = os.path.abspath(ruta)
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(" usuarios.json no encontrado, usando solo sistema de BD")
        return {}

# ACTUALIZADO: Usar el sistema de autenticación avanzado
def login_requerido(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        print("🔐 Verificando sesión avanzada:", session.get('usuario'))
        
        # Verificar si hay usuario en sesión
        if 'usuario' not in session:
            print("No hay usuario en sesión")
            return redirect(url_for('inicio'))
        
        usuario = session.get('usuario')
        
        # Actualizar actividad de sesión
        auth_system._actualizar_actividad_sesion(usuario)
        
        return f(*args, **kwargs)
    return decorada


def render_landing_page(login_error=None, login_username=None):
    """Renderiza la landing page con o sin sesión activa."""
    authenticated = 'usuario' in session
    nombre_completo = None
    permisos = {}
    roles = []

    if authenticated:
        usuario = session.get('usuario')
        nombre_completo = session.get('nombre_completo', usuario)
        permisos = session.get('permisos', {})

        try:
            from .db_mysql import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT r.nombre
                FROM usuarios_sistema u
                JOIN usuario_roles ur ON u.id = ur.usuario_id
                JOIN roles r ON ur.rol_id = r.id
                WHERE u.username = %s AND u.activo = 1 AND r.activo = 1
            ''', (usuario,))
            roles = [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"⚠️ Error obteniendo roles: {e}")
        finally:
            try:
                if 'cursor' in locals() and cursor:
                    cursor.close()
            except Exception:
                pass
            try:
                if 'conn' in locals() and conn:
                    conn.close()
            except Exception:
                pass

    upcoming_apps = [
        {
            'name': 'Más Herramientas',
            'description': 'Expansión futura',
            'long_description': 'Nuevas aplicaciones serán agregadas pronto.',
            'icon': 'rocket'
        }
    ]

    return render_template(
        'landing.html',
        nombre_usuario=nombre_completo,
        permisos=permisos,
        roles=roles,
        upcoming_apps=upcoming_apps,
        usuario_autenticado=authenticated,
        login_error=login_error,
        login_username=login_username
    )

@app.route('/')
def index():
    return redirect(url_for('inicio'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return redirect(url_for('inicio'))

    is_ajax = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('Accept', '')
    )

    user = request.form.get('username', '').strip()
    pw = request.form.get('password', '')
    print(f"🔐 Intento de login: {user}")
        
    # PRIORIDAD 1: Intentar con el nuevo sistema de BD
    resultado_auth = auth_system.verificar_usuario(user, pw)

    # verificar_usuario devuelve (success, message) en lugar de diccionario
    if isinstance(resultado_auth, tuple):
        auth_success, auth_message = resultado_auth
    else:
        auth_success = resultado_auth.get('success', False) if isinstance(resultado_auth, dict) else False
        auth_message = resultado_auth.get('message', 'Error desconocido') if isinstance(resultado_auth, dict) else str(resultado_auth)

    if auth_success:
        print(f" Login exitoso con sistema BD: {user}")
        session['usuario'] = user

        # Obtener información completa del usuario
        info_usuario = auth_system.obtener_informacion_usuario(user)
        if info_usuario:
            session['nombre_completo'] = info_usuario['nombre_completo']
            session['email'] = info_usuario['email']
            session['departamento'] = info_usuario['departamento']
            print(f"✅ Información completa cargada para {user}:")
            print(f"  - Nombre completo: {info_usuario['nombre_completo']}")
            print(f"  - Email: {info_usuario['email']}")
            print(f"  - Departamento: {info_usuario['departamento']}")
        else:
            # Fallback si no se puede obtener la información
            session['nombre_completo'] = user  # Usar username como fallback
            print(f"⚠️ No se pudo cargar información completa para {user}, usando username como fallback")

        # Registrar auditoría
        auth_system.registrar_auditoria(
            usuario=user,
            modulo='sistema',
            accion='login',
            descripcion='Inicio de sesión exitoso',
            resultado='EXITOSO'
        )

        # Obtener permisos del usuario
        permisos_resultado = auth_system.obtener_permisos_usuario(user)

        # Verificar si devuelve tupla (permisos, rol_id) o solo permisos
        if isinstance(permisos_resultado, tuple):
            permisos, rol_id = permisos_resultado
        else:
            permisos = permisos_resultado
            rol_id = None

        session['permisos'] = permisos
        print(f"🔍 Permisos establecidos en sesión para {user}: {permisos}")

        # Redirigir siempre al hub de aplicaciones (landing page)
        print(f"✅ Login exitoso para {user}, redirigiendo al hub de aplicaciones")
        redirect_url = url_for('inicio')
        if is_ajax:
            return jsonify({'success': True, 'redirect': redirect_url})
        return redirect(redirect_url)

    # FALLBACK: Intentar con el sistema antiguo (usuarios.json)
    try:
        usuarios_json = cargar_usuarios()
        if user in usuarios_json and usuarios_json[user] == pw:
            print(f" Login exitoso con sistema JSON (fallback): {user}")
            session['usuario'] = user

            # Para usuarios del sistema JSON, usar el username como nombre completo
            session['nombre_completo'] = user  # Fallback para usuarios del sistema antiguo
            session['email'] = ''  # Sin email para usuarios del sistema antiguo
            session['departamento'] = ''  # Sin departamento para usuarios del sistema antiguo
            print(f"⚠️ Usuario del sistema JSON (fallback): {user}")

            # Registrar auditoría del fallback
            auth_system.registrar_auditoria(
                usuario=user,
                modulo='sistema', 
                accion='login_json',
                descripcion='Inicio de sesión con sistema JSON (fallback)',
                resultado='EXITOSO'
            )

            # Redirigir según el usuario (lógica original)
            redirect_url = url_for('inicio')
            if user.startswith("Materiales") or user == "1111":
                redirect_url = url_for('material')
            elif user.startswith("Produccion") or user == "2222":
                redirect_url = url_for('produccion')
            elif user.startswith("DDESARROLLO") or user == "3333":
                redirect_url = url_for('desarrollo')

            if is_ajax:
                return jsonify({'success': True, 'redirect': redirect_url})
            return redirect(redirect_url)
    except Exception as e:
        print(f" Error en fallback JSON: {e}")

    # Si llega aquí, login falló
    print(f"❌ Login falló: {user} ({auth_message})")
    auth_system.registrar_auditoria(
        usuario=user,
        modulo='sistema',
        accion='login_failed',
        descripcion='Intento de login fallido - credenciales incorrectas',
        resultado='ERROR'
    )

    error_message = "Usuario o contraseña incorrectos. Por favor, intente de nuevo"

    if is_ajax:
        return jsonify({'success': False, 'message': error_message}), 401

    return render_landing_page(
        login_error=error_message,
        login_username=user
    )

@app.route('/inicio')
def inicio():
    """Landing page / Hub de aplicaciones"""
    return render_landing_page()

@app.route('/calendario')
@login_requerido
def calendario():
    """Página del calendario de producción"""
    return render_template('calendario.html')

@app.route('/defect-management')
@login_requerido
def defect_management():
    """Módulo de Gestión de Defectos (En Desarrollo)"""
    # TODO: Implementar módulo completo de gestión de defectos
    return render_template('info.html', 
                         titulo="Gestión de Defectos",
                         mensaje="Módulo en desarrollo. Próximamente disponible.",
                         tipo="warning")

@app.route('/favicon.ico')
def favicon():
    """Servir favicon usando un icono existente"""
    return send_from_directory(
        os.path.join(app.root_path, 'static', 'icons'),
        'produccion.png',
        mimetype='image/png'
    )

@app.route('/sistemas')
@login_requerido
def sistemas():
    """Redirige al hub de inicio"""
    return redirect(url_for('inicio'))

@app.route('/soporte')
@login_requerido
def soporte():
    """Página de soporte técnico"""
    return render_template('soporte.html') if os.path.exists('app/templates/soporte.html') else \
           f"<h1>Soporte Técnico</h1><p>En construcción. <a href='/inicio'>Volver al inicio</a></p>"

@app.route('/documentacion')
@login_requerido
def documentacion():
    """Página de documentación"""
    return render_template('documentacion.html') if os.path.exists('app/templates/documentacion.html') else \
           f"<h1>Documentación</h1><p>En construcción. <a href='/inicio'>Volver al inicio</a></p>"

@app.route('/ILSAN-ELECTRONICS')
@login_requerido
def material():
    usuario = session.get('usuario', 'Invitado')
    nombre_completo = session.get('nombre_completo', None)
    
    # Si no tenemos el nombre completo en la sesión, obtenerlo de la BD
    if not nombre_completo and usuario != 'Invitado':
        print(f"⚠️ Nombre completo no encontrado en sesión para {usuario}, obteniendo de BD...")
        from .auth_system import auth_system
        info_usuario = auth_system.obtener_informacion_usuario(usuario)
        if info_usuario and info_usuario['nombre_completo']:
            nombre_completo = info_usuario['nombre_completo']
            session['nombre_completo'] = nombre_completo  # Guardar en sesión para futuras consultas
            print(f"✅ Nombre completo obtenido de BD: {nombre_completo}")
        else:
            nombre_completo = usuario  # Fallback al username
            session['nombre_completo'] = usuario
            print(f"⚠️ No se pudo obtener nombre completo de BD, usando username: {usuario}")
    
    # Si todavía no tenemos nombre completo, usar el username
    if not nombre_completo:
        nombre_completo = usuario
        
    permisos = session.get('permisos', {})
    
    # Verificar si tiene permisos de administración de usuarios
    tiene_permisos_usuarios = False
    if isinstance(permisos, dict) and 'sistema' in permisos:
        tiene_permisos_usuarios = 'usuarios' in permisos['sistema']
    
    return render_template('MaterialTemplate.html', 
                        usuario=nombre_completo,  # Pasar nombre completo en lugar de username 
                        tiene_permisos_usuarios=tiene_permisos_usuarios)

@app.route('/dashboard')
@login_requerido
def dashboard():
    """Alias para la página principal (MaterialTemplate)"""
    usuario = session.get('usuario')
    nombre_completo = session.get('nombre_completo')
    
    # Si no tenemos nombre completo, intentar obtenerlo
    if not nombre_completo and usuario:
        try:
            query = "SELECT nombre_completo FROM users WHERE usuario = %s"
            result = execute_query(query, (usuario,), fetch='one')
            if result and result.get('nombre_completo'):
                nombre_completo = result['nombre_completo']
                session['nombre_completo'] = nombre_completo
        except Exception as e:
            print(f"⚠️ Error obteniendo nombre completo para dashboard: {e}")
            nombre_completo = usuario
    
    if not nombre_completo:
        nombre_completo = usuario
        
    permisos = session.get('permisos', {})
    tiene_permisos_usuarios = False
    if isinstance(permisos, dict) and 'sistema' in permisos:
        tiene_permisos_usuarios = 'usuarios' in permisos['sistema']
    
    return render_template('MaterialTemplate.html', 
                        usuario=nombre_completo,
                        tiene_permisos_usuarios=tiene_permisos_usuarios)

@app.route('/Prueba')
@login_requerido
def produccion():
    usuario = session.get('usuario', 'Invitado')
    return render_template('Control de material/Control de salida.html', usuario=usuario)

@app.route('/DESARROLLO')
@login_requerido
def desarrollo():
    usuario = session.get('usuario', 'Invitado')
    return render_template('Control de material/Control de salida.html', usuario=usuario)


@app.route('/logout')
def logout():
    usuario = session.get('usuario', 'unknown')
    
    # Registrar auditoría del logout
    if usuario != 'unknown':
        auth_system.registrar_auditoria(
            usuario=usuario,
            modulo='sistema',
            accion='logout', 
            descripcion='Cierre de sesión',
            resultado='EXITOSO'
        )
        print(f"🚪 Logout exitoso: {usuario}")
    
    # Limpiar sesión completa
    session.clear()
    
    return redirect(url_for('inicio'))

# =============================
# FRONT PLAN: Vistas y estáticos
# =============================

# Alias para servir los assets originales de FRONT PLAN ubicados en
# app/FRONT PLAN/static sin depender de moverlos físicamente.
@app.route('/front-plan/static/<path:filename>')
def front_plan_static(filename):
    try:
        base_dir = os.path.join(os.path.dirname(__file__), 'FRONT PLAN', 'static')
        return send_from_directory(base_dir, filename)
    except Exception as e:
        return jsonify({'error': f'Recurso no encontrado: {str(e)}'}), 404

@app.route('/plan-main')
@login_requerido
def view_plan_main():
    # Página de planeación (plantilla en Control de proceso)
    return render_template('Control de proceso/Control_produccion_assy.html')

@app.route('/control-main')
@login_requerido
def view_control_main():
    # Panel de control de operación (plantilla en Control de proceso)
    return render_template('Control de proceso/Control de operacion de linea Main.html')

# Rutas AJAX para cargar módulos en el área de Control de Proceso (prompts)
@app.route('/plan-main-assy-ajax')
@login_requerido
def plan_main_assy_ajax():
    try:
        return render_template('Control de proceso/Control_produccion_assy.html')
    except Exception as e:
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control-operacion-linea-main-ajax')
@login_requerido
def ctrl_operacion_linea_main_ajax():
    try:
        return render_template('Control de proceso/Control de operacion de linea Main.html')
    except Exception as e:
        return f"Error al cargar el contenido: {str(e)}", 500

# =============================
# FRONT PLAN: API mínima plan_main
# =============================

def _fp_safe_date(s: str):
    try:
        return datetime.strptime(s[:10], '%Y-%m-%d').date()
    except Exception:
        return None

def _fp_generate_lot_no(fecha: datetime):
    try:
        fecha_str = fecha.strftime('%y%m%d')
        prefix = f'ASSYLINE-{fecha_str}'
        row = execute_query("SELECT COUNT(*) AS c FROM plan_main WHERE lot_no LIKE %s", (f"{prefix}%",), fetch='one')
        count = 0
        if row:
            if isinstance(row, dict):
                count = list(row.values())[0] if len(row.values()) == 1 else (row.get('c') or row.get('COUNT(*)') or 0)
            else:
                count = row[0]
        return f"{prefix}-{int(count)+1:03d}"
    except Exception:
        # Fallback
        return f"ASSYLINE-{fecha.strftime('%y%m%d')}-001"

@app.route('/api/plan', methods=['GET'])
@login_requerido
def api_plan_list():
    try:
        start = request.args.get('start')
        end = request.args.get('end')
        where = []
        params = []
        if start:
            # Si solo viene start sin end, filtrar por fecha exacta
            if not end:
                where.append('DATE(working_date) = %s')
                params.append(start)
            else:
                where.append('DATE(working_date) >= %s')
                params.append(start)
        if end:
            where.append('DATE(working_date) <= %s')
            params.append(end)
        sql = (
            "SELECT id, lot_no, wo_code, po_code, working_date, line, routing, model_code, part_no, project, process, "
            "COALESCE(ct,0) AS ct, COALESCE(uph,0) AS uph, COALESCE(plan_count,0) AS plan_count, "
            "COALESCE(produced_count,0) AS input, 0 AS output, COALESCE(entregadas_main,0) AS entregadas_main, "
            "COALESCE(produced_count,0) AS produced, status, group_no, sequence FROM plan_main"
        )
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        sql += ' ORDER BY COALESCE(group_no,999), COALESCE(sequence,999), working_date, created_at'
        rows = execute_query(sql, tuple(params) if params else None, fetch='all')
        # Normalizar claves esperadas por el frontend
        data = []
        for r in rows:
            data.append({
                'lot_no': r.get('lot_no') if isinstance(r, dict) else r[1],
                'wo_code': r.get('wo_code') if isinstance(r, dict) else r[2],
                'po_code': r.get('po_code') if isinstance(r, dict) else r[3],
                'working_date': str((r.get('working_date') if isinstance(r, dict) else r[4]) or '')[:10],
                'line': r.get('line') if isinstance(r, dict) else r[5],
                'routing': r.get('routing') if isinstance(r, dict) else r[6],
                'model_code': r.get('model_code') if isinstance(r, dict) else r[7],
                'part_no': r.get('part_no') if isinstance(r, dict) else r[8],
                'project': r.get('project') if isinstance(r, dict) else r[9],
                'process': r.get('process') if isinstance(r, dict) else r[10],
                'ct': r.get('ct') if isinstance(r, dict) else r[11],
                'uph': r.get('uph') if isinstance(r, dict) else r[12],
                'plan_count': r.get('plan_count') if isinstance(r, dict) else r[13],
                'input': r.get('input') if isinstance(r, dict) else r[14],
                'output': r.get('output') if isinstance(r, dict) else r[15],
                'entregadas_main': r.get('entregadas_main') if isinstance(r, dict) else r[16],
                'produced': r.get('produced') if isinstance(r, dict) else r[17],
                'status': r.get('status') if isinstance(r, dict) else r[18],
                'group_no': r.get('group_no') if isinstance(r, dict) else r[19],
                'sequence': r.get('sequence') if isinstance(r, dict) else r[20],
            })
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/plan', methods=['POST'])
@login_requerido
def api_plan_create():
    try:
        data = request.get_json() or {}
        working_date = data.get('working_date')
        part_no = data.get('part_no')
        line = data.get('line')
        turno = (data.get('turno') or 'DIA').strip().upper()
        plan_count = int(data.get('plan_count') or 0)
        
        # 🔧 Si no se especifica WO o PO, usar valores por defecto
        wo_code = data.get('wo_code') or ''
        po_code = data.get('po_code') or ''
        
        # Si están vacíos, asignar valores por defecto
        if not wo_code or wo_code.strip() == '':
            wo_code = 'SIN-WO'
        if not po_code or po_code.strip() == '':
            po_code = 'SIN-PO'
        
        if not (working_date and part_no and line):
            return jsonify({'error': 'Parámetros requeridos'}), 400
        fecha = _fp_safe_date(working_date) or datetime.utcnow().date()
        routing = {'DIA': 1, 'TIEMPO EXTRA': 2, 'NOCHE': 3}.get(turno, 1)
        lot_no = _fp_generate_lot_no(datetime.combine(fecha, datetime.min.time()))
        
        # 🔍 Buscar información adicional en raw (CT, UPH, MODEL, PROJECT) basándose en part_no
        raw_data_query = """
            SELECT part_no, model, project, c_t as ct, uph
            FROM raw
            WHERE part_no = %s OR part_no LIKE %s OR model = %s OR model LIKE %s
            ORDER BY id DESC
            LIMIT 1
        """
        raw_params = (part_no, f"%{part_no}%", part_no, f"%{part_no}%")
        
        raw_data = execute_query(raw_data_query, raw_params, fetch='one')
        
        # Extraer datos de raw o usar valores por defecto
        if raw_data:
            model_code = raw_data.get('model') or part_no
            project = raw_data.get('project') or ''
            
            # Normalizar CT y UPH
            try:
                ct = float(raw_data.get('ct') or 0)
            except:
                ct = 0.0
            try:
                uph_raw = raw_data.get('uph')
                if uph_raw and str(uph_raw).strip().replace('.', '').isdigit():
                    uph = int(float(str(uph_raw).strip()))
                else:
                    uph = 0
            except:
                uph = 0
        else:
            # Si no hay datos en raw, usar valores por defecto
            model_code = part_no
            project = ''
            ct = 0.0
            uph = 0
        
        # 🎯 Obtener group_no si fue especificado (para asignación directa a grupo)
        group_no = data.get('group_no')
        sequence = None
        
        # Si se especifica grupo, calcular el siguiente sequence para ese grupo
        if group_no is not None:
            # Obtener el sequence más alto del grupo
            seq_query = "SELECT MAX(sequence) as max_seq FROM plan_main WHERE group_no = %s"
            seq_result = execute_query(seq_query, (int(group_no),), fetch='one')
            max_seq = seq_result.get('max_seq') if seq_result else None
            sequence = (max_seq + 1) if max_seq is not None else 1
        
        # Insert con datos completos
        if group_no is not None and sequence is not None:
            # Si se especifica grupo, incluirlo en el INSERT con sequence
            sql = (
                "INSERT INTO plan_main (lot_no, wo_code, po_code, working_date, line, model_code, part_no, project, process, plan_count, ct, uph, routing, status, group_no, sequence, created_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PLAN',%s,%s,NOW())"
            )
            params = (lot_no, wo_code, po_code, fecha, line, model_code, part_no, project, 'MAIN', plan_count, ct, uph, routing, int(group_no), sequence)
        else:
            # Sin grupo especificado, usar INSERT original
            sql = (
                "INSERT INTO plan_main (lot_no, wo_code, po_code, working_date, line, model_code, part_no, project, process, plan_count, ct, uph, routing, status, created_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PLAN',NOW())"
            )
            params = (lot_no, wo_code, po_code, fecha, line, model_code, part_no, project, 'MAIN', plan_count, ct, uph, routing)
        
        execute_query(sql, params)
        return jsonify({'success': True, 'lot_no': lot_no, 'model_code': model_code, 'ct': ct, 'uph': uph, 'project': project})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/plan/update', methods=['POST'])
@login_requerido
def api_plan_update():
    try:
        data = request.get_json() or {}
        lot_no = data.get('lot_no')
        if not lot_no:
            return jsonify({'error': 'lot_no requerido'}), 400
        fields = []
        vals = []
        if 'plan_count' in data:
            fields.append('plan_count = %s')
            vals.append(int(data.get('plan_count') or 0))
        if 'status' in data:
            fields.append('status = %s')
            vals.append(str(data.get('status')))
        if 'line' in data:
            fields.append('line = %s')
            vals.append(str(data.get('line')))
        if 'wo_code' in data:
            fields.append('wo_code = %s')
            vals.append(str(data.get('wo_code')))
        if 'po_code' in data:
            fields.append('po_code = %s')
            vals.append(str(data.get('po_code')))
        if 'turno' in data:
            routing = {'DIA': 1, 'TIEMPO EXTRA': 2, 'NOCHE': 3}.get(str(data.get('turno')).strip().upper(), 1)
            fields.append('routing = %s')
            vals.append(routing)
        # Agregar campos actualizados desde RAW
        if 'uph' in data:
            fields.append('uph = %s')
            vals.append(str(data.get('uph')))
        if 'ct' in data:
            fields.append('ct = %s')
            vals.append(str(data.get('ct')))
        if 'project' in data:
            fields.append('project = %s')
            vals.append(str(data.get('project')))
        if 'model_code' in data:
            fields.append('model_code = %s')
            vals.append(str(data.get('model_code')))
        if not fields:
            return jsonify({'error': 'Sin cambios'}), 400
        fields.append('updated_at = NOW()')
        sql = f"UPDATE plan_main SET {', '.join(fields)} WHERE lot_no = %s"
        vals.append(lot_no)
        execute_query(sql, tuple(vals))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/raw/search', methods=['GET'])
@login_requerido
def api_raw_search():
    """Buscar datos en la tabla RAW por part_no o model"""
    try:
        part_no = request.args.get('part_no', '').strip()
        if not part_no:
            return jsonify({'error': 'part_no requerido'}), 400
        
        # Buscar con múltiples campos para mayor flexibilidad
        # Usar TRIM para ignorar espacios y comparación case-insensitive
        sql = """
            SELECT part_no, model, project, c_t as ct, uph 
            FROM raw 
            WHERE TRIM(model) = %s 
               OR TRIM(part_no) = %s 
               OR TRIM(part_no) LIKE %s
               OR UPPER(TRIM(part_no)) = UPPER(%s)
            LIMIT 1
        """
        params = (part_no, part_no, f'%{part_no}%', part_no)
        
        # CRÍTICO: Usar fetch='all' para obtener los datos, no el rowcount
        result = execute_query(sql, params, fetch='all')
        
        # Verificar que result sea una lista/tupla antes de usar len()
        if result and isinstance(result, (list, tuple)) and len(result) > 0:
            row = result[0]
            
            # execute_query con fetch='all' retorna lista de diccionarios
            # Acceder como diccionario, no como tupla
            data = {
                'part_no': row.get('part_no', '') if row.get('part_no') is not None else '',
                'model': row.get('model', '') if row.get('model') is not None else '',
                'model_code': row.get('model', '') if row.get('model') is not None else '',  # Alias
                'project': row.get('project', '') if row.get('project') is not None else '',
                'ct': str(row.get('ct', '0')) if row.get('ct') is not None else '0',
                'uph': str(row.get('uph', '0')) if row.get('uph') is not None else '0'
            }
            return jsonify([data])
        else:
            return jsonify([])
            
    except Exception as e:
        print(f"Error en api_raw_search: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/plan/status', methods=['POST'])
@login_requerido
def api_plan_status():
    """Actualizar el status de un plan con validaciones y motivos"""
    try:
        data = request.get_json() or {}
        lot_no = data.get('lot_no', '').strip()
        new_status = data.get('status', '').strip().upper()
        
        if not lot_no:
            return jsonify({'error': 'lot_no requerido', 'error_code': 'MISSING_LOT_NO'}), 400
        
        if not new_status:
            return jsonify({'error': 'status requerido', 'error_code': 'MISSING_STATUS'}), 400
        
        # Validar status permitidos
        valid_statuses = ['PENDIENTE', 'EN PROGRESO', 'PAUSADO', 'TERMINADO', 'CANCELADO']
        if new_status not in valid_statuses:
            return jsonify({'error': f'Status inválido: {new_status}', 'error_code': 'INVALID_STATUS'}), 400
        
        # Obtener información del plan actual
        check_sql = "SELECT line, status, plan_count, produced_count, started_at, pause_started_at, paused_at FROM plan_main WHERE lot_no = %s"
        plan_result = execute_query(check_sql, (lot_no,), fetch='one')
        
        if not plan_result:
            return jsonify({'error': 'Plan no encontrado', 'error_code': 'NOT_FOUND'}), 404
        
        current_line = plan_result.get('line') or plan_result.get('linea')
        current_status = (plan_result.get('status') or '').strip().upper()
        plan_count = int(plan_result.get('plan_count') or plan_result.get('qty') or 0)
        produced_count = int(plan_result.get('produced_count') or plan_result.get('producido') or 0)
        started_at = plan_result.get('started_at')
        pause_started_at = plan_result.get('pause_started_at')
        paused_at = int(plan_result.get('paused_at') or 0)
        
        # Validación: Si se intenta poner EN PROGRESO, verificar que no haya otro plan EN PROGRESO en la misma línea
        if new_status == 'EN PROGRESO' and current_status != 'EN PROGRESO':
            conflict_sql = """
                SELECT lot_no FROM plan_main 
                WHERE line = %s AND status = 'EN PROGRESO' AND lot_no != %s 
                LIMIT 1
            """
            conflict_result = execute_query(conflict_sql, (current_line, lot_no), fetch='one')
            
            if conflict_result:
                conflicting_lot = conflict_result.get('lot_no') or conflict_result.get('lote')
                return jsonify({
                    'error': 'Ya existe un plan EN PROGRESO en esta línea',
                    'error_code': 'LINE_CONFLICT',
                    'line': current_line,
                    'lot_no_en_progreso': conflicting_lot
                }), 409
        
        # Construir el UPDATE
        update_fields = ['status = %s', 'updated_at = NOW()']
        update_values = [new_status]
        
        # Si cambia a EN PROGRESO
        if new_status == 'EN PROGRESO':
            if current_status == 'PAUSADO' and pause_started_at:
                # Resumiendo desde pausa: calcular tiempo pausado y acumular
                # MANTENER pause_started_at para historial (no limpiar)
                update_fields.append('paused_at = paused_at + TIMESTAMPDIFF(SECOND, pause_started_at, NOW())')
            elif current_status != 'EN PROGRESO' and not started_at:
                # Iniciando por primera vez
                update_fields.append('started_at = NOW()')
        
        # Si cambia a PAUSADO, guardar motivo de pausa y timestamp
        if new_status == 'PAUSADO' and current_status == 'EN PROGRESO':
            if 'pause_reason' in data:
                update_fields.append('pause_reason = %s')
                update_values.append(str(data.get('pause_reason', '')))
            # Actualizar pause_started_at con la nueva pausa
            update_fields.append('pause_started_at = NOW()')
        
        # Si cambia a TERMINADO, guardar ended_at y motivo si está incompleto
        if new_status == 'TERMINADO':
            if current_status == 'PAUSADO' and pause_started_at:
                # Si estaba pausado, acumular tiempo pausado antes de terminar
                # MANTENER pause_started_at para historial (no limpiar)
                update_fields.append('paused_at = paused_at + TIMESTAMPDIFF(SECOND, pause_started_at, NOW())')
            update_fields.append('ended_at = NOW()')
            if produced_count < plan_count and 'end_reason' in data:
                update_fields.append('end_reason = %s')
                update_values.append(str(data.get('end_reason', '')))
        
        # Ejecutar UPDATE
        update_sql = f"UPDATE plan_main SET {', '.join(update_fields)} WHERE lot_no = %s"
        update_values.append(lot_no)
        
        rows_affected = execute_query(update_sql, tuple(update_values))
        
        if isinstance(rows_affected, int) and rows_affected == 0:
            return jsonify({'error': 'No se actualizó ninguna fila', 'error_code': 'NO_ROWS_UPDATED'}), 400
        
        return jsonify({
            'success': True,
            'lot_no': lot_no,
            'new_status': new_status,
            'line': current_line
        })
        
    except Exception as e:
        print(f"Error en api_plan_status: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'error_code': 'UNHANDLED_EXCEPTION'}), 500

@app.route('/api/plan/save-sequences', methods=['POST'])
@login_requerido
def api_plan_save_sequences():
    try:
        payload = request.get_json() or {}
        sequences = payload.get('sequences', [])
        updated = 0
        for item in sequences:
            lot_no = item.get('lot_no')
            group_no = item.get('group_no')
            sequence = item.get('sequence')
            if not (lot_no and group_no is not None and sequence is not None):
                continue
            vals = []
            sets = []
            sets.append('group_no = %s'); vals.append(int(group_no))
            sets.append('sequence = %s'); vals.append(int(sequence))
            if item.get('plan_start_date') and item.get('plan_start_date') != '--':
                sets.append('plan_start_date = %s'); vals.append(item['plan_start_date'])
            if item.get('planned_start') and item.get('planned_start') != '--':
                sets.append('planned_start = %s'); vals.append(item['planned_start'])
            if item.get('planned_end') and item.get('planned_end') != '--':
                sets.append('planned_end = %s'); vals.append(item['planned_end'])
            if 'effective_minutes' in item:
                sets.append('effective_minutes = %s'); vals.append(int(item.get('effective_minutes') or 0))
            if 'breaks_minutes' in item:
                sets.append('breaks_minutes = %s'); vals.append(int(item.get('breaks_minutes') or 0))
            sets.append('updated_at = NOW()')
            vals.append(lot_no)
            sql = f"UPDATE plan_main SET {', '.join(sets)} WHERE lot_no = %s"
            execute_query(sql, tuple(vals))
            updated += 1
        return jsonify({'success': True, 'updated_count': updated, 'message': f'{updated} secuencias guardadas correctamente'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/plan/pending', methods=['GET'])
@login_requerido
def api_plan_pending():
    """
    Obtener planes con cantidad pendiente (plan_count > produced_count)
    Filtra por rango de fechas si se proporcionan start y end.
    """
    try:
        start = request.args.get('start')
        end = request.args.get('end')
        
        where = ["status <> 'CANCELADO'"]
        params = []
        
        if start:
            where.append('DATE(working_date) >= %s')
            params.append(start)
            print(f"📅 Filtro START aplicado: {start}")
        
        if end:
            where.append('DATE(working_date) <= %s')
            params.append(end)
            print(f"📅 Filtro END aplicado: {end}")
        
        # Solo planes con cantidad pendiente
        where.append('COALESCE(plan_count, 0) > COALESCE(produced_count, 0)')
        
        sql = (
            "SELECT lot_no, working_date, part_no, line, "
            "COALESCE(plan_count,0) AS plan_count, "
            "COALESCE(produced_count,0) AS input, "
            "status "
            "FROM plan_main "
            "WHERE " + ' AND '.join(where) + " "
            "ORDER BY working_date, lot_no"
        )
        
        print(f"🔍 SQL Query: {sql}")
        print(f"🔍 Parámetros: {tuple(params) if params else 'Sin parámetros'}")
        
        rows = execute_query(sql, tuple(params) if params else None, fetch='all')
        
        data = []
        for r in rows:
            data.append({
                'lot_no': r['lot_no'] if isinstance(r, dict) else r[0],
                'working_date': str((r['working_date'] if isinstance(r, dict) else r[1]) or '')[:10],
                'part_no': r['part_no'] if isinstance(r, dict) else r[2],
                'line': r['line'] if isinstance(r, dict) else r[3],
                'plan_count': r['plan_count'] if isinstance(r, dict) else r[4],
                'input': r['input'] if isinstance(r, dict) else r[5],
                'status': r['status'] if isinstance(r, dict) else r[6]
            })
        
        print(f"✅ Planes pendientes encontrados: {len(data)}")
        return jsonify(data)
        
    except Exception as e:
        print(f"❌ Error en api_plan_pending: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/plan/reschedule', methods=['POST'])
@login_requerido
def api_plan_reschedule():
    """
    Reprogramar planes pendientes creando NUEVOS planes con la cantidad restante.
    NO modifica el plan original, sino que crea un nuevo registro con:
    - Mismo lot_no, part_no
    - Nueva working_date
    - plan_count = plan_count_original - produced_count (cantidad pendiente)
    
    Ejemplo: Si plan=500 y produced_count=300, el nuevo plan será de 200 unidades.
    """
    try:
        data = request.get_json() or {}
        lot_nos = data.get('lot_nos', [])
        new_date = data.get('new_working_date')
        
        if not (lot_nos and new_date):
            return jsonify({'error': 'Parámetros requeridos'}), 400
        
        # Obtener los planes originales con su información completa
        placeholders = ','.join(['%s'] * len(lot_nos))
        sql_select = f"""
            SELECT lot_no, wo_id, wo_code, po_code, working_date, line, model_code, 
                   part_no, project, process, plan_count, produced_count, ct, uph, routing, 
                   status, group_no, sequence
            FROM plan_main 
            WHERE lot_no IN ({placeholders})
        """
        print(f"🔍 Buscando {len(lot_nos)} planes para reprogramar")
        planes_originales = execute_query(sql_select, tuple(lot_nos), fetch='all')
        
        if not planes_originales:
            print(f"❌ No se encontraron planes para los lot_nos: {lot_nos}")
            return jsonify({'error': 'No se encontraron planes para reprogramar'}), 404
        
        print(f"✅ Se encontraron {len(planes_originales)} planes")
        nuevos_planes_creados = 0
        
        for plan in planes_originales:
            lot_no_original = plan['lot_no']
            plan_count_original = plan['plan_count'] or 0
            produced_count = plan['produced_count'] or 0
            
            # Calcular la cantidad pendiente (plan - produced_count)
            cantidad_pendiente = plan_count_original - produced_count
            
            print(f"📦 Plan {lot_no_original}: plan_count={plan_count_original}, produced={produced_count}, pendiente={cantidad_pendiente}")
            
            if cantidad_pendiente <= 0:
                # Si no hay pendiente, no crear nuevo plan
                print(f"⏭️ Saltando {lot_no_original} - no hay cantidad pendiente")
                continue
            
            # *** GENERAR NUEVO LOT_NO manteniendo trazabilidad del lote original ***
            # Formato: LOTE-ORIGINAL-XX (secuencial de reprogramaciones)
            # Ejemplo: ASSYLINE-251017-003 -> ASSYLINE-251017-003-01, ASSYLINE-251017-003-02, etc.
            
            # Obtener el lote base (sin sufijo de reprogramación si ya existe)
            # Si el lote es ASSYLINE-251017-003-01, el base es ASSYLINE-251017-003
            if lot_no_original.count('-') >= 3:
                # Ya tiene sufijo de reprogramación, extraer el base
                parts = lot_no_original.rsplit('-', 1)
                lot_no_base = parts[0]
            else:
                # Es un lote original sin reprogramar
                lot_no_base = lot_no_original
            
            # Buscar cuántas reprogramaciones existen de este lote base
            sql_count = """
                SELECT COUNT(*) as count 
                FROM plan_main 
                WHERE lot_no LIKE %s AND lot_no <> %s
            """
            pattern = f"{lot_no_base}-%"
            result = execute_query(sql_count, (pattern, lot_no_base), fetch='one')
            count = result['count'] if result else 0
            next_seq = count + 1
            
            # Generar nuevo lot_no con sufijo secuencial
            nuevo_lot_no = f"{lot_no_base}-{next_seq:02d}"
            print(f"🆕 Nuevo lot_no generado: {nuevo_lot_no} (reprogramación #{next_seq} de {lot_no_base})")
            
            # Crear nuevo plan con la cantidad pendiente
            sql_insert = """
                INSERT INTO plan_main 
                (lot_no, wo_id, wo_code, po_code, working_date, line, model_code, 
                 part_no, project, process, plan_count, ct, uph, routing, status, 
                 group_no, sequence, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            print(f"➕ Creando nuevo plan {nuevo_lot_no} con {cantidad_pendiente} unidades para {new_date}")
            
            execute_query(sql_insert, (
                nuevo_lot_no,  # NUEVO lot_no con sufijo secuencial
                plan.get('wo_id'),
                plan.get('wo_code'),
                plan.get('po_code'),
                new_date,  # Nueva fecha de trabajo
                plan.get('line'),
                plan.get('model_code'),
                plan.get('part_no'),
                plan.get('project'),
                plan.get('process'),
                cantidad_pendiente,  # Cantidad pendiente (plan_count - produced_count)
                plan.get('ct'),
                plan.get('uph'),
                plan.get('routing'),
                'PLAN',  # Estado inicial del nuevo plan
                plan.get('group_no'),
                plan.get('sequence')
            ))
            
            print(f"✅ Nuevo plan creado: {nuevo_lot_no} (trazabilidad: {lot_no_original} -> {nuevo_lot_no})")
            nuevos_planes_creados += 1
        
        print(f"🎉 Total de planes creados: {nuevos_planes_creados}")
        return jsonify({
            'success': True, 
            'created': nuevos_planes_creados,
            'message': f'{nuevos_planes_creados} nuevo(s) plan(es) creado(s) para {new_date}'
        })
        
    except Exception as e:
        print(f"❌ Error en api_plan_reschedule: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/plan/export-excel', methods=['POST'])
@login_requerido
def api_plan_export_excel():
    try:
        payload = request.get_json() or {}
        plans = payload.get('plans', [])
        if not plans:
            return jsonify({'error': 'No hay datos para exportar'}), 400
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment
        import io
        wb = Workbook()
        ws = wb.active
        ws.title = 'Plan Producción'
        headers = ['Sec', 'LOT NO', 'WO', 'PO', 'Fecha', 'Línea', 'Turno', 'Modelo', 'Part No', 'Proyecto', 'Proceso', 'CT', 'UPH', 'Plan', 'Producido', 'Status', 'Tiempo', 'Inicio', 'Fin', 'Grupo', 'Extra']
        ws.append(headers)
        for c in ws[1]:
            c.font = Font(bold=True)
            c.alignment = Alignment(horizontal='center')
        for p in plans:
            if p.get('isGroupHeader'):
                ws.append([p.get('groupTitle', f"GRUPO {p.get('groupIndex', 0)+1}")])
                continue
            ws.append([
                p.get('secuencia',''), p.get('lot_no',''), p.get('wo_code',''), p.get('po_code',''), p.get('working_date',''),
                p.get('line',''), p.get('turno',''), p.get('model_code',''), p.get('part_no',''), p.get('project',''), p.get('process',''),
                p.get('ct',''), p.get('uph',''), p.get('plan_count',''), p.get('produced',''), p.get('status',''), p.get('tiempo_produccion',''), p.get('inicio',''), p.get('fin',''), p.get('grupo',''), p.get('extra','')
            ])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)
        ts = datetime.utcnow().strftime('%Y%m%d_%H%M')
        return send_file(bio, as_attachment=True, download_name=f'Plan_Produccion_{ts}.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/plan-main/list', methods=['GET'])
@login_requerido
def api_plan_main_list():
    try:
        q = request.args.get('q', '').strip()
        linea = request.args.get('linea')
        desde = request.args.get('desde')
        hasta = request.args.get('hasta')
        solo_pendientes = request.args.get('solo_pendientes') == 'true'
        where = []
        params = []
        if q:
            where.append('(lot_no LIKE %s OR part_no LIKE %s OR model_code LIKE %s)')
            qv = f"%{q}%"; params.extend([qv, qv, qv])
        if linea and linea not in ('Todos','ALL'):
            where.append('line = %s'); params.append(linea)
        if desde:
            where.append('DATE(working_date) >= %s'); params.append(desde)
        if hasta:
            where.append('DATE(working_date) <= %s'); params.append(hasta)
        if solo_pendientes:
            where.append("status = 'PLAN'")
        sql = (
            "SELECT id, lot_no, part_no, model_code, line, working_date, COALESCE(plan_count,0) AS qty, COALESCE(produced_count,0) AS producido, "
            "GREATEST(COALESCE(plan_count,0)-COALESCE(produced_count,0),0) AS falta, COALESCE(ct,0) AS ct, COALESCE(uph,0) AS uph, status, process "
            "FROM plan_main"
        )
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        sql += ' ORDER BY working_date DESC, created_at DESC'
        rows = execute_query(sql, tuple(params) if params else None, fetch='all')
        out = []
        for r in rows:
            qty = r['qty'] if isinstance(r, dict) else r[6]
            producido = r['produced_count'] if isinstance(r, dict) and 'produced_count' in r else (r['producido'] if isinstance(r, dict) else r[7])
            pct = int(round((producido/qty)*100, 0)) if qty else 0
            out.append({
                'id': r['id'] if isinstance(r, dict) else r[0],
                'lote': r['lot_no'] if isinstance(r, dict) else r[1],
                'nparte': r['part_no'] if isinstance(r, dict) else r[2],
                'modelo': r['model_code'] if isinstance(r, dict) else r[3],
                'linea': r['line'] if isinstance(r, dict) else r[4],
                'fecha_inicio': str((r['working_date'] if isinstance(r, dict) else r[5]) or '')[:10],
                'qty': qty,
                'producido': producido,
                'falta': max(0, qty - producido),
                'ct': r['ct'] if isinstance(r, dict) else r[9],
                'uph': r['uph'] if isinstance(r, dict) else r[10],
                'estatus': r['status'] if isinstance(r, dict) else r[11],
                'process': r['process'] if isinstance(r, dict) else r[12],
            })
        return jsonify(out)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-orders/import', methods=['POST'])
@login_requerido
def api_work_orders_import():
    try:
        data = request.get_json() or {}
        wo_ids = data.get('wo_ids', [])
        import_date = data.get('import_date', None)  # Fecha de importación desde el frontend
        
        if not wo_ids:
            return jsonify({'error': 'No se seleccionaron work orders'}), 400
        
        # Parsear fecha de importación si se proporciona
        fecha_importacion = None
        if import_date:
            try:
                fecha_importacion = datetime.strptime(import_date, '%Y-%m-%d').date()
            except Exception as e:
                return jsonify({'error': f'Fecha de importación inválida: {str(e)}'}), 400
        
        imported = 0
        plans = []
        errors = []
        for wo_id in wo_ids:
            row = execute_query("SELECT * FROM work_orders WHERE id = %s", (wo_id,), fetch='one')
            if not row:
                errors.append(f'WO id {wo_id} no encontrado')
                continue
            wo = row
            # Verificar si ya existe (buscar por wo_id para ser más preciso)
            existing = execute_query(
                "SELECT lot_no, status FROM plan_main WHERE wo_id = %s OR wo_code = %s", 
                (wo_id, wo.get('codigo_wo')), 
                fetch='one'
            )
            if existing:
                lot_existente = existing.get('lot_no') if isinstance(existing, dict) else existing[0]
                errors.append(f"WO {wo.get('codigo_wo')} ya fue importada como LOT: {lot_existente}")
                continue
            
            # Obtener part_no y línea del WO
            # En work_orders: 'modelo' es el part_no (ej: EBR42005002)
            # La línea viene directamente de la columna 'linea' del WO
            part_no = wo.get('modelo') or wo.get('codigo_modelo') or ''
            line = wo.get('linea') or 'MAIN_LINE'  # Línea del WO directamente
            
            # Buscar información adicional en raw (CT, UPH, MODEL, PROJECT)
            # Usar consulta combinada como en FRONT PLAN original
            # NO buscar linea en raw, solo CT, UPH, MODEL y PROJECT
            raw_data_query = """
                SELECT part_no, model, project, c_t as ct, uph
                FROM raw
                WHERE model = %s OR model = %s OR part_no = %s OR part_no LIKE %s
                ORDER BY id DESC
                LIMIT 1
            """
            raw_params = (wo.get('modelo'), wo.get('codigo_modelo'), wo.get('codigo_modelo'), f"%{wo.get('modelo')}%")
            
            raw_data = execute_query(raw_data_query, raw_params, fetch='one')
            
            # Extraer datos de raw o usar valores por defecto
            if raw_data:
                part_no = raw_data.get('part_no') or part_no
                model_code = raw_data.get('model') or wo.get('modelo') or ''
                project = raw_data.get('project') or wo.get('nombre_modelo') or ''
                
                # Normalizar CT y UPH
                try:
                    ct = float(raw_data.get('ct') or 0)
                except:
                    ct = 0.0
                try:
                    uph_raw = raw_data.get('uph')
                    if uph_raw and str(uph_raw).strip().isdigit():
                        uph = int(str(uph_raw).strip())
                    else:
                        uph = 0
                except:
                    uph = 0
            else:
                # Si no hay datos en raw, usar lo que venga de la WO
                part_no = wo.get('codigo_modelo') or wo.get('modelo') or ''
                model_code = wo.get('modelo') or ''
                project = wo.get('nombre_modelo') or ''
                ct = 0.0
                uph = 0
            
            # Generar lot y crear plan
            # Usar fecha de importación si se proporciona, sino usar fecha_operacion de la WO
            if fecha_importacion:
                fecha_dt = fecha_importacion
            else:
                fecha_op = wo.get('fecha_operacion')
                try:
                    if isinstance(fecha_op, str):
                        fecha_dt = _fp_safe_date(fecha_op) or datetime.utcnow().date()
                    else:
                        fecha_dt = (fecha_op.date() if hasattr(fecha_op, 'date') else datetime.utcnow().date())
                except Exception:
                    fecha_dt = datetime.utcnow().date()
            
            lot_no = _fp_generate_lot_no(datetime.combine(fecha_dt, datetime.min.time()))
            
            # Insertar plan con wo_id para rastrear la importación
            insert_sql = (
                "INSERT INTO plan_main (lot_no, wo_id, wo_code, po_code, working_date, line, model_code, part_no, project, process, plan_count, ct, uph, routing, status, created_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PLAN',NOW())"
            )
            params = (
                lot_no,
                wo_id,  # Agregar wo_id para rastreo
                wo.get('codigo_wo'),
                wo.get('codigo_po'),
                fecha_dt,
                line,
                model_code,
                part_no,
                project,
                'MAIN',
                int(wo.get('cantidad_planeada') or 0),
                ct,
                uph,
                1,  # routing por defecto: DIA
            )
            execute_query(insert_sql, params)
            imported += 1
            plans.append({'lot_no': lot_no, 'wo_code': wo.get('codigo_wo')})
        return jsonify({'success': True, 'imported': imported, 'plans': plans, 'errors': errors})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cargar_template', methods=['POST'])
@login_requerido
def cargar_template():
    template_path = None  # Initialize template_path
    try:
        data = request.get_json()
        template_path = data.get('template_path')
        
        if not template_path:
            return jsonify({'error': 'No se especificó la ruta del template'}), 400
        
        # Validar que la ruta del template sea segura
        if '..' in template_path or template_path.startswith('/'):
            return jsonify({'error': 'Ruta de template no válida'}), 400
        
        # Renderizar el template y devolver el HTML
        html_content = render_template(template_path)
        return html_content
        
    except Exception as e:
        template_name = template_path if template_path else 'unknown'
        print(f"Error al cargar template {template_name}: {str(e)}")
        return jsonify({'error': f'Error al cargar el template: {str(e)}'}), 500

@app.route('/importar_excel_bom', methods=['POST'])
@login_requerido
def importar_excel_bom():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No se encontró el archivo'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No se seleccionó ningún archivo'})

    try:
        print("--- Iniciando importación de BOM ---")
        df = pd.read_excel(file)
        
        # Imprime las columnas detectadas para depuración
        print(f"Columnas detectadas en el Excel: {df.columns.tolist()}")
        
        registrador = session.get('usuario', 'desconocido')
        
        # Llamar a la nueva función de la base de datos
        resultado = insertar_bom_desde_dataframe(df, registrador)
        
        insertados = resultado.get('insertados', 0)
        omitidos = resultado.get('omitidos', 0)
        
        mensaje = f"Importación completada: {insertados} registros guardados."
        if omitidos > 0:
            mensaje += f" Se omitieron {omitidos} filas por no tener 'Modelo' o 'Número de parte'."
        
        print(f"--- Finalizando importación: {mensaje} ---")
        
        return jsonify({'success': True, 'message': mensaje})

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f"Ocurrió un error: {str(e)}"})

@app.route('/listar_modelos_bom', methods=['GET'])
@login_requerido
def listar_modelos_bom():
    """
    Devuelve la lista de modelos únicos disponibles en la tabla BOM
    """
    try:
        from .db_mysql import obtener_modelos_bom
        modelos = obtener_modelos_bom()
        return jsonify(modelos)
    except Exception as e:
        print(f"Error al obtener modelos BOM: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/listar_bom', methods=['POST'])
@login_requerido
def listar_bom():
    """
    Lista los registros de BOM, opcionalmente filtrados por modelo y classification
    """
    try:
        data = request.get_json()
        modelo = data.get('modelo', 'todos') if data else 'todos'
        classification = data.get('classification', None) if data else None
        
        bom_data = listar_bom_por_modelo(modelo, classification)
        return jsonify(bom_data)
        
    except Exception as e:
        print(f"Error al listar BOM: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/consultar_bom', methods=['GET'])
@login_requerido
def consultar_bom():
    """
    Consulta datos de BOM con filtros GET para la interfaz de Control de salida
    """
    try:
        # Obtener filtros de los parámetros de consulta
        modelo = request.args.get('modelo', '').strip()
        numero_parte = request.args.get('numero_parte', '').strip()
        
        # Si no hay filtros específicos, obtener todos los datos
        if not modelo and not numero_parte:
            bom_data = listar_bom_por_modelo('todos')
        else:
            # Aplicar filtros
            bom_data = listar_bom_por_modelo(modelo if modelo else 'todos')
            
            # Filtrar por número de parte si se proporciona
            if numero_parte and bom_data:
                bom_data = [
                    item for item in bom_data 
                    if numero_parte.lower() in str(item.get('numero_parte', '')).lower()
                ]
        
        return jsonify(bom_data)
        
    except Exception as e:
        print(f"Error al consultar BOM: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/buscar_material_por_numero_parte', methods=['GET'])
@login_requerido
def buscar_material_por_numero_parte():
    """
    Busca materiales en inventario por número de parte usando MySQL
    """
    try:
        numero_parte = request.args.get('numero_parte', '').strip()
        
        if not numero_parte:
            return jsonify({'success': False, 'error': 'Número de parte requerido'})
        
        # Usar funciones de MySQL en lugar de SQLite
        from .db_mysql import buscar_material_por_numero_parte_mysql, calcular_inventario_general_mysql
        
        # Buscar materiales por número de parte usando MySQL
        materiales = buscar_material_por_numero_parte_mysql(numero_parte)
        
        # Calcular inventario general para este número de parte
        inventario_info = calcular_inventario_general_mysql(numero_parte)
        
        # Preparar respuesta con información completa
        response_data = []
        for material in materiales:
            material_data = {
                'codigo_material_recibido': material['codigo_material_recibido'],
                'codigo_material_original': material['codigo_material_original'] or '',
                'codigo_material': material['codigo_material'] or '',
                'especificacion': material['especificacion'] or '',
                'numero_parte': material['numero_parte'],
                'cantidad_actual': material['cantidad_actual'] or 0,
                'numero_lote_material': material['numero_lote_material'] or '',
                'fecha_recibo': material['fecha_recibo'] or '',
                'database_type': 'MySQL'  # Indicador de que se está usando MySQL
            }
            response_data.append(material_data)
        
        # Agregar información del inventario general si está disponible
        result = {
            'success': True,
            'materiales': response_data,
            'total_materiales': len(response_data),
            'numero_parte_buscado': numero_parte,
            'database_type': 'MySQL'
        }
        
        if inventario_info:
            result['inventario_general'] = inventario_info
        
        if materiales:
            return jsonify(result)
        else:
            return jsonify({'success': False, 'error': f'No se encontraron materiales con número de parte: {numero_parte}'})
            
    except Exception as e:
        print(f"❌ ERROR en buscar_material_por_numero_parte (MySQL): {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def exportar_bom_a_excel(modelo=None, classification=None):
    """
    Función auxiliar para exportar datos de BOM a Excel con filtros opcionales
    """
    try:
        import tempfile
        import os
        
        # Construir la consulta SQL con filtros
        base_query = """
            SELECT modelo, codigo_material, numero_parte, side, tipo_material, 
                   classification, especificacion_material, vender, cantidad_total, 
                   cantidad_original, ubicacion, posicion_assy, material_sustituto, material_original, 
                   registrador, fecha_registro
            FROM bom 
        """
        
        where_clauses = []
        params = []
        
        if modelo:
            where_clauses.append("modelo = %s")
            params.append(modelo)
        
        if classification and classification != 'TODOS':
            where_clauses.append("classification = %s")
            params.append(classification)
        
        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)
        
        base_query += " ORDER BY modelo, codigo_material"
        
        # Ejecutar la consulta
        result = execute_query(base_query, tuple(params) if params else (), fetch='all')
        
        if not result:
            print(f"No se encontraron datos de BOM para exportar (modelo={modelo}, classification={classification})")
            return None
        
        # Crear DataFrame
        df = pd.DataFrame(result)
        
        # Renombrar columnas para mejor legibilidad
        column_mapping = {
            'modelo': 'Modelo',
            'codigo_material': 'Código de Material',
            'numero_parte': 'Número de Parte',
            'side': 'Side',
            'tipo_material': 'Tipo de Material',
            'classification': 'Classification',
            'especificacion_material': 'Especificación de Material',
            'vender': 'Vendor',
            'cantidad_total': 'Cantidad Total',
            'cantidad_original': 'Cantidad Original',
            'ubicacion': 'Ubicación',
            'posicion_assy': 'Posición ASSY',
            'material_sustituto': 'Material Sustituto',
            'material_original': 'Material Original',
            'registrador': 'Registrador',
            'fecha_registro': 'Fecha de Registro'
        }
        
        df = df.rename(columns=column_mapping)
        
        # Crear archivo temporal
        temp_file = tempfile.NamedTemporaryFile(
            suffix='.xlsx', 
            delete=False, 
            mode='wb'
        )
        
        # Escribir a Excel
        with pd.ExcelWriter(temp_file.name, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='BOM_Data', index=False)
            
            # Obtener el workbook y worksheet para formateo
            workbook = writer.book
            worksheet = writer.sheets['BOM_Data']
            
            # Ajustar ancho de columnas automáticamente
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                adjusted_width = min(max_length + 2, 50)  # Máximo 50 caracteres
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        temp_file.close()
        return temp_file.name
        
    except Exception as e:
        print(f"Error en exportar_bom_a_excel: {e}")
        traceback.print_exc()
        return None

@app.route('/exportar_excel_bom', methods=['GET'])
@login_requerido
def exportar_excel_bom():
    """
    Exporta datos de BOM a un archivo Excel, filtrados por modelo y classification
    """
    try:
        # Obtener parámetros de consulta
        modelo = request.args.get('modelo', None)
        classification = request.args.get('classification', None)
        
        if modelo and modelo.strip() and modelo != 'todos':
            # Exportar modelo específico con filtro opcional de classification
            archivo_temp = exportar_bom_a_excel(modelo, classification)
            
            # Construir nombre del archivo
            nombre_base = f'bom_export_{modelo}'
            if classification and classification != 'TODOS':
                nombre_base += f'_{classification}'
            download_name = f'{nombre_base}_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        else:
            # Exportar todos con filtro opcional
            archivo_temp = exportar_bom_a_excel(None, classification)
            nombre_base = 'bom_export_todos'
            if classification and classification != 'TODOS':
                nombre_base += f'_{classification}'
            download_name = f'{nombre_base}_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        if archivo_temp:
            return send_file(
                archivo_temp,
                as_attachment=True,
                download_name=download_name,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            return jsonify({'error': 'Error al generar el archivo Excel'}), 500
            
    except Exception as e:
        print(f"Error al exportar BOM: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bom/update', methods=['POST'])
@login_requerido
def api_bom_update():
    """
    Actualiza un registro de BOM existente
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
        
        # Validar campos requeridos
        codigo_material = data.get('codigoMaterial')
        modelo = data.get('modelo')
        
        if not codigo_material or not modelo:
            return jsonify({'error': 'Código de material y modelo son requeridos'}), 400
        
        # Construir query de actualización
        campos_actualizables = {
            'numero_parte': data.get('numeroParte'),
            'side': data.get('side'),
            'tipo_material': data.get('tipoMaterial'),
            'classification': data.get('classification'),
            'especificacion_material': data.get('especificacionMaterial'),
            'vender': data.get('vender'),
            'cantidad_total': data.get('cantidadTotal'),
            'cantidad_original': data.get('cantidadOriginal'),
            'ubicacion': data.get('ubicacion'),
            'posicion_assy': data.get('posicionAssy')
        }
        
        # Filtrar campos que no son None
        campos_update = {k: v for k, v in campos_actualizables.items() if v is not None}
        
        if not campos_update:
            return jsonify({'error': 'No hay campos para actualizar'}), 400
        
        # Construir query SQL
        set_clauses = []
        values = []
        
        for campo, valor in campos_update.items():
            set_clauses.append(f"`{campo}` = %s")
            values.append(valor)
        
        # Agregar condiciones WHERE
        values.append(codigo_material)
        values.append(modelo)
        
        query = f"""
            UPDATE bom
            SET {', '.join(set_clauses)}
            WHERE codigo_material = %s AND modelo = %s
        """
        
        print(f"🔄 Actualizando BOM: codigo_material={codigo_material}, modelo={modelo}")
        print(f"📝 Query: {query}")
        print(f"📊 Values: {values}")
        
        # Ejecutar actualización usando execute_query
        result = execute_query(query, tuple(values), fetch=None)
        
        # execute_query retorna el cursor o None
        if result is not None:
            return jsonify({
                'success': True,
                'message': 'BOM actualizado exitosamente'
            }), 200
        else:
            return jsonify({
                'success': True,
                'message': 'BOM actualizado (sin cambios o no encontrado)'
            }), 200
        
    except Exception as e:
        print(f"Error al actualizar BOM: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/bom/update-posiciones-assy', methods=['POST'])
def api_bom_update_posiciones_assy():
    """Actualiza múltiples posiciones ASSY en el BOM de forma optimizada"""
    try:
        data = request.get_json()
        print(f"🔄 Actualizando posiciones ASSY masivamente")
        
        if not data or 'cambios' not in data:
            return jsonify({'error': 'No se proporcionaron cambios'}), 400
        
        cambios = data.get('cambios', [])
        if not cambios:
            return jsonify({'error': 'Lista de cambios vacía'}), 400
        
        print(f"📦 Total de cambios a procesar: {len(cambios)}")
        
        # Usar executemany para actualizar todo en una sola transacción
        connection = get_db_connection()
        cursor = connection.cursor()
        
        try:
            # Preparar datos para executemany
            valores = []
            for cambio in cambios:
                codigo_material = cambio.get('codigoMaterial')
                modelo = cambio.get('modelo')
                posicion_assy = cambio.get('posicionAssy', '')
                
                if codigo_material and modelo:
                    valores.append((posicion_assy, codigo_material, modelo))
            
            if not valores:
                return jsonify({'error': 'No hay valores válidos para actualizar'}), 400
            
            # Ejecutar todas las actualizaciones en una sola transacción
            query = """
                UPDATE bom 
                SET posicion_assy = %s
                WHERE codigo_material = %s AND modelo = %s
            """
            
            cursor.executemany(query, valores)
            connection.commit()
            
            actualizados = cursor.rowcount
            print(f"✅ Total actualizado en una transacción: {actualizados} registros")
            
            cursor.close()
            connection.close()
            
            return jsonify({
                'success': True,
                'message': f'Se actualizaron {actualizados} posiciones ASSY correctamente',
                'actualizados': actualizados
            }), 200
            
        except Exception as e:
            connection.rollback()
            cursor.close()
            connection.close()
            raise e
        
    except Exception as e:
        print(f"❌ Error al actualizar posiciones ASSY: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/cargar_template_test', methods=['POST'])
def cargar_template_test():
    """Endpoint de prueba sin autenticación para debug"""
    try:
        data = request.get_json()
        template_path = data.get('template_path')
        
        if not template_path:
            return jsonify({'error': 'No se especificó la ruta del template'}), 400
        
        # Validar que la ruta del template sea segura
        if '..' in template_path or template_path.startswith('/'):
            return jsonify({'error': 'Ruta de template no válida'}), 400
        
        # Renderizar el template y devolver el HTML
        html_content = render_template(template_path)
        
        return html_content
        
    except Exception as e:
        error_msg = f"Error al cargar template {template_path}: {str(e)}"
        return jsonify({'error': error_msg}), 500


# A continuación se definen las rutas para manejar las entradas de materiales aéreos
@app.route('/guardar_entrada_aereo', methods=['POST'])
def guardar_entrada_aereo():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    # Usar función de db.py para agregar entrada aéreo
    entrada_data = {
        'forma_material': data.get('formaMaterial'),
        'cliente': data.get('cliente'),
        'codigo_material': data.get('codigoMaterial'),
        'fecha_fabricacion': data.get('fechaFab'),
        'origen_material': data.get('origenMaterial'),
        'cantidad_actual': data.get('cantidadActual'),
        'fecha_recibo': data.get('fechaRecibo'),
        'lote_material': data.get('loteMaterial'),
        'codigo_recibido': data.get('codRecibido'),
        'numero_parte': data.get('numParte'),
        'propiedad': data.get('propiedad')
    }
    
    success = agregar_entrada_aereo(entrada_data)
    if not success:
        return jsonify({'success': False, 'error': 'Error al guardar entrada aéreo'}), 500
    return jsonify({'success': True})


@app.route('/listar_entradas_aereo')
def listar_entradas_aereo():
    # Usar función de db.py para obtener entradas aéreo
    resultado = obtener_entradas_aereo()
    return jsonify(resultado)

# Función de conexión movida a db.py - usar get_db_connection() importada

# Rutas para manejo de materiales
@app.route('/guardar_material', methods=['POST'])
def guardar_material_route():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    try:
        # Obtener usuario de la sesión
        usuario_actual = session.get('usuario', 'USUARIO_MANUAL')
        
        # Preparar datos del material
        material_data = {
            'codigo_material': data.get('codigoMaterial'),
            'numero_parte': data.get('numeroParte'),
            'propiedad_material': data.get('propiedadMaterial'),
            'classification': data.get('classification'),
            'especificacion_material': data.get('especificacionMaterial'),
            'unidad_empaque': data.get('unidadEmpaque'),
            'ubicacion_material': data.get('ubicacionMaterial'),
            'vendedor': data.get('vendedor'),
            'prohibido_sacar': int(data.get('prohibidoSacar', 0)),
            'reparable': int(data.get('reparable', 0)),
            'nivel_msl': data.get('nivelMSL'),
            'espesor_msl': data.get('espesorMSL')
        }
        
        # Usar función de db_mysql.py con información del usuario
        print(f"🔍 Material registrado manualmente por: {usuario_actual}")
        success = guardar_material(material_data, usuario_registro=usuario_actual)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Error al guardar material'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/listar_materiales')
def listar_materiales():
    try:
        # Usar función de db_mysql.py que ya devuelve el formato correcto
        materiales = obtener_materiales() or []
        
        # La función obtener_materiales() ya devuelve el formato correcto
        # No necesitamos procesamiento adicional
        return jsonify(materiales)
        
    except Exception as e:
        print(f"Error obteniendo materiales: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventario/lotes_detalle', methods=['POST'])
@login_requerido
def consultar_lotes_detalle():
    """Endpoint para obtener detalles específicos de lotes por número de parte"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        numero_parte = data.get('numero_parte', '').strip()
        
        if not numero_parte:
            return jsonify({
                'success': False,
                'error': 'Número de parte requerido'
            }), 400
        
        from .db import is_mysql_connection
        using_mysql = is_mysql_connection()
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': False,
                'error': 'No se pudo conectar a la base de datos'
            }), 500
            
        cursor = conn.cursor()
        
        # Query para obtener todos los lotes de un número de parte específico (solo con inventario disponible)
        if using_mysql:
            query = '''
                SELECT 
                    codigo_material_recibido,
                    numero_lote_material,
                    total_entrada as cantidad_total_entrada,
                    total_salidas,
                    (total_entrada - total_salidas) as cantidad_disponible,
                    fecha_recibo,
                    fecha_fabricacion,
                    especificacion,
                    propiedad_material,
                    ubicacion_salida,
                    codigo_material,
                    codigo_material_original
                FROM (
                    SELECT 
                        cma.codigo_material_recibido,
                        cma.numero_lote_material,
                        SUM(cma.cantidad_actual) as total_entrada,
                        COALESCE((
                            SELECT SUM(cms.cantidad_salida) 
                            FROM control_material_salida cms 
                            WHERE cms.codigo_material_recibido = cma.codigo_material_recibido
                        ), 0) as total_salidas,
                        MIN(cma.fecha_recibo) as fecha_recibo,
                        MIN(cma.fecha_fabricacion) as fecha_fabricacion,
                        MIN(cma.especificacion) as especificacion,
                        MIN(cma.propiedad_material) as propiedad_material,
                        MIN(cma.ubicacion_salida) as ubicacion_salida,
                        MIN(cma.codigo_material) as codigo_material,
                        MIN(cma.codigo_material_original) as codigo_material_original
                    FROM control_material_almacen cma
                    WHERE cma.numero_parte = %s 
                    GROUP BY cma.codigo_material_recibido, cma.numero_lote_material
                ) lotes_calc
                WHERE (total_entrada - total_salidas) > 0
                ORDER BY fecha_recibo DESC
            '''
            cursor.execute(query, [numero_parte])
        else:
            # Fallback para SQLite (aunque no lo usamos)
            return jsonify({
                'success': False,
                'error': 'Solo MySQL soportado'
            }), 500
        rows = cursor.fetchall()
        
        lotes_detalle = []
        for i, row in enumerate(rows):
            try:
                lote_data = {
                    'codigo_material_recibido': row['codigo_material_recibido'],
                    'numero_lote': row['numero_lote_material'],
                    'cantidad_original': float(row['cantidad_total_entrada']) if row['cantidad_total_entrada'] else 0.0,
                    'total_salidas': float(row['total_salidas']) if row['total_salidas'] else 0.0,
                    'cantidad_disponible': float(row['cantidad_disponible']) if row['cantidad_disponible'] else 0.0,
                    'fecha_recibo': row['fecha_recibo'].strftime('%Y-%m-%d') if row['fecha_recibo'] else '',
                    'fecha_fabricacion': row['fecha_fabricacion'].strftime('%Y-%m-%d') if row['fecha_fabricacion'] else '',
                    'especificacion': row['especificacion'] or '',
                    'propiedad_material': row['propiedad_material'] or 'COMMON USE',
                    'ubicacion': row['ubicacion_salida'] or '',
                    'codigo_material': row['codigo_material'] or '',
                    'codigo_material_original': row['codigo_material_original'] or ''
                }
                lotes_detalle.append(lote_data)
            except Exception as e:
                print(f"❌ Error procesando fila {i+1}: {e}")
                print(f"❌ Datos de la fila: {row}")
                continue
        
        print(f" Detalles de lotes consultados: {len(lotes_detalle)} lotes encontrados para {numero_parte}")
        
        return jsonify({
            'success': True,
            'numero_parte': numero_parte,
            'lotes': lotes_detalle,
            'total_lotes': len(lotes_detalle)
        })
        
    except Exception as e:
        print(f"❌ Error al consultar detalles de lotes: {e}")
        return jsonify({
            'success': False,
            'error': f'Error al consultar detalles de lotes: {str(e)}'
        }), 500
        
    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass
        try:
            if conn is not None:
                conn.close()
        except:
            pass

@app.route('/importar_excel', methods=['POST'])
def importar_excel():
    conn = None
    cursor = None
    temp_path = None
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No se proporcionó archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400
        
        if not file or not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'error': 'Formato de archivo no válido. Use .xlsx o .xls'}), 400
        
        # Guardar el archivo temporalmente
        filename = secure_filename(file.filename)
        temp_path = os.path.join(os.path.dirname(__file__), 'temp_' + filename)
        file.save(temp_path)
        
        # Leer el archivo Excel
        try:
            df = pd.read_excel(temp_path, engine='openpyxl' if filename.endswith('.xlsx') else 'xlrd')
        except Exception as e:
            try:
                df = pd.read_excel(temp_path)
            except Exception as e2:
                return jsonify({'success': False, 'error': f'Error al leer el archivo Excel: {str(e2)}'}), 500
        
        # Verificar que el DataFrame no esté vacío
        if df.empty:
            return jsonify({'success': False, 'error': 'El archivo Excel está vacío'}), 400
        
        # Obtener las columnas del Excel
        columnas_excel = df.columns.tolist()
        print(f"Columnas detectadas en Excel: {columnas_excel}")
        
        # Mapeo de columnas (flexible para diferentes nombres)
        mapeo_columnas = {
            'codigo_material': ['Codigo de material', 'Código de material', 'codigo_material', 'Código+de+material'],
            'numero_parte': ['Numero de parte', 'Número de parte', 'numero_parte', 'Número+de+parte'],
            'propiedad_material': ['Propiedad de material', 'propiedad_material', 'Propiedad+de+material'],
            'classification': ['Classification', 'classification', 'Clasificación', 'Clasificacion'],
            'especificacion_material': ['Especificacion de material', 'Especificación de material', 'especificacion_material', 'Especificación+de+material'],
            'unidad_empaque': ['Unidad de empaque', 'unidad_empaque', 'Unidad+de+empaque'],
            'ubicacion_material': ['Ubicacion de material', 'Ubicación de material', 'ubicacion_material', 'Ubicación+de+material'],
            'vendedor': ['Vendedor', 'vendedor', 'Proveedor', 'proveedor'],
            'prohibido_sacar': ['Prohibido sacar', 'prohibido_sacar', 'Prohibido+sacar'],
            'reparable': ['Reparable', 'reparable'],
            'nivel_msl': ['Nivel de MSL', 'nivel_msl', 'Nivel+de+MSL'],
            'espesor_msl': ['Espesor de MSL', 'espesor_msl', 'Espesor+de+MSL']
        }
        
        def obtener_valor_columna(row, campo):
            """Obtiene el valor de una columna usando el mapeo flexible"""
            posibles_nombres = mapeo_columnas.get(campo, [campo])
            
            for nombre in posibles_nombres:
                if nombre in row:
                    valor = row[nombre]
                    if pd.isna(valor) or valor is None:
                        return ''
                    return str(valor).strip()
            
            # Si no encuentra la columna, usar posición por índice como fallback
            try:
                campos_orden = ['codigo_material', 'numero_parte', 'propiedad_material', 'classification',
                               'especificacion_material', 'unidad_empaque', 'ubicacion_material', 'vendedor',
                               'prohibido_sacar', 'reparable', 'nivel_msl', 'espesor_msl']
                if campo in campos_orden:
                    idx = campos_orden.index(campo)
                    if idx < len(columnas_excel):
                        valor = row.get(columnas_excel[idx], '')
                        if pd.isna(valor) or valor is None:
                            return ''                   
                        return str(valor).strip()
            except:
                pass
            
            return ''
        
        def convertir_checkbox(valor):
            """Convierte valores de checkbox del Excel a 0 o 1"""
            if not valor or pd.isna(valor):
                return '0'
            
            valor_str = str(valor).strip().lower()
            
            # Valores que se consideran como "true" o "checked"
            valores_true = ['1', 'true', 'yes', 'sí', 'si', 'checked', 'x', 'on', 'habilitado', 'activo']
            # Valores que se consideran como "false" o "unchecked"
            valores_false = ['0', 'false', 'no', 'unchecked', 'off', 'deshabilitado', 'inactivo', '']
            
            if valor_str in valores_true:
                return '1'
            elif valor_str in valores_false:
                return '0'
            else:
                # Si no reconoce el valor, asumir false por seguridad
                return '0'
        
        def limpiar_numero(valor):
            """Limpia números eliminando decimales innecesarios (.0)"""
            if not valor or pd.isna(valor):
                return ''
            
            try:
                numero = float(valor)
                if numero % 1 == 0:  # Es un número entero
                    return str(int(numero))  # Devolver como entero sin decimales
                else:
                    return str(numero)  # Mantener decimales si son necesarios
            except (ValueError, TypeError):
                # Si no es un número válido, devolver como string
                return str(valor).strip()
        
        # Insertar los datos usando funciones de MySQL
        registros_insertados = 0
        errores = []
        
        for index, row in df.iterrows():
            try:
                # Convert index to int safely
                row_number = int(index) + 1 if isinstance(index, (int, float)) else len(errores) + registros_insertados + 1
                
                # Obtener valores usando el mapeo flexible
                codigo_material = obtener_valor_columna(row, 'codigo_material')
                numero_parte = obtener_valor_columna(row, 'numero_parte')
                propiedad_material = obtener_valor_columna(row, 'propiedad_material')
                classification = obtener_valor_columna(row, 'classification')
                especificacion_material = obtener_valor_columna(row, 'especificacion_material')
                unidad_empaque = limpiar_numero(obtener_valor_columna(row, 'unidad_empaque'))
                ubicacion_material = obtener_valor_columna(row, 'ubicacion_material')
                vendedor = obtener_valor_columna(row, 'vendedor')
                
                # Convertir valores de checkbox correctamente
                prohibido_sacar = int(convertir_checkbox(obtener_valor_columna(row, 'prohibido_sacar')))
                reparable = int(convertir_checkbox(obtener_valor_columna(row, 'reparable')))
                
                nivel_msl = limpiar_numero(obtener_valor_columna(row, 'nivel_msl'))
                espesor_msl = obtener_valor_columna(row, 'espesor_msl')
                
                # Validar que al menos el código de material no esté vacío
                if not codigo_material:
                    errores.append(f"Fila {row_number}: Código de material vacío")
                    continue
                
                # Preparar datos del material
                material_data = {
                    'codigo_material': codigo_material,
                    'numero_parte': numero_parte,
                    'propiedad_material': propiedad_material,
                    'classification': classification,
                    'especificacion_material': especificacion_material,
                    'unidad_empaque': unidad_empaque,
                    'ubicacion_material': ubicacion_material,
                    'vendedor': vendedor,
                    'prohibido_sacar': prohibido_sacar,
                    'reparable': reparable,
                    'nivel_msl': nivel_msl,
                    'espesor_msl': espesor_msl
                }
                
                # Obtener usuario de la sesión para registro
                usuario_actual = session.get('usuario', 'USUARIO_MANUAL')
                
                success = guardar_material(material_data, usuario_registro=usuario_actual)
                
                if success:
                    registros_insertados += 1
                else:
                    error_msg = f"Fila {row_number}: Error al guardar en base de datos"
                    errores.append(error_msg)
                
            except Exception as e:
                row_number = int(index) + 1 if isinstance(index, (int, float)) else len(errores) + registros_insertados + 1
                error_msg = f"Error en fila {row_number}: {str(e)}"
                errores.append(error_msg)
                continue
        
        # Preparar respuesta
        mensaje = f'Se importaron {registros_insertados} registros exitosamente'
        if errores:
            mensaje += f'. Se encontraron {len(errores)} errores'
            if len(errores) <= 5:
                mensaje += f': {"; ".join(errores)}'
        
        return jsonify({'success': True, 'message': mensaje})
        
    except Exception as e:
        print(f"Error general en importar_excel: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error al procesar el archivo: {str(e)}'}), 500
        
    finally:
        # Limpiar archivo temporal
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass

@app.route('/actualizar_campo_material', methods=['POST'])
def actualizar_campo_material():
    """Actualizar un campo específico de un material"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No se proporcionaron datos'}), 400
        
        codigo_material = data.get('codigoMaterial')
        campo = data.get('campo')
        valor = data.get('valor')
        
        if not codigo_material or not campo:
            return jsonify({'success': False, 'error': 'Faltan datos requeridos'}), 400
        
        # Validar que el campo es permitido para actualizar
        campos_permitidos = ['prohibidoSacar', 'reparable']
        if campo not in campos_permitidos:
            return jsonify({'success': False, 'error': 'Campo no permitido para actualización'}), 400
        
        # Mapear nombres de campo a nombres de columna en la base de datos
        mapeo_campos = {
            'prohibidoSacar': 'prohibido_sacar',
            'reparable': 'reparable'
        }
        
        columna_db = mapeo_campos.get(campo)
        if not columna_db:
            return jsonify({'success': False, 'error': 'Campo no válido'}), 400
        
        # Verificar que el material existe
        query_verificar = 'SELECT codigo_material FROM materiales WHERE codigo_material = %s'
        material_existe = execute_query(query_verificar, (codigo_material,), fetch='one')
        
        if not material_existe:
            return jsonify({'success': False, 'error': 'Material no encontrado'}), 404
        
        # Actualizar el campo
        query_actualizar = f'UPDATE materiales SET {columna_db} = %s WHERE codigo_material = %s'
        rows_affected = execute_query(query_actualizar, (int(valor), codigo_material))
        
        if rows_affected == 0:
            return jsonify({'success': False, 'error': 'No se pudo actualizar el material'}), 500
        
        return jsonify({'success': True, 'message': 'Campo actualizado correctamente'})
        
    except Exception as e:
        print(f"Error al actualizar campo: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno del servidor: {str(e)}'}), 500

@app.route('/actualizar_material_completo', methods=['POST'])
@login_requerido
def actualizar_material_completo_route():
    """Actualizar todos los campos de un material existente"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No se recibieron datos'}), 400
        
        codigo_original = data.get('codigo_material_original')
        nuevos_datos = data.get('nuevos_datos')
        
        if not codigo_original:
            return jsonify({'success': False, 'error': 'Código de material original requerido'}), 400
        
        if not nuevos_datos:
            return jsonify({'success': False, 'error': 'Nuevos datos requeridos'}), 400
        
        # Limpiar el código original (eliminar espacios y caracteres extraños)
        codigo_limpio = str(codigo_original).strip()
        
        # Llamar a la función de db_mysql
        resultado = actualizar_material_completo(codigo_limpio, nuevos_datos)
        
        if resultado['success']:
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error en actualizar_material_completo_route: {error_msg}")
        return jsonify({'success': False, 'error': f'Error interno del servidor: {error_msg}'}), 500

@app.route('/debug_materiales', methods=['GET'])
@login_requerido
def debug_materiales():
    """Endpoint temporal para debug - listar algunos materiales"""
    try:
        # Obtener algunos materiales para debug
        query = "SELECT codigo_material, numero_parte FROM materiales LIMIT 10"
        materiales = execute_query(query, fetch='all')
        
        resultado = {
            'total_encontrados': len(materiales) if materiales else 0,
            'materiales': []
        }
        
        if materiales:
            for material in materiales:
                resultado['materiales'].append({
                    'codigo_material': material['codigo_material'],
                    'numero_parte': material['numero_parte'],
                    'codigo_length': len(material['codigo_material']) if material['codigo_material'] else 0
                })
        
        return jsonify(resultado), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/debug_estructura_materiales', methods=['GET'])
@login_requerido
def debug_estructura_materiales():
    """Endpoint temporal para debug - ver estructura de tabla materiales"""
    try:
        # Obtener estructura de la tabla
        query = "DESCRIBE materiales"
        estructura = execute_query(query, fetch='all')
        
        resultado = {
            'columnas': []
        }
        
        if estructura:
            for columna in estructura:
                resultado['columnas'].append({
                    'nombre': columna['Field'],
                    'tipo': columna['Type'],
                    'nulo': columna['Null'],
                    'default': columna['Default']
                })
        
        return jsonify(resultado), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/exportar_excel', methods=['GET'])
@login_requerido
def exportar_excel():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener todos los materiales
        cursor.execute('''
            SELECT codigo_material, numero_parte, propiedad_material, classification, 
                   especificacion_material, unidad_empaque, ubicacion_material, vendedor, 
                   prohibido_sacar, reparable, nivel_msl, espesor_msl, fecha_registro
            FROM materiales
            ORDER BY fecha_registro DESC
        ''')
        materiales = cursor.fetchall()
        
        conn.close()
        
        if not materiales:
            # Crear un DataFrame vacío con headers
            df = pd.DataFrame(columns=[
                'Código de material', 'Número de parte', 'Propiedad de material', 
                'Classification', 'Especificación de material', 'Unidad de empaque', 
                'Ubicación de material', 'Vendedor', 'Prohibido sacar', 'Reparable', 
                'Nivel de MSL', 'Espesor de MSL', 'Fecha de registro'
            ])
        else:
            # Convertir a DataFrame
            data = []
            for material in materiales:
                data.append({
                    'Código de material': material['codigo_material'],
                    'Número de parte': material['numero_parte'],
                    'Propiedad de material': material['propiedad_material'],
                    'Classification': material['classification'],
                    'Especificación de material': material['especificacion_material'],
                    'Unidad de empaque': material['unidad_empaque'],
                    'Ubicación de material': material['ubicacion_material'],
                    'Vendedor': material['vendedor'],
                    'Prohibido sacar': 'Sí' if material['prohibido_sacar'] == 1 else 'No',
                    'Reparable': 'Sí' if material['reparable'] == 1 else 'No',
                    'Nivel de MSL': material['nivel_msl'],
                    'Espesor de MSL': material['espesor_msl'],
                    'Fecha de registro': material['fecha_registro']
                })
            df = pd.DataFrame(data)
            print(f"DataFrame creado con {len(df)} filas")
        
        # Crear archivo Excel en memoria
        from io import BytesIO
        output = BytesIO()
        
        print("Creando archivo Excel...")
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Materiales')
        
        output.seek(0)
        print("Archivo Excel creado exitosamente")
        
        # Crear nombre del archivo
        fecha_actual = obtener_fecha_hora_mexico().strftime('%Y-%m-%d_%H-%M-%S')
        nombre_archivo = f'materiales_export_{fecha_actual}.xlsx'
        
        print(f"Enviando archivo: {nombre_archivo}")
        # Devolver el archivo directamente
        return send_file(
            output,
            as_attachment=True,
            download_name=nombre_archivo,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        print(f"Error en exportar_excel: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/obtener_codigos_material')
def obtener_codigos_material():
    """Endpoint para obtener códigos de material para el dropdown del control de almacén con búsqueda inteligente"""
    conn = None
    cursor = None
    try:
        print("🔍 Iniciando obtener_codigos_material...")
        
        # Obtener parámetro de búsqueda si existe
        busqueda = request.args.get('busqueda', '').strip()
        
        conn = get_db_connection()
        if not conn:
            print("❌ Error: No se pudo obtener conexión a la base de datos")
            return jsonify([])
        
        cursor = conn.cursor()
        
        # Si hay parámetro de búsqueda, implementar búsqueda inteligente
        if busqueda:
            print(f"🔍 Búsqueda inteligente para: '{busqueda}'")
            
            # Query con búsqueda parcial usando LIKE con wildcards
            # Busca en código_material y numero_parte
            cursor.execute('''
                SELECT codigo_material, numero_parte, especificacion_material, 
                       propiedad_material, unidad_empaque,
                       CASE 
                           WHEN codigo_material LIKE %s THEN 1
                           WHEN numero_parte LIKE %s THEN 2
                           WHEN codigo_material LIKE %s THEN 3
                           WHEN numero_parte LIKE %s THEN 4
                           ELSE 5
                       END as relevancia
                FROM materiales 
                WHERE codigo_material IS NOT NULL AND codigo_material != ''
                AND (
                    codigo_material LIKE %s OR 
                    numero_parte LIKE %s OR
                    especificacion_material LIKE %s OR
                    propiedad_material LIKE %s
                )
                ORDER BY relevancia ASC, codigo_material ASC
                LIMIT 50
            ''', (
                f'{busqueda}%',  # Empieza con
                f'{busqueda}%',  # Empieza con (numero_parte)
                f'%{busqueda}%',  # Contiene
                f'%{busqueda}%',  # Contiene (numero_parte)
                f'%{busqueda}%',  # Para WHERE - contiene en codigo_material
                f'%{busqueda}%',  # Para WHERE - contiene en numero_parte
                f'%{busqueda}%',  # Para WHERE - contiene en especificacion
                f'%{busqueda}%'   # Para WHERE - contiene en propiedad
            ))
        else:
            # Sin búsqueda, devolver todos los materiales
            cursor.execute('''
                SELECT codigo_material, numero_parte, especificacion_material, 
                       propiedad_material, unidad_empaque
                FROM materiales 
                WHERE codigo_material IS NOT NULL AND codigo_material != ''
                ORDER BY codigo_material ASC
                LIMIT 1000
            ''')
        
        rows = cursor.fetchall()
        
        print(f" Se encontraron {len(rows)} materiales" + (f" para búsqueda '{busqueda}'" if busqueda else ""))
        
        codigos = []
        for row in rows:
            # Usar nombres de columnas en lugar de índices (MySQL con PyMySQL devuelve diccionarios)
            material = {
                'codigo': row['codigo_material'] if row['codigo_material'] else '',
                'nombre': row['numero_parte'] if row['numero_parte'] else row['codigo_material'] if row['codigo_material'] else '',
                'spec': row['especificacion_material'] if row['especificacion_material'] else '',
                'numero_parte': row['numero_parte'] if row['numero_parte'] else '',
                'cantidad_estandarizada': str(row['unidad_empaque']) if row['unidad_empaque'] else '',
                'propiedad_material': row['propiedad_material'] if row['propiedad_material'] else '',
                'especificacion_material': row['especificacion_material'] if row['especificacion_material'] else '',
                # Agregar campo de coincidencia para debugging
                'coincidencia': busqueda in (row['codigo_material'] or '') or busqueda in (row['numero_parte'] or '') if busqueda else False
            }
            codigos.append(material)
        
        print(f"📤 Devolviendo {len(codigos)} materiales formateados")
        return jsonify(codigos)
        
    except Exception as e:
        print(f"❌ Error en obtener_codigos_material MySQL: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # En caso de error, devolver datos de prueba para que el sistema funcione
        print(" Devolviendo datos de prueba como fallback...")
        datos_prueba = [
            {
                'codigo': 'M2606809020', 
                'nombre': 'M2606809020', 
                'spec': '68F 1608', 
                'cantidad_estandarizada': '1000', 
                'propiedad_material': '68F 1608',
                'numero_parte': 'M2606809020',
                'especificacion_material': '68F 1608',
                'coincidencia': False
            },
            {
                'codigo': 'M2609109005', 
                'nombre': 'M2609109005', 
                'spec': '91F 1608', 
                'cantidad_estandarizada': '2000', 
                'propiedad_material': '91F 1608',
                'numero_parte': 'M2609109005',
                'especificacion_material': '91F 1608',
                'coincidencia': False
            }
        ]
        return jsonify(datos_prueba)
        
    finally:
        try:
            if cursor is not None:
                cursor.close()
        except:
            pass
        try:
            if conn is not None:
                conn.close()
        except:
            pass

@app.route('/control_almacen')
@login_requerido
def control_almacen():
    return render_template('Control de material/Control de material de almacen.html')

@app.route('/control_salida')
@login_requerido
def control_salida():
    """
    🚀 Ruta principal para Control de Salida de Material
    
    Características:
    - Autenticación requerida
    - Información del usuario para personalización
    - Configuración inicial del módulo
    - Datos de contexto para mejor experiencia
    """
    try:
        usuario = session.get('usuario', 'Usuario')
        
        # Obtener información adicional del usuario si está disponible
        user_info = {
            'username': usuario,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'module': 'Control de Salida'
        }
        
        print(f" Control de Salida cargado para usuario: {usuario}")
        
        return render_template('Control de material/Control de salida.html', 
                             usuario=usuario,
                             user_info=user_info)
                             
    except Exception as e:
        print(f"❌ Error al cargar Control de Salida: {e}")
        return render_template('Control de material/Control de salida.html', 
                             usuario='Usuario',
                             error='Error al cargar el módulo')

@app.route('/control_calidad')
@login_requerido
def control_calidad():
    return render_template('Control de material/Control de calidad.html')

@app.route('/guardar_control_almacen', methods=['POST'])
@login_requerido
def guardar_control_almacen():
    """Endpoint para guardar los datos del formulario de control de material de almacén"""
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        if not data.get('codigo_material_original'):
            return jsonify({'success': False, 'error': 'Código de material original es requerido'}), 400
        
        # Usar la función correcta de db.py
        resultado = agregar_control_material_almacen(data)
        
        if resultado:
            print(f"✅ Registro de almacén guardado exitosamente para {data.get('numero_parte', 'N/A')}")
            
            return jsonify({
                'success': True, 
                'message': 'Registro guardado exitosamente'
            })
        else:
            return jsonify({'success': False, 'error': 'Error al guardar en la base de datos'}), 500
        
    except Exception as e:
        print(f"Error al guardar control de almacén: {str(e)}")


@app.route('/obtener_secuencial_lote_interno', methods=['POST'])
@login_requerido
def obtener_secuencial_lote_interno():
    """Obtener el siguiente secuencial para lote interno del día"""
    try:
        data = request.get_json()
        fecha = data.get('fecha', '')  # Formato: DD.MM.YYYY
        
        if not fecha:
            return jsonify({'siguiente_secuencial': 1}), 200
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Obtener el máximo secuencial para esta fecha en control_material_almacen
            # Buscar lotes internos que coincidan con el patrón DD.MM.YYYY.XXXX
            query = '''
                SELECT numero_lote_material,
                       CAST(SUBSTRING_INDEX(numero_lote_material, '.', -1) AS UNSIGNED) as seq
                FROM control_material_almacen
                WHERE numero_lote_material LIKE %s
                ORDER BY seq DESC
                LIMIT 1
            '''
            cursor.execute(query, (f'{fecha}.%',))
            
            result = cursor.fetchone()
            
            print(f"DEBUG: Consultando secuencial para fecha: {fecha}")
            print(f"DEBUG: Resultado de query: {result}")
            
            # Si get_db_connection devuelve DictCursor, result será dict
            # Si no, será tupla
            if result:
                if isinstance(result, dict):
                    max_seq = result.get('seq', 0) or 0
                else:
                    # Tupla: (numero_lote_material, seq)
                    max_seq = result[1] if len(result) > 1 and result[1] else 0
            else:
                max_seq = 0
            
            siguiente_secuencial = max_seq + 1
            
            print(f"DEBUG: max_seq encontrado: {max_seq}, siguiente: {siguiente_secuencial}")
            
            conn.close()
            return jsonify({'siguiente_secuencial': siguiente_secuencial}), 200
            
        except Exception as e:
            print(f"Error consultando secuencial: {e}")
            conn.close()
            return jsonify({'siguiente_secuencial': 1}), 200
            
    except Exception as e:
        print(f"Error en obtener_secuencial_lote_interno: {str(e)}")
        return jsonify({'error': str(e), 'siguiente_secuencial': 1}), 500

@app.route('/consultar_control_almacen', methods=['GET'])
@login_requerido
def consultar_control_almacen():
    """Endpoint para consultar los registros de control de material de almacén"""
    conn = None
    cursor = None
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Construir query con filtros de fecha si se proporcionan
        query = '''
            SELECT * FROM control_material_almacen 
            WHERE 1=1
        '''
        params = []
        
        if fecha_inicio:
            query += ' AND date(fecha_recibo) >= %s'
            params.append(fecha_inicio)
            
        if fecha_fin:
            query += ' AND date(fecha_recibo) <= %s'
            params.append(fecha_fin)
            
        query += ' ORDER BY fecha_registro DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        registros = []
        for row in rows:
            registros.append({
                'id': row['id'],
                'forma_material': row['forma_material'],
                'cliente': row['cliente'],
                'codigo_material_original': row['codigo_material_original'],
                'codigo_material': row['codigo_material'],
                'material_importacion_local': row['material_importacion_local'],
                'fecha_recibo': row['fecha_recibo'],
                'fecha_fabricacion': row['fecha_fabricacion'],
                'cantidad_actual': row['cantidad_actual'],
                'numero_lote_material': row['numero_lote_material'],
                'codigo_material_recibido': row['codigo_material_recibido'],
                'numero_parte': row['numero_parte'],
                'cantidad_estandarizada': row['cantidad_estandarizada'],
                'codigo_material_final': row['codigo_material_final'],
                'propiedad_material': row['propiedad_material'],
                'especificacion': row['especificacion'],
                'material_importacion_local_final': row['material_importacion_local_final'],
                'estado_desecho': row['estado_desecho'],
                'ubicacion_salida': row['ubicacion_salida'],
                'fecha_registro': row['fecha_registro']
            })
        
        return jsonify(registros)
        
    except Exception as e:
        print(f"Error al consultar control de almacén: {str(e)}")
        return jsonify({'error': f'Error al consultar: {str(e)}'}), 500
        
    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass

@app.route('/actualizar_control_almacen', methods=['POST'])
@login_requerido
def actualizar_control_almacen():
    """Endpoint para actualizar un registro de control de material de almacén"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        
        if not data or 'id' not in data:
            return jsonify({'success': False, 'error': 'ID no proporcionado'}), 400
        
        # Obtener el ID del registro a actualizar
        registro_id = data['id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # PASO 1: Obtener los valores actuales de la base de datos
        cursor.execute("SELECT * FROM control_material_almacen WHERE id = %s", (registro_id,))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({'success': False, 'error': 'Registro no encontrado'}), 404
        
        # Convertir a dict usando nombres de columna
        columns = [desc[0] for desc in cursor.description]
        valores_actuales = dict(zip(columns, row))
        
        # PASO 2: Comparar y construir query solo para campos que cambiaron
        campos_actualizables = [
            'forma_material', 'cliente', 'codigo_material_original', 'codigo_material',
            'material_importacion_local', 'fecha_recibo', 'fecha_fabricacion',
            'cantidad_actual', 'numero_lote_material', 'codigo_material_recibido',
            'numero_parte', 'cantidad_estandarizada', 'codigo_material_final',
            'propiedad_material', 'especificacion', 'material_importacion_local_final',
            'estado_desecho', 'ubicacion_salida'
        ]
        
        sets = []
        params = []
        campos_modificados = []
        
        for campo in campos_actualizables:
            # Solo procesar campos que fueron enviados explícitamente
            if campo in data:
                valor_nuevo = data[campo]
                valor_actual = valores_actuales.get(campo)
                
                # Normalizar valores para comparación
                # Manejar campos de fecha vacíos
                if campo in ['fecha_recibo', 'fecha_fabricacion']:
                    if valor_nuevo == '':
                        valor_nuevo = None
                    # Convertir datetime a string para comparación
                    if valor_actual is not None:
                        valor_actual = str(valor_actual)
                
                # Manejar conversión de estado_desecho (texto a entero)
                if campo == 'estado_desecho':
                    if valor_nuevo == 'Activo' or valor_nuevo == '1' or valor_nuevo == 1:
                        valor_nuevo = 1
                    elif valor_nuevo == 'Inactivo' or valor_nuevo == 'Desecho' or valor_nuevo == '0' or valor_nuevo == 0:
                        valor_nuevo = 0
                    else:
                        valor_nuevo = 1 if valor_nuevo else 0
                
                # Convertir ambos valores a string para comparación consistente
                valor_nuevo_str = str(valor_nuevo) if valor_nuevo is not None else ''
                valor_actual_str = str(valor_actual) if valor_actual is not None else ''
                
                # Solo actualizar si los valores son diferentes
                if valor_nuevo_str != valor_actual_str:
                    sets.append(f"{campo} = %s")
                    params.append(valor_nuevo)
                    campos_modificados.append(campo)
                    print(f"✓ Campo MODIFICADO: {campo} = '{valor_actual}' -> '{valor_nuevo}'")
                else:
                    print(f"⚪ Campo SIN CAMBIOS: {campo} = '{valor_actual}'")
            else:
                print(f"➖ Campo NO ENVIADO (se mantiene): {campo} = '{valores_actuales.get(campo)}'")
        
        if not sets:
            return jsonify({
                'success': True, 
                'message': 'No hay cambios que guardar',
                'campos_modificados': []
            })
        
        # Agregar ID al final de los parámetros
        params.append(registro_id)
        
        # Query de actualización solo para campos modificados
        query = f"""
            UPDATE control_material_almacen 
            SET {', '.join(sets)}
            WHERE id = %s
        """
        
        print(f"📤 Query SQL: {query}")
        print(f"📤 Parámetros: {params}")
        print(f"📝 Campos modificados: {campos_modificados}")
        
        # Ejecutar la actualización
        cursor.execute(query, params)
        conn.commit()
        
        print(f"✅ Filas afectadas: {cursor.rowcount}")
        
        if cursor.rowcount > 0:
            print(f"Registro de control de almacén actualizado: ID {registro_id}")
            
            # Verificar si necesitamos actualizar el inventario consolidado
            if any(campo in campos_modificados for campo in ['cantidad_actual', 'codigo_material']):
                try:
                    from app.db import actualizar_inventario_consolidado_entrada
                    actualizar_inventario_consolidado_entrada()
                    print("Inventario consolidado actualizado automáticamente")
                except Exception as e:
                    print(f"Error al actualizar inventario consolidado: {str(e)}")
            
            return jsonify({
                'success': True, 
                'message': f'Registro actualizado exitosamente. Campos modificados: {", ".join(campos_modificados)}',
                'campos_modificados': campos_modificados
            })
        else:
            print(f"❌ No se pudo actualizar el registro con ID: {registro_id}")
            return jsonify({'success': False, 'error': 'No se pudo actualizar el registro'}), 500
        
    except Exception as e:
        print(f"Error al actualizar control de almacén: {str(e)}")
        return jsonify({'success': False, 'error': f'Error al actualizar: {str(e)}'}), 500
        
    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass

@app.route('/guardar_cliente_seleccionado', methods=['POST'])
@login_requerido
def guardar_cliente_seleccionado():
    """Guardar la selección de cliente del usuario"""
    try:
        data = request.get_json()
        if not data or 'cliente' not in data:
            return jsonify({'success': False, 'error': 'Cliente no proporcionado'}), 400
            
        cliente = data['cliente']
        usuario = session.get('usuario', 'default')
        
        # Guardar la configuración
        if guardar_configuracion_usuario(usuario, 'cliente_seleccionado', cliente):
            return jsonify({'success': True, 'message': 'Cliente guardado exitosamente'})
        else:
            return jsonify({'success': False, 'error': 'Error al guardar cliente'}), 500
            
    except Exception as e:
        print(f"Error en guardar_cliente_seleccionado: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500

@app.route('/cargar_cliente_seleccionado', methods=['GET'])
@login_requerido  
def cargar_cliente_seleccionado():
    """Cargar la última selección de cliente del usuario"""
    try:
        usuario = session.get('usuario', 'default')
        config = cargar_configuracion_usuario(usuario)
        cliente = config.get('cliente_seleccionado', '') if config else ''
        
        return jsonify({'success': True, 'cliente': cliente})
        
    except Exception as e:
        print(f"Error en cargar_cliente_seleccionado: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500

@app.route('/actualizar_estado_desecho_almacen', methods=['POST'])
@login_requerido
def actualizar_estado_desecho_almacen():
    """Actualizar el estado de desecho de un registro de control de almacén"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No se proporcionaron datos'}), 400
            
        registro_id = data.get('id')
        estado_desecho = data.get('estado_desecho', 0)
        
        if not registro_id:
            return jsonify({'success': False, 'error': 'ID de registro no proporcionado'}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Convertir a entero (0 o 1)
        estado_valor = 1 if estado_desecho else 0
        
        cursor.execute('''
            UPDATE control_material_almacen 
            SET estado_desecho = %s 
            WHERE id = %s
        ''', (estado_valor, registro_id))
        
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'error': 'Registro no encontrado'}), 404
            
        conn.commit()
        return jsonify({'success': True, 'message': 'Estado de desecho actualizado correctamente'})
        
    except Exception as e:
        print(f"Error al actualizar estado de desecho: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500
        
    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass

@app.route('/obtener_siguiente_secuencial', methods=['GET'])
def obtener_siguiente_secuencial():
    """
    Obtiene el siguiente número secuencial para el código de material recibido.
    Formato corregido: NUMERO_PARTE,YYYYMMDD0001 (donde 0001 incrementa por cada registro del mismo número de parte y fecha)
    
    Ejemplos:
    - 0CE106AH638,202507080001 (primer registro del día)
    - 0CE106AH638,202507080002 (segundo registro del día)  
    - 0CE106AH638,202507080003 (tercer registro del día)
    """
    try:
        # Obtener el código de material del parámetro de la URL
        codigo_material = request.args.get('codigo_material', '')
        
        if not codigo_material:
            return jsonify({
                'success': False,
                'error': 'Código de material es requerido',
                'siguiente_secuencial': 1
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Primero buscar el número de parte correspondiente al código de material
        query_numero_parte = """
        SELECT numero_parte
        FROM materiales 
        WHERE codigo_material = %s
        LIMIT 1
        """
        
        cursor.execute(query_numero_parte, (codigo_material,))
        resultado_numero_parte = cursor.fetchone()
        
        if resultado_numero_parte:
            numero_parte = resultado_numero_parte['numero_parte']
            print(f"🔍 Número de parte encontrado: '{numero_parte}' para código: '{codigo_material}'")
        else:
            numero_parte = codigo_material  # Fallback al código original
            print(f"⚠️ No se encontró número de parte, usando código material: '{numero_parte}'")
        
        # Obtener la fecha actual en formato YYYYMMDD
        fecha_actual = obtener_fecha_hora_mexico().strftime('%Y%m%d')
        
        print(f"🔍 Buscando secuenciales para número de parte: '{numero_parte}' y fecha: {fecha_actual}")
        
        # Buscar registros específicos para este número de parte y fecha exacta
        # El formato buscado es: NUMERO_PARTE,YYYYMMDD0001 en el campo codigo_material_recibido
        query = """
        SELECT codigo_material_recibido, fecha_registro
        FROM control_material_almacen 
        WHERE codigo_material_recibido LIKE %s
        ORDER BY fecha_registro DESC
        """
        
        # Patrón de búsqueda: NUMERO_PARTE,YYYYMMDD seguido de 4 dígitos (usando número de parte)
        patron_busqueda = f"{numero_parte},{fecha_actual}%"
        
        cursor.execute(query, (patron_busqueda,))
        resultados = cursor.fetchall()
        
        print(f"🔍 Encontrados {len(resultados)} registros para el patrón '{patron_busqueda}'")
        
        # Buscar el secuencial más alto para este número de parte y fecha específica
        secuencial_mas_alto = 0
        patron_regex = rf'^{re.escape(numero_parte)},{fecha_actual}(\d{{4}})$'
        
        for resultado in resultados:
            codigo_recibido = resultado['codigo_material_recibido'] or ''
            
            print(f" Analizando: codigo_material_recibido='{codigo_recibido}'")
            
            # Buscar patrón exacto: NUMERO_PARTE,YYYYMMDD0001
            match = re.match(patron_regex, codigo_recibido)
            
            if match:
                secuencial_encontrado = int(match.group(1))
                print(f"✓ Secuencial encontrado: {secuencial_encontrado}")
                
                if secuencial_encontrado > secuencial_mas_alto:
                    secuencial_mas_alto = secuencial_encontrado
                    print(f"📊 Nuevo secuencial más alto: {secuencial_mas_alto}")
            else:
                print(f" No coincide con patrón esperado: {codigo_recibido}")
        
        siguiente_secuencial = secuencial_mas_alto + 1
        
        # Generar el próximo código de material recibido completo usando número de parte
        siguiente_codigo_completo = f"{numero_parte},{fecha_actual}{siguiente_secuencial:04d}"
        
        print(f" Siguiente secuencial: {siguiente_secuencial}")
        print(f" Próximo código completo: {siguiente_codigo_completo}")
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'siguiente_secuencial': siguiente_secuencial,
            'fecha_actual': fecha_actual,
            'codigo_material': codigo_material,
            'numero_parte': numero_parte,
            'secuencial_mas_alto_encontrado': secuencial_mas_alto,
            'patron_busqueda': patron_busqueda,
            'proximo_codigo_completo': siguiente_codigo_completo
        })
        
    except Exception as e:
        print(f"❌ Error al obtener siguiente secuencial: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'siguiente_secuencial': 1  # Valor por defecto en caso de error
        }), 500

@app.route('/informacion_basica/control_de_material')
@login_requerido
def control_de_material_ajax():
    """Ruta para cargar dinámicamente el contenido de Control de Material"""
    try:
        return render_template('INFORMACION BASICA/CONTROL_DE_MATERIAL.html')
    except Exception as e:
        print(f"Error al cargar template Control de Material: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/informacion_basica/control_de_bom')
@login_requerido
def control_de_bom_ajax():
    """Ruta para cargar dinámicamente el contenido de Control de BOM"""
    try:
        # Obtener modelos para pasarlos al template
        modelos = obtener_modelos_bom_db()
        return render_template('INFORMACION BASICA/CONTROL_DE_BOM.html', modelos=modelos)
    except Exception as e:
        print(f"Error al cargar template Control de BOM: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

# Rutas para cargar contenido dinámicamente (AJAX)
@app.route('/listas/informacion_basica')
@login_requerido
def lista_informacion_basica():
    """Cargar dinámicamente la lista de Información Básica"""
    try:
        return render_template('LISTAS/LISTA_INFORMACIONBASICA.html')
    except Exception as e:
        print(f"Error al cargar LISTA_INFORMACIONBASICA: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/listas/control_material')
@login_requerido
def lista_control_material():
    """Cargar dinámicamente la lista de Control de Material"""
    try:
        return render_template('LISTAS/LISTA_DE_MATERIALES.html')
    except Exception as e:
        print(f"Error al cargar LISTA_DE_MATERIALES: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/listas/control_produccion')
@login_requerido
def lista_control_produccion():
    """Cargar dinámicamente la lista de Control de Producción"""
    try:
        return render_template('LISTAS/LISTA_CONTROLDEPRODUCCION.html')
    except Exception as e:
        print(f"Error al cargar LISTA_CONTROLDEPRODUCCION: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control_produccion/control_embarque')
@login_requerido
def control_embarque():
    """Cargar la página de Control de Embarque"""
    try:
        return render_template('Control de produccion/Control de embarque.html')
    except Exception as e:
        print(f"Error al cargar Control de embarque: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/Control de embarque')
@login_requerido
def control_embarque_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de embarque"""
    try:
        return render_template('Control de produccion/Control de embarque.html')
    except Exception as e:
        print(f"Error al cargar template Control de embarque AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control_produccion/crear_plan')
@login_requerido
def crear_plan_produccion():
    """Cargar la página de Crear Plan de Producción"""
    try:
        fecha_hoy = obtener_fecha_hora_mexico().strftime('%Y-%m-%d')
        usuario_logueado = session.get('usuario', '')
        return render_template('Control de produccion/Crear plan de produccion.html', 
                             fecha_hoy=fecha_hoy, 
                             usuario_logueado=usuario_logueado)
    except Exception as e:
        print(f"Error al cargar Crear Plan de Producción: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control_produccion/plan_smt')
@login_requerido
def plan_smt_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de PLAN SMT"""
    try:
        return render_template('Control de produccion/plan_smd_interfaz.html')
    except Exception as e:
        print(f"Error al cargar template PLAN SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

# ==========================================
# AGENTE GENERADOR DE PLAN SMD
# ==========================================

def crear_tabla_plan_smd():
    """Crear tabla plan_smd si no existe"""
    try:
        query = """
        CREATE TABLE IF NOT EXISTS plan_smd (
            id INT AUTO_INCREMENT PRIMARY KEY,
            linea VARCHAR(32) NOT NULL,
            lote VARCHAR(32) NOT NULL COMMENT 'Código WO para trazabilidad',
            nparte VARCHAR(64) NOT NULL,
            modelo VARCHAR(64) NOT NULL,
            tipo VARCHAR(32) NOT NULL DEFAULT 'Main',
            turno VARCHAR(32) NOT NULL,
            ct VARCHAR(32) DEFAULT '',
            uph VARCHAR(32) DEFAULT '',
            qty INT NOT NULL DEFAULT 0,
            fisico INT NOT NULL DEFAULT 0,
            falta INT NOT NULL DEFAULT 0,
            pct INT NOT NULL DEFAULT 0,
            comentarios TEXT DEFAULT '',
            fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
            usuario_creacion VARCHAR(64) DEFAULT 'sistema',
            INDEX idx_lote (lote),
            INDEX idx_modelo (modelo),
            INDEX idx_nparte (nparte)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        execute_query(query)
        print("✅ Tabla plan_smd creada/verificada")
    except Exception as e:
        print(f"❌ Error creando tabla plan_smd: {e}")

# Crear tabla al inicializar
crear_tabla_plan_smd()

@app.route('/api/work-orders', methods=['GET'])
@login_requerido
def api_work_orders():
    """API para obtener Work Orders con filtros"""
    try:
        # Parámetros de filtro
        q = request.args.get('q', '').strip()
        estados_param = request.args.get('estado', '')
        desde = request.args.get('desde', '')
        hasta = request.args.get('hasta', '')
        
        # Estados por defecto
        if estados_param:
            estados = [estado.strip() for estado in estados_param.split(',')]
        else:
            estados = ['CREADA', 'PLANIFICADA']
        
        # Construir query base
        query = """
        SELECT id, codigo_wo, codigo_po, modelo, nombre_modelo, codigo_modelo, 
               cantidad_planeada, fecha_operacion, estado, usuario_creacion,
               orden_proceso, modificador, fecha_modificacion
        FROM work_orders 
        WHERE 1=1
        """
        params = []
        
        # Filtros
        if estados:
            placeholders = ','.join(['%s'] * len(estados))
            query += f" AND estado IN ({placeholders})"
            params.extend(estados)
        
        if q:
            query += " AND (codigo_wo LIKE %s OR codigo_po LIKE %s OR modelo LIKE %s OR codigo_modelo LIKE %s)"
            q_param = f"%{q}%"
            params.extend([q_param, q_param, q_param, q_param])
        
        if desde:
            query += " AND fecha_operacion >= %s"
            params.append(desde)
        
        if hasta:
            query += " AND fecha_operacion <= %s"
            params.append(hasta)
        
        query += " ORDER BY fecha_operacion ASC, codigo_modelo ASC"
        
        # Ejecutar query
        work_orders = execute_query(query, params, fetch='all')
        
        # Verificar cuáles WOs ya fueron importadas (existen en plan_main)
        wo_ids = [wo['id'] for wo in work_orders]
        ya_importados = {}
        
        if wo_ids:
            placeholders = ','.join(['%s'] * len(wo_ids))
            check_query = f"""
            SELECT DISTINCT wo_id, lot_no
            FROM plan_main 
            WHERE wo_id IN ({placeholders}) AND wo_id IS NOT NULL
            """
            importados = execute_query(check_query, wo_ids, fetch='all')
            
            for imp in importados:
                ya_importados[imp['wo_id']] = imp['lot_no']
        
        # Formatear respuesta
        resultado = []
        for wo in work_orders:
            wo_id = wo['id']
            resultado.append({
                'id': wo_id,
                'codigo_wo': wo['codigo_wo'],
                'codigo_po': wo['codigo_po'] or '',
                'modelo': wo['modelo'] or '',
                'nombre_modelo': wo['nombre_modelo'] or '',
                'codigo_modelo': wo['codigo_modelo'] or '',
                'cantidad_planeada': wo['cantidad_planeada'] or 0,
                'fecha_operacion': wo['fecha_operacion'].strftime('%Y-%m-%d') if wo['fecha_operacion'] else '',
                'estado': wo['estado'] or '',
                'usuario_creacion': wo['usuario_creacion'] or '',
                'orden_proceso': wo['orden_proceso'] or '',
                'modificador': wo['modificador'] or '',
                'fecha_modificacion': wo['fecha_modificacion'].strftime('%Y-%m-%d %H:%M:%S') if wo['fecha_modificacion'] else '',
                'ya_importado': wo_id in ya_importados,
                'lot_no_existente': ya_importados.get(wo_id, None)
            })
        
        return jsonify(resultado)
        
    except Exception as e:
        print(f"❌ Error en API work-orders: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventario/modelo/<codigo_modelo>', methods=['GET'])
@login_requerido
def api_inventario_modelo(codigo_modelo):
    """API para obtener inventario por código de modelo"""
    try:
        query = """
        SELECT modelo, nparte, stock_total, ubicaciones,
               ultima_entrada, ultima_salida, updated_at
        FROM inv_resumen_modelo
        WHERE nparte = %s
        """

        inventario = execute_query(query, (codigo_modelo,), fetch='all')
        
        # Formatear respuesta
        resultado = []
        for item in inventario:
            resultado.append({
                'modelo': item['modelo'],
                'nparte': item['nparte'],
                'stock_total': item['stock_total'] or 0,
                'ubicaciones': item['ubicaciones'] or '',
                'ultima_entrada': item['ultima_entrada'].strftime('%Y-%m-%d %H:%M:%S') if item['ultima_entrada'] else '',
                'ultima_salida': item['ultima_salida'].strftime('%Y-%m-%d %H:%M:%S') if item['ultima_salida'] else '',
                'updated_at': item['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if item['updated_at'] else ''
            })
        
        return jsonify(resultado)
        
    except Exception as e:
        print(f"❌ Error en API inventario modelo {codigo_modelo}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/plan-smd', methods=['POST'])
@login_requerido
def api_plan_smd_guardar():
    """API para guardar renglones del plan SMD"""
    try:
        data = request.get_json()
        if not data or not isinstance(data, list):
            return jsonify({'error': 'Se esperaba un arreglo de renglones'}), 400
        
        usuario = session.get('usuario', 'sistema')
        renglones_guardados = 0
        
        for renglon in data:
            # Validar campos requeridos
            if not all(k in renglon for k in ['linea', 'lote', 'nparte', 'modelo', 'tipo', 'turno', 'qty']):
                continue
            
            query = """
            INSERT INTO plan_smd (linea, lote, nparte, modelo, tipo, turno, ct, uph, 
                                 qty, fisico, falta, pct, comentarios, usuario_creacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                renglon['linea'],
                renglon['lote'],
                renglon['nparte'],
                renglon['modelo'],
                renglon['tipo'],
                renglon['turno'],
                renglon.get('ct', ''),
                renglon.get('uph', ''),
                renglon['qty'],
                renglon.get('fisico', 0),
                renglon.get('falta', renglon['qty']),
                renglon.get('pct', 0),
                renglon.get('comentarios', ''),
                usuario
            )
            
            execute_query(query, params)
            renglones_guardados += 1
        
        return jsonify({
            'success': True,
            'renglones_guardados': renglones_guardados,
            'message': f'Se guardaron {renglones_guardados} renglones del plan SMD'
        })
        
    except Exception as e:
        print(f"❌ Error guardando plan SMD: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generar-plan-smd', methods=['POST'])
@login_requerido
def api_generar_plan_smd():
    """🤖 AGENTE GENERADOR DE PLAN SMD - Sólo faltantes por codigo_modelo"""
    try:
        # Parámetros de entrada
        data = request.get_json() or {}
        
        # Parámetros con defaults
        q = data.get('q', '')
        estados = data.get('estados', ['CREADA', 'PLANIFICADA'])
        desde = data.get('desde', '')
        hasta = data.get('hasta', '')
        linea_default = data.get('linea_default', 'SMT A')
        turno_default = data.get('turno_default', 'DIA')
        tipo_default = data.get('tipo_default', 'Main')
        limite_wo = data.get('limite_wo', None)
        dry_run = data.get('dry_run', False)
        
        print(f"🤖 AGENTE PLAN SMD iniciado - DRY_RUN: {dry_run}")
        
        # Variables de seguimiento
        wo_procesadas = 0
        renglones_generados = 0
        qty_total_plan = 0
        faltante_total_plan = 0
        inventario_acumulado_considerado = 0
        lotes = []
        omitidas_sin_faltante = []
        incidencias = []
        renglones_plan = []
        
        # 1. TRAER WORK ORDERS
        try:
            fecha_actual = obtener_fecha_hora_mexico().strftime('%Y%m%d')
            
            # Construir filtros para work orders
            filtros = {
                'q': q,
                'estado': ','.join(estados),
                'desde': desde,
                'hasta': hasta
            }
            
            # Simular llamada a API interna
            query_wo = """
            SELECT id, codigo_wo, codigo_po, modelo, nombre_modelo, codigo_modelo, 
                   cantidad_planeada, fecha_operacion, estado
            FROM work_orders 
            WHERE estado IN ({})
            """.format(','.join(['%s'] * len(estados)))
            
            params_wo = estados[:]
            
            if q:
                query_wo += " AND (codigo_wo LIKE %s OR codigo_po LIKE %s OR modelo LIKE %s OR codigo_modelo LIKE %s)"
                q_param = f"%{q}%"
                params_wo.extend([q_param, q_param, q_param, q_param])
            
            if desde:
                query_wo += " AND fecha_operacion >= %s"
                params_wo.append(desde)
            
            if hasta:
                query_wo += " AND fecha_operacion <= %s"
                params_wo.append(hasta)
            
            query_wo += " ORDER BY fecha_operacion ASC, codigo_modelo ASC"
            
            if limite_wo:
                query_wo += f" LIMIT {int(limite_wo)}"
            
            work_orders = execute_query(query_wo, params_wo, fetch='all')
            print(f"📋 Encontradas {len(work_orders)} work orders")
            
        except Exception as e:
            incidencias.append({
                "wo": "SISTEMA",
                "tipo": "error_consulta_wo",
                "detalle": f"Error consultando work orders: {str(e)}"
            })
            work_orders = []
        
        # 2. PROCESAR CADA WO
        lote_counter = 1
        
        for wo in work_orders:
            wo_procesadas += 1
            codigo_wo = wo['codigo_wo']
            codigo_modelo = wo['codigo_modelo']
            cantidad_planeada = wo['cantidad_planeada']
            
            # Validaciones
            if not codigo_modelo or not codigo_modelo.strip():
                incidencias.append({
                    "wo": codigo_wo,
                    "tipo": "sin_codigo_modelo",
                    "detalle": "La WO no tiene codigo_modelo"
                })
                continue
            
            if not cantidad_planeada or cantidad_planeada <= 0:
                incidencias.append({
                    "wo": codigo_wo,
                    "tipo": "cantidad_invalida",
                    "detalle": f"Cantidad planeada inválida: {cantidad_planeada}"
                })
                continue
            
            # 3. CONSULTAR INVENTARIO POR CODIGO_MODELO
            try:
                query_inv = """
                SELECT SUM(stock_total) as inventario_total
                FROM inv_resumen_modelo
                WHERE nparte = %s
                """

                resultado_inv = execute_query(query_inv, (codigo_modelo,), fetch='one')
                inventario_total = resultado_inv['inventario_total'] if resultado_inv and resultado_inv['inventario_total'] else 0
                inventario_acumulado_considerado += inventario_total
                
                print(f"📦 WO {codigo_wo} | Modelo: {codigo_modelo} | Planeado: {cantidad_planeada} | Inventario: {inventario_total}")
                
            except Exception as e:
                incidencias.append({
                    "wo": codigo_wo,
                    "tipo": "inventario_endpoint_error",
                    "detalle": f"Error consultando inventario: {str(e)}"
                })
                inventario_total = 0
            
            # 4. CALCULAR FALTANTE
            faltante = max(0, cantidad_planeada - inventario_total)
            
            if faltante <= 0:
                omitidas_sin_faltante.append(codigo_wo)
                print(f"⏭️ WO {codigo_wo} omitida - Sin faltante (inventario suficiente)")
                continue
            
            # 5. GENERAR RENGLÓN DEL PLAN
            lote = f"P{fecha_actual}-{lote_counter:03d}"
            lotes.append(lote)
            lote_counter += 1
            
            renglon = {
                "linea": linea_default,
                "lote": lote,
                "nparte": codigo_modelo,  # ✅ Usamos codigo_modelo
                "modelo": codigo_modelo,  # ✅ Usamos codigo_modelo
                "tipo": tipo_default,
                "turno": turno_default,
                "ct": "",
                "uph": "",
                "qty": faltante,
                "fisico": int(inventario_total),  # ✅ Usar el inventario real consultado
                "falta": faltante,
                "pct": int((inventario_total / cantidad_planeada) * 100) if cantidad_planeada > 0 else 0,  # ✅ Calcular porcentaje real
                "comentarios": f"Inventario: {int(inventario_total)} | Requerido: {int(cantidad_planeada)} | Faltante: {faltante}"
            }
            
            renglones_plan.append(renglon)
            renglones_generados += 1
            qty_total_plan += faltante
            faltante_total_plan += faltante
            
            print(f"✅ Renglón generado - Lote: {lote} | Modelo: {codigo_modelo} | QTY: {faltante}")
        
        # 6. GUARDAR SI NO ES DRY_RUN
        if not dry_run and renglones_plan:
            try:
                usuario = session.get('usuario', 'sistema')
                renglones_guardados = 0
                
                for renglon in renglones_plan:
                    query_insert = """
                    INSERT INTO plan_smd (linea, lote, nparte, modelo, tipo, turno, ct, uph, 
                                         qty, fisico, falta, pct, comentarios, usuario_creacion)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    params_insert = (
                        renglon['linea'], renglon['lote'], renglon['nparte'], renglon['modelo'],
                        renglon['tipo'], renglon['turno'], renglon['ct'], renglon['uph'],
                        renglon['qty'], renglon['fisico'], renglon['falta'], renglon['pct'],
                        renglon['comentarios'], usuario
                    )
                    
                    execute_query(query_insert, params_insert)
                    renglones_guardados += 1
                
                print(f"💾 Plan guardado: {renglones_guardados} renglones")
                
            except Exception as e:
                incidencias.append({
                    "wo": "SISTEMA",
                    "tipo": "error_guardado",
                    "detalle": f"Error guardando plan: {str(e)}"
                })
        
        # 7. RESUMEN FINAL
        resumen = {
            "wo_procesadas": wo_procesadas,
            "renglones_generados": renglones_generados,
            "qty_total_plan": qty_total_plan,
            "faltante_total_plan": faltante_total_plan,
            "inventario_acumulado_considerado": inventario_acumulado_considerado,
            "lotes": lotes,
            "omitidas_sin_faltante": omitidas_sin_faltante,
            "incidencias": incidencias,
            "dry_run": dry_run,
            "plan_generado": renglones_plan if dry_run else f"{len(renglones_plan)} renglones guardados"
        }
        
        print(f"🎯 AGENTE COMPLETADO - Generados: {renglones_generados} | Total QTY: {qty_total_plan}")
        
        return jsonify(resumen)
        
    except Exception as e:
        print(f"❌ Error en Agente PLAN SMD: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== AGENTE GENERADOR DE PLAN SMD ====================

@app.route('/api/generar-plan-smd', methods=['POST'])
@login_requerido
def generar_plan_smd():
    """
    Agente Generador de PLAN SMD - Sólo cantidades faltantes por codigo_modelo
    
    Proceso:
    1. Obtiene WO con filtros
    2. Para cada WO, consulta inventario por codigo_modelo  
    3. Calcula faltante = max(0, cantidad_planeada - inventario_total)
    4. Genera renglón SOLO si faltante > 0
    5. Guarda el plan o devuelve preview (dry_run)
    """
    try:
        data = request.get_json() or {}
        
        # Parámetros de entrada con defaults
        q = data.get('q', '')
        estados = data.get('estados', ['CREADA', 'PLANIFICADA'])
        desde = data.get('desde')
        hasta = data.get('hasta')
        linea_default = data.get('linea_default', 'SMT A')
        turno_default = data.get('turno_default', 'DIA')
        tipo_default = data.get('tipo_default', 'Main')
        limite_wo = data.get('limite_wo')
        dry_run = data.get('dry_run', False)
        
        print(f"🤖 AGENTE PLAN SMD - Iniciando con parámetros:")
        print(f"   Estados: {estados}, Desde: {desde}, Hasta: {hasta}")
        print(f"   Línea: {linea_default}, Turno: {turno_default}, Dry Run: {dry_run}")
        
        # Contadores y resultados
        wo_procesadas = 0
        renglones_generados = 0
        qty_total_plan = 0
        faltante_total_plan = 0
        inventario_acumulado_considerado = 0
        lotes = []
        omitidas_sin_faltante = []
        incidencias = []
        plan_renglones = []
        
        # Generar fecha y contador de lote
        fecha_lote = obtener_fecha_hora_mexico().strftime('%Y%m%d')
        contador_lote = 1
        
        def generar_lote():
            nonlocal contador_lote
            lote = f"P{fecha_lote}-{contador_lote:03d}"
            contador_lote += 1
            if lote not in lotes:
                lotes.append(lote)
            return lote
        
        # PASO 1: Obtener Work Orders
        print("📋 PASO 1: Obteniendo Work Orders...")
        
        # Construir query para WO
        query_wo = """
        SELECT id, codigo_wo, codigo_po, modelo, nombre_modelo, codigo_modelo, 
               cantidad_planeada, fecha_operacion, estado
        FROM work_orders 
        WHERE 1=1
        """
        params_wo = []
        
        # Filtros de estado
        if estados:
            placeholders = ','.join(['%s'] * len(estados))
            query_wo += f" AND estado IN ({placeholders})"
            params_wo.extend(estados)
        
        # Filtro de búsqueda
        if q:
            query_wo += " AND (codigo_wo LIKE %s OR codigo_po LIKE %s OR modelo LIKE %s OR codigo_modelo LIKE %s)"
            like_q = f"%{q}%"
            params_wo.extend([like_q, like_q, like_q, like_q])
        
        # Filtros de fecha
        if desde:
            query_wo += " AND fecha_operacion >= %s"
            params_wo.append(desde)
        if hasta:
            query_wo += " AND fecha_operacion <= %s"
            params_wo.append(hasta)
        
        # Ordenar por fecha y código
        query_wo += " ORDER BY fecha_operacion ASC, codigo_modelo ASC"
        
        # Límite opcional
        if limite_wo and isinstance(limite_wo, int) and limite_wo > 0:
            query_wo += f" LIMIT {limite_wo}"
        
        work_orders = execute_query(query_wo, params_wo, fetch='all')
        
        print(f"📊 Encontradas {len(work_orders) if work_orders else 0} Work Orders")
        
        if not work_orders:
            return jsonify({
                'wo_procesadas': 0,
                'renglones_generados': 0,
                'qty_total_plan': 0,
                'faltante_total_plan': 0,
                'inventario_acumulado_considerado': 0,
                'lotes': [],
                'omitidas_sin_faltante': [],
                'incidencias': [{'tipo': 'sin_wo', 'detalle': 'No se encontraron Work Orders con los filtros especificados'}],
                'dry_run': dry_run
            })
        
        # PASO 2: Procesar cada WO
        print("🔄 PASO 2: Procesando Work Orders...")
        
        for wo in work_orders:
            wo_procesadas += 1
            codigo_wo = wo.get('codigo_wo', '')
            codigo_modelo = wo.get('codigo_modelo', '')
            cantidad_planeada = wo.get('cantidad_planeada', 0)
            
            print(f"   🔍 Procesando WO: {codigo_wo} - Modelo: {codigo_modelo}")
            
            # Validar campos obligatorios
            if not codigo_modelo:
                incidencias.append({
                    'wo': codigo_wo,
                    'tipo': 'sin_codigo_modelo',
                    'detalle': 'La WO no tiene codigo_modelo'
                })
                print(f"   ⚠️ Omitida por falta de codigo_modelo")
                continue
            
            if not isinstance(cantidad_planeada, (int, float)) or cantidad_planeada <= 0:
                incidencias.append({
                    'wo': codigo_wo,
                    'tipo': 'cantidad_invalida',
                    'detalle': f'Cantidad planeada inválida: {cantidad_planeada}'
                })
                print(f"   ⚠️ Omitida por cantidad inválida: {cantidad_planeada}")
                continue
            
            # PASO 3: Consultar inventario por codigo_modelo
            try:
                print(f"   📦 Consultando inventario para modelo: {codigo_modelo}")
                
                # Endpoint: GET /api/inventario/modelo/{codigo_modelo}
                # Simular la consulta directa a la tabla inv_resumen_modelo
                query_inv = """
                SELECT COALESCE(SUM(stock_total), 0) as inventario_total
                FROM inv_resumen_modelo 
                WHERE nparte = %s
                """
                
                result_inv = execute_query(query_inv, (codigo_modelo,), fetch='one')
                inventario_total = float(result_inv.get('inventario_total', 0)) if result_inv else 0.0
                
                inventario_acumulado_considerado += inventario_total
                
                print(f"   📊 Inventario total para {codigo_modelo}: {inventario_total}")
                print(f"   📐 Cantidad planeada: {cantidad_planeada}")
                
            except Exception as e:
                incidencias.append({
                    'wo': codigo_wo,
                    'tipo': 'inventario_endpoint_error',
                    'detalle': f'Error al consultar inventario: {str(e)}'
                })
                print(f"   ❌ Error consultando inventario: {e}")
                continue
            
            # PASO 4: Calcular faltante
            faltante = max(0, cantidad_planeada - inventario_total)
            
            print(f"   🧮 Faltante calculado: {faltante}")
            
            # PASO 5: Generar renglón SOLO si faltante > 0
            if faltante <= 0:
                omitidas_sin_faltante.append(codigo_wo)
                print(f"   ✅ WO omitida - no hay faltantes (inventario suficiente)")
                continue
            
            # Crear renglón del plan
            lote = generar_lote()
            
            renglon = {
                'linea': linea_default,
                'lote': lote,
                'nparte': codigo_modelo,  # ✅ codigo_modelo
                'modelo': codigo_modelo,  # ✅ codigo_modelo como identificador visible
                'tipo': tipo_default,     # Siempre "Main"
                'turno': turno_default,
                'ct': '',
                'uph': '',
                'qty': int(faltante),
                'fisico': int(inventario_total),  # ✅ Usar el inventario real consultado
                'falta': int(faltante),
                'pct': int((inventario_total / cantidad_planeada) * 100) if cantidad_planeada > 0 else 0,  # ✅ Calcular porcentaje real
                'comentarios': f'Inventario: {int(inventario_total)} | Requerido: {int(cantidad_planeada)} | Faltante: {int(faltante)}'
            }
            
            plan_renglones.append(renglon)
            renglones_generados += 1
            qty_total_plan += int(faltante)
            faltante_total_plan += int(faltante)
            
            print(f"   ✅ Renglón generado - Lote: {lote}, QTY: {int(faltante)}")
        
        # PASO 6: Guardar o devolver preview
        print(f"📋 RESUMEN: {renglones_generados} renglones generados de {wo_procesadas} WO procesadas")
        
        if not dry_run and plan_renglones:
            try:
                print("💾 Guardando plan en base de datos...")
                
                # Insertar renglones en tabla plan_smd (ajustar según tu esquema)
                query_insert = """
                INSERT INTO plan_smd (linea, lote, nparte, modelo, tipo, turno, ct, uph, qty, fisico, falta, pct, comentarios, fecha_creacion, usuario_creacion)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
                """
                
                usuario_actual = session.get('usuario', 'sistema')
                
                for renglon in plan_renglones:
                    execute_query(query_insert, (
                        renglon['linea'], renglon['lote'], renglon['nparte'], renglon['modelo'],
                        renglon['tipo'], renglon['turno'], renglon['ct'], renglon['uph'],
                        renglon['qty'], renglon['fisico'], renglon['falta'], renglon['pct'],
                        renglon['comentarios'], usuario_actual
                    ))
                    # Registrar trazabilidad en estado PLANEADO
                    try:
                        execute_query(
                            "INSERT INTO trazabilidad (linea, lot_no, codigo_wo, estado, usuario) VALUES (%s,%s,%s,'PLANEADO',%s)",
                            (
                                renglon.get('linea', ''),
                                renglon.get('lote', ''),
                                renglon.get('wo', ''),
                                usuario_actual
                            )
                        )
                    except Exception as e2:
                        print(f"⚠️ Error insertando trazabilidad: {e2}")
                
                print(f"✅ {len(plan_renglones)} renglones guardados exitosamente")
                
            except Exception as e:
                print(f"❌ Error guardando plan: {e}")
                return jsonify({
                    'error': f'Error guardando plan: {str(e)}',
                    'plan_generado': plan_renglones,
                    'dry_run': True  # Forzar dry_run en caso de error
                }), 500
        
        # Resumen final
        resumen = {
            'wo_procesadas': wo_procesadas,
            'renglones_generados': renglones_generados,
            'qty_total_plan': qty_total_plan,
            'faltante_total_plan': faltante_total_plan,
            'inventario_acumulado_considerado': int(inventario_acumulado_considerado),
            'lotes': lotes,
            'omitidas_sin_faltante': omitidas_sin_faltante,
            'incidencias': incidencias,
            'dry_run': dry_run
        }
        
        if dry_run:
            resumen['plan_preview'] = plan_renglones
        
        print(f"🎯 AGENTE COMPLETADO - Resultado: {resumen}")
        
        return jsonify(resumen)
        
    except Exception as e:
        print(f"❌ Error en agente PLAN SMD: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Error interno del agente: {str(e)}',
            'wo_procesadas': 0,
            'renglones_generados': 0,
            'dry_run': True
        }), 500

@app.route('/api/inventario/modelo/<codigo_modelo>', methods=['GET'])
@login_requerido  
def obtener_inventario_por_modelo(codigo_modelo):
    """
    Endpoint para obtener inventario por código de modelo
    Usado por el agente PLAN SMD para calcular faltantes
    """
    try:
        print(f"📦 Consultando inventario para modelo: {codigo_modelo}")
        
        # Consulta a la tabla inv_resumen_modelo
        query = """
        SELECT modelo, nparte, stock_total, ubicaciones, ultima_entrada, ultima_salida, updated_at
        FROM inv_resumen_modelo 
        WHERE nparte = %s
        ORDER BY nparte
        """
        
        resultados = execute_query(query, (codigo_modelo,), fetch='all')
        
        if not resultados:
            print(f"📦 No se encontró inventario para modelo: {codigo_modelo}")
            return jsonify([])
        
        inventario_data = []
        stock_total_acumulado = 0
        
        for row in resultados:
            stock_total = float(row.get('stock_total', 0))
            stock_total_acumulado += stock_total
            
            inventario_data.append({
                'modelo': row.get('modelo'),
                'nparte': row.get('nparte'),
                'stock_total': stock_total,
                'ubicaciones': row.get('ubicaciones', ''),
                'ultima_entrada': row.get('ultima_entrada'),
                'ultima_salida': row.get('ultima_salida'),
                'updated_at': row.get('updated_at')
            })
        
        print(f"📊 Inventario encontrado: {len(inventario_data)} items, total: {stock_total_acumulado}")
        
        return jsonify(inventario_data)
        
    except Exception as e:
        print(f"❌ Error consultando inventario para modelo {codigo_modelo}: {e}")
        return jsonify({
            'error': f'Error consultando inventario: {str(e)}'
        }), 500

@app.route('/api/plan-smd', methods=['POST'])
@login_requerido
def guardar_plan_smd():
    """
    Endpoint para guardar renglones del plan SMD
    Recibe arreglo de renglones y los inserta en la base de datos
    """
    try:
        data = request.get_json()
        
        if not isinstance(data, list):
            return jsonify({
                'error': 'Se esperaba un arreglo de renglones del plan'
            }), 400
        
        if not data:
            return jsonify({
                'error': 'No se proporcionaron renglones para guardar'
            }), 400
        
        print(f"💾 Guardando {len(data)} renglones del plan SMD...")
        
        # Validar estructura de renglones
        campos_requeridos = ['linea', 'lote', 'nparte', 'modelo', 'tipo', 'turno', 'qty']
        
        for i, renglon in enumerate(data):
            for campo in campos_requeridos:
                if campo not in renglon:
                    return jsonify({
                        'error': f'Renglón {i+1}: Falta campo requerido "{campo}"'
                    }), 400
        
        # Insertar renglones en base de datos
        query_insert = """
        INSERT INTO plan_smd (
            linea, lote, nparte, modelo, tipo, turno, ct, uph, qty, fisico, falta, pct, 
            comentarios, fecha_creacion, usuario_creacion
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
        """
        
        usuario_actual = session.get('usuario', 'sistema')
        renglones_insertados = 0
        
        for renglon in data:
            try:
                execute_query(query_insert, (
                    renglon.get('linea', ''),
                    renglon.get('lote', ''),
                    renglon.get('nparte', ''),
                    renglon.get('modelo', ''),
                    renglon.get('tipo', 'Main'),
                    renglon.get('turno', 'DIA'),
                    renglon.get('ct', ''),
                    renglon.get('uph', ''),
                    int(renglon.get('qty', 0)),
                    int(renglon.get('fisico', 0)),
                    int(renglon.get('falta', 0)),
                    float(renglon.get('pct', 0)),
                    renglon.get('comentarios', ''),
                    usuario_actual
                ))
                renglones_insertados += 1
                
            except Exception as e:
                print(f"❌ Error insertando renglón {renglon}: {e}")
                continue
        
        print(f"✅ {renglones_insertados} renglones guardados exitosamente")
        
        return jsonify({
            'success': True,
            'renglones_insertados': renglones_insertados,
            'total_renglones': len(data),
            'message': f'Plan SMD guardado: {renglones_insertados} renglones'
        })
        
    except Exception as e:
        print(f"❌ Error guardando plan SMD: {e}")
        return jsonify({
            'error': f'Error guardando plan: {str(e)}'
        }), 500

@app.route('/api/work-orders', methods=['GET'])
@login_requerido
def obtener_work_orders():
    """
    Endpoint para obtener Work Orders con filtros
    Usado por el agente PLAN SMD y la interfaz PLAN SMT
    
    Parámetros:
    - q: texto de búsqueda
    - estado: filtro por estado (puede ser múltiple)
    - desde: fecha desde (YYYY-MM-DD)
    - hasta: fecha hasta (YYYY-MM-DD)
    """
    try:
        # Obtener parámetros de consulta
        q = request.args.get('q', '').strip()
        estado = request.args.get('estado', '')
        desde = request.args.get('desde', '')
        hasta = request.args.get('hasta', '')
        
        print(f"📋 Consultando Work Orders - q: '{q}', estado: '{estado}', desde: '{desde}', hasta: '{hasta}'")
        
        # Construir query base
        query = """
        SELECT id, codigo_wo, codigo_po, modelo, nombre_modelo, codigo_modelo, 
               cantidad_planeada, fecha_operacion, estado, usuario_creacion, 
               orden_proceso, modificador, fecha_modificacion
        FROM work_orders 
        WHERE 1=1
        """
        params = []
        
        # Filtro de búsqueda
        if q:
            query += """ AND (
                codigo_wo LIKE %s OR 
                codigo_po LIKE %s OR 
                modelo LIKE %s OR 
                codigo_modelo LIKE %s OR
                nombre_modelo LIKE %s
            )"""
            like_q = f"%{q}%"
            params.extend([like_q, like_q, like_q, like_q, like_q])
        
        # Filtro por estado
        if estado:
            # Permitir múltiples estados separados por coma
            estados = [e.strip().upper() for e in estado.split(',') if e.strip()]
            if estados:
                placeholders = ','.join(['%s'] * len(estados))
                query += f" AND estado IN ({placeholders})"
                params.extend(estados)
        
        # Filtros de fecha
        if desde:
            query += " AND fecha_operacion >= %s"
            params.append(desde)
        if hasta:
            query += " AND fecha_operacion <= %s"
            params.append(hasta)
        
        # Ordenar por fecha y código
        query += " ORDER BY fecha_operacion DESC, codigo_wo DESC"
        
        work_orders = execute_query(query, params, fetch='all')
        
        if not work_orders:
            print("📋 No se encontraron Work Orders con los filtros especificados")
            return jsonify([])
        
        # Formatear resultados
        wo_data = []
        for wo in work_orders:
            wo_data.append({
                'id': wo.get('id'),
                'codigo_wo': wo.get('codigo_wo'),
                'codigo_po': wo.get('codigo_po'),
                'modelo': wo.get('modelo'),
                'nombre_modelo': wo.get('nombre_modelo'),
                'codigo_modelo': wo.get('codigo_modelo'),
                'cantidad_planeada': wo.get('cantidad_planeada'),
                'fecha_operacion': wo.get('fecha_operacion').strftime('%Y-%m-%d') if wo.get('fecha_operacion') else '',
                'estado': wo.get('estado'),
                'usuario_creacion': wo.get('usuario_creacion'),
                'orden_proceso': wo.get('orden_proceso'),
                'modificador': wo.get('modificador'),
                'fecha_modificacion': wo.get('fecha_modificacion').strftime('%Y-%m-%d %H:%M:%S') if wo.get('fecha_modificacion') else ''
            })
        
        print(f"📊 Encontradas {len(wo_data)} Work Orders")
        
        return jsonify(wo_data)
        
    except Exception as e:
        print(f"❌ Error consultando Work Orders: {e}")
        return jsonify({
            'error': f'Error consultando Work Orders: {str(e)}'
        }), 500

@app.route('/control_proceso/control_produccion_smt')
@login_requerido
def control_produccion_smt_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de produccion SMT"""
    try:
        # Devolver fragmento AJAX dedicado para evitar cargar una página completa dentro de un contenedor
        return render_template('Control de proceso/control_produccion_smt_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Control de produccion SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

# Ruta eliminada - Control de operacion de linea SMT será reemplazado por Control BOM

@app.route('/control-bom-ajax')
@login_requerido
def control_bom_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control BOM"""
    try:
        # Obtener modelos para el dropdown
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT DISTINCT Modelo FROM tbl_numero_parte_bom ORDER BY Modelo')
        modelos = [row['Modelo'] for row in cursor.fetchall()]
        cursor.close()
        
        return render_template('INFORMACION BASICA/CONTROL_DE_BOM.html', modelos=modelos)
    except Exception as e:
        print(f"Error al cargar template Control BOM AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/crear-plan-micom-ajax')
@login_requerido
def crear_plan_micom_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Crear plan micom"""
    try:
        return render_template('Control de produccion/crear_plan_micom_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Crear plan micom AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control-operacion-linea-smt-ajax')
@login_requerido
def control_operacion_linea_smt_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de operación de línea SMT"""
    try:
        fecha_hoy = obtener_fecha_hora_mexico().strftime('%d/%m/%Y')
        return render_template('Control de proceso/control_operacion_linea_smt_ajax.html', fecha_hoy=fecha_hoy)
    except Exception as e:
        print(f"Error al cargar template Control de operación de línea SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

# Rutas AJAX para todos los módulos de Control de Proceso
@app.route('/control-impresion-identificacion-smt-ajax')
@login_requerido
def control_impresion_identificacion_smt_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de impresión de identificación SMT"""
    try:
        return render_template('Control de proceso/control_impresion_identificacion_smt_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Control de impresión de identificación SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control-registro-identificacion-smt-ajax')
@login_requerido
def control_registro_identificacion_smt_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de registro de identificación SMT"""
    try:
        return render_template('Control de proceso/control_registro_identificacion_smt_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Control de registro de identificación SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/historial-operacion-proceso-ajax')
@login_requerido
def historial_operacion_proceso_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Historial de operación de proceso"""
    try:
        return render_template('Control de proceso/historial_operacion_proceso_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Historial de operación de proceso AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/bom-management-process-ajax')
@login_requerido
def bom_management_process_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de BOM Management Process"""
    try:
        return render_template('Control de proceso/bom_management_process_ajax.html')
    except Exception as e:
        print(f"Error al cargar template BOM Management Process AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/reporte-diario-inspeccion-smt-ajax')
@login_requerido
def reporte_diario_inspeccion_smt_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Reporte diario de inspección SMT"""
    try:
        return render_template('Control de proceso/reporte_diario_inspeccion_smt_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Reporte diario de inspección SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control-diario-inspeccion-smt-ajax')
@login_requerido
def control_diario_inspeccion_smt_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control diario de inspección SMT"""
    try:
        return render_template('Control de proceso/control_diario_inspeccion_smt_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Control diario de inspección SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/reporte-diario-inspeccion-proceso-ajax')
@login_requerido
def reporte_diario_inspeccion_proceso_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Reporte diario de inspección de proceso"""
    try:
        return render_template('Control de proceso/reporte_diario_inspeccion_proceso_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Reporte diario de inspección de proceso AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control-unidad-empaque-modelo-ajax')
@login_requerido
def control_unidad_empaque_modelo_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de unidad de empaque modelo"""
    try:
        return render_template('Control de proceso/control_unidad_empaque_modelo_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Control de unidad de empaque modelo AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/packaging-register-management-ajax')
@login_requerido
def packaging_register_management_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Packaging Register Management"""
    try:
        return render_template('Control de proceso/packaging_register_management_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Packaging Register Management AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/search-packaging-history-ajax')
@login_requerido
def search_packaging_history_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Search Packaging History"""
    try:
        return render_template('Control de proceso/search_packaging_history_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Search Packaging History AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/shipping-register-management-ajax')
@login_requerido
def shipping_register_management_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Shipping Register Management"""
    try:
        return render_template('Control de proceso/shipping_register_management_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Shipping Register Management AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/search-shipping-history-ajax')
@login_requerido
def search_shipping_history_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Search Shipping History"""
    try:
        return render_template('Control de proceso/search_shipping_history_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Search Shipping History AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/return-warehousing-register-ajax')
@login_requerido
def return_warehousing_register_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Return Warehousing Register"""
    try:
        return render_template('Control de proceso/return_warehousing_register_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Return Warehousing Register AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/return-warehousing-history-ajax')
@login_requerido
def return_warehousing_history_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Return Warehousing History"""
    try:
        return render_template('Control de proceso/return_warehousing_history_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Return Warehousing History AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/registro-movimiento-identificacion-ajax')
@login_requerido
def registro_movimiento_identificacion_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Registro Movimiento Identificación"""
    try:
        return render_template('Control de proceso/registro_movimiento_identificacion_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Registro Movimiento Identificación AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control-otras-identificaciones-ajax')
@login_requerido
def control_otras_identificaciones_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control Otras Identificaciones"""
    try:
        return render_template('Control de proceso/control_otras_identificaciones_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Control Otras Identificaciones AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control-movimiento-ns-producto-ajax')
@login_requerido
def control_movimiento_ns_producto_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control Movimiento NS Producto"""
    try:
        return render_template('Control de proceso/control_movimiento_ns_producto_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Control Movimiento NS Producto AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/model-sn-management-ajax')
@login_requerido
def model_sn_management_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Model SN Management"""
    try:
        return render_template('Control de proceso/model_sn_management_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Model SN Management AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control-scrap-ajax')
@login_requerido
def control_scrap_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control Scrap"""
    try:
        return render_template('Control de proceso/control_scrap_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Control Scrap AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

# Rutas AJAX para módulos de Control de Producción
@app.route('/line-material-status-ajax')
@login_requerido
def line_material_status_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Line Material Status_es"""
    try:
        return render_template('Control de produccion/line_material_status_es_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Line Material Status_es AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control-mask-metal-ajax')
@login_requerido
def control_mask_metal_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de mask de metal"""
    try:
        return render_template('Control de produccion/control_mask_metal_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Control de mask de metal AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control-squeegee-ajax')
@login_requerido
def control_squeegee_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de squeegee"""
    try:
        return render_template('Control de produccion/control_squeegee_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Control de squeegee AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control-caja-mask-metal-ajax')
@login_requerido
def control_caja_mask_metal_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de caja de mask de metal"""
    try:
        return render_template('Control de produccion/control_caja_mask_metal_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Control de caja de mask de metal AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/estandares-soldadura-ajax')
@login_requerido
def estandares_soldadura_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Estandares sobre control de soldadura"""
    try:
        return render_template('Control de produccion/estandares_soldadura_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Estandares sobre control de soldadura AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/registro-recibo-soldadura-ajax')
@login_requerido
def registro_recibo_soldadura_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Registro de recibo de soldadura"""
    try:
        return render_template('Control de produccion/registro_recibo_soldadura_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Registro de recibo de soldadura AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control-salida-soldadura-ajax')
@login_requerido
def control_salida_soldadura_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de salida de soldadura"""
    try:
        return render_template('Control de produccion/control_salida_soldadura_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Control de salida de soldadura AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/historial-tension-mask-metal-ajax')
@login_requerido
def historial_tension_mask_metal_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Historial de tension de mask de metal"""
    try:
        return render_template('Control de produccion/historial_tension_mask_metal_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Historial de tension de mask de metal AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control_proceso/inventario_imd_terminado')
@login_requerido
@requiere_permiso_dropdown('LISTA_CONTROL_DE_PROCESO', 'Inventario', 'IMD-SMD TERMINADO')
def inventario_imd_terminado_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Inventario IMD Terminado"""
    try:
        print("🔍 Iniciando carga de Inventario IMD Terminado AJAX...")
        result = render_template('Control de proceso/inventario_imd_terminado_ajax.html')
        print(f" Template Inventario IMD Terminado AJAX renderizado exitosamente, tamaño: {len(result)} caracteres")
        return result
    except Exception as e:
        print(f"❌ Error al cargar template Inventario IMD Terminado AJAX: {e}")
        import traceback
        traceback.print_exc()
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/listas/control_proceso')
@login_requerido
def lista_control_proceso():
    """Cargar dinámicamente la lista de Control de Proceso"""
    try:
        return render_template('LISTAS/LISTA_CONTROL_DE_PROCESO.html')
    except Exception as e:
        print(f"Error al cargar LISTA_CONTROL_DE_PROCESO: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/listas/control_calidad')
@login_requerido
def lista_control_calidad():
    """Cargar dinámicamente la lista de Control de Calidad"""
    try:
        return render_template('LISTAS/LISTA_CONTROL_DE_CALIDAD.html')
    except Exception as e:
        print(f"Error al cargar LISTA_CONTROL_DE_CALIDAD: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/listas/control_resultados')
@login_requerido
def lista_control_resultados():
    """Cargar dinámicamente la lista de Control de Resultados"""
    try:
        return render_template('LISTAS/LISTA_DE_CONTROL_DE_RESULTADOS.html')
    except Exception as e:
        print(f"Error al cargar LISTA_DE_CONTROL_DE_RESULTADOS: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/historial-aoi')
@login_requerido
def historial_aoi():
    """Servir la página de Historial AOI"""
    try:
        return render_template('Control de resultados/Historial AOI.html')
    except Exception as e:
        print(f"Error al cargar Historial AOI: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/historial-ict-ajax')
@login_requerido
def historial_ict_ajax():
    """Ruta AJAX para cargar el Historial ICT"""
    try:
        return render_template('Control de resultados/history_ict.html')
    except Exception as e:
        print(f"Error al cargar template de Historial ICT: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/historial-aoi-ajax')
@login_requerido
def historial_aoi_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Historial AOI"""
    try:
        return render_template('Control de resultados/Historial AOI.html')
    except Exception as e:
        print(f"Error al cargar template de Historial AOI: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/listas/control_reporte')
@login_requerido
def lista_control_reporte():
    """Cargar dinámicamente la lista de Control de Reporte"""
    try:
        return render_template('LISTAS/LISTA_DE_CONTROL_DE_REPORTE.html')
    except Exception as e:
        print(f"Error al cargar LISTA_DE_CONTROL_DE_REPORTE: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/listas/configuracion_programa')
@login_requerido
def lista_configuracion_programa():
    """Cargar dinámicamente la lista de Configuración de Programa"""
    try:
        return render_template('LISTAS/LISTA_DE_CONFIGPG.html')
    except Exception as e:
        print(f"Error al cargar LISTA_DE_CONFIGPG: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/material/info')
@login_requerido
def material_info():
    """Cargar dinámicamente la información general de material"""
    try:
        return render_template('info.html')
    except Exception as e:
        print(f"Error al cargar info.html: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/material/control_almacen')
@login_requerido
def material_control_almacen():
    """Cargar dinámicamente el control de almacén"""
    try:
        return render_template('Control de material/Control de material de almacen.html')
    except Exception as e:
        print(f"Error al cargar Control de material de almacen: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/material/control_salida')
@login_requerido
def material_control_salida():
    """Cargar dinámicamente el control de salida"""
    try:
        return render_template('Control de material/Control de salida.html')
    except Exception as e:
        print(f"Error al cargar Control de salida: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/consultar_especificacion_por_numero_parte')
@login_requerido
def consultar_especificacion_por_numero_parte():
    """Consultar especificación de material por número de parte directamente en BD"""
    try:
        numero_parte = request.args.get('numero_parte', '').strip()
        
        if not numero_parte:
            return jsonify({
                'success': False,
                'error': 'Número de parte requerido'
            }), 400
        
        print(f"🔍 Consultando especificación para número de parte: {numero_parte}")
        
        # Consultar en la tabla de materiales usando get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Intentar diferentes consultas para encontrar el material
        consultas = [
            "SELECT * FROM materiales WHERE numero_parte = %s",
            "SELECT * FROM materiales WHERE TRIM(numero_parte) = %s",
            "SELECT * FROM materiales WHERE numero_parte LIKE ?",
            "SELECT * FROM materiales WHERE codigo_material = %s",
            "SELECT * FROM materiales WHERE codigo_material_original = %s"
        ]
        
        material_encontrado = None
        
        for consulta in consultas:
            if "LIKE" in consulta:
                parametro = f"%{numero_parte}%"
            else:
                parametro = numero_parte
                
            print(f"🔍 Ejecutando consulta: {consulta} con parámetro: {parametro}")
            
            try:
                cursor.execute(consulta, (parametro,))
                result = cursor.fetchone()
                
                if result:
                    material_encontrado = result
                    break
            except Exception as consulta_error:
                print(f"❌ Error en consulta: {consulta_error}")
                continue
        
        if not material_encontrado:
            print(f"❌ No se encontró material con número de parte: {numero_parte}")
            conn.close()
            return jsonify({
                'success': False,
                'error': f'No se encontró material con número de parte: {numero_parte}'
            })
        
        # Convertir resultado a diccionario
        # Obtener nombres de columnas usando MySQL
        cursor.execute("DESCRIBE materiales")
        columns_result = cursor.fetchall()
        column_names = [col['Field'] for col in columns_result] if columns_result else []
        
        # Crear diccionario con nombres de columnas
        material_dict = {}
        for i, value in enumerate(material_encontrado):
            if i < len(column_names):
                material_dict[column_names[i]] = value
        
        conn.close()
        print(f"📦 Material completo encontrado: {material_dict}")
        
        # Buscar especificación en diferentes campos posibles
        campos_especificacion = [
            'especificacion_material',
            'especificacion',
            'descripcion_material',
            'descripcion',
            'nombre_material',
            'descripcion_completa'
        ]
        
        especificacion_encontrada = None
        campo_usado = None
        
        for campo in campos_especificacion:
            if campo in material_dict and material_dict[campo] and str(material_dict[campo]).strip():
                especificacion_encontrada = str(material_dict[campo]).strip()
                campo_usado = campo
                print(f" Especificación encontrada en campo '{campo}': {especificacion_encontrada}")
                break
        
        if not especificacion_encontrada:
            # Si no encontramos especificación directa, buscar campos descriptivos largos
            campos_descriptivos = []
            for key, value in material_dict.items():
                if isinstance(value, str) and len(value) > 15 and not any(x in key.lower() for x in ['codigo', 'numero', 'cantidad', 'fecha', 'id']):
                    campos_descriptivos.append((key, value))
            
            if campos_descriptivos:
                especificacion_encontrada = campos_descriptivos[0][1]
                campo_usado = campos_descriptivos[0][0]
                print(f"💡 Usando campo descriptivo '{campo_usado}': {especificacion_encontrada}")
        
        if especificacion_encontrada:
            return jsonify({
                'success': True,
                'especificacion': especificacion_encontrada,
                'campo_origen': campo_usado,
                'numero_parte': numero_parte,
                'material_completo': material_dict
            })
        else:
            print(f" No se encontró especificación para el material")
            print(f" Campos disponibles: {list(material_dict.keys())}")
            return jsonify({
                'success': False,
                'error': 'No se encontró especificación en el material',
                'material_disponible': material_dict,
                'campos_disponibles': list(material_dict.keys())
            })
            
    except Exception as e:
        print(f"❌ Error consultando especificación: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error interno: {str(e)}'
        }), 500

@app.route('/material/control_calidad')
@login_requerido
def material_control_calidad():
    """Cargar dinámicamente el control de calidad"""
    try:
        return render_template('Control de material/Control de calidad.html')
    except Exception as e:
        print(f"Error al cargar Control de calidad: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/material/historial_inventario')
@login_requerido
def material_historial_inventario():
    """Cargar dinámicamente el historial de inventario real"""
    try:
        return render_template('Control de material/Historial de inventario real.html')
    except Exception as e:
        print(f"Error al cargar Historial de inventario real: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/material/registro_material')
@login_requerido
def material_registro_material():
    """Cargar dinámicamente el registro de material real"""
    try:
        return render_template('Control de material/Registro de material real.html')
    except Exception as e:
        print(f"Error al cargar Registro de material real: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/material/control_retorno')
@login_requerido
def material_control_retorno():
    """Cargar dinámicamente el control de material de retorno"""
    try:
        return render_template('Control de material/Control de material de retorno.html')
    except Exception as e:
        print(f"Error al cargar Control de material de retorno: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/material/estatus_material')
@login_requerido
def material_estatus_material():
    """Cargar dinámicamente el estatus de material"""
    try:
        return render_template('Control de material/Estatus de material.html')
    except Exception as e:
        print(f"Error al cargar Estatus de material: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/api/estatus_material/consultar', methods=['POST'])
@login_requerido
def consultar_estatus_material():
    """API para obtener los datos del estatus de material basándose en inventario general y materiales"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        filtros = data if data else {}
        
        print(f"🔍 Consultando estatus de material con filtros: {filtros}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query principal que combina inventario_general con tabla materiales
        query = '''
            SELECT DISTINCT
                COALESCE(ig.codigo_material, ig.numero_parte) as codigo_material,
                ig.numero_parte as numero_parte_fabricante,
                ig.propiedad_material,
                COALESCE(m.especificacion_material, ig.especificacion, '') as especificacion,
                COALESCE(m.vendedor, '') as vendedor,
                COALESCE(m.ubicacion_material, '') as ubicacion_almacen,
                ig.cantidad_total as remanente,
                ig.fecha_actualizacion as ultima_actualizacion,
                ig.fecha_creacion
            FROM inventario_general ig
            LEFT JOIN materiales m ON (
                ig.numero_parte = m.numero_parte OR 
                ig.codigo_material = m.codigo_material OR
                ig.numero_parte = m.codigo_material
            )
            WHERE ig.cantidad_total > 0
        '''
        
        params = []
        
        # Aplicar filtros
        if filtros.get('codigo_material') and str(filtros.get('codigo_material')).strip().lower() != 'todos':
            query += ' AND (ig.codigo_material LIKE %s OR ig.numero_parte LIKE %s)'
            filtro_codigo = f"%{filtros['codigo_material']}%"
            params.extend([filtro_codigo, filtro_codigo])
        
        query += ' ORDER BY ig.fecha_actualizacion DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        inventario = []
        for row in rows:
            inventario.append({
                'codigo_material': row[0] or '',
                'numero_parte_fabricante': row[1] or '',
                'propiedad_de': row[2] or 'COMMON USE',
                'especificacion': row[3] or '',
                'vendedor': row[4] or '',
                'ubicacion_almacen': row[5] or '',
                'cantidad': float(row[6]) if row[6] else 0.0,
                'ultima_actualizacion': row[7] or '',
                'fecha_creacion': row[8] or ''
            })
        
        print(f" Estatus de material consultado: {len(inventario)} items encontrados")
        
        return jsonify({
            'success': True,
            'inventario': inventario,
            'total': len(inventario),
            'filtros_aplicados': filtros
        })
        
    except Exception as e:
        print(f"❌ Error al consultar estatus de material: {e}")
        return jsonify({
            'success': False,
            'error': f'Error al consultar estatus de material: {str(e)}'
        }), 500
        
    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass

@app.route('/obtener_reglas_escaneo')
def obtener_reglas_escaneo():
    """Endpoint para obtener las reglas de escaneo desde rules.json"""
    try:
        ruta_rules = os.path.join(os.path.dirname(__file__), 'database', 'rules.json')
        ruta_rules = os.path.abspath(ruta_rules)
        
        if os.path.exists(ruta_rules):
            with open(ruta_rules, 'r', encoding='utf-8') as f:
                reglas = json.load(f)
            return jsonify(reglas)
        else:
            print(f"❌ Archivo rules.json no encontrado en: {ruta_rules}")
            return jsonify({}), 404
            
    except Exception as e:
        print(f"❌ Error al cargar reglas de escaneo: {str(e)}")
        return jsonify({'error': str(e)}), 500

# === BUSCAR POR CODIGO MATERIAL RECIBIDO ===
@app.route('/buscar_codigo_recibido')
@login_requerido
def buscar_codigo_recibido():
    codigo = request.args.get('codigo_material_recibido')
    print(f"🔍 SERVER: Recibida petición para código: '{codigo}'")
    print(f"🔍 SERVER: Usuario en sesión: {session.get('usuario', 'No logueado')}")
    
    if not codigo:
        print("❌ SERVER: Código no proporcionado")
        return jsonify({'success': False, 'error': 'Código no proporcionado'})
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print(f"🔍 SERVER: Buscando en BD: {codigo}")
        cursor.execute('SELECT * FROM control_material_almacen WHERE codigo_material_recibido = %s', (codigo,))
        row = cursor.fetchone()
        
        if row:
            print(" SERVER: Registro encontrado en BD")
            # Convertir a dict usando nombres de columna
            columns = [desc[0] for desc in cursor.description]
            registro = dict(zip(columns, row))
            print(f"📦 SERVER: Datos encontrados: {registro}")
            return jsonify({'success': True, 'registro': registro})
        else:
            print("❌ SERVER: Código no encontrado en almacén")
            return jsonify({'success': False, 'error': 'Código no encontrado en almacén'})
            
    except Exception as e:
        print(f"💥 SERVER: Error en buscar_codigo_recibido: {str(e)}")
        return jsonify({'success': False, 'error': f'Error al buscar: {str(e)}'}), 500
        
    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass

# === GUARDAR SALIDA DE LOTE ===
@app.route('/guardar_salida_lote', methods=['POST'])
@login_requerido
def guardar_salida_lote():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        codigo_material_recibido = data.get('codigo_material_recibido')
        cantidad_salida = data.get('cantidad_salida')
        
        if not codigo_material_recibido or not cantidad_salida:
            return jsonify({'success': False, 'error': 'Faltan datos requeridos'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Consultar la fila original con propiedad de material
        cursor.execute('''
            SELECT cma.cantidad_actual, cma.propiedad_material 
            FROM control_material_almacen cma
            WHERE cma.codigo_material_recibido = %s
        ''', (codigo_material_recibido,))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({'success': False, 'error': 'Código no encontrado en almacén'})
        
        cantidad_actual = float(row[0]) if row[0] else 0
        propiedad_material_real = row[1] if row[1] else data.get('especificacion_material', '')
        cantidad_salida = float(cantidad_salida)
        
        if cantidad_salida > cantidad_actual:
            return jsonify({'success': False, 'error': f'Cantidad de salida ({cantidad_salida}) mayor a la disponible ({cantidad_actual})'})
        
        nueva_cantidad = cantidad_actual - cantidad_salida
        
        # Actualizar la cantidad en almacen
        cursor.execute('UPDATE control_material SET cantidad_actual = %s WHERE codigo_material_recibido = %s', 
                      (nueva_cantidad, codigo_material_recibido))
        
        # Obtener el numero_parte desde control_material_almacen
        cursor.execute('''
            SELECT numero_parte, especificacion 
            FROM control_material_almacen 
            WHERE codigo_material_recibido = %s
            LIMIT 1
        ''', (codigo_material_recibido,))
        
        resultado_almacen = cursor.fetchone()
        numero_parte_real = resultado_almacen[0] if resultado_almacen else codigo_material_recibido
        especificacion_real = resultado_almacen[1] if resultado_almacen else data.get('especificacion_material', '')
        
        # Registrar la salida en control_material_salida CON numero_parte
        cursor.execute('''
            INSERT INTO control_material_salida (
                codigo_material_recibido, numero_parte, numero_lote, modelo, depto_salida, 
                proceso_salida, cantidad_salida, fecha_salida, especificacion_material
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            codigo_material_recibido,
            numero_parte_real,  # NUEVO: numero_parte desde almacen
            data.get('numero_lote', ''),
            data.get('modelo', ''),
            data.get('depto_salida', ''),
            data.get('proceso_salida', ''),
            cantidad_salida,
            data.get('fecha_salida', ''),
            especificacion_real  # MEJORADO: especificacion desde almacen
        ))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Salida registrada exitosamente'})
        
    except Exception as e:
        print(f"Error en guardar_salida_lote: {str(e)}")
        return jsonify({'success': False, 'error': f'Error al guardar: {str(e)}'}), 500
        
    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass

# === CONSULTAR HISTORIAL DE SALIDAS ===
@app.route('/consultar_historial_salidas')
@login_requerido
def consultar_historial_salidas():
    conn = None
    cursor = None
    try:
        # Obtener parámetros de filtro (soportar ambos nombres para compatibilidad)
        fecha_inicio = request.args.get('fecha_inicio') or request.args.get('fecha_desde')
        fecha_fin = request.args.get('fecha_fin') or request.args.get('fecha_hasta')
        numero_lote = request.args.get('numero_lote', '').strip()
        codigo_material = request.args.get('codigo_material', '').strip()
        
        print(f"🔍 Filtros recibidos - fecha_desde: {fecha_inicio}, fecha_hasta: {fecha_fin}, codigo_material: {codigo_material}, numero_lote: {numero_lote}")
        
        # Crear clave de caché simple
        cache_key = f"{fecha_inicio}_{fecha_fin}_{codigo_material}_{numero_lote}"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Construir la consulta SQL optimizada para velocidad y sin duplicados
        query = '''
            SELECT DISTINCT
                s.fecha_salida,
                s.proceso_salida,
                s.codigo_material_recibido,
                COALESCE(a.codigo_material, s.codigo_material_recibido) as codigo_material,
                COALESCE(a.numero_parte, '') as numero_parte,
                s.cantidad_salida as disp,
                0 as hist,
                COALESCE(a.codigo_material_original, '') as codigo_material_original,
                s.numero_lote,
                s.modelo as maquina_linea,
                s.depto_salida as departamento,
                COALESCE(s.especificacion_material, a.especificacion, '') as especificacion_material
            FROM control_material_salida s
            LEFT JOIN control_material_almacen a ON s.codigo_material_recibido = a.codigo_material_recibido
            WHERE 1=1
        '''
        
        params = []
        
        if fecha_inicio:
            query += ' AND DATE(s.fecha_salida) >= %s'
            params.append(fecha_inicio)
        
        if fecha_fin:
            query += ' AND DATE(s.fecha_salida) <= %s'
            params.append(fecha_fin)
        
        if numero_lote:
            query += ' AND s.numero_lote LIKE %s'
            params.append(f'%{numero_lote}%')
            
        if codigo_material:
            query += ' AND (s.codigo_material_recibido LIKE %s OR a.codigo_material LIKE %s OR a.codigo_material_original LIKE %s)'
            params.extend([f'%{codigo_material}%', f'%{codigo_material}%', f'%{codigo_material}%'])
        
        # Optimizar ORDER BY y agregar LIMIT para velocidad máxima
        query += ' ORDER BY s.fecha_salida DESC LIMIT 500'
        
        print(f"✓ SQL Query ULTRA-OPTIMIZADO: {query}")
        print(f"📊 SQL Params: {params}")
        
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        
        # Convertir a lista de diccionarios
        datos = []
        for fila in resultados:
            if isinstance(fila, dict):
                # Si ya es un diccionario, usarlo directamente
                registro = fila
            else:
                # Si es una tupla, convertir usando las columnas
                columnas = [desc[0] for desc in cursor.description]
                registro = dict(zip(columnas, fila))
            datos.append(registro)
        
        # Obtener conteo total de registros (sin LIMIT)
        # Crear una consulta de conteo más simple sin DISTINCT problemático
        count_query = '''
            SELECT COUNT(*) as total
            FROM control_material_salida s
            LEFT JOIN control_material_almacen a ON s.codigo_material_recibido = a.codigo_material_recibido
            WHERE 1=1
        '''
        
        # Agregar los mismos filtros que la consulta principal
        count_params = []
        
        if fecha_inicio:
            count_query += ' AND DATE(s.fecha_salida) >= %s'
            count_params.append(fecha_inicio)
        
        if fecha_fin:
            count_query += ' AND DATE(s.fecha_salida) <= %s'
            count_params.append(fecha_fin)
        
        if numero_lote:
            count_query += ' AND s.numero_lote LIKE %s'
            count_params.append(f'%{numero_lote}%')
            
        if codigo_material:
            count_query += ' AND (s.codigo_material_recibido LIKE %s OR a.codigo_material LIKE %s OR a.codigo_material_original LIKE %s)'
            count_params.extend([f'%{codigo_material}%', f'%{codigo_material}%', f'%{codigo_material}%'])
        
        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()
        
        # Extraer el valor del conteo
        if isinstance(total_count, dict):
            total_registros = list(total_count.values())[0]
        else:
            total_registros = total_count[0] if total_count else 0
        
        print(f"📊 Consulta completada: {len(datos)} registros mostrados, {total_registros} registros totales")
        
        # Devolver tanto los datos como el conteo total
        return jsonify({
            'datos': datos,
            'total': total_registros,
            'mostrados': len(datos)
        })
        
    except Exception as e:
        print(f"Error al consultar historial de salidas: {str(e)}")
        return jsonify({'error': str(e)}), 500
        
    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass

# Nuevas funciones para Control de Salida
@app.route('/buscar_material_por_codigo', methods=['GET'])
@login_requerido
def buscar_material_por_codigo():
    """Buscar material en control_material_almacen por código de material recibido y calcular stock disponible real usando MySQL"""
    try:
        codigo_recibido = request.args.get('codigo_recibido', '').strip()
        
        if not codigo_recibido:
            return jsonify({'success': False, 'error': 'Código de material recibido no proporcionado'}), 400
        
        # Usar funciones de MySQL en lugar de SQLite
        from .db_mysql import buscar_material_por_codigo_mysql, obtener_total_salidas_material
        
        material = buscar_material_por_codigo_mysql(codigo_recibido)
        
        if not material:
            return jsonify({'success': False, 'error': 'Código de material no encontrado en almacén'})
        
        # Calcular el total de salidas para este código específico usando MySQL
        total_salidas = obtener_total_salidas_material(codigo_recibido)
        
        # Calcular stock disponible real
        cantidad_original = float(material['cantidad_actual'])
        stock_disponible = cantidad_original - total_salidas
        
        print(f"📊 STOCK CALCULADO para {codigo_recibido} (MySQL):")
        print(f"   - Cantidad original: {cantidad_original}")
        print(f"   - Total salidas: {total_salidas}")
        print(f"   - Stock disponible: {stock_disponible}")
        
        # Verificar si hay stock disponible
        if stock_disponible <= 0:
            return jsonify({
                'success': False, 
                'error': f'Material sin stock disponible. Original: {cantidad_original}, Salidas: {total_salidas}, Disponible: {stock_disponible}'
            })
        
        # Convertir el resultado a diccionario con stock actualizado
        material_data = {
            'id': material['id'],
            'forma_material': material['forma_material'],
            'cliente': material['cliente'],
            'codigo_material_original': material['codigo_material_original'],
            'codigo_material': material['codigo_material'],
            'material_importacion_local': material['material_importacion_local'],
            'fecha_recibo': material['fecha_recibo'],
            'fecha_fabricacion': material['fecha_fabricacion'],
            'cantidad_actual': stock_disponible,  # ← USAR STOCK CALCULADO EN LUGAR DE CANTIDAD ORIGINAL
            'cantidad_original': cantidad_original,  # ← MANTENER REFERENCIA A LA CANTIDAD ORIGINAL
            'total_salidas': total_salidas,  # ← INFORMACIÓN ADICIONAL
            'numero_lote_material': material['numero_lote_material'],
            'codigo_material_recibido': material['codigo_material_recibido'],
            'numero_parte': material['numero_parte'],
            'cantidad_estandarizada': material['cantidad_estandarizada'],
            'codigo_material_final': material['codigo_material_final'],
            'propiedad_material': material['propiedad_material'],
            'especificacion': material['especificacion'],
            'material_importacion_local_final': material['material_importacion_local_final'],
            'estado_desecho': material['estado_desecho'],
            'ubicacion_salida': material['ubicacion_salida'],
            'fecha_registro': material['fecha_registro'],
            'database_type': 'MySQL'  # Indicador de que se está usando MySQL
        }
        
        return jsonify({'success': True, 'material': material_data})
    
    except Exception as e:
        print(f"❌ ERROR en buscar_material_por_codigo (MySQL): {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500

@app.route('/verificar_stock_rapido', methods=['GET'])
@login_requerido
def verificar_stock_rapido():
    """Verificación ultra rápida de stock para salidas masivas - Solo devuelve stock disponible"""
    try:
        codigo = request.args.get('codigo', '').strip()
        
        if not codigo:
            return jsonify({'success': False, 'error': 'Código no proporcionado'}), 400
        
        # Consulta SQL ultra optimizada - solo lo esencial
        query = """
        SELECT 
            codigo_material_recibido,
            numero_parte,
            cantidad_actual,
            numero_lote_material,
            especificacion_material
        FROM control_material_almacen 
        WHERE codigo_material_recibido = %s 
        LIMIT 1
        """
        
        result = execute_query(query, (codigo,))
        
        if not result:
            return jsonify({'success': False, 'error': 'Material no encontrado'})
        
        material = result[0]
        
        # Consulta rápida de salidas totales
        query_salidas = """
        SELECT COALESCE(SUM(cantidad_salida), 0) as total_salidas
        FROM movimientos_inventario 
        WHERE codigo_material_recibido = %s AND tipo_movimiento = 'SALIDA'
        """
        
        salidas_result = execute_query(query_salidas, (codigo,))
        total_salidas = salidas_result[0]['total_salidas'] if salidas_result else 0
        
        # Calcular stock disponible
        cantidad_original = float(material['cantidad_actual'])
        stock_disponible = cantidad_original - total_salidas
        
        if stock_disponible <= 0:
            return jsonify({
                'success': False, 
                'error': 'Sin stock disponible',
                'stock': 0,
                'original': cantidad_original,
                'salidas': total_salidas
            })
        
        return jsonify({
            'success': True,
            'stock': stock_disponible,
            'numero_parte': material['numero_parte'],
            'numero_lote': material['numero_lote_material'],
            'especificacion': material['especificacion_material'],
            'original': cantidad_original,
            'salidas': total_salidas
        })
        
    except Exception as e:
        print(f"❌ ERROR en verificar_stock_rapido: {str(e)}")
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500

@app.route('/procesar_salida_material', methods=['POST'])
@login_requerido
def procesar_salida_material():
    """Procesar salida de material con respuesta inmediata y actualización de inventario en background usando MySQL"""
    import threading
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        required_fields = ['codigo_material_recibido', 'cantidad_salida']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Campo requerido: {field}'}), 400
        
        codigo_recibido = data['codigo_material_recibido']
        cantidad_salida = float(data['cantidad_salida'])
        
        if cantidad_salida <= 0:
            return jsonify({'success': False, 'error': 'La cantidad de salida debe ser mayor a 0'}), 400
        
        # Usar funciones de MySQL en lugar de SQLite
        from .db_mysql import (buscar_material_por_codigo_mysql, obtener_total_salidas_material, 
                               registrar_salida_material_mysql, actualizar_inventario_general_salida_mysql)
        
        # Buscar el material en almacén para obtener información completa
        material = buscar_material_por_codigo_mysql(codigo_recibido)
        
        if not material:
            return jsonify({'success': False, 'error': 'Material no encontrado en almacén'}), 400
        
        cantidad_original = material['cantidad_actual']
        numero_parte = material['numero_parte'] or ''
        
        # Calcular el total de salidas existentes para este código específico usando MySQL
        total_salidas_previas = obtener_total_salidas_material(codigo_recibido)
        
        # Calcular stock disponible real
        stock_disponible = cantidad_original - total_salidas_previas
        
        print(f"📊 VERIFICACIÓN STOCK PARA SALIDA {codigo_recibido} (MySQL):")
        print(f"   - Cantidad original: {cantidad_original}")
        print(f"   - Salidas previas: {total_salidas_previas}")
        print(f"   - Stock disponible: {stock_disponible}")
        print(f"   - Cantidad solicitada: {cantidad_salida}")
        
        if stock_disponible <= 0:
            return jsonify({'success': False, 'error': f'Sin stock disponible. Original: {cantidad_original}, Salidas previas: {total_salidas_previas}'}), 400
        
        if cantidad_salida > stock_disponible:
            return jsonify({'success': False, 'error': f'Cantidad insuficiente. Stock disponible: {stock_disponible}, solicitado: {cantidad_salida}'}), 400
        
        # Preparar datos para registrar la salida usando MySQL
        salida_data = {
            'codigo_material_recibido': codigo_recibido,
            'numero_lote': data.get('numero_lote', ''),
            'modelo': data.get('modelo', ''),
            'depto_salida': data.get('depto_salida', ''),
            'proceso_salida': data.get('proceso_salida', ''),
            'cantidad_salida': cantidad_salida,
            'fecha_salida': data.get('fecha_salida', '')
        }
        
        # Solo incluir especificacion_material si se proporciona explícitamente
        if 'especificacion_material' in data and data['especificacion_material']:
            salida_data['especificacion_material'] = data['especificacion_material']
        
        # Registrar la salida usando MySQL
        resultado_salida = registrar_salida_material_mysql(salida_data)
        
        if not resultado_salida.get('success', False):
            error_msg = resultado_salida.get('error', 'Error al registrar la salida en la base de datos')
            return jsonify({'success': False, 'error': error_msg}), 500
        
        # Obtener información del proceso determinado
        proceso_destino = resultado_salida.get('proceso_destino', 'PRODUCCION')
        especificacion_usada = resultado_salida.get('especificacion_usada', '')
        
        nueva_cantidad = stock_disponible - cantidad_salida
        
        #  OPTIMIZACIÓN: Actualizar inventario general en BACKGROUND THREAD
        def actualizar_inventario_background():
            """Función para actualizar inventario en segundo plano usando MySQL"""
            try:
                if numero_parte:
                    print(f" BACKGROUND (MySQL): Actualizando inventario para {numero_parte}")
                    resultado = actualizar_inventario_general_salida_mysql(numero_parte, cantidad_salida)
                    if resultado:
                        print(f" BACKGROUND (MySQL): Inventario actualizado exitosamente: -{cantidad_salida} para {numero_parte}")
                    else:
                        print(f"❌ BACKGROUND (MySQL): Error al actualizar inventario para {numero_parte}")
            except Exception as e:
                print(f"❌ BACKGROUND ERROR (MySQL): {e}")
        
        # Ejecutar actualización de inventario en hilo separado
        if numero_parte:
            inventario_thread = threading.Thread(target=actualizar_inventario_background)
            inventario_thread.daemon = True  # Se cierra con la aplicación
            inventario_thread.start()
            print(f"🚀 OPTIMIZADO (MySQL): Salida registrada, inventario actualizándose en background")
        
        #  RESPUESTA INMEDIATA AL USUARIO
        return jsonify({
            'success': True,
            'message': f'Salida registrada exitosamente. Cantidad: {cantidad_salida}',
            'nueva_cantidad_disponible': nueva_cantidad,
            'proceso_destino': proceso_destino,  # Incluir proceso destino determinado
            'especificacion_usada': especificacion_usada,  # Incluir especificación usada
            'optimized': True,  # Indicador de que se está usando optimización
            'numero_parte': numero_parte,  # Para debugging
            'inventario_actualizado_en_background': True,
            'database_type': 'MySQL'  # Indicador de que se está usando MySQL
        })
        
    except Exception as e:
        print(f"❌ ERROR GENERAL en procesar_salida_material (MySQL): {e}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500

@app.route('/forzar_actualizacion_inventario/<numero_parte>', methods=['POST'])
@login_requerido  
def forzar_actualizacion_inventario(numero_parte):
    """
    Endpoint para forzar la actualización del inventario general para un número de parte específico
    """
    try:
        print(f" FORZANDO actualización de inventario para: {numero_parte}")
        
        # Recalcular inventario para este número de parte específico
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener todas las entradas para este número de parte
        cursor.execute('''
            SELECT SUM(cantidad_actual) as total_entradas
            FROM control_material_almacen 
            WHERE numero_parte = %s
        ''', (numero_parte,))
        entradas_result = cursor.fetchone()
        total_entradas = entradas_result[0] if entradas_result and entradas_result[0] else 0
        
        # Obtener todas las salidas para este número de parte
        cursor.execute('''
            SELECT SUM(cantidad_salida) as total_salidas
            FROM control_material_salida cms
            JOIN control_material_almacen cma ON cms.codigo_material_recibido = cma.codigo_material_recibido
            WHERE cma.numero_parte = %s
        ''', (numero_parte,))
        salidas_result = cursor.fetchone()
        total_salidas = salidas_result[0] if salidas_result and salidas_result[0] else 0
        
        # Calcular cantidad total actual
        cantidad_total_actual = total_entradas - total_salidas
        
        # Actualizar o insertar en inventario_general
        cursor.execute('''
            INSERT INTO inventario_general 
            (numero_parte, cantidad_entradas, cantidad_salidas, cantidad_total, fecha_actualizacion)
            VALUES (%s, %s, %s, %s, NOW()) ON DUPLICATE KEY UPDATE cantidad_entradas = VALUES(cantidad_entradas), cantidad_salidas = VALUES(cantidad_salidas), cantidad_total = VALUES(cantidad_total), fecha_actualizacion = VALUES(fecha_actualizacion)
        ''', (numero_parte, total_entradas, total_salidas, cantidad_total_actual))
        
        conn.commit()
        conn.close()
        
        print(f" FORZADO: Inventario actualizado para {numero_parte}: {cantidad_total_actual}")
        
        return jsonify({
            'success': True,
            'numero_parte': numero_parte,
            'cantidad_total_actualizada': cantidad_total_actual,
            'total_entradas': total_entradas,
            'total_salidas': total_salidas
        })
        
    except Exception as e:
        print(f"❌ ERROR al forzar actualización de inventario: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
        print(f"Error al procesar salida de material: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500
        
    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass

@app.route('/recalcular_inventario_general', methods=['POST'])
@login_requerido
def recalcular_inventario_general_endpoint():
    """Endpoint para recalcular todo el inventario consolidado desde cero"""
    try:
        # Importar función de base de datos
        from .db_mysql import get_connection
        
        connection = get_connection()
        if not connection:
            return jsonify({
                'success': False,
                'error': 'Error de conexión a la base de datos'
            }), 500
            
        cursor = connection.cursor()
        
        # 1. Limpiar tabla inventario_consolidado
        cursor.execute("DELETE FROM inventario_consolidado")
        
        # 2. Recalcular desde control_material_almacen
        query_recalcular = """
            INSERT INTO inventario_consolidado 
            (numero_parte, codigo_material, especificacion, propiedad_material,
             cantidad_actual, total_lotes, fecha_ultima_entrada, fecha_primera_entrada,
             total_entradas, total_salidas)
            SELECT 
                numero_parte,
                MAX(codigo_material) as codigo_material,
                MAX(especificacion) as especificacion,
                MAX(propiedad_material) as propiedad_material,
                SUM(COALESCE(cantidad_actual, 0)) as cantidad_actual,
                COUNT(DISTINCT numero_lote_material) as total_lotes,
                MAX(fecha_recibo) as fecha_ultima_entrada,
                MIN(fecha_recibo) as fecha_primera_entrada,
                SUM(COALESCE(cantidad_actual, 0)) as total_entradas,
                0 as total_salidas
            FROM control_material_almacen 
            WHERE estado_desecho = FALSE
            GROUP BY numero_parte
        """
        
        cursor.execute(query_recalcular)
        filas_afectadas = cursor.rowcount
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print(f"✅ Inventario consolidado recalculado: {filas_afectadas} números de parte actualizados")
        
        return jsonify({
            'success': True,
            'message': f'Inventario consolidado recalculado exitosamente. {filas_afectadas} números de parte actualizados.'
        })
            
    except Exception as e:
        print(f"Error en endpoint recalcular inventario: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error interno: {str(e)}'
        }), 500

@app.route('/obtener_inventario_general', methods=['GET'])
@login_requerido
def obtener_inventario_general_endpoint():
    """Endpoint para obtener el inventario general (para uso futuro)"""
    try:
        from app.db_mysql import obtener_inventario
        inventario = obtener_inventario()
        return jsonify({
            'success': True,
            'inventario': inventario,
            'total_items': len(inventario)
        })
        
    except Exception as e:
        print(f"Error al obtener inventario general: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error interno: {str(e)}'
        }), 500

@app.route('/verificar_estado_inventario', methods=['GET'])
@login_requerido
def verificar_estado_inventario():
    """Endpoint opcional para verificar si el inventario general está actualizado"""
    try:
        numero_parte = request.args.get('numero_parte')
        
        if not numero_parte:
            return jsonify({'success': False, 'error': 'Número de parte requerido'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar estado del inventario para este número de parte
        cursor.execute('''
            SELECT numero_parte, cantidad_total, fecha_actualizacion 
            FROM inventario_general 
            WHERE numero_parte = %s
        ''', (numero_parte,))
        
        resultado = cursor.fetchone()
        
        if resultado:
            from datetime import datetime, timedelta
            
            # Verificar si la actualización es reciente (últimos 30 segundos)
            try:
                fecha_actualizacion = datetime.strptime(resultado['fecha_actualizacion'], '%Y-%m-%d %H:%M:%S')
                tiempo_transcurrido = datetime.now() - fecha_actualizacion
                actualizado_recientemente = tiempo_transcurrido < timedelta(seconds=30)
            except:
                actualizado_recientemente = False
            
            return jsonify({
                'success': True,
                'numero_parte': resultado['numero_parte'],
                'cantidad_total': resultado['cantidad_total'],
                'fecha_actualizacion': resultado['fecha_actualizacion'],
                'actualizado_recientemente': actualizado_recientemente,
                'mensaje': 'Inventario actualizado' if actualizado_recientemente else 'Inventario estable'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'No se encontró registro de inventario para {numero_parte}'
            }), 404
        
    except Exception as e:
        print(f"Error al verificar estado de inventario: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500
    
    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass

@app.route('/imprimir_zebra', methods=['POST'])
@login_requerido
def imprimir_zebra():
    """
    Endpoint para enviar comandos ZPL a impresora Zebra ZT230 (USB o Red)
    """
    import socket
    import subprocess
    import tempfile
    import os
    import time
    import traceback
    from datetime import datetime
    
    try:
        data = request.get_json()
        metodo_conexion = data.get('metodo_conexion', 'usb')  # 'usb' o 'red'
        ip_impresora = data.get('ip_impresora')
        comando_zpl = data.get('comando_zpl')
        codigo = data.get('codigo', '')
        
        print(f"🦓 ZT230: Método: {metodo_conexion}")
        print(f"🦓 ZT230: Código: {codigo}")
        print(f"🦓 ZT230: Comando ZPL: {comando_zpl}")
        
        if not comando_zpl:
            return jsonify({
                'success': False, 
                'error': 'Comando ZPL es requerido'
            }), 400
        
        if metodo_conexion == 'usb':
            # Impresión por USB para ZT230 - usar IP local por defecto
            ip_local = ip_impresora or '127.0.0.1'  # IP local por defecto
            return imprimir_zebra_red(ip_local, comando_zpl, codigo)
        else:
            # Impresión por red para ZT230
            return imprimir_zebra_red(ip_impresora, comando_zpl, codigo)
            
    except Exception as e:
        error_msg = f'Error interno del servidor: {str(e)}'
        print(f"❌ ZT230 CRITICAL ERROR: {error_msg}")
        print(f"❌ ZT230 TRACEBACK: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

def imprimir_zebra_red(ip_impresora, comando_zpl, codigo):
    """
    Imprime en Zebra ZT230 por red (protocolo estándar)
    """
    import socket
    from datetime import datetime
    
    try:
        if not ip_impresora:
            return jsonify({
                'success': False, 
                'error': 'IP de impresora es requerida para conexión por red'
            }), 400
        
        # Configuración de conexión Zebra ZD421
        puerto_zebra = 9100  # Puerto estándar para impresoras Zebra
        timeout = 10  # 10 segundos timeout
        
        try:
            # Crear socket TCP
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            print(f"🔌 ZEBRA RED: Conectando a {ip_impresora}:{puerto_zebra}")
            
            # Conectar a la impresora
            sock.connect((ip_impresora, puerto_zebra))
            print(" ZEBRA RED: Conexión establecida")
            
            # Enviar comando ZPL
            comando_bytes = comando_zpl.encode('utf-8')
            sock.send(comando_bytes)
            print(f"📤 ZEBRA RED: Comando enviado ({len(comando_bytes)} bytes)")
            
            # Pequeña pausa para procesamiento
            import time
            time.sleep(1)
            
            # Cerrar conexión
            sock.close()
            print(" ZEBRA RED: Etiqueta enviada exitosamente")
            
            # Log del evento
            print(f"📊 ZEBRA LOG: {obtener_fecha_hora_mexico()} - Usuario: {session.get('usuario')} - Código: {codigo} - IP: {ip_impresora}")
            
            return jsonify({
                'success': True,
                'message': f'Etiqueta enviada a impresora Zebra {ip_impresora}',
                'metodo': 'red',
                'codigo': codigo,
                'timestamp': obtener_fecha_hora_mexico().isoformat()
            })
            
        except socket.timeout:
            error_msg = f'Timeout al conectar con la impresora en {ip_impresora}:{puerto_zebra}'
            print(f"⏰ ZEBRA RED ERROR: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg,
                'suggestion': 'Verifique que la impresora esté encendida y conectada a la red'
            }), 408
            
        except socket.gaierror as e:
            error_msg = f'No se pudo resolver la dirección IP: {ip_impresora}'
            print(f"🌐 ZEBRA RED ERROR: {error_msg} - {str(e)}")
            return jsonify({
                'success': False,
                'error': error_msg,
                'suggestion': 'Verifique que la IP sea correcta'
            }), 400
            
        except ConnectionRefusedError:
            error_msg = f'Conexión rechazada por {ip_impresora}:{puerto_zebra}'
            print(f"🚫 ZEBRA RED ERROR: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg,
                'suggestion': 'Verifique que la impresora esté encendida y el puerto 9100 esté abierto'
            }), 503
            
        except Exception as socket_error:
            error_msg = f'Error de conexión: {str(socket_error)}'
            print(f"💥 ZEBRA RED ERROR: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg,
                'suggestion': 'Verifique la configuración de red de la impresora'
            }), 500
        
    except Exception as e:
        error_msg = f'Error en impresión por red: {str(e)}'
        print(f"❌ ZEBRA RED CRITICAL ERROR: {error_msg}")
        
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

@app.route('/imprimir_etiqueta_qr', methods=['POST'])
@login_requerido
def imprimir_etiqueta_qr():
    """
    Endpoint optimizado para impresión automática directa de etiquetas QR
    Sin confirmaciones, imprime inmediatamente al guardar material
    """
    import socket
    import subprocess
    import tempfile
    import os
    import time
    from datetime import datetime
    
    try:
        data = request.get_json()
        codigo = data.get('codigo', '')
        comando_zpl = data.get('comando_zpl', '')
        metodo = data.get('metodo', 'usb')  # 'usb' o 'red'
        ip = data.get('ip', '192.168.1.100')
        
        print(f" IMPRESIÓN DIRECTA: Código={codigo}, Método={metodo}")
        
        if not codigo or not comando_zpl:
            return jsonify({
                'success': False,
                'error': 'Código y comando ZPL son requeridos'
            }), 400
        
        # Log del intento de impresión
        timestamp = obtener_fecha_hora_mexico().isoformat()
        usuario = session.get('usuario', 'unknown')
        print(f"📊 PRINT LOG: {timestamp} - User: {usuario} - Code: {codigo} - Method: {metodo}")
        
        if metodo == 'usb':
            return imprimir_directo_usb(comando_zpl, codigo)
        else:
            return imprimir_directo_red(comando_zpl, codigo, ip)
            
    except Exception as e:
        error_msg = f'Error en impresión directa: {str(e)}'
        print(f"❌ IMPRESIÓN DIRECTA ERROR: {error_msg}")
        print(f"❌ TRACEBACK: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

def imprimir_directo_usb(comando_zpl, codigo):
    """
    Impresión directa por USB - envía inmediatamente a la impresora predeterminada
    """
    from datetime import datetime
    import subprocess
    import tempfile
    import os
    
    try:
        print("🔌 IMPRESIÓN USB DIRECTA: Iniciando...")
        
        # Crear archivo temporal
        temp_dir = 'C:\\temp'
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"etiqueta_{codigo.replace(',', '_')}_{timestamp}.zpl"
        filepath = os.path.join(temp_dir, filename)
        
        # Escribir comando ZPL
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(comando_zpl)
        
        print(f"📄 Archivo creado: {filepath}")
        
        # MÉTODO 1: Intentar impresión directa usando copy command a puerto LPT1
        try:
            print("🖨️ Intentando impresión directa vía copy command...")
            result = subprocess.run(
                ['copy', filepath, 'LPT1:'], 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(" Impresión exitosa vía LPT1")
                return jsonify({
                    'success': True,
                    'message': 'Etiqueta enviada directamente a impresora USB',
                    'metodo': 'copy_lpt1',
                    'codigo': codigo,
                    'timestamp': datetime.now().isoformat()
                })
                
        except Exception as e1:
            print(f" LPT1 falló: {str(e1)}")
        
        # MÉTODO 2: Usar comando de Windows para imprimir directamente
        try:
            print("🖨️ Intentando con comando print de Windows...")
            result = subprocess.run(
                ['print', '/D:USB001', filepath],
                shell=True,
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                print(" Impresión exitosa vía print command")
                return jsonify({
                    'success': True,
                    'message': 'Etiqueta enviada directamente a impresora USB',
                    'metodo': 'windows_print',
                    'codigo': codigo,
                    'timestamp': datetime.now().isoformat()
                })
                
        except Exception as e2:
            print(f" Windows print falló: {str(e2)}")
        
        # MÉTODO 3: Usar PowerShell para imprimir
        try:
            print("🖨️ Intentando con PowerShell...")
            ps_command = f'Get-Content "{filepath}" | Out-Printer -Name "ZDesigner ZT230-300dpi ZPL"'
            result = subprocess.run(
                ['powershell', '-Command', ps_command],
                capture_output=True,
                text=True,
                timeout=20
            )
            
            if result.returncode == 0:
                print(" Impresión exitosa vía PowerShell")
                return jsonify({
                    'success': True,
                    'message': 'Etiqueta enviada directamente a impresora Zebra',
                    'metodo': 'powershell',
                    'codigo': codigo,
                    'timestamp': datetime.now().isoformat()
                })
                
        except Exception as e3:
            print(f" PowerShell falló: {str(e3)}")
        
        # MÉTODO 4: Fallback - crear archivo y abrir carpeta
        print("📁 Fallback: Creando archivo para impresión manual...")
        
        try:
            os.startfile(temp_dir)
        except:
            pass
        
        return jsonify({
            'success': True,
            'message': 'Archivo de etiqueta creado. Revisar carpeta temp.',
            'metodo': 'file_fallback',
            'archivo': filepath,
            'codigo': codigo,
            'instrucciones': [
                f'Archivo guardado en: {filepath}',
                'Se abrió la carpeta automáticamente',
                'Haga doble clic en el archivo para imprimir'
            ],
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        error_msg = f'Error en impresión USB directa: {str(e)}'
        print(f"❌ USB DIRECTO ERROR: {error_msg}")
        
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

def imprimir_directo_red(comando_zpl, codigo, ip):
    """
    Impresión directa por red - envía inmediatamente vía socket TCP
    """
    import socket
    from datetime import datetime
    
    try:
        print(f"🌐 IMPRESIÓN RED DIRECTA: {ip}:9100")
        
        # Configuración de socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # Timeout de 10 segundos
        
        # Conectar y enviar
        sock.connect((ip, 9100))
        sock.send(comando_zpl.encode('utf-8'))
        sock.close()
        
        print(f" Etiqueta enviada exitosamente a {ip}")
        
        return jsonify({
            'success': True,
            'message': f'Etiqueta enviada directamente a impresora {ip}',
            'metodo': 'socket_directo',
            'codigo': codigo,
            'ip': ip,
            'timestamp': datetime.now().isoformat()
        })
        
    except socket.timeout:
        error_msg = f'Timeout al conectar con {ip}:9100'
        print(f"⏰ RED DIRECTA ERROR: {error_msg}")
        
        return jsonify({
            'success': False,
            'error': error_msg
        }), 408
        
    except Exception as e:
        error_msg = f'Error de conexión de red: {str(e)}'
        print(f"❌ RED DIRECTA ERROR: {error_msg}")
        
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

@app.route('/test_modelos')
def test_modelos():
    """Página de prueba para verificar la carga de modelos"""
    return render_template('test_modelos.html')

# Ruta para el inventario general (nuevo)
@app.route('/api/inventario/consultar', methods=['POST'])
@login_requerido
def consultar_inventario_general():
    """Endpoint optimizado usando tabla inventario_consolidado para mayor eficiencia"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        filtros = data if data else {}
        
        # Usar específicamente la conexión MySQL del hosting
        from .config_mysql import get_mysql_connection
        
        conn = get_mysql_connection()
        using_mysql = True
        
        if conn is None:
            return jsonify({
                'success': False,
                'error': 'No se pudo conectar a la base de datos MySQL'
            }), 500
            
        cursor = conn.cursor()  # Usar cursor normal
        
        # Verificar que la tabla inventario_consolidado existe en MySQL
        try:
            cursor.execute("SHOW TABLES LIKE 'inventario_consolidado'")
            
            if not cursor.fetchone():
                return jsonify({
                    'success': False,
                    'error': 'Tabla inventario_consolidado no encontrada en MySQL'
                }), 500
        except Exception as table_error:
            return jsonify({
                'success': False,
                'error': f'Error verificando tablas: {str(table_error)}'
            }), 500
        
        # Construir consulta optimizada para MySQL
        query = '''
            SELECT 
                ic.numero_parte,
                ic.codigo_material,
                ic.especificacion,
                ic.propiedad_material,
                ic.cantidad_actual as cantidad_total,
                ic.total_lotes,
                ic.fecha_ultima_entrada as fecha_ultimo_recibo,
                ic.fecha_primera_entrada as fecha_primer_recibo,
                ic.total_entradas,
                ic.total_salidas
            FROM inventario_consolidado ic
            WHERE 1=1
        '''
        
        params = []
        
        # Aplicar filtros MySQL
        if filtros.get('numeroParte'):
            query += ' AND ic.numero_parte LIKE %s'
            params.append(f"%{filtros['numeroParte']}%")
            
        if filtros.get('propiedad'):
            query += ' AND ic.propiedad_material = %s'
            params.append(filtros['propiedad'])
        
        # Filtrar por cantidad mínima
        if filtros.get('cantidadMinima') and float(filtros['cantidadMinima']) > 0:
            query += ' AND ic.cantidad_actual >= %s'
            params.append(float(filtros['cantidadMinima']))
        
        query += ' ORDER BY ic.fecha_ultima_entrada DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        inventario = []
        for i, row in enumerate(rows):
            try:
                # Procesar como tupla (orden según la consulta SELECT)
                # SELECT numero_parte, codigo_material, especificacion, propiedad_material,
                #        cantidad_actual, total_lotes, fecha_ultima_entrada, fecha_primera_entrada,
                #        total_entradas, total_salidas
                numero_parte = row[0] if len(row) > 0 else ''
                codigo_material = row[1] if len(row) > 1 else numero_parte
                especificacion = row[2] if len(row) > 2 else ''
                propiedad_material = row[3] if len(row) > 3 else 'COMMON USE'
                cantidad_total = float(row[4]) if len(row) > 4 and row[4] is not None else 0.0
                total_lotes = int(row[5]) if len(row) > 5 and row[5] is not None else 0
                fecha_ultimo_recibo = row[6] if len(row) > 6 else None
                fecha_primer_recibo = row[7] if len(row) > 7 else None
                total_entradas = float(row[8]) if len(row) > 8 and row[8] is not None else 0.0
                total_salidas = float(row[9]) if len(row) > 9 and row[9] is not None else 0.0
                    
                # Mostrar registros que tengan entradas (aunque la cantidad total sea 0 o negativa)
                if total_entradas > 0:
                    inventario.append({
                        'id': i + 1,
                        'numero_parte': numero_parte,
                        'codigo_material': codigo_material,
                        'especificacion': especificacion,
                        'propiedad_material': propiedad_material,
                        'cantidad_total': cantidad_total,
                        'total_entradas': total_entradas,
                        'total_salidas': total_salidas,
                        'total_lotes': total_lotes,
                        'lotes_disponibles': [],  # Se consulta por separado si es necesario
                        'fecha_ultimo_recibo': fecha_ultimo_recibo,
                        'fecha_primer_recibo': fecha_primer_recibo
                    })
                        
            except Exception as row_error:
                continue
        
        return jsonify({
            'success': True,
            'inventario': inventario,
            'total': len(inventario),
            'filtros_aplicados': filtros,
            'modo': 'agrupado_por_numero_parte'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al consultar inventario: {str(e)}'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/inventario/historial', methods=['POST'])
@login_requerido
def obtener_historial_numero_parte():
    """Endpoint para obtener el historial completo de entradas y salidas de un número de parte"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        numero_parte = data.get('numero_parte', '').strip()
        
        if not numero_parte:
            return jsonify({
                'success': False,
                'error': 'Número de parte requerido'
            }), 400
        
        from .db import is_mysql_connection
        using_mysql = is_mysql_connection()
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': False,
                'error': 'No se pudo conectar a la base de datos'
            }), 500
            
        cursor = conn.cursor()
        
        # Obtener todas las entradas (registros en control_material_almacen)
        if using_mysql:
            entradas_query = '''
                SELECT 
                    'ENTRADA' as tipo_movimiento,
                    fecha_recibo as fecha_movimiento,
                    numero_lote_material as lote,
                    cantidad_actual as cantidad,
                    codigo_material_recibido,
                    especificacion,
                    propiedad_material,
                    'RECIBO INICIAL' as detalle_movimiento,
                    fecha_registro
                FROM control_material_almacen
                WHERE numero_parte = %s
                ORDER BY fecha_recibo DESC
            '''
            cursor.execute(entradas_query, [numero_parte])
        else:
            entradas_query = '''
                SELECT 
                    'ENTRADA' as tipo_movimiento,
                    fecha_recibo as fecha_movimiento,
                    numero_lote_material as lote,
                    cantidad_actual as cantidad,
                    codigo_material_recibido,
                    especificacion,
                    propiedad_material,
                    'RECIBO INICIAL' as detalle_movimiento,
                    fecha_registro
                FROM control_material_almacen
                WHERE numero_parte = ?
                ORDER BY fecha_recibo DESC
            '''
            cursor.execute(entradas_query, [numero_parte])
        
        entradas_rows = cursor.fetchall()
        
        # Obtener todas las salidas usando numero_parte directamente
        if using_mysql:
            salidas_query = '''
                SELECT 
                    'SALIDA' as tipo_movimiento,
                    cms.fecha_salida as fecha_movimiento,
                    cms.numero_lote as lote,
                    cms.cantidad_salida as cantidad,
                    cms.codigo_material_recibido,
                    cms.especificacion_material as especificacion,
                    'N/A' as propiedad_material,
                    CONCAT('SALIDA - ', cms.modelo, ' - ', cms.depto_salida, ' - ', cms.proceso_salida) as detalle_movimiento,
                    cms.fecha_registro
                FROM control_material_salida cms
                WHERE cms.numero_parte = %s
                ORDER BY cms.fecha_salida DESC
            '''
            cursor.execute(salidas_query, [numero_parte])
        else:
            salidas_query = '''
                SELECT 
                    'SALIDA' as tipo_movimiento,
                    cms.fecha_salida as fecha_movimiento,
                    cms.numero_lote as lote,
                    cms.cantidad_salida as cantidad,
                    cms.codigo_material_recibido,
                    cms.especificacion_material as especificacion,
                    'N/A' as propiedad_material,
                    ('SALIDA - ' || cms.modelo || ' - ' || cms.depto_salida || ' - ' || cms.proceso_salida) as detalle_movimiento,
                    cms.fecha_registro
                FROM control_material_salida cms
                WHERE cms.numero_parte = ?
                ORDER BY cms.fecha_salida DESC
            '''
            cursor.execute(salidas_query, [numero_parte])
        
        salidas_rows = cursor.fetchall()
        
        # Combinar entradas y salidas
        historial = []
        
        # Procesar entradas
        for row in entradas_rows:
            if hasattr(row, 'keys'):
                historial.append({
                    'tipo_movimiento': row.get('tipo_movimiento', ''),
                    'fecha_movimiento': row.get('fecha_movimiento'),
                    'lote': row.get('lote', ''),
                    'cantidad': float(row.get('cantidad', 0)) if row.get('cantidad') else 0.0,
                    'codigo_material_recibido': row.get('codigo_material_recibido', ''),
                    'especificacion': row.get('especificacion', ''),
                    'propiedad_material': row.get('propiedad_material', ''),
                    'detalle_movimiento': row.get('detalle_movimiento', ''),
                    'fecha_registro': row.get('fecha_registro')
                })
            else:
                historial.append({
                    'tipo_movimiento': row[0] or '',
                    'fecha_movimiento': row[1],
                    'lote': row[2] or '',
                    'cantidad': float(row[3] or 0),
                    'codigo_material_recibido': row[4] or '',
                    'especificacion': row[5] or '',
                    'propiedad_material': row[6] or '',
                    'detalle_movimiento': row[7] or '',
                    'fecha_registro': row[8]
                })
        
        # Procesar salidas
        for row in salidas_rows:
            if hasattr(row, 'keys'):
                historial.append({
                    'tipo_movimiento': row.get('tipo_movimiento', ''),
                    'fecha_movimiento': row.get('fecha_movimiento'),
                    'lote': row.get('lote', ''),
                    'cantidad': -float(row.get('cantidad', 0)) if row.get('cantidad') else 0.0,  # Negativo para salidas
                    'codigo_material_recibido': row.get('codigo_material_recibido', ''),
                    'especificacion': row.get('especificacion', ''),
                    'propiedad_material': row.get('propiedad_material', ''),
                    'detalle_movimiento': row.get('detalle_movimiento', ''),
                    'fecha_registro': row.get('fecha_registro')
                })
            else:
                historial.append({
                    'tipo_movimiento': row[0] or '',
                    'fecha_movimiento': row[1],
                    'lote': row[2] or '',
                    'cantidad': -float(row[3] or 0),  # Negativo para salidas
                    'codigo_material_recibido': row[4] or '',
                    'especificacion': row[5] or '',
                    'propiedad_material': row[6] or '',
                    'detalle_movimiento': row[7] or '',
                    'fecha_registro': row[8]
                })
        
        # Ordenar por fecha de movimiento descendente
        historial.sort(key=lambda x: x['fecha_movimiento'] or '', reverse=True)
        
        # Calcular balance acumulado
        balance_acumulado = 0
        for movimiento in reversed(historial):  # Procesar en orden cronológico para el balance
            balance_acumulado += movimiento['cantidad']
            movimiento['balance_acumulado'] = balance_acumulado
        
        # Revertir orden para mostrar más recientes primero
        historial.reverse()
        
        print(f" Historial obtenido: {len(historial)} movimientos para {numero_parte}")
        
        return jsonify({
            'success': True,
            'historial': historial,
            'numero_parte': numero_parte,
            'total_movimientos': len(historial),
            'balance_actual': balance_acumulado
        })
        
    except Exception as e:
        print(f"❌ Error al obtener historial: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error al obtener historial: {str(e)}'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/inventario/historial/<numero_parte>')
@login_requerido
def obtener_historial_numero_parte_get(numero_parte):
    """Endpoint GET para obtener el historial completo de entradas y salidas de un número de parte"""
    conn = None
    cursor = None
    try:
        if not numero_parte:
            return jsonify({
                'success': False,
                'error': 'Número de parte requerido'
            }), 400
        
        print(f"🔍 Consultando historial GET para número de parte: {numero_parte}")
        
        from .db import is_mysql_connection
        using_mysql = is_mysql_connection()
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': False,
                'error': 'No se pudo conectar a la base de datos'
            }), 500
            
        cursor = conn.cursor()
        
        # Obtener todas las entradas (registros en control_material_almacen)
        if using_mysql:
            entradas_query = '''
                SELECT 
                    'ENTRADA' as tipo_movimiento,
                    fecha_recibo as fecha_movimiento,
                    numero_lote_material as lote,
                    cantidad_actual as cantidad,
                    codigo_material_recibido,
                    especificacion,
                    propiedad_material,
                    'RECIBO INICIAL' as detalle_movimiento,
                    fecha_registro
                FROM control_material_almacen
                WHERE numero_parte = %s
                ORDER BY fecha_recibo DESC
            '''
            cursor.execute(entradas_query, [numero_parte])
        else:
            entradas_query = '''
                SELECT 
                    'ENTRADA' as tipo_movimiento,
                    fecha_recibo as fecha_movimiento,
                    numero_lote_material as lote,
                    cantidad_actual as cantidad,
                    codigo_material_recibido,
                    especificacion,
                    propiedad_material,
                    'RECIBO INICIAL' as detalle_movimiento,
                    fecha_registro
                FROM control_material_almacen
                WHERE numero_parte = ?
                ORDER BY fecha_recibo DESC
            '''
            cursor.execute(entradas_query, [numero_parte])
        
        entradas_rows = cursor.fetchall()
        
        # Obtener todas las salidas
        if using_mysql:
            salidas_query = '''
                SELECT 
                    'SALIDA' as tipo_movimiento,
                    cms.fecha_salida as fecha_movimiento,
                    cms.numero_lote as lote,
                    cms.cantidad_salida as cantidad,
                    cms.codigo_material_recibido,
                    cms.especificacion_material as especificacion,
                    'N/A' as propiedad_material,
                    CONCAT('SALIDA - ', cms.modelo, ' - ', cms.depto_salida, ' - ', cms.proceso_salida) as detalle_movimiento,
                    cms.fecha_registro
                FROM control_material_salida cms
                INNER JOIN control_material_almacen cma ON cms.codigo_material_recibido = cma.codigo_material_recibido
                WHERE cma.numero_parte = %s
                ORDER BY cms.fecha_salida DESC
            '''
            cursor.execute(salidas_query, [numero_parte])
        else:
            salidas_query = '''
                SELECT 
                    'SALIDA' as tipo_movimiento,
                    cms.fecha_salida as fecha_movimiento,
                    cms.numero_lote as lote,
                    cms.cantidad_salida as cantidad,
                    cms.codigo_material_recibido,
                    cms.especificacion_material as especificacion,
                    'N/A' as propiedad_material,
                    ('SALIDA - ' || cms.modelo || ' - ' || cms.depto_salida || ' - ' || cms.proceso_salida) as detalle_movimiento,
                    cms.fecha_registro
                FROM control_material_salida cms
                INNER JOIN control_material_almacen cma ON cms.codigo_material_recibido = cma.codigo_material_recibido
                WHERE cma.numero_parte = ?
                ORDER BY cms.fecha_salida DESC
            '''
            cursor.execute(salidas_query, [numero_parte])
        
        salidas_rows = cursor.fetchall()
        
        # Combinar entradas y salidas
        historial = []
        
        # Procesar entradas
        for row in entradas_rows:
            if hasattr(row, 'keys'):
                historial.append({
                    'tipo_movimiento': row.get('tipo_movimiento', ''),
                    'fecha_movimiento': row.get('fecha_movimiento'),
                    'lote': row.get('lote', ''),
                    'cantidad': float(row.get('cantidad', 0)) if row.get('cantidad') else 0.0,
                    'codigo_material_recibido': row.get('codigo_material_recibido', ''),
                    'especificacion': row.get('especificacion', ''),
                    'propiedad_material': row.get('propiedad_material', ''),
                    'detalle_movimiento': row.get('detalle_movimiento', ''),
                    'fecha_registro': row.get('fecha_registro')
                })
            else:
                historial.append({
                    'tipo_movimiento': row[0] or '',
                    'fecha_movimiento': row[1],
                    'lote': row[2] or '',
                    'cantidad': float(row[3] or 0),
                    'codigo_material_recibido': row[4] or '',
                    'especificacion': row[5] or '',
                    'propiedad_material': row[6] or '',
                    'detalle_movimiento': row[7] or '',
                    'fecha_registro': row[8]
                })
        
        # Procesar salidas (cantidad negativa para balance)
        for row in salidas_rows:
            if hasattr(row, 'keys'):
                historial.append({
                    'tipo_movimiento': row.get('tipo_movimiento', ''),
                    'fecha_movimiento': row.get('fecha_movimiento'),
                    'lote': row.get('lote', ''),
                    'cantidad': -float(row.get('cantidad', 0)) if row.get('cantidad') else 0.0,
                    'codigo_material_recibido': row.get('codigo_material_recibido', ''),
                    'especificacion': row.get('especificacion', ''),
                    'propiedad_material': row.get('propiedad_material', ''),
                    'detalle_movimiento': row.get('detalle_movimiento', ''),
                    'fecha_registro': row.get('fecha_registro')
                })
            else:
                historial.append({
                    'tipo_movimiento': row[0] or '',
                    'fecha_movimiento': row[1],
                    'lote': row[2] or '',
                    'cantidad': -float(row[3] or 0),
                    'codigo_material_recibido': row[4] or '',
                    'especificacion': row[5] or '',
                    'propiedad_material': row[6] or '',
                    'detalle_movimiento': row[7] or '',
                    'fecha_registro': row[8]
                })
        
        # Ordenar por fecha
        historial.sort(key=lambda x: x['fecha_movimiento'] or '', reverse=True)
        
        # Calcular balance acumulado
        balance_acumulado = 0
        for mov in reversed(historial):
            balance_acumulado += mov['cantidad']
            mov['balance_acumulado'] = balance_acumulado
        
        print(f" Historial obtenido: {len(historial)} movimientos, balance: {balance_acumulado}")
        
        return jsonify({
            'success': True,
            'historial': historial,
            'numero_parte': numero_parte,
            'total_movimientos': len(historial),
            'balance_actual': balance_acumulado
        })
        
    except Exception as e:
        print(f"❌ Error al obtener historial GET: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error al obtener historial: {str(e)}'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/inventario/lotes', methods=['POST'])
@login_requerido  
def obtener_lotes_numero_parte():
    """Endpoint mejorado para obtener todos los lotes disponibles de un número de parte"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        numero_parte = data.get('numero_parte', '').strip()
        
        if not numero_parte:
            return jsonify({
                'success': False,
                'error': 'Número de parte requerido'
            }), 400
        
        print(f"🔍 Consultando lotes para número de parte: {numero_parte}")
        
        from .db import is_mysql_connection
        using_mysql = is_mysql_connection()
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': False,
                'error': 'No se pudo conectar a la base de datos'
            }), 500
            
        cursor = conn.cursor()
        
        # Query mejorado para obtener lotes con información completa
        if using_mysql:
            query = '''
                SELECT 
                    cma.numero_lote_material,
                    cma.cantidad_actual,
                    cma.fecha_recibo,
                    cma.fecha_fabricacion,
                    cma.codigo_material_recibido,
                    cma.especificacion,
                    cma.propiedad_material,
                    cma.ubicacion_salida,
                    COALESCE(salidas.total_salidas, 0) as total_salidas,
                    (cma.cantidad_actual - COALESCE(salidas.total_salidas, 0)) as cantidad_disponible
                FROM control_material_almacen cma
                LEFT JOIN (
                    SELECT 
                        codigo_material_recibido,
                        numero_lote,
                        SUM(cantidad_salida) as total_salidas
                    FROM control_material_salida
                    GROUP BY codigo_material_recibido, numero_lote
                ) salidas ON cma.codigo_material_recibido = salidas.codigo_material_recibido 
                          AND cma.numero_lote_material = salidas.numero_lote
                WHERE cma.numero_parte = %s
                  AND cma.cantidad_actual > 0
                  AND (cma.cantidad_actual - COALESCE(salidas.total_salidas, 0)) > 0
                ORDER BY cma.fecha_recibo DESC
            '''
            cursor.execute(query, [numero_parte])
        else:
            query = '''
                SELECT 
                    cma.numero_lote_material,
                    cma.cantidad_actual,
                    cma.fecha_recibo,
                    cma.fecha_fabricacion,
                    cma.codigo_material_recibido,
                    cma.especificacion,
                    cma.propiedad_material,
                    cma.ubicacion_salida,
                    COALESCE(salidas.total_salidas, 0) as total_salidas,
                    (cma.cantidad_actual - COALESCE(salidas.total_salidas, 0)) as cantidad_disponible
                FROM control_material_almacen cma
                LEFT JOIN (
                    SELECT 
                        codigo_material_recibido,
                        numero_lote,
                        SUM(cantidad_salida) as total_salidas
                    FROM control_material_salida
                    GROUP BY codigo_material_recibido, numero_lote
                ) salidas ON cma.codigo_material_recibido = salidas.codigo_material_recibido 
                          AND cma.numero_lote_material = salidas.numero_lote
                WHERE cma.numero_parte = ?
                  AND cma.cantidad_actual > 0
                  AND (cma.cantidad_actual - COALESCE(salidas.total_salidas, 0)) > 0
                ORDER BY cma.fecha_recibo DESC
            '''
            cursor.execute(query, [numero_parte])
        
        rows = cursor.fetchall()
        
        print(f"🔍 Lotes encontrados: {len(rows) if rows else 0}")
        
        lotes = []
        for row in rows:
            try:
                if hasattr(row, 'keys'):
                    cantidad_disponible = float(row.get('cantidad_disponible', 0))
                    if cantidad_disponible > 0:
                        lotes.append({
                            'numero_lote': row.get('numero_lote_material', ''),
                            'cantidad_original': float(row.get('cantidad_actual', 0)),
                            'total_salidas': float(row.get('total_salidas', 0)),
                            'cantidad_disponible': cantidad_disponible,
                            'fecha_recibo': row.get('fecha_recibo'),
                            'fecha_fabricacion': row.get('fecha_fabricacion'),
                            'codigo_material_recibido': row.get('codigo_material_recibido', ''),
                            'especificacion': row.get('especificacion', ''),
                            'propiedad_material': row.get('propiedad_material', ''),
                            'ubicacion_salida': row.get('ubicacion_salida', '')
                        })
                else:
                    cantidad_disponible = float(row[9] if row[9] else 0)
                    if cantidad_disponible > 0:
                        lotes.append({
                            'numero_lote': row[0] or '',
                            'cantidad_original': float(row[1] if row[1] else 0),
                            'total_salidas': float(row[8] if row[8] else 0),
                            'cantidad_disponible': cantidad_disponible,
                            'fecha_recibo': row[2],
                            'fecha_fabricacion': row[3],
                            'codigo_material_recibido': row[4] or '',
                            'especificacion': row[5] or '',
                            'propiedad_material': row[6] or '',
                            'ubicacion_salida': row[7] or ''
                        })
            except Exception as row_error:
                print(f"❌ Error procesando lote: {row_error}")
                continue
        
        print(f" Lotes disponibles: {len(lotes)} para {numero_parte}")
        
        return jsonify({
            'success': True,
            'lotes': lotes,
            'numero_parte': numero_parte,
            'total_lotes': len(lotes)
        })
        
    except Exception as e:
        print(f"❌ Error al consultar lotes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error al consultar lotes: {str(e)}'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/inventario/lotes/<numero_parte>')
@login_requerido
def obtener_lotes_numero_parte_get(numero_parte):
    """Endpoint GET para obtener todos los lotes disponibles de un número de parte"""
    conn = None
    cursor = None
    try:
        if not numero_parte:
            return jsonify({
                'success': False,
                'error': 'Número de parte requerido'
            }), 400
        
        print(f"🔍 Consultando lotes GET para número de parte: {numero_parte}")
        
        from .db import is_mysql_connection
        using_mysql = is_mysql_connection()
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': False,
                'error': 'No se pudo conectar a la base de datos'
            }), 500
            
        cursor = conn.cursor()
        
        # Query optimizada para obtener lotes con balance disponible
        if using_mysql:
            query = '''
            SELECT
                    cma.numero_lote_material,
                    cma.cantidad_actual,
                    cma.fecha_recibo,
                    cma.fecha_fabricacion,
                    cma.codigo_material_recibido,
                    cma.especificacion,
                    cma.propiedad_material,
                    cma.ubicacion_salida,
                    COALESCE(salidas.total_salidas, 0) as total_salidas,
                    (cma.cantidad_actual - COALESCE(salidas.total_salidas, 0)) as cantidad_disponible
                FROM control_material_almacen cma
                LEFT JOIN (
                    SELECT 
                        codigo_material_recibido,
                        numero_lote,
                        SUM(cantidad_salida) as total_salidas
                    FROM control_material_salida
                    GROUP BY codigo_material_recibido, numero_lote
                ) salidas ON cma.codigo_material_recibido = salidas.codigo_material_recibido 
                          AND cma.numero_lote_material = salidas.numero_lote
                WHERE cma.numero_parte = %s
                  AND cma.cantidad_actual > 0
                  AND (cma.cantidad_actual - COALESCE(salidas.total_salidas, 0)) > 0
                ORDER BY cma.fecha_recibo DESC
            '''
            cursor.execute(query, [numero_parte])
        else:
            query = '''
                SELECT 
                    cma.numero_lote_material,
                    cma.cantidad_actual,
                    cma.fecha_recibo,
                    cma.fecha_fabricacion,
                    cma.codigo_material_recibido,
                    cma.especificacion,
                    cma.propiedad_material,
                    cma.ubicacion_salida,
                    COALESCE(salidas.total_salidas, 0) as total_salidas,
                    (cma.cantidad_actual - COALESCE(salidas.total_salidas, 0)) as cantidad_disponible
                FROM control_material_almacen cma
                LEFT JOIN (
                    SELECT 
                        codigo_material_recibido,
                        numero_lote,
                        SUM(cantidad_salida) as total_salidas
                    FROM control_material_salida
                    GROUP BY codigo_material_recibido, numero_lote
                ) salidas ON cma.codigo_material_recibido = salidas.codigo_material_recibido 
                          AND cma.numero_lote_material = salidas.numero_lote
                WHERE cma.numero_parte = ?
                  AND cma.cantidad_actual > 0
                  AND (cma.cantidad_actual - COALESCE(salidas.total_salidas, 0)) > 0
                ORDER BY cma.fecha_recibo DESC
            '''
            cursor.execute(query, [numero_parte])
        
        rows = cursor.fetchall()
        
        print(f"🔍 Lotes encontrados: {len(rows) if rows else 0}")
        
        lotes = []
        for row in rows:
            try:
                if hasattr(row, 'keys'):
                    cantidad_disponible = float(row.get('cantidad_disponible', 0))
                    if cantidad_disponible > 0:
                        lotes.append({
                            'numero_lote': row.get('numero_lote_material', ''),
                            'cantidad_original': float(row.get('cantidad_actual', 0)),
                            'total_salidas': float(row.get('total_salidas', 0)),
                            'cantidad_disponible': cantidad_disponible,
                            'fecha_recibo': row.get('fecha_recibo'),
                            'fecha_fabricacion': row.get('fecha_fabricacion'),
                            'codigo_material_recibido': row.get('codigo_material_recibido', ''),
                            'especificacion': row.get('especificacion', ''),
                            'propiedad_material': row.get('propiedad_material', ''),
                            'ubicacion_salida': row.get('ubicacion_salida', '')
                        })
                else:
                    cantidad_disponible = float(row[9] if row[9] else 0)
                    if cantidad_disponible > 0:
                        lotes.append({
                            'numero_lote': row[0] or '',
                            'cantidad_original': float(row[1] if row[1] else 0),
                            'total_salidas': float(row[8] if row[8] else 0),
                            'cantidad_disponible': cantidad_disponible,
                            'fecha_recibo': row[2],
                            'fecha_fabricacion': row[3],
                            'codigo_material_recibido': row[4] or '',
                            'especificacion': row[5] or '',
                            'propiedad_material': row[6] or '',
                            'ubicacion_salida': row[7] or ''
                        })
            except Exception as row_error:
                print(f"❌ Error procesando lote: {row_error}")
                continue
        
        print(f" Lotes disponibles: {len(lotes)} para {numero_parte}")
        
        return jsonify({
            'success': True,
            'lotes': lotes,
            'numero_parte': numero_parte,
            'total_lotes': len(lotes)
        })
        
    except Exception as e:
        print(f"❌ Error al consultar lotes GET: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error al consultar lotes: {str(e)}'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/templates/LISTAS/<filename>')
def serve_list_template(filename):
    """Servir plantillas de listas para el menú móvil"""
    try:
        # Verificar que el archivo existe y es uno de los permitidos
        allowed_files = [
            'LISTA_INFORMACIONBASICA.html',
            'LISTA_DE_MATERIALES.html', 
            'LISTA_CONTROLDEPRODUCCION.html',
            'LISTA_CONTROL_DE_PROCESO.html',
            'LISTA_CONTROL_DE_CALIDAD.html',
            'LISTA_DE_CONFIGPG.html',
            'LISTA_DE_CONTROL_DE_REPORTE.html',
            'LISTA_DE_CONTROL_DE_RESULTADOS.html'
        ]
        
        if filename not in allowed_files:
            return "Archivo no encontrado", 404
            
        # Leer el archivo directamente
        template_folder = app.template_folder or 'templates'
        template_path = os.path.join(template_folder, 'LISTAS', filename)
        
        if not os.path.exists(template_path):
            return f"Archivo no encontrado: {template_path}", 404
            
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
    except Exception as e:
        print(f"Error sirviendo plantilla {filename}: {str(e)}")
        return f"Error cargando la plantilla: {str(e)}", 500

# ===== RUTAS PARA EL SISTEMA DE PERMISOS DROPDOWNS =====

@app.route('/verificar_permiso_dropdown', methods=['POST'])
def verificar_permiso_dropdown():
    """
    Verificar si el usuario actual tiene permiso para un dropdown específico
    """
    try:
        if 'username' not in session:
            return jsonify({'tiene_permiso': False, 'error': 'Usuario no autenticado'}), 401
        
        # Obtener datos desde JSON
        data = request.get_json()
        if not data:
            return jsonify({'tiene_permiso': False, 'error': 'Datos JSON requeridos'}), 400
            
        pagina = data.get('pagina', '').strip()
        seccion = data.get('seccion', '').strip() 
        boton = data.get('boton', '').strip()
        
        if not all([pagina, seccion, boton]):
            return jsonify({'tiene_permiso': False, 'error': 'Parámetros incompletos'}), 400
        
        username = session['username']
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener roles del usuario desde la nueva estructura
        cursor.execute('''
            SELECT r.nombre
            FROM usuarios_sistema u
            JOIN usuario_roles ur ON u.id = ur.usuario_id
            JOIN roles r ON ur.rol_id = r.id
            WHERE u.username = %s AND u.activo = 1 AND r.activo = 1
            ORDER BY r.nivel DESC
            LIMIT 1
        ''', (username,))
        
        usuario_rol = cursor.fetchone()
        
        if not usuario_rol:
            return jsonify({'tiene_permiso': False, 'error': 'Usuario no encontrado o sin roles'}), 404
        
        rol_nombre = usuario_rol[0]
        
        # Superadmin tiene todos los permisos
        if rol_nombre == 'superadmin':
            return jsonify({'tiene_permiso': True, 'motivo': 'superadmin'})
        
        # Verificar permiso específico
        cursor.execute('''
            SELECT COUNT(*) FROM usuarios_sistema u
            JOIN usuario_roles ur ON u.id = ur.usuario_id
            JOIN rol_permisos_botones rpb ON ur.rol_id = rpb.rol_id
            JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
            WHERE u.username = %s AND pb.pagina = %s AND pb.seccion = %s AND pb.boton = %s
            AND u.activo = 1 AND pb.activo = 1
        ''', (username, pagina, seccion, boton))
        
        tiene_permiso = cursor.fetchone()[0] > 0
        conn.close()
        
        return jsonify({
            'tiene_permiso': tiene_permiso,
            'usuario': username,
            'rol': rol_nombre,
            'permiso': f"{pagina} > {seccion} > {boton}"
        })
        
    except Exception as e:
        print(f"Error verificando permiso: {e}")
        return jsonify({'tiene_permiso': False, 'error': str(e)}), 500

@app.route('/obtener_permisos_usuario_actual', methods=['GET'])
@login_requerido
def obtener_permisos_usuario_actual():
    """
    Obtener todos los permisos del usuario actual para caché en frontend
    """
    try:
        if 'usuario' not in session:
            return jsonify({'permisos': [], 'error': 'Usuario no autenticado'}), 401
        
        username = session['usuario']
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener roles del usuario desde la nueva estructura
        cursor.execute('''
            SELECT r.nombre
            FROM usuarios_sistema u
            JOIN usuario_roles ur ON u.id = ur.usuario_id
            JOIN roles r ON ur.rol_id = r.id
            WHERE u.username = %s AND u.activo = 1 AND r.activo = 1
            ORDER BY r.nivel DESC
            LIMIT 1
        ''', (username,))
        
        usuario_rol = cursor.fetchone()
        
        if not usuario_rol:
            conn.close()
            return jsonify({'permisos': {}, 'error': 'Usuario no encontrado o sin roles'}), 404
        
        # Acceso compatible con dict o tupla
        rol_nombre = usuario_rol['nombre'] if isinstance(usuario_rol, dict) else usuario_rol[0]
        
        # Superadmin tiene todos los permisos
        if rol_nombre == 'superadmin':
            cursor.execute('SELECT pagina, seccion, boton FROM permisos_botones WHERE activo = 1 ORDER BY pagina, seccion, boton')
            permisos = cursor.fetchall()
        else:
            # Obtener permisos específicos del rol
            cursor.execute('''
                SELECT pb.pagina, pb.seccion, pb.boton 
                FROM usuarios_sistema u
                JOIN usuario_roles ur ON u.id = ur.usuario_id
                JOIN rol_permisos_botones rpb ON ur.rol_id = rpb.rol_id
                JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
                WHERE u.username = %s AND u.activo = 1 AND pb.activo = 1
                ORDER BY pb.pagina, pb.seccion, pb.boton
            ''', (username,))
            permisos = cursor.fetchall()
        
        conn.close()
        
        # Formatear permisos para JavaScript en estructura jerárquica
        permisos_jerarquicos = {}
        total_permisos = 0
        
        for permiso in permisos:
            # Acceso compatible con dict o tupla
            if isinstance(permiso, dict):
                pagina = permiso['pagina']
                seccion = permiso['seccion']
                boton = permiso['boton']
            else:
                pagina, seccion, boton = permiso
            
            if pagina not in permisos_jerarquicos:
                permisos_jerarquicos[pagina] = {}
            
            if seccion not in permisos_jerarquicos[pagina]:
                permisos_jerarquicos[pagina][seccion] = []
            
            permisos_jerarquicos[pagina][seccion].append(boton)
            total_permisos += 1
        
        return jsonify({
            'permisos': permisos_jerarquicos,
            'usuario': username,
            'rol': rol_nombre,
            'total_permisos': total_permisos
        })
        
    except Exception as e:
        print(f"Error obteniendo permisos: {e}")
        return jsonify({'permisos': [], 'error': str(e)}), 500

@app.route('/test-permisos')
@login_requerido
def test_permisos():
    """Página de testing del sistema de permisos"""
    usuario = session.get('usuario')
    return render_template('test_permisos.html', usuario=usuario)

@app.route('/test-frontend-permisos')
@login_requerido
def test_frontend_permisos():
    """Página de testing frontend del sistema de permisos"""
    return send_file('../test_frontend_permisos.html')

@app.route('/test-ajax-manager')
@login_requerido
def test_ajax_manager():
    """Página de testing del AjaxContentManager"""
    return render_template('test_ajax_manager.html')

# ============== CSV VIEWER ROUTES ==============
@app.route('/csv-viewer')
@login_requerido
def csv_viewer():
    """Página principal del visor de CSV"""
    try:
        return render_template('csv-viewer.html')
    except Exception as e:
        print(f"Error al cargar CSV viewer: {e}")
        return f"Error al cargar la página: {str(e)}", 500

# Nueva ruta para historial de cambio de material de SMT
@app.route('/historial-cambio-material-smt')
@login_requerido
def historial_cambio_material_smt():
    """Página del historial de cambio de material de SMT"""
    try:
        return render_template('Control de calidad/historial_cambio_material_smt.html')
    except Exception as e:
        print(f"Error al cargar historial de cambio de material SMT: {e}")
        return f"Error al cargar la página: {str(e)}", 500

@app.route('/historial-cambio-material-smt-ajax')
def historial_cambio_material_smt_ajax():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    try:
        return render_template('Control de calidad/historial_cambio_material_smt_ajax.html')
    except Exception as e:
        print(f"Error en historial_cambio_material_smt_ajax: {e}")
        return f"Error interno del servidor: {e}", 500

@app.route('/api/csv_data')
@login_requerido
def get_csv_data():
    """API para obtener datos SMT desde MySQL (no archivos CSV)"""
    try:
        folder = request.args.get('folder', '')
        print(f"🔍 Solicitud recibida para carpeta: '{folder}'")
        
        if not folder:
            print("❌ No se proporcionó parámetro de carpeta")
            return jsonify({'success': False, 'error': 'Folder parameter required'}), 400
        
        # Conectar a MySQL directamente
        import mysql.connector
        
        mysql_config = {
            'host': os.getenv('MYSQL_HOST', 'up-de-fra1-mysql-1.db.run-on-seenode.com'),
            'port': int(os.getenv('MYSQL_PORT', 11550)),
            'user': os.getenv('MYSQL_USER', 'db_rrpq0erbdujn'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'db_rrpq0erbdujn'),
            'charset': 'utf8mb4'
        }
        
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor(dictionary=True)
        
        print(f"🔍 Consultando datos SMT desde MySQL para carpeta: {folder}")
        
        # Query para obtener datos de la tabla MySQL
        query = """
            SELECT
            ScanDate,
            ScanTime,
            SlotNo,
            Result,
            PreviousBarcode,
            Productdate,
            PartName,
            Quantity,
            SEQ,
            Vendor,
            LOTNO,
            Barcode,
            FeederBase,
            archivo,
            linea,
            maquina,
            fecha_subida
        FROM logs_maquina
        WHERE archivo LIKE %s OR linea LIKE %s OR maquina LIKE %s
        ORDER BY ScanDate DESC, ScanTime DESC
        LIMIT 1000
        """
        
        cursor.execute(query, (f"%{folder}%", f"%{folder}%", f"%{folder}%"))
        resultados = cursor.fetchall()
        
        print(f"✓ Encontrados {len(resultados)} registros en MySQL")
        
        # Convertir datos para JSON
        all_data = []
        for resultado in resultados:
            cleaned_record = {}
            for key, value in resultado.items():
                if hasattr(value, 'isoformat'):  # Es una fecha/datetime
                    cleaned_record[key] = value.isoformat()
                elif value is None:
                    cleaned_record[key] = None
                else:
                    cleaned_record[key] = str(value)
            
            # Mapear nombres para compatibilidad con frontend (usar nombres de la nueva tabla)
            cleaned_record['ScanDate'] = cleaned_record.get('ScanDate', '')
            cleaned_record['ScanTime'] = cleaned_record.get('ScanTime', '')
            cleaned_record['SlotNo'] = cleaned_record.get('SlotNo', '')
            cleaned_record['Result'] = cleaned_record.get('Result', '')
            cleaned_record['PartName'] = cleaned_record.get('PartName', '')
            cleaned_record['SourceFile'] = cleaned_record.get('archivo', '')  # Mapear archivo a SourceFile
            cleaned_record['LOTNO'] = cleaned_record.get('LOTNO', '')
            cleaned_record['Barcode'] = cleaned_record.get('Barcode', '')
            cleaned_record['Quantity'] = cleaned_record.get('Quantity', '')
            cleaned_record['Vendor'] = cleaned_record.get('Vendor', '')
            cleaned_record['FeederBase'] = cleaned_record.get('FeederBase', '')
            cleaned_record['PreviousBarcode'] = cleaned_record.get('PreviousBarcode', '')
            
            all_data.append(cleaned_record)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': all_data,
            'message': f'Datos MySQL cargados para {folder}: {len(all_data)} registros',
            'files_processed': len(set([d.get('SourceFile', '') for d in all_data])),
            'source': 'mysql_logs_maquina'
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo datos desde MySQL: {e}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False, 
            'error': f'Error al consultar base de datos MySQL: {str(e)}'
        }), 500


@app.route('/api/csv_stats')
@login_requerido
def get_csv_stats():
    """API para obtener estadísticas SMT desde MySQL (no archivos CSV)"""
    try:
        folder = request.args.get('folder', '')
        print(f"🔍 Solicitud recibida para estadísticas de carpeta: '{folder}'")
        
        if not folder:
            print("❌ No se proporcionó parámetro de carpeta")
            return jsonify({'success': False, 'error': 'Folder parameter required'}), 400
        
        # Conectar a MySQL directamente
        import mysql.connector
        
        mysql_config = {
            'host': os.getenv('MYSQL_HOST', 'up-de-fra1-mysql-1.db.run-on-seenode.com'),
            'port': int(os.getenv('MYSQL_PORT', 11550)),
            'user': os.getenv('MYSQL_USER', 'db_rrpq0erbdujn'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'db_rrpq0erbdujn'),
            'charset': 'utf8mb4'
        }
        
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor(dictionary=True)
        
        print(f"🔍 Consultando estadísticas SMT desde MySQL para carpeta: {folder}")
        
        # Query para obtener estadísticas de la tabla MySQL
        query = """
            SELECT
            COUNT(*) as total_records,
            COUNT(DISTINCT archivo) as total_files,
            COUNT(DISTINCT ScanDate) as total_days,
            COUNT(CASE WHEN Result = 'OK' THEN 1 END) as ok_count,
            COUNT(CASE WHEN Result = 'NG' THEN 1 END) as ng_count,
            MIN(ScanDate) as first_date,
            MAX(ScanDate) as last_date
        FROM logs_maquina
        WHERE archivo LIKE %s OR linea LIKE %s OR maquina LIKE %s
        """
        
        cursor.execute(query, (f"%{folder}%", f"%{folder}%", f"%{folder}%"))
        stats = cursor.fetchone()
        
        # Query para obtener archivos únicos
        files_query = """
        SELECT DISTINCT archivo, COUNT(*) as records
        FROM logs_maquina
        WHERE archivo LIKE %s OR linea LIKE %s OR maquina LIKE %s
        GROUP BY archivo
        ORDER BY archivo
        """
        
        cursor.execute(files_query, (f"%{folder}%", f"%{folder}%", f"%{folder}%"))
        files_info = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        print(f"📊 Estadísticas obtenidas: {stats['total_records']} registros de {stats['total_files']} archivos")
        
        return jsonify({
            'success': True,
            'stats': {
                'total_records': stats['total_records'] or 0,
                'total_files': stats['total_files'] or 0,
                'total_days': stats['total_days'] or 0,
                'ok_count': stats['ok_count'] or 0,
                'ng_count': stats['ng_count'] or 0,
                'first_date': stats['first_date'].isoformat() if stats['first_date'] else None,
                'last_date': stats['last_date'].isoformat() if stats['last_date'] else None
            },
            'files': [{'name': f['source_file'], 'records': f['records']} for f in files_info],
            'message': f'Estadísticas MySQL para {folder}',
            'source': 'mysql'
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas desde MySQL: {e}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False, 
            'error': f'Error al consultar estadísticas MySQL: {str(e)}'
        }), 500

        print(f"📁 Encontrados {len(csv_files)} archivos CSV")
        
        # Leer y combinar todos los archivos CSV
        all_data = []
        
        for csv_file in csv_files:
            try:
                print(f"📄 Leyendo archivo: {os.path.basename(csv_file)} (tamaño: {os.path.getsize(csv_file)} bytes)")
                
                # Intentar lectura simple primero
                try:
                    df = pd.read_csv(csv_file, encoding='utf-8', on_bad_lines='skip')
                    print(f" Lectura exitosa con pandas básico: {len(df)} filas")
                except Exception as simple_error:
                    print(f" Error con lectura simple: {str(simple_error)}")
                    
                    # Leer el archivo como texto primero para limpiar formato
                    with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    print(f" Contenido leído: {len(content)} caracteres")
                    
                    # Limpiar saltos de línea incorrectos en el contenido
                    lines = content.strip().split('\n')
                    cleaned_lines = []
                    
                    for line in lines:
                        # Si la línea no termina con una coma y la siguiente no empieza con una fecha,
                        # probablemente es una línea cortada
                        if line and not line.endswith(','):
                            cleaned_lines.append(line)
                        elif line.endswith(','):
                            # Línea que termina en coma, probablemente incompleta
                            if cleaned_lines:
                                cleaned_lines[-1] += line
                            else:
                                cleaned_lines.append(line)
                    
                    print(f"🧹 Líneas limpiadas: {len(cleaned_lines)} de {len(lines)} originales")
                    
                    # Crear DataFrame desde el contenido limpio
                    from io import StringIO
                    cleaned_content = '\n'.join(cleaned_lines)
                    
                    # Leer el archivo CSV con pandas usando el contenido limpio
                    df = pd.read_csv(StringIO(cleaned_content), encoding='utf-8', on_bad_lines='skip')
                
                print(f"📊 DataFrame creado: {len(df)} filas, {len(df.columns)} columnas")
                print(f" Columnas: {list(df.columns)}")
                
                # Verificar que el DataFrame tenga las columnas esperadas
                expected_columns = ['ScanDate', 'ScanTime', 'SlotNo', 'Result', 'PartName']
                missing_columns = [col for col in expected_columns if col not in df.columns]
                
                if missing_columns:
                    print(f" Columnas faltantes en {csv_file}: {missing_columns}")
                    # Intentar leer de forma más básica
                    df = pd.read_csv(csv_file, encoding='utf-8', on_bad_lines='skip', sep=',')
                
                # Convertir a diccionarios y agregar nombre del archivo fuente
                file_data = df.to_dict('records')
                
                # Limpiar valores NaN y convertir a tipos JSON válidos
                cleaned_data = []
                for record in file_data:
                    cleaned_record = {}
                    for key, value in record.items():
                        # Convertir NaN y valores problemáticos a None (null en JSON)
                        if pd.isna(value) or str(value).lower() == 'nan':
                            cleaned_record[key] = None
                        elif isinstance(value, (int, float)) and (value != value):  # Check for NaN
                            cleaned_record[key] = None
                        else:
                            # Convertir a string para asegurar compatibilidad JSON
                            cleaned_record[key] = str(value) if value is not None else None
                    
                    cleaned_record['SourceFile'] = os.path.basename(csv_file)
                    cleaned_data.append(cleaned_record)
                
                print(f"💾 Datos procesados y limpiados: {len(cleaned_data)} registros del archivo {os.path.basename(csv_file)}")
                all_data.extend(cleaned_data)
                
            except Exception as file_error:
                print(f"❌ Error definitivo leyendo {csv_file}: {str(file_error)}")
                print(f"❌ Tipo de error: {type(file_error).__name__}")
                import traceback
                print(f"❌ Traceback: {traceback.format_exc()}")
                continue
        
        if not all_data:
            return jsonify({
                'success': False,
                'error': 'No se pudieron leer datos de los archivos CSV',
                'files_found': len(csv_files)
            }), 500
        
        print(f" Datos cargados: {len(all_data)} registros de {len(csv_files)} archivos")
        
        return jsonify({
            'success': True,
            'data': all_data,
            'message': f'Datos cargados para {folder}: {len(all_data)} registros',
            'files_processed': len(csv_files),
            'path': folder_path
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo datos CSV: {e}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False, 
            'error': f'Error al acceder a los archivos CSV: {str(e)}'
        }), 500

@app.route('/api/filter_data', methods=['POST'])
@login_requerido
def filter_csv_data():
    """API para filtrar datos SMT desde MySQL (no archivos CSV)"""
    try:
        filters = request.get_json()
        folder = filters.get('folder', '')
        part_name = filters.get('partName', '')
        result = filters.get('result', '')
        date_from = filters.get('dateFrom', '')
        date_to = filters.get('dateTo', '')
        
        if not folder:
            return jsonify({'success': False, 'error': 'Folder parameter required'}), 400
        
        print(f"🔍 Filtrando datos MySQL para carpeta: {folder}")
        print(f"🔍 Filtros: partName={part_name}, result={result}, dateFrom={date_from}, dateTo={date_to}")
        
        # Conectar a MySQL directamente
        import mysql.connector
        
        mysql_config = {
            'host': os.getenv('MYSQL_HOST', 'up-de-fra1-mysql-1.db.run-on-seenode.com'),
            'port': int(os.getenv('MYSQL_PORT', 11550)),
            'user': os.getenv('MYSQL_USER', 'db_rrpq0erbdujn'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'db_rrpq0erbdujn'),
            'charset': 'utf8mb4'
        }
        
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor(dictionary=True)
        
        # Construir query dinámicamente con filtros
        where_conditions = ["source_file LIKE %s"]
        params = [f"%{folder}%"]
        
        if part_name:
            where_conditions.append("part_name LIKE %s")
            params.append(f"%{part_name}%")
        
        if result:
            where_conditions.append("result = %s")
            params.append(result.upper())
        
        if date_from:
            where_conditions.append("ScanDate >= %s")
            params.append(date_from.replace('-', ''))  # Convertir YYYY-MM-DD a YYYYMMDD
        
        if date_to:
            where_conditions.append("ScanDate <= %s")
            params.append(date_to.replace('-', ''))  # Convertir YYYY-MM-DD a YYYYMMDD
        
        where_clause = " AND ".join(where_conditions)
        
        query = f"""
            SELECT
            scan_date,
            scan_time,
            slot_no,
            result,
            previous_barcode,
            product_date,
            part_name,
            quantity,
            seq,
            vendor,
            lot_no,
            barcode,
            feeder_base,
            source_file,
            created_at
        FROM historial_cambio_material_smt
        WHERE {where_clause}
        ORDER BY ScanDate DESC, ScanTime DESC
            LIMIT 5000
        """
        
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        
        print(f"📊 Encontrados {len(resultados)} registros con filtros aplicados")
        
        # Convertir datos para JSON y mapear nombres para compatibilidad
        filtered_data = []
        for resultado in resultados:
            cleaned_record = {}
            for key, value in resultado.items():
                if hasattr(value, 'isoformat'):  # Es una fecha/datetime
                    cleaned_record[key] = value.isoformat()
                elif value is None:
                    cleaned_record[key] = None
                else:
                    cleaned_record[key] = str(value)
            
            # Mapear nombres para compatibilidad con frontend
            cleaned_record['ScanDate'] = cleaned_record.get('ScanDate', '')
            cleaned_record['ScanTime'] = cleaned_record.get('scan_time', '')
            cleaned_record['SlotNo'] = cleaned_record.get('slot_no', '')
            cleaned_record['Result'] = cleaned_record.get('result', '')
            cleaned_record['PartName'] = cleaned_record.get('part_name', '')
            cleaned_record['SourceFile'] = cleaned_record.get('source_file', '')
            cleaned_record['LOTNO'] = cleaned_record.get('lot_no', '')
            cleaned_record['Barcode'] = cleaned_record.get('barcode', '')
            cleaned_record['Quantity'] = cleaned_record.get('quantity', '')
            cleaned_record['Vendor'] = cleaned_record.get('vendor', '')
            cleaned_record['FeederBase'] = cleaned_record.get('feeder_base', '')
            cleaned_record['PreviousBarcode'] = cleaned_record.get('previous_barcode', '')
            
            filtered_data.append(cleaned_record)
        
        # Calcular estadísticas de los datos filtrados
        stats = {
            'total_records': len(filtered_data),
            'ok_count': len([d for d in filtered_data if str(d.get('Result', '')).upper() == 'OK']),
            'ng_count': len([d for d in filtered_data if str(d.get('Result', '')).upper() == 'NG'])
        }
        
        cursor.close()
        conn.close()
        
        print(f" Datos filtrados desde MySQL: {len(filtered_data)} registros")
        
        return jsonify({
            'success': True,
            'data': filtered_data,
            'stats': stats,
            'source': 'mysql',
            'message': f'Datos filtrados desde MySQL para {folder}'
        })
        
    except Exception as e:
        print(f"❌ Error filtrando datos desde MySQL: {e}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': f'Error al filtrar datos MySQL: {str(e)}'}), 500


def crear_patron_caracteres(texto_original, part_start, part_length, lot_start, lot_length):
    """
    Crea un patrón de caracteres donde:
    - Caracteres específicos se mantienen como están
    - Números se marcan como 'N'
    - Letras se marcan como 'A'
    - Las zonas de número de parte y lote se marcan como 'X' (cualquier carácter)
    """
    patron = list(texto_original)
    
    # Marcar la zona del número de parte como 'X' (cualquier carácter)
    for i in range(part_start, part_start + part_length):
        if i < len(patron):
            patron[i] = 'X'
    
    # Marcar la zona del lote como 'X' solo si existe lote
    if lot_start != -1 and lot_length > 0:
        for i in range(lot_start, lot_start + lot_length):
            if i < len(patron):
                patron[i] = 'X'
    
    # Para el resto de caracteres, determinar el tipo
    for i, char in enumerate(patron):
        if char != 'X':  # Si no es una zona variable
            if char.isdigit():
                patron[i] = 'N'  # Número específico
            elif char.isalpha():
                patron[i] = 'A'  # Letra específica
            # Los caracteres especiales y espacios se mantienen como están
    
    return ''.join(patron)


def cargar_configuracion_usuario(usuario):
    """Cargar configuración específica del usuario"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT configuracion FROM usuarios_sistema 
            WHERE username = %s
        """, (usuario,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result and result[0]:  # Usar índice en lugar de clave de diccionario
            import json
            return json.loads(result[0])
        else:
            return {}
            
    except Exception as e:
        print(f"Error cargando configuración del usuario {usuario}: {e}")
        return {}


def guardar_configuracion_usuario(usuario, config):
    """Guardar configuración específica del usuario"""
    try:
        import json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        config_json = json.dumps(config)
        
        cursor.execute("""
            UPDATE usuarios_sistema 
            SET configuracion = %s 
            WHERE username = %s
        """, (config_json, usuario))
        
        success = cursor.rowcount > 0
        conn.commit()
        cursor.close()
        conn.close()
        
        return success
        
    except Exception as e:
        print(f"Error guardando configuración del usuario {usuario}: {e}")
        return False

@app.route('/guardar_regla_trazabilidad', methods=['POST'])
def guardar_regla_trazabilidad():
    """Guardar nueva regla de trazabilidad en rules.json"""
    try:
        if 'usuario' not in session:
            return jsonify({'error': 'Usuario no autenticado'}), 401
        
        # Obtener los datos de la nueva regla
        nueva_regla = request.get_json()
        
        if not nueva_regla:
            return jsonify({'error': 'No se recibieron datos'}), 400
        
        # Validar campos requeridos
        campos_requeridos = ['proveedor', 'numero_parte', 'texto_original']
        for campo in campos_requeridos:
            if not nueva_regla.get(campo):
                return jsonify({'error': f'Campo requerido faltante: {campo}'}), 400
        
        # Ruta del archivo rules.json
        rules_file = os.path.join(os.path.dirname(__file__), 'database', 'rules.json')
        
        # Cargar reglas existentes
        reglas_existentes = {}
        if os.path.exists(rules_file):
            try:
                with open(rules_file, 'r', encoding='utf-8') as f:
                    reglas_existentes = json.load(f)
            except json.JSONDecodeError:
                reglas_existentes = {}
        
        # Generar clave única para la nueva regla
        proveedor = nueva_regla['proveedor'].upper()
        contador = 1
        clave_base = proveedor
        clave_final = clave_base
        
        # Si ya existe la clave, agregar número secuencial
        while clave_final in reglas_existentes:
            contador += 1
            clave_final = f"{clave_base}{contador}"
        
        # Convertir la nueva regla al formato esperado
        texto_original = nueva_regla['texto_original']
        numero_parte = nueva_regla['numero_parte']
        numero_lote = nueva_regla.get('numero_lote', '')
        
        # Calcular posiciones reales
        part_number_start = texto_original.find(numero_parte)
        part_number_length = len(numero_parte)
        
        if numero_lote and numero_lote.strip():
            lot_number_start = texto_original.find(numero_lote)
            lot_number_length = len(numero_lote)
        else:
            lot_number_start = -1
            lot_number_length = 0
        
        # Validar que se encontraron las posiciones
        if part_number_start == -1:
            return jsonify({'error': 'No se pudo encontrar el número de parte en el texto original'}), 400
        
        if numero_lote and numero_lote.strip() and lot_number_start == -1:
            return jsonify({'error': 'No se pudo encontrar el número de lote en el texto original'}), 400
        
        # Crear patrón de caracteres
        character_pattern = crear_patron_caracteres(texto_original, part_number_start, part_number_length, 
                                                   lot_number_start, lot_number_length)
        
        regla_formateada = {
            "character_pattern": character_pattern,
            "partNumberStart": part_number_start,
            "partNumberLength": part_number_length,
            "lotNumberStart": lot_number_start,
            "lotNumberLength": lot_number_length
        }
        
        # Agregar la nueva regla con la clave generada
        reglas_existentes[clave_final] = regla_formateada
        
        # Guardar de vuelta al archivo
        with open(rules_file, 'w', encoding='utf-8') as f:
            json.dump(reglas_existentes, f, indent=2, ensure_ascii=False)
        
        print(f" Nueva regla de trazabilidad guardada: {clave_final} - {nueva_regla['proveedor']} - {nueva_regla['numero_parte']}")
        
        return jsonify({
            'success': True,
            'message': 'Regla guardada exitosamente',
            'regla_clave': clave_final,
            'proveedor': nueva_regla['proveedor']
        })
        
    except Exception as e:
        print(f"❌ Error guardando regla de trazabilidad: {e}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Error interno del servidor: {str(e)}'}), 500

# ===================================================================
# 🚀 RUTAS ADICIONALES PARA CONTROL DE SALIDA OPTIMIZADO
# ===================================================================

@app.route('/control_salida/estado', methods=['GET'])
@login_requerido
def control_salida_estado():
    """
    🔍 Obtener estado general del módulo Control de Salida
    
    Retorna:
    - Estadísticas del día
    - Configuración del usuario
    - Estado del sistema
    """
    try:
        usuario = session.get('usuario', 'Usuario')
        hoy = time.strftime('%Y-%m-%d')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener estadísticas del día
        cursor.execute('''
            SELECT 
                COUNT(*) as total_salidas,
                COALESCE(SUM(cantidad_salida), 0) as total_cantidad
            FROM salidas_material 
            WHERE DATE(fecha_salida) = %s
        ''', (hoy,))
        
        stats = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'estado': {
                'usuario': usuario,
                'fecha': hoy,
                'estadisticas': {
                    'salidas_hoy': stats['total_salidas'] if stats else 0,
                    'cantidad_total_hoy': stats['total_cantidad'] if stats else 0
                },
                'configuracion': {
                    'auto_focus': True,
                    'scan_mode': 'optimized',
                    'version': '2.0'
                }
            }
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo estado Control de Salida: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/control_salida/configuracion', methods=['GET', 'POST'])
@login_requerido
def control_salida_configuracion():
    """
    ⚙️ Gestionar configuración del usuario para Control de Salida
    
    GET: Obtener configuración actual
    POST: Guardar nueva configuración
    """
    try:
        usuario = session.get('usuario', 'Usuario')
        
        if request.method == 'GET':
            # Obtener configuración del usuario
            config = cargar_configuracion_usuario(usuario)
            
            # Configuración por defecto para Control de Salida
            control_salida_config = config.get('control_salida', {
                'registro_automatico': True,
                'verificacion_requerida': True,
                'auto_focus': True,
                'mostrar_ayuda': True,
                'tiempo_mensaje': 2500
            })
            
            return jsonify({
                'success': True,
                'configuracion': control_salida_config
            })
            
        elif request.method == 'POST':
            # Guardar nueva configuración
            data = request.get_json()
            
            if not data:
                return jsonify({'success': False, 'error': 'No se recibieron datos'}), 400
            
            # Cargar configuración existente
            config = cargar_configuracion_usuario(usuario)
            config['control_salida'] = data
            
            # Guardar configuración actualizada
            success = guardar_configuracion_usuario(usuario, config)
            
            return jsonify({
                'success': success,
                'message': 'Configuración guardada exitosamente' if success else 'Error al guardar configuración'
            })
            
    except Exception as e:
        print(f"❌ Error en configuración Control de Salida: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/control_salida/validar_stock', methods=['POST'])
@login_requerido
def control_salida_validar_stock():
    """
    📊 Validar stock disponible antes de procesar salida
    
    Útil para validaciones rápidas sin procesar la salida
    """
    try:
        data = request.get_json()
        codigo_recibido = data.get('codigo_recibido')
        cantidad_requerida = float(data.get('cantidad_requerida', 1))
        
        if not codigo_recibido:
            return jsonify({'success': False, 'error': 'Código de material requerido'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar material por código
        cursor.execute('''
            SELECT
                codigo_material_recibido,
                numero_parte,
                especificacion,
                cantidad_actual,
                numero_lote_material
            FROM control_material_almacen 
            WHERE codigo_material_recibido = %s OR codigo_material = %s
            ORDER BY fecha_registro DESC
            LIMIT 1
        ''', (codigo_recibido, codigo_recibido))
        
        material = cursor.fetchone()
        conn.close()
        
        if not material:
            return jsonify({
                'success': False,
                'disponible': False,
                'error': 'Material no encontrado'
            })
        
        cantidad_actual = float(material['cantidad_actual'] or 0)
        stock_suficiente = cantidad_actual >= cantidad_requerida
        
        return jsonify({
            'success': True,
            'disponible': stock_suficiente,
            'material': {
                'codigo': material['codigo_material_recibido'],
                'numero_parte': material['numero_parte'],
                'especificacion': material['especificacion'],
                'stock_actual': cantidad_actual,
                'cantidad_requerida': cantidad_requerida,
                'diferencia': 0,  # diferencia inicial = 0 (campo vacío para entrada manual)
                'lote': material['numero_lote_material']
            }
        })
        
    except Exception as e:
        print(f"❌ Error validando stock: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/control_salida/reporte_diario', methods=['GET'])
@login_requerido
def control_salida_reporte_diario():
    """
    📈 Generar reporte diario de salidas de material
    
    Parámetros opcionales:
    - fecha: fecha específica (YYYY-MM-DD)
    - formato: 'json' o 'excel'
    """
    try:
        fecha = request.args.get('fecha', time.strftime('%Y-%m-%d'))
        formato = request.args.get('formato', 'json')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Consultar salidas del día
        cursor.execute('''
            SELECT 
                fecha_salida,
                codigo_material_recibido,
                numero_parte,
                cantidad_salida,
                modelo,
                numero_lote,
                proceso_salida,
                departamento
            FROM salidas_material 
            WHERE DATE(fecha_salida) = %s
            ORDER BY fecha_salida DESC
        ''', (fecha,))
        
        salidas = cursor.fetchall()
        
        # Estadísticas resumen
        cursor.execute('''
            SELECT 
                COUNT(*) as total_salidas,
                COALESCE(SUM(cantidad_salida), 0) as cantidad_total,
                COUNT(DISTINCT numero_parte) as partes_diferentes,
                COUNT(DISTINCT modelo) as modelos_diferentes
            FROM salidas_material 
            WHERE DATE(fecha_salida) = %s
        ''', (fecha,))
        
        estadisticas = cursor.fetchone()
        conn.close()
        
        if formato == 'json':
            return jsonify({
                'success': True,
                'fecha': fecha,
                'estadisticas': {
                    'total_salidas': estadisticas['total_salidas'],
                    'cantidad_total': estadisticas['cantidad_total'],
                    'partes_diferentes': estadisticas['partes_diferentes'],
                    'modelos_diferentes': estadisticas['modelos_diferentes']
                },
                'salidas': [dict(row) for row in salidas]
            })
        
        # TODO: Implementar exportación a Excel si se requiere
        return jsonify({'success': False, 'error': 'Formato no soportado aún'}), 400
    
    except Exception as e:
        print(f"❌ Error generando reporte diario: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/importar_excel_plan_produccion', methods=['POST'])
@login_requerido
def importar_excel_plan_produccion():
    """Importar plan de producción desde Excel"""
    conn = None
    cursor = None
    temp_path = None
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No se proporcionó archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400
        
        if not file or not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'error': 'Formato de archivo no válido. Use .xlsx o .xls'}), 400
        
        # Guardar el archivo temporalmente
        filename = secure_filename(file.filename)
        temp_path = os.path.join(os.path.dirname(__file__), 'temp_' + filename)
        file.save(temp_path)
        
        # Leer el archivo Excel
        try:
            # Intentar leer con encabezados primero
            df = pd.read_excel(temp_path, engine='openpyxl' if filename.endswith('.xlsx') else 'xlrd')
            
            # Si las primeras filas contienen datos directamente (sin encabezados claros)
            # y las columnas tienen nombres genéricos como 0, 1, 2, etc.
            if all(isinstance(col, int) for col in df.columns):
                # Leer sin encabezados y asignar nombres de columnas
                df = pd.read_excel(temp_path, header=None, engine='openpyxl' if filename.endswith('.xlsx') else 'xlrd')
                # Asignar nombres basados en la posición
                if len(df.columns) >= 3:
                    df.columns = ['Modelo', 'Numero_Parte', 'Cantidad'] + [f'Col_{i}' for i in range(3, len(df.columns))]
                elif len(df.columns) == 2:
                    df.columns = ['Modelo', 'Cantidad']
                else:
                    df.columns = ['Modelo']
        except Exception as e:
            try:
                # Intentar leer sin encabezados como respaldo
                df = pd.read_excel(temp_path, header=None)
                if len(df.columns) >= 3:
                    df.columns = ['Modelo', 'Numero_Parte', 'Cantidad'] + [f'Col_{i}' for i in range(3, len(df.columns))]
                elif len(df.columns) == 2:
                    df.columns = ['Modelo', 'Cantidad']
                else:
                    df.columns = ['Modelo']
            except Exception as e2:
                return jsonify({'success': False, 'error': f'Error al leer el archivo Excel: {str(e2)}'}), 500
        
        # Verificar que el DataFrame no esté vacío
        if df.empty:
            return jsonify({'success': False, 'error': 'El archivo Excel está vacío'}), 400
        
        # Obtener usuario de la sesión
        usuario_actual = session.get('usuario', 'USUARIO_EXCEL')
        
        # Obtener fecha de operación seleccionada por el usuario
        fecha_operacion_usuario = request.form.get('fecha_operacion', '').strip()
        if fecha_operacion_usuario:
            print(f"📅 Fecha de operación personalizada seleccionada: {fecha_operacion_usuario}")
        else:
            print("📅 Usando fechas del Excel o fecha actual como respaldo")
        
        # Función auxiliar para obtener nombre del modelo desde raw
        def obtener_nombre_modelo(codigo_modelo):
            """Obtener nombre (project) desde raw por part_no"""
            try:
                if not codigo_modelo:
                    return ''
                cursor.execute(
                    "SELECT project FROM raw WHERE TRIM(part_no)=TRIM(%s) ORDER BY id DESC LIMIT 1",
                    (codigo_modelo,)
                )
                row = cursor.fetchone()
                return (row.get('project') if row else '') or ''
            except Exception as e:
                print(f"Error obteniendo nombre modelo para {codigo_modelo}: {e}")
                return ''
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Asegurar que la tabla work_orders tenga la columna linea
        try:
            cursor.execute("SHOW COLUMNS FROM work_orders LIKE 'linea'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE work_orders ADD COLUMN linea VARCHAR(32)")
                print("✅ Columna 'linea' agregada a work_orders")
        except Exception as e:
            print(f"Error agregando columna linea: {e}")
        
        registros_insertados = 0
        registros_actualizados = 0
        errores = []
        
        # Mapeo de columnas (flexible para diferentes nombres)
        mapeo_columnas = {
            'linea': ['Linea', 'linea', 'Line', 'LINEA', 'Línea'],
            'modelo': ['Modelo', 'modelo', 'Model', 'MODELO'],
            'numero_parte': ['Numero de parte', 'Número de parte', 'numero_parte', 'Part Number', 'NUMERO_PARTE', 'Numero_Parte'],
            'cantidad': ['Cantidad', 'cantidad', 'Quantity', 'CANTIDAD'],
            'fecha_operacion': ['Fecha', 'fecha_operacion', 'Fecha de operación', 'Date', 'FECHA'],
            'codigo_po': ['PO', 'codigo_po', 'Código PO', 'Purchase Order', 'CODIGO_PO']
        }
        
        # Debug: Mostrar información del DataFrame
        print(f"Columnas en el DataFrame: {list(df.columns)}")
        print(f"Primeras 3 filas del DataFrame:")
        print(df.head(3))
        
        # Detectar columnas disponibles
        columnas_detectadas = {}
        for campo, posibles_nombres in mapeo_columnas.items():
            for nombre in posibles_nombres:
                if nombre in df.columns:
                    columnas_detectadas[campo] = nombre
                    break
        
        print(f"Columnas detectadas: {columnas_detectadas}")
        
        # Verificar que al menos tengamos modelo y cantidad
        if 'modelo' not in columnas_detectadas or 'cantidad' not in columnas_detectadas:
            # Información detallada para debugging
            error_msg = f"El archivo debe contener al menos las columnas: Modelo y Cantidad. "
            error_msg += f"Columnas encontradas: {list(df.columns)}. "
            error_msg += f"Mapeo detectado: {columnas_detectadas}"
            
            return jsonify({
                'success': False, 
                'error': error_msg
            }), 400
        
        # Procesar cada fila del DataFrame
        for index, row in df.iterrows():
            try:
                # Extraer datos de la fila
                modelo = str(row.get(columnas_detectadas['modelo'], '')).strip()
                cantidad = row.get(columnas_detectadas['cantidad'], 0)
                
                # Validar datos básicos
                if not modelo or modelo == 'nan':
                    errores.append(f"Fila {index + 2}: Modelo vacío")
                    continue
                
                try:
                    cantidad = int(float(cantidad)) if cantidad and str(cantidad) != 'nan' else 0
                except (ValueError, TypeError):
                    cantidad = 0
                
                if cantidad <= 0:
                    errores.append(f"Fila {index + 2}: Cantidad inválida ({cantidad})")
                    continue
                
                # Datos opcionales
                linea = str(row.get(columnas_detectadas.get('linea', ''), '')).strip()
                if linea == 'nan':
                    linea = ''
                
                numero_parte = str(row.get(columnas_detectadas.get('numero_parte', ''), '')).strip()
                if numero_parte == 'nan':
                    numero_parte = ''
                
                codigo_po = str(row.get(columnas_detectadas.get('codigo_po', ''), 'SIN-PO')).strip()
                if codigo_po == 'nan' or not codigo_po:
                    codigo_po = 'SIN-PO'
                
                # Fecha de operación - priorizar la fecha seleccionada por el usuario
                fecha_operacion_usuario = request.form.get('fecha_operacion', '').strip()
                
                if fecha_operacion_usuario:
                    # Usar la fecha seleccionada por el usuario
                    fecha_operacion = fecha_operacion_usuario
                else:
                    # Usar la fecha del Excel o fecha actual como respaldo
                    fecha_operacion = row.get(columnas_detectadas.get('fecha_operacion', ''), '')
                    if pd.isna(fecha_operacion) or fecha_operacion == 'nan':
                        fecha_operacion = datetime.now().strftime('%Y-%m-%d')
                    else:
                        try:
                            if isinstance(fecha_operacion, str):
                                # Intentar convertir string a fecha
                                from dateutil import parser
                                fecha_operacion = parser.parse(fecha_operacion).strftime('%Y-%m-%d')
                            else:
                                # Es datetime o similar
                                fecha_operacion = fecha_operacion.strftime('%Y-%m-%d')
                        except:
                            fecha_operacion = datetime.now().strftime('%Y-%m-%d')
                
                # Generar código WO único
                fecha_codigo = datetime.now().strftime('%y%m%d')
                
                # Buscar el último número de secuencia para hoy
                cursor.execute("""
                    SELECT codigo_wo FROM work_orders 
                    WHERE codigo_wo LIKE %s 
                    ORDER BY codigo_wo DESC LIMIT 1
                """, (f'WO-{fecha_codigo}-%',))
                
                ultimo_wo = cursor.fetchone()
                if ultimo_wo:
                    try:
                        ultimo_numero = int(ultimo_wo['codigo_wo'].split('-')[-1])
                        nuevo_numero = ultimo_numero + 1
                    except:
                        nuevo_numero = 1
                else:
                    nuevo_numero = 1
                
                codigo_wo = f"WO-{fecha_codigo}-{nuevo_numero:04d}"
                
                # Obtener nombre del modelo desde la tabla raw
                codigo_modelo = modelo
                nombre_modelo = obtener_nombre_modelo(codigo_modelo)
                
                # Insertar nueva WO
                cursor.execute("""
                    INSERT INTO work_orders 
                    (codigo_wo, codigo_po, modelo, codigo_modelo, nombre_modelo, linea, 
                     cantidad_planeada, fecha_operacion, usuario_creacion, modificador, estado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'CREADA')
                """, (
                    codigo_wo,
                    codigo_po,
                    modelo if modelo else numero_parte,  # Usar modelo o numero_parte como respaldo
                    codigo_modelo,
                    nombre_modelo,
                    linea,
                    cantidad,
                    fecha_operacion,
                    usuario_actual,
                    usuario_actual
                ))
                
                registros_insertados += 1
                
            except Exception as e:
                errores.append(f"Fila {index + 2}: {str(e)}")
                continue
        
        # Confirmar transacción
        conn.commit()
        
        # Preparar respuesta
        mensaje = f"Importación completada. {registros_insertados} WOs creadas."
        if fecha_operacion_usuario:
            mensaje += f" Fecha de operación aplicada: {fecha_operacion_usuario}."
        if errores:
            mensaje += f" {len(errores)} errores encontrados."
        
        return jsonify({
            'success': True, 
            'message': mensaje,
            'registros_procesados': registros_insertados,
            'errores': len(errores),
            'fecha_aplicada': fecha_operacion_usuario or 'Fechas del Excel/Actual',
            'detalles': {
                'insertados': registros_insertados,
                'errores': errores[:10] if errores else []  # Solo primeros 10 errores
            }
        })
        
    except Exception as e:
        print(f"Error general en importar_excel_plan_produccion: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500
    
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            print(f"Error en cleanup: {str(e)}")

# ===================================================================
# 🔧 RUTAS DE MANTENIMIENTO Y DEBUGGING PARA CONTROL DE SALIDA
# ===================================================================

@app.route('/control_salida/debug/test_connection', methods=['GET'])
@login_requerido
def control_salida_test_connection():
    """
    🧪 Probar conexión y funcionalidad básica del módulo
    """
    try:
        tests = []
        
        # Test 1: Conexión a base de datos
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            conn.close()
            tests.append({'test': 'Database Connection', 'status': 'OK'})
        except Exception as e:
            tests.append({'test': 'Database Connection', 'status': 'FAIL', 'error': str(e)})
        
        # Test 2: Verificar tablas necesarias
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar tabla salidas_material
            cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'salidas_material'")
            if cursor.fetchone():
                tests.append({'test': 'Table salidas_material', 'status': 'OK'})
            else:
                tests.append({'test': 'Table salidas_material', 'status': 'MISSING'})
            
            # Verificar tabla control_material_almacen
            cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'control_material_almacen'")
            if cursor.fetchone():
                tests.append({'test': 'Table control_material_almacen', 'status': 'OK'})
            else:
                tests.append({'test': 'Table control_material_almacen', 'status': 'MISSING'})
            
            conn.close()
        except Exception as e:
            tests.append({'test': 'Table Verification', 'status': 'FAIL', 'error': str(e)})
        
        # Test 3: Funciones de inventario
        try:
            from .db import actualizar_inventario_general_salida
            tests.append({'test': 'Inventory Functions', 'status': 'OK'})
        except Exception as e:
            tests.append({'test': 'Inventory Functions', 'status': 'FAIL', 'error': str(e)})
        
        return jsonify({
            'success': True,
            'tests': tests,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'overall_status': 'OK' if all(t['status'] == 'OK' for t in tests) else 'ISSUES'
        })
        
    except Exception as e:
        print(f"❌ Error en test de conexión: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Rutas de importación AJAX para todas las secciones de material
@app.route('/importar_excel_almacen', methods=['POST'])
def importar_excel_almacen():
    """Importación AJAX para Control de Material de Almacén"""
    conn = None
    cursor = None
    temp_path = None
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No se proporcionó archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400
        
        if not file or not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'error': 'Formato de archivo no válido. Use .xlsx o .xls'}), 400
        
        # Guardar el archivo temporalmente
        filename = secure_filename(file.filename)
        temp_path = os.path.join(os.path.dirname(__file__), 'temp_' + filename)
        file.save(temp_path)
        
        # Leer el archivo Excel
        try:
            df = pd.read_excel(temp_path, engine='openpyxl' if filename.endswith('.xlsx') else 'xlrd')
        except Exception as e:
            try:
                df = pd.read_excel(temp_path)
            except Exception as e2:
                return jsonify({'success': False, 'error': f'Error al leer el archivo Excel: {str(e2)}'}), 500
        
        # Verificar que el DataFrame no esté vacío
        if df.empty:
            return jsonify({'success': False, 'error': 'El archivo Excel está vacío'}), 400
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        registros_insertados = 0
        errores = []
        
        # Procesar cada fila del DataFrame
        for index, row in df.iterrows():
            try:
                # Insertar en tabla de control de almacén (ajustar según estructura de tu tabla)
                cursor.execute("""
                    INSERT OR REPLACE INTO control_almacen 
                    (codigo_material_recibido, codigo_material, numero_parte, numero_lote, 
                     propiedad_material, fecha_recibo, cantidad_actual, ubicacion)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    str(row.get('Codigo Material Recibido', '')),
                    str(row.get('Codigo Material', '')),
                    str(row.get('Numero Parte', '')),
                    str(row.get('Numero Lote', '')),
                    str(row.get('Propiedad Material', '')),
                    str(row.get('Fecha Recibo', '')),
                    str(row.get('Cantidad Recibida', 0)),
                    str(row.get('Ubicacion', ''))
                ))
                registros_insertados += 1
            except Exception as e:
                errores.append(f"Fila {index + 1}: {str(e)}")
        
        conn.commit()
        
        mensaje = f"Importación completada. {registros_insertados} registros insertados."
        if errores:
            mensaje += f" {len(errores)} errores encontrados."
        
        return jsonify({'success': True, 'message': mensaje})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error durante la importación: {str(e)}'}), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/produccion/info')
@login_requerido
def produccion_info():
    try:
        return render_template('CONTROL DE PRODUCCION/info_produccion.html')
    except Exception as e:
        return f'Error al cargar información de producción: {str(e)}', 500

# ===============================================
# RUTAS PARA CARGA DINÁMICA DE CONTENEDORES
# ===============================================

@app.route('/material/recibo_pago')
@login_requerido
def material_recibo_pago():
    """Cargar dinámicamente el recibo y pago del material"""
    try:
        return render_template('Control de material/Recibo y pago del material.html')
    except Exception as e:
        print(f"Error al cargar Recibo y pago del material: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/material/historial_material')
@login_requerido
def material_historial_material():
    """Cargar dinámicamente el historial de material"""
    try:
        return render_template('Control de material/Historial de material.html')
    except Exception as e:
        print(f"Error al cargar Historial de material: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/material/material_sustituto')
@login_requerido
def material_material_sustituto():
    """Cargar dinámicamente el material sustituto"""
    try:
        return render_template('Control de material/Material sustituto.html')
    except Exception as e:
        print(f"Error al cargar Material sustituto: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/material/consultar_peps')
@login_requerido
def material_consultar_peps():
    """Cargar dinámicamente consultar PEPS"""
    try:
        return render_template('Control de material/Consultar PEPS.html')
    except Exception as e:
        print(f"Error al cargar Consultar PEPS: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/material/longterm_inventory')
@login_requerido
def material_longterm_inventory():
    """Cargar dinámicamente el control de Long-Term Inventory"""
    try:
        return render_template('Control de material/Control de Long-Term Inventory.html')
    except Exception as e:
        print(f"Error al cargar Control de Long-Term Inventory: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/material/ajuste_numero')
@login_requerido
def material_ajuste_numero():
    """Cargar dinámicamente el ajuste de número de parte"""
    try:
        return render_template('Control de material/Ajuste de número de parte.html')
    except Exception as e:
        print(f"Error al cargar Ajuste de número de parte: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/importar_excel_salida', methods=['POST'])
def importar_excel_salida():
    """Importación AJAX para Control de Salida"""
    conn = None
    cursor = None
    temp_path = None
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No se proporcionó archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400
        
        if not file or not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'error': 'Formato de archivo no válido. Use .xlsx o .xls'}), 400
        
        # Guardar el archivo temporalmente
        filename = secure_filename(file.filename)
        temp_path = os.path.join(os.path.dirname(__file__), 'temp_' + filename)
        file.save(temp_path)
        
        # Leer el archivo Excel
        try:
            df = pd.read_excel(temp_path, engine='openpyxl' if filename.endswith('.xlsx') else 'xlrd')
        except Exception as e:
            try:
                df = pd.read_excel(temp_path)
            except Exception as e2:
                return jsonify({'success': False, 'error': f'Error al leer el archivo Excel: {str(e2)}'}), 500
        
        # Verificar que el DataFrame no esté vacío
        if df.empty:
            return jsonify({'success': False, 'error': 'El archivo Excel está vacío'}), 400
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        registros_insertados = 0
        errores = []
        
        # Procesar cada fila del DataFrame
        for index, row in df.iterrows():
            try:
                # Insertar en tabla de control de salida
                cursor.execute("""
                    INSERT OR REPLACE INTO control_salida 
                    (fecha_salida, proceso_salida, codigo_material_recibido, codigo_material, 
                     numero_parte, cantidad_salida, destino)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    str(row.get('Fecha Salida', '')),
                    str(row.get('Proceso Salida', '')),
                    str(row.get('Codigo Material Recibido', '')),
                    str(row.get('Codigo Material', '')),
                    str(row.get('Numero Parte', '')),
                    str(row.get('Cantidad Salida', 0)),
                    str(row.get('Destino', ''))
                ))
                registros_insertados += 1
            except Exception as e:
                errores.append(f"Fila {index + 1}: {str(e)}")
        
        conn.commit()
        
        mensaje = f"Importación completada. {registros_insertados} registros insertados."
        if errores:
            mensaje += f" {len(errores)} errores encontrados."
        
        return jsonify({'success': True, 'message': mensaje})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error durante la importación: {str(e)}'}), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/importar_excel_retorno', methods=['POST'])
def importar_excel_retorno():
    """Importación AJAX para Control de Material de Retorno"""
    conn = None
    cursor = None
    temp_path = None
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No se proporcionó archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400
        
        if not file or not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'error': 'Formato de archivo no válido. Use .xlsx o .xls'}), 400
        
        # Guardar el archivo temporalmente
        filename = secure_filename(file.filename)
        temp_path = os.path.join(os.path.dirname(__file__), 'temp_' + filename)
        file.save(temp_path)
        
        # Leer el archivo Excel
        try:
            df = pd.read_excel(temp_path, engine='openpyxl' if filename.endswith('.xlsx') else 'xlrd')
        except Exception as e:
            try:
                df = pd.read_excel(temp_path)
            except Exception as e2:
                return jsonify({'success': False, 'error': f'Error al leer el archivo Excel: {str(e2)}'}), 500
        
        # Verificar que el DataFrame no esté vacío
        if df.empty:
            return jsonify({'success': False, 'error': 'El archivo Excel está vacío'}), 400
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        registros_insertados = 0
        errores = []
        
        # Procesar cada fila del DataFrame
        for index, row in df.iterrows():
            try:
                # Insertar en tabla de control de retorno
                cursor.execute("""
                    INSERT OR REPLACE INTO control_retorno 
                    (codigo_material, numero_parte, cantidad_retorno, fecha_retorno, 
                     motivo_retorno, estado_material)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    str(row.get('Codigo Material', '')),
                    str(row.get('Numero Parte', '')),
                    str(row.get('Cantidad Retorno', 0)),
                    str(row.get('Fecha Retorno', '')),
                    str(row.get('Motivo Retorno', '')),
                    str(row.get('Estado Material', ''))
                ))
                registros_insertados += 1
            except Exception as e:
                errores.append(f"Fila {index + 1}: {str(e)}")
        
        conn.commit()
        
        mensaje = f"Importación completada. {registros_insertados} registros insertados."
        if errores:
            mensaje += f" {len(errores)} errores encontrados."
        
        return jsonify({'success': True, 'message': mensaje})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error durante la importación: {str(e)}'}), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/importar_excel_registro', methods=['POST'])
def importar_excel_registro():
    """Importación AJAX para Registro de Material Real"""
    conn = None
    cursor = None
    temp_path = None
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No se proporcionó archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400
        
        if not file or not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'error': 'Formato de archivo no válido. Use .xlsx o .xls'}), 400
        
        # Guardar el archivo temporalmente
        filename = secure_filename(file.filename)
        temp_path = os.path.join(os.path.dirname(__file__), 'temp_' + filename)
        file.save(temp_path)
        
        # Leer el archivo Excel
        try:
            df = pd.read_excel(temp_path, engine='openpyxl' if filename.endswith('.xlsx') else 'xlrd')
        except Exception as e:
            try:
                df = pd.read_excel(temp_path)
            except Exception as e2:
                return jsonify({'success': False, 'error': f'Error al leer el archivo Excel: {str(e2)}'}), 500
        
        # Verificar que el DataFrame no esté vacío
        if df.empty:
            return jsonify({'success': False, 'error': 'El archivo Excel está vacío'}), 400
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        registros_insertados = 0
        errores = []
        
        # Procesar cada fila del DataFrame
        for index, row in df.iterrows():
            try:
                # Insertar en tabla de registro de material real
                cursor.execute("""
                    INSERT OR REPLACE INTO registro_material_real 
                    (codigo_material, numero_parte, cantidad_real, fecha_registro, 
                     ubicacion_fisica, estado_inventario)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    str(row.get('Codigo Material', '')),
                    str(row.get('Numero Parte', '')),
                    str(row.get('Cantidad Real', 0)),
                    str(row.get('Fecha Registro', '')),
                    str(row.get('Ubicacion Fisica', '')),
                    str(row.get('Estado Inventario', ''))
                ))
                registros_insertados += 1
            except Exception as e:
                errores.append(f"Fila {index + 1}: {str(e)}")
        
        conn.commit()
        
        mensaje = f"Importación completada. {registros_insertados} registros insertados."
        if errores:
            mensaje += f" {len(errores)} errores encontrados."
        
        return jsonify({'success': True, 'message': mensaje})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error durante la importación: {str(e)}'}), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/importar_excel_estatus_inventario', methods=['POST'])
def importar_excel_estatus_inventario():
    """Importación AJAX para Estatus de Material - Inventario"""
    conn = None
    cursor = None
    temp_path = None
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No se proporcionó archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400
        
        if not file or not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'error': 'Formato de archivo no válido. Use .xlsx o .xls'}), 400
        
        # Guardar el archivo temporalmente
        filename = secure_filename(file.filename)
        temp_path = os.path.join(os.path.dirname(__file__), 'temp_' + filename)
        file.save(temp_path)
        
        # Leer el archivo Excel
        try:
            df = pd.read_excel(temp_path, engine='openpyxl' if filename.endswith('.xlsx') else 'xlrd')
        except Exception as e:
            try:
                df = pd.read_excel(temp_path)
            except Exception as e2:
                return jsonify({'success': False, 'error': f'Error al leer el archivo Excel: {str(e2)}'}), 500
        
        # Verificar que el DataFrame no esté vacío
        if df.empty:
            return jsonify({'success': False, 'error': 'El archivo Excel está vacío'}), 400
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        registros_insertados = 0
        errores = []
        
        # Procesar cada fila del DataFrame
        for index, row in df.iterrows():
            try:
                # Insertar en tabla de estatus inventario
                cursor.execute("""
                    INSERT OR REPLACE INTO estatus_inventario 
                    (codigo_material, numero_parte, cantidad_disponible, estatus_material, 
                     fecha_actualizacion, ubicacion)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    str(row.get('Codigo Material', '')),
                    str(row.get('Numero Parte', '')),
                    str(row.get('Cantidad Disponible', 0)),
                    str(row.get('Estatus Material', '')),
                    str(row.get('Fecha Actualizacion', '')),
                    str(row.get('Ubicacion', ''))
                ))
                registros_insertados += 1
            except Exception as e:
                errores.append(f"Fila {index + 1}: {str(e)}")
        
        conn.commit()
        
        mensaje = f"Importación completada. {registros_insertados} registros insertados."
        if errores:
            mensaje += f" {len(errores)} errores encontrados."
        
        return jsonify({'success': True, 'message': mensaje})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error durante la importación: {str(e)}'}), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/importar_excel_estatus_recibido', methods=['POST'])
def importar_excel_estatus_recibido():
    """Importación AJAX para Estatus de Material - Material Recibido"""
    conn = None
    cursor = None
    temp_path = None
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No se proporcionó archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400
        
        if not file or not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'error': 'Formato de archivo no válido. Use .xlsx o .xls'}), 400
        
        # Guardar el archivo temporalmente
        filename = secure_filename(file.filename)
        temp_path = os.path.join(os.path.dirname(__file__), 'temp_' + filename)
        file.save(temp_path)
        
        # Leer el archivo Excel
        try:
            df = pd.read_excel(temp_path, engine='openpyxl' if filename.endswith('.xlsx') else 'xlrd')
        except Exception as e:
            try:
                df = pd.read_excel(temp_path)
            except Exception as e2:
                return jsonify({'success': False, 'error': f'Error al leer el archivo Excel: {str(e2)}'}), 500
        
        # Verificar que el DataFrame no esté vacío
        if df.empty:
            return jsonify({'success': False, 'error': 'El archivo Excel está vacío'}), 400
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        registros_insertados = 0
        errores = []
        
        # Procesar cada fila del DataFrame
        for index, row in df.iterrows():
            try:
                # Insertar en tabla de material recibido
                cursor.execute("""
                    INSERT OR REPLACE INTO material_recibido 
                    (codigo_material_recibido, codigo_material, numero_parte, fecha_recibo, 
                     cantidad_actual, proveedor, estado_recepcion)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    str(row.get('Codigo Material Recibido', '')),
                    str(row.get('Codigo Material', '')),
                    str(row.get('Numero Parte', '')),
                    str(row.get('Fecha Recibo', '')),
                    str(row.get('Cantidad Recibida', 0)),
                    str(row.get('Proveedor', '')),
                    str(row.get('Estado Recepcion', ''))
                ))
                registros_insertados += 1
            except Exception as e:
                errores.append(f"Fila {index + 1}: {str(e)}")
        
        conn.commit()
        
        mensaje = f"Importación completada. {registros_insertados} registros insertados."
        if errores:
            mensaje += f" {len(errores)} errores encontrados."
        
        return jsonify({'success': True, 'message': mensaje})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error durante la importación: {str(e)}'}), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/importar_excel_historial', methods=['POST'])
def importar_excel_historial():
    """Importación AJAX para Historial de Inventario Real"""
    conn = None
    cursor = None
    temp_path = None
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No se proporcionó archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400
        
        if not file or not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'error': 'Formato de archivo no válido. Use .xlsx o .xls'}), 400
        
        # Guardar el archivo temporalmente
        filename = secure_filename(file.filename)
        temp_path = os.path.join(os.path.dirname(__file__), 'temp_' + filename)
        file.save(temp_path)
        
        # Leer el archivo Excel
        try:
            df = pd.read_excel(temp_path, engine='openpyxl' if filename.endswith('.xlsx') else 'xlrd')
        except Exception as e:
            try:
                df = pd.read_excel(temp_path)
            except Exception as e2:
                return jsonify({'success': False, 'error': f'Error al leer el archivo Excel: {str(e2)}'}), 500
        
        # Verificar que el DataFrame no esté vacío
        if df.empty:
            return jsonify({'success': False, 'error': 'El archivo Excel está vacío'}), 400
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        registros_insertados = 0
        errores = []
        
        # Procesar cada fila del DataFrame
        for index, row in df.iterrows():
            try:
                # Insertar en tabla de historial de inventario
                cursor.execute("""
                    INSERT OR REPLACE INTO historial_inventario 
                    (codigo_material, numero_parte, fecha_movimiento, tipo_movimiento, 
                     cantidad_anterior, cantidad_nueva, usuario, observaciones)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    str(row.get('Codigo Material', '')),
                    str(row.get('Numero Parte', '')),
                    str(row.get('Fecha Movimiento', '')),
                    str(row.get('Tipo Movimiento', '')),
                    str(row.get('Cantidad Anterior', 0)),
                    str(row.get('Cantidad Nueva', 0)),
                    str(row.get('Usuario', '')),
                    str(row.get('Observaciones', ''))
                ))
                registros_insertados += 1
            except Exception as e:
                errores.append(f"Fila {index + 1}: {str(e)}")
        
        conn.commit()
        
        mensaje = f"Importación completada. {registros_insertados} registros insertados."
        if errores:
            mensaje += f" {len(errores)} errores encontrados."
        
        return jsonify({'success': True, 'message': mensaje})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error durante la importación: {str(e)}'}), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

# ... (rest of the code remains unchanged)

@app.route('/api/wo/exportar', methods=['GET'])
@login_requerido
def exportar_wos_excel():
    """Exportar WOs a Excel"""
    try:
        import io
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from flask import send_file
        
        # Obtener parámetros de filtro
        fecha_desde = request.args.get('fecha_desde')
        fecha_hasta = request.args.get('fecha_hasta')
        
        # Obtener WOs con filtros
        from .po_wo_models import listar_wos
        wos = listar_wos(fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)
        
        # Crear workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Work Orders"
        
        # Definir encabezados que coincidan con la tabla HTML
        headers = [
            'Código WO', 'Estado', 'Fecha Operación', 'Línea', 'Código Modelo', 
            'Nombre Modelo', 'Cantidad Planeada', 'Código PO', 'Registrado',
            'Modificador', 'Fecha Modificación', 'Fecha Creación'
        ]
        
        # Estilos para encabezados
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="172A46", end_color="172A46", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin")
        )
        
        # Escribir encabezados
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = border
        
        # Escribir datos
        for row_num, wo in enumerate(wos, 2):
            # Datos que coincidan con las columnas de la tabla HTML
            data = [
                wo.get('codigo_wo', ''),                                    # Código WO
                wo.get('estado', 'CREADA'),                                 # Estado
                wo.get('fecha_operacion', ''),                              # Fecha Operación
                wo.get('linea', 'SMT-1'),                                   # Línea
                wo.get('codigo_modelo', '') or wo.get('modelo', ''),        # Código Modelo
                wo.get('nombre_modelo', ''),                                # Nombre Modelo
                wo.get('cantidad_planeada', 0),                             # Cantidad Planeada
                wo.get('codigo_po', 'SIN-PO'),                              # Código PO
                'Sí' if wo.get('registrado') else 'No',                    # Registrado
                wo.get('modificador', ''),                                  # Modificador
                wo.get('fecha_modificacion', ''),                           # Fecha Modificación
                wo.get('fecha_creacion', '')                                # Fecha Creación
            ]
            
            for col_num, value in enumerate(data, 1):
                cell = ws.cell(row=row_num, column=col_num, value=value)
                cell.border = border
                cell.alignment = Alignment(horizontal="center", vertical="center")
        
        # Ajustar ancho de columnas
        column_widths = {
            'A': 15,  # Código WO
            'B': 12,  # Estado
            'C': 15,  # Fecha Operación
            'D': 8,   # Línea
            'E': 15,  # Código Modelo
            'F': 20,  # Nombre Modelo
            'G': 12,  # Cantidad Planeada
            'H': 12,  # Código PO
            'I': 10,  # Registrado
            'J': 15,  # Modificador
            'K': 18,  # Fecha Modificación
            'L': 18   # Fecha Creación
        }
        
        for column, width in column_widths.items():
            ws.column_dimensions[column].width = width
        
        # Guardar en buffer
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        # Generar nombre de archivo
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'work_orders_{timestamp}.xlsx'
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        print(f"Error exportando WOs: {e}")
        return jsonify({
            'success': False,
            'error': f'Error exportando WOs: {str(e)}'
        }), 500

@app.route('/api/plan-smd/import', methods=['POST'])
@login_requerido
def api_plan_smd_import():
    """API para importar plan SMD desde CSV o JSON"""
    try:
        usuario = session.get('usuario', 'sistema')
        
        # Verificar si es archivo o JSON
        if 'file' in request.files:
            # Importar desde archivo CSV
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No se seleccionó archivo'}), 400
            
            if not file.filename.lower().endswith('.csv'):
                return jsonify({'error': 'Solo se permiten archivos CSV'}), 400
            
            # Leer CSV
            import csv
            import io
            
            content = file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            data = list(csv_reader)
            
        else:
            # Importar desde JSON
            data = request.get_json()
            if not data or not isinstance(data, list):
                return jsonify({'error': 'Se esperaba un arreglo JSON'}), 400
        
        # Validar y procesar datos
        inserted = 0
        updated = 0
        errors = []
        
        for i, row in enumerate(data):
            try:
                # Validar campos requeridos
                if not all(k in row for k in ['linea', 'lote', 'modelo']):
                    errors.append(f"Fila {i+1}: Faltan campos requeridos (linea, lote, modelo)")
                    continue
                
                # Normalizar datos
                linea = str(row.get('linea', '')).strip().upper()
                lote = str(row.get('lote', '')).strip()
                nparte = str(row.get('nparte', '')).strip()
                modelo = str(row.get('modelo', '')).strip().upper()
                tipo = str(row.get('tipo', '')).strip()
                turno = str(row.get('turno', '')).strip().upper()
                ct = str(row.get('ct', '')).strip()
                uph = str(row.get('uph', '')).strip()
                qty = float(row.get('qty', 0)) if row.get('qty') else 0
                fisico = float(row.get('fisico', 0)) if row.get('fisico') else 0
                comentarios = str(row.get('comentarios', '')).strip()
                usuario_creacion = str(row.get('usuario_creacion', usuario)).strip()
                
                # Validaciones
                if qty < 0:
                    errors.append(f"Fila {i+1}: qty debe ser >= 0")
                    continue
                
                if fisico < 0:
                    errors.append(f"Fila {i+1}: fisico debe ser >= 0")
                    continue
                
                # Calcular falta y pct
                falta = max(qty - fisico, 0)
                pct = round((qty - falta) * 100 / qty) if qty > 0 else 0
                
                # Verificar si ya existe (upsert por lote, modelo)
                check_query = """
                SELECT id FROM plan_smd 
                WHERE lote = %s AND modelo = %s
                """
                existing = execute_query(check_query, (lote, modelo), fetch='one')
                
                if existing:
                    # Actualizar registro existente
                    update_query = """
                    UPDATE plan_smd SET 
                        linea = %s, nparte = %s, tipo = %s, turno = %s, ct = %s, uph = %s,
                        qty = %s, fisico = %s, falta = %s, pct = %s, comentarios = %s
                    WHERE id = %s
                    """
                    execute_query(update_query, (
                        linea, nparte, tipo, turno, ct, uph, qty, fisico, falta, pct, comentarios, existing['id']
                    ))
                    updated += 1
                else:
                    # Insertar nuevo registro
                    insert_query = """
                    INSERT INTO plan_smd (linea, lote, nparte, modelo, tipo, turno, ct, uph, 
                                         qty, fisico, falta, pct, comentarios, usuario_creacion)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    execute_query(insert_query, (
                        linea, lote, nparte, modelo, tipo, turno, ct, uph, qty, fisico, falta, pct, comentarios, usuario_creacion
                    ))
                    inserted += 1
                    
            except Exception as e:
                errors.append(f"Fila {i+1}: {str(e)}")
                continue
        
        return jsonify({
            'success': True,
            'inserted': inserted,
            'updated': updated,
            'errors': errors,
            'message': f'Importación completada: {inserted} insertados, {updated} actualizados'
        })
        
    except Exception as e:
        print(f"❌ Error importando plan SMD: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventario', methods=['GET'])
@login_requerido
def api_inventario():
    """API para consultar inventario por modelo y/o nparte"""
    try:
        modelo = request.args.get('modelo', '').strip()
        nparte = request.args.get('nparte', '').strip()
        
        if not modelo:
            return jsonify({'error': 'Parámetro modelo es requerido'}), 400
        
        if nparte:
            # Consultar inventario específico por modelo y nparte
            query = """
            SELECT modelo, nparte, stock_total, ubicaciones, ultima_entrada, ultima_salida, updated_at
            FROM inv_resumen_modelo 
            WHERE modelo = %s AND nparte = %s
            """
            result = execute_query(query, (modelo, nparte), fetch='one')
            
            if result:
                return jsonify({
                    'modelo': result['modelo'],
                    'nparte': result['nparte'],
                    'stock_total': result['stock_total'] or 0
                })
            else:
                return jsonify({
                    'modelo': modelo,
                    'nparte': nparte,
                    'stock_total': 0
                })
        else:
            # Consultar inventario total del modelo
            query = """
            SELECT modelo, SUM(stock_total) as stock_total
            FROM inv_resumen_modelo 
            WHERE modelo = %s
            GROUP BY modelo
            """
            result = execute_query(query, (modelo,), fetch='one')
            
            if result:
                return jsonify({
                    'modelo': result['modelo'],
                    'stock_total': result['stock_total'] or 0
                })
            else:
                return jsonify({
                    'modelo': modelo,
                    'stock_total': 0
                })
        
    except Exception as e:
        print(f"❌ Error consultando inventario: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/plan-micom/generar', methods=['POST'])
@login_requerido
def api_plan_micom_generar():
    """API para generar plan MICOM desde selección de modelos"""
    try:
        data = request.get_json()
        if not data or not isinstance(data, list):
            return jsonify({'error': 'Se esperaba un arreglo de modelos'}), 400
        
        usuario = session.get('usuario', 'sistema')
        modelos_procesados = 0
        errores = []
        
        for modelo_data in data:
            try:
                # Validar campos requeridos
                required_fields = ['modelo', 'ici1_nparte', 'checksum', 'faltante_total', 'fisico', 'dif']
                if not all(field in modelo_data for field in required_fields):
                    errores.append(f"Modelo {modelo_data.get('modelo', 'N/A')}: Faltan campos requeridos")
                    continue
                
                modelo = str(modelo_data['modelo']).strip()
                ici1_nparte = str(modelo_data['ici1_nparte']).strip()
                checksum = str(modelo_data['checksum']).strip()
                faltante_total = float(modelo_data['faltante_total'])
                fisico = float(modelo_data['fisico'])
                dif = float(modelo_data['dif'])
                comentarios = str(modelo_data.get('comentarios', 'MICOM auto-plan')).strip()
                
                # Validaciones
                if faltante_total < 0 or fisico < 0 or dif < 0:
                    errores.append(f"Modelo {modelo}: Valores negativos no permitidos")
                    continue
                
                # Aquí puedes implementar la lógica para guardar en plan_smd si es necesario
                # Por ahora solo validamos y contamos
                modelos_procesados += 1
                
            except Exception as e:
                errores.append(f"Modelo {modelo_data.get('modelo', 'N/A')}: {str(e)}")
                continue
        
        return jsonify({
            'success': True,
            'modelos_procesados': modelos_procesados,
            'errores': errores,
            'message': f'Plan MICOM generado: {modelos_procesados} modelos procesados'
        })
        
    except Exception as e:
        print(f"❌ Error generando plan MICOM: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# RUTAS PARA CONTROL DE CALIDAD
# ============================================================================

@app.route('/control-resultado-reparacion-ajax')
@login_requerido
def control_resultado_reparacion_ajax():
    """Template para Control de resultado de reparación"""
    return render_template('Control de calidad/control_resultado_reparacion_ajax.html')

@app.route('/control-item-reparado-ajax')
@login_requerido
def control_item_reparado_ajax():
    """Template para Control de item reparado"""
    return render_template('Control de calidad/control_item_reparado_ajax.html')

@app.route('/historial-cambio-material-maquina-ajax')
@login_requerido
def historial_cambio_material_maquina_ajax():
    """Template para Historial de cambio de material por máquina"""
    return render_template('Control de calidad/historial_cambio_material_maquina_ajax.html')

@app.route('/api/historial-cambio-material-maquina', methods=['GET'])
@login_requerido
def api_historial_cambio_material_maquina():
    """API para obtener historial de cambio de material por máquina"""
    try:
        # Obtener parámetros de filtrado
        equipment = request.args.get('equipment', '')
        slot_no = request.args.get('slot_no', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        part_name = request.args.get('part_name', '')
        
        print(f"🔍 API Historial cambio material - Filtros:")
        print(f"  Equipment: {equipment}")
        print(f"  Slot No: {slot_no}")
        print(f"  Date From: {date_from}")
        print(f"  Date To: {date_to}")
        print(f"  Part Name: {part_name}")
        
        from .db_mysql import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Consulta simple y segura
        query = """
            SELECT
                linea,
                maquina, 
                ScanDate,
                ScanTime,
                SlotNo,
                Result,
                PreviousBarcode,
                Productdate,
                PartName,
                Quantity,
                SEQ,
                Vendor,
                LOTNO,
                Barcode,
                FeederBase,
                archivo
            FROM historial_cambio_material_smt
            WHERE ScanDate >= %s
            ORDER BY ScanDate DESC, ScanTime DESC
            LIMIT 1000
        """
        
        # Usar fecha por defecto si no se proporciona
        default_date = '20250801'
        cursor.execute(query, [default_date])
        resultados = cursor.fetchall()
        
        print(f"📊 Encontrados {len(resultados)} registros en historial cambio material")
        
        # Formatear datos para la tabla de manera más segura
        formatted_data = []
        for i, row in enumerate(resultados):
            try:
                # Acceso seguro a índices
                linea = row[0] if len(row) > 0 else ''
                maquina = row[1] if len(row) > 1 else ''
                scan_date = row[2] if len(row) > 2 else ''
                scan_time = row[3] if len(row) > 3 else ''
                slot_no = row[4] if len(row) > 4 else ''
                result = row[5] if len(row) > 5 else ''
                previous_barcode = row[6] if len(row) > 6 else ''
                product_date = row[7] if len(row) > 7 else ''
                part_name = row[8] if len(row) > 8 else ''
                quantity = row[9] if len(row) > 9 else 0
                seq = row[10] if len(row) > 10 else ''
                vendor = row[11] if len(row) > 11 else ''
                lot_no = row[12] if len(row) > 12 else ''
                barcode = row[13] if len(row) > 13 else ''
                feeder_base = row[14] if len(row) > 14 else ''
                archivo = row[15] if len(row) > 15 else ''
                
                # Formatear fecha
                formatted_date = scan_date
                if scan_date and len(str(scan_date)) == 8:
                    date_str = str(scan_date)
                    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                
                formatted_row = {
                    'equipment': linea or '',
                    'slot_no': str(slot_no) if slot_no else '',
                    'regist_date': formatted_date or '',
                    'warehousing': vendor or '',
                    'regist_quantity': quantity or 0,
                    'current_quantity': quantity or 0,
                    'part_name': part_name or '',
                    'machine': maquina or '',
                    'result': result or '',
                    'scan_time': scan_time or '',
                    'barcode': barcode or '',
                    'lot_no': lot_no or ''
                }
                formatted_data.append(formatted_row)
                
            except Exception as row_error:
                print(f"❌ Error procesando fila {i}: {row_error}")
                continue
        
        cursor.close()
        conn.close()
        
        print(f"? Enviando {len(formatted_data)} registros al frontend")
        
        return jsonify({
            'success': True,
            'data': formatted_data,
            'total': len(formatted_data),
            'message': f'Se encontraron {len(formatted_data)} registros'
        })
        
    except Exception as e:
        print(f"❌ Error en API historial cambio material: {e}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==========================
# Historial SMT (ultimo por linea/maquina/slot)
# ==========================
@app.route('/api/historial_smt_latest', methods=['GET'])
@login_requerido
def api_historial_smt_latest():
    """Devuelve el ultimo escaneo por (linea, maquina, SlotNo) desde la tabla
    historial_cambio_material_smt. Pensado para el panel de Control de Operacion SMT
    que requiere el ultimo material escaneado para hacer match con el BOM.

    Parametros:
      - linea: opcional. Ej: 'SMT B'. Si se omite, devuelve para todas las lineas.
    """
    try:
        linea = request.args.get('linea', '').strip()

        from .db_mysql import get_connection
        conn = get_connection()
        cursor = conn.cursor()

        where_sub = ""
        params = []
        if linea:
            where_sub = "WHERE linea = %s"
            params.append(linea)

        # Seleccionar el ultimo registro por grupo usando fecha_subida
        query = f"""
            SELECT h.id, h.linea, h.maquina, h.archivo, h.ScanDate, h.ScanTime,
                   h.SlotNo, h.Result, h.PreviousBarcode, h.Productdate,
                   h.PartName, h.Quantity, h.SEQ, h.Vendor, h.LOTNO,
                   h.Barcode, h.FeederBase, h.fecha_subida,
                   CASE WHEN UPPER(h.FeederBase) LIKE '%%F%%' THEN 'FRONT'
                        WHEN UPPER(h.FeederBase) LIKE '%%R%%' THEN 'REAR'
                        ELSE 'UNKNOWN' END AS side_norm
            FROM historial_cambio_material_smt h
            INNER JOIN (
                SELECT linea, maquina, SlotNo,
                       CASE WHEN UPPER(FeederBase) LIKE '%%F%%' THEN 'FRONT'
                            WHEN UPPER(FeederBase) LIKE '%%R%%' THEN 'REAR'
                            ELSE 'UNKNOWN' END AS side_norm,
                       MAX(fecha_subida) AS max_fecha
                FROM historial_cambio_material_smt
                {where_sub}
                GROUP BY linea, maquina, SlotNo, side_norm
            ) m
            ON h.linea = m.linea AND h.maquina = m.maquina
               AND h.SlotNo = m.SlotNo AND h.fecha_subida = m.max_fecha
               AND (
                    (CASE WHEN UPPER(h.FeederBase) LIKE '%%F%%' THEN 'FRONT'
                          WHEN UPPER(h.FeederBase) LIKE '%%R%%' THEN 'REAR'
                          ELSE 'UNKNOWN' END) = m.side_norm
               )
            {('WHERE h.linea = %s' if linea else '')}
            ORDER BY h.linea, h.maquina, h.SlotNo, side_norm
        """

        if linea:
            # Parametros para subconsulta y para el filtro externo
            cursor.execute(query, params + params)
        else:
            cursor.execute(query)

        rows = cursor.fetchall()

        data = []
        for r in rows:
            # Indices alineados al SELECT de arriba
            linea_v = r[1] if len(r) > 1 else ''
            maquina_v = r[2] if len(r) > 2 else ''
            scan_date = r[4] if len(r) > 4 else ''
            scan_time = r[5] if len(r) > 5 else ''
            slot_no = r[6] if len(r) > 6 else ''
            part_name = r[10] if len(r) > 10 else ''
            quantity = r[11] if len(r) > 11 else 0
            vendor = r[13] if len(r) > 13 else ''
            feeder_base = r[16] if len(r) > 16 else ''

            # Normalizaciones amigables para el frontend existente
            formatted = {
                'linea': linea_v,
                'maquina': maquina_v,              # usado para extraer mounter (mN)
                'Equipment': maquina_v,            # alias por compatibilidad
                'SlotNo': slot_no,
                'FeederBase': feeder_base,
                'RegistDate': scan_date,           # el frontend ya acepta varios nombres
                'fecha_formateada': scan_date,
                'PartName': part_name,             # se usa para matching contra BOM Material Code
                'Quantity': quantity,
                'Vendor': vendor,
                'ScanDate': scan_date,
                'ScanTime': scan_time
            }
            data.append(formatted)

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'data': data,
            'total': len(data)
        })
    except Exception as e:
        print(f"Error en api_historial_smt_latest: {e}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

# Variante robusta con lado FRONT/REAR agrupado explicitamente
@app.route('/api/historial_smt_latest_v2', methods=['GET'])
@login_requerido
def api_historial_smt_latest_v2():
    try:
        linea_input = request.args.get('linea', '').strip()
        # Convertir nombre de línea a formato de BD
        linea = convertir_linea_smt(linea_input)

        from .db_mysql import get_connection
        conn = get_connection()
        cursor = conn.cursor()

        where_sub = ""
        params = []
        if linea:
            where_sub = "WHERE linea = %s"
            params.append(linea)

        query = f"""
            SELECT h.id, h.linea, h.maquina, h.archivo, h.ScanDate, h.ScanTime,
                   h.SlotNo, h.Result, h.PreviousBarcode, h.Productdate,
                   h.PartName, h.Quantity, h.SEQ, h.Vendor, h.LOTNO,
                   h.Barcode, h.FeederBase, h.fecha_subida,
                   CASE WHEN UPPER(h.FeederBase) LIKE '%%F%%' THEN 'FRONT'
                        WHEN UPPER(h.FeederBase) LIKE '%%R%%' THEN 'REAR'
                        ELSE 'UNKNOWN' END AS side_norm
            FROM historial_cambio_material_smt h
            INNER JOIN (
                SELECT linea, maquina, SlotNo,
                       (CASE WHEN UPPER(FeederBase) LIKE '%%F%%' THEN 'FRONT'
                             WHEN UPPER(FeederBase) LIKE '%%R%%' THEN 'REAR'
                             ELSE 'UNKNOWN' END) AS side_norm,
                       MAX(fecha_subida) AS max_fecha
                FROM historial_cambio_material_smt
                {where_sub}
                GROUP BY linea, maquina, SlotNo,
                         (CASE WHEN UPPER(FeederBase) LIKE '%%F%%' THEN 'FRONT'
                               WHEN UPPER(FeederBase) LIKE '%%R%%' THEN 'REAR'
                               ELSE 'UNKNOWN' END)
            ) m
              ON h.linea = m.linea AND h.maquina = m.maquina
             AND h.SlotNo = m.SlotNo AND h.fecha_subida = m.max_fecha
             AND (
                 (CASE WHEN UPPER(h.FeederBase) LIKE '%%F%%' THEN 'FRONT'
                       WHEN UPPER(h.FeederBase) LIKE '%%R%%' THEN 'REAR'
                       ELSE 'UNKNOWN' END) = m.side_norm
             )
            {('WHERE h.linea = %s' if linea else '')}
            ORDER BY h.linea, h.maquina, h.SlotNo, m.side_norm
        """

        if linea:
            cursor.execute(query, params + params)
        else:
            cursor.execute(query)

        rows = cursor.fetchall()
        data = []
        for r in rows:
            linea_v = r[1] if len(r) > 1 else ''
            maquina_v = r[2] if len(r) > 2 else ''
            scan_date = r[4] if len(r) > 4 else ''
            scan_time = r[5] if len(r) > 5 else ''
            slot_no = r[6] if len(r) > 6 else ''
            part_name = r[10] if len(r) > 10 else ''
            quantity = r[11] if len(r) > 11 else 0
            vendor = r[13] if len(r) > 13 else ''
            feeder_base = r[16] if len(r) > 16 else ''

            formatted = {
                'linea': linea_v,
                'maquina': maquina_v,
                'Equipment': maquina_v,
                'SlotNo': slot_no,
                'FeederBase': feeder_base,
                'RegistDate': scan_date,
                'fecha_formateada': scan_date,
                'PartName': part_name,
                'Quantity': quantity,
                'Vendor': vendor,
                'ScanDate': scan_date,
                'ScanTime': scan_time
            }
            data.append(formatted)

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'data': data, 'total': len(data)})
    except Exception as e:
        print('Error en api_historial_smt_latest_v2:', e)
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

# ==========================
# Metal Mask info lookup
# ==========================
@app.route('/api/masks/info', methods=['GET'])
@login_requerido
def api_masks_info():
    try:
        code = request.args.get('code', '').strip()
        if not code:
            return jsonify({'success': False, 'error': 'code requerido'}), 400

        from .db_mysql import get_connection
        conn = get_connection()
        cursor = conn.cursor()

        q = """
            SELECT management_no, storage_box, pcb_code, side, production_date,
                   used_count, max_count, allowance, model_name, tension_min,
                   tension_max, thickness, supplier, registration_date, disuse
            FROM masks
            WHERE management_no = %s
            LIMIT 1
        """
        cursor.execute(q, [code])
        row = cursor.fetchone()
        cursor.close(); conn.close()

        if not row:
            return jsonify({'success': False, 'found': False, 'message': 'No encontrado'})

        fields = ['management_no','storage_box','pcb_code','side','production_date',
                  'used_count','max_count','allowance','model_name','tension_min',
                  'tension_max','thickness','supplier','registration_date','disuse']
        data = { fields[i]: (row[i] if i < len(row) else None) for i in range(len(fields)) }

        def to_int(v):
            try:
                return int(v)
            except Exception:
                try:
                    return int(float(v))
                except Exception:
                    return 0

        data['used_count'] = to_int(data.get('used_count'))
        data['max_count'] = to_int(data.get('max_count'))
        data['allowance'] = to_int(data.get('allowance'))

        return jsonify({'success': True, 'found': True, 'data': data})
    except Exception as e:
        print('Error en api_masks_info:', e)
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/historial-uso-pegamento-soldadura-ajax')
@login_requerido
def historial_uso_pegamento_soldadura_ajax():
    """Template para Historial de uso de pegamento de soldadura"""
    return render_template('Control de calidad/historial_uso_pegamento_soldadura_ajax.html')

# ==========================
# API para historial de Metal Mask
# ==========================
@app.route('/api/metal-mask/history', methods=['POST'])
@login_requerido
def api_save_metal_mask_history():
    """Guardar historial de uso de Metal Mask"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        required_fields = ['mask_code', 'model_code', 'linea', 'quantity_used']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} es requerido'}), 400
        
        from .db_mysql import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # Crear tabla si no existe
        create_table_query = """
            CREATE TABLE IF NOT EXISTS metal_mask_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                mask_code VARCHAR(50) NOT NULL,
                model_code VARCHAR(50) NOT NULL,
                linea VARCHAR(20) NOT NULL,
                quantity_used INT NOT NULL DEFAULT 0,
                scan_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                usuario VARCHAR(50),
                plan_id INT,
                run_id INT,
                available_uses INT DEFAULT 0,
                total_uses INT DEFAULT 0,
                status ENUM('OK', 'NG', 'WARNING') DEFAULT 'OK',
                notes TEXT,
                INDEX idx_mask_code (mask_code),
                INDEX idx_model_code (model_code),
                INDEX idx_linea (linea),
                INDEX idx_scan_date (scan_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        cursor.execute(create_table_query)
        conn.commit()
        
        # Insertar registro de historial
        insert_query = """
            INSERT INTO metal_mask_history 
            (mask_code, model_code, linea, quantity_used, usuario, plan_id, run_id, 
             available_uses, total_uses, status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        usuario = session.get('usuario_logueado', 'Sistema')
        plan_id = data.get('plan_id')
        run_id = data.get('run_id')
        available_uses = data.get('available_uses', 0)
        total_uses = data.get('total_uses', 0)
        status = data.get('status', 'OK')
        notes = data.get('notes', '')
        
        cursor.execute(insert_query, [
            data['mask_code'],
            data['model_code'],
            data['linea'],
            data['quantity_used'],
            usuario,
            plan_id,
            run_id,
            available_uses,
            total_uses,
            status,
            notes
        ])
        
        history_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'history_id': history_id,
            'message': 'Historial de Metal Mask guardado correctamente'
        })
        
    except Exception as e:
        print('Error en api_save_metal_mask_history:', e)
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/metal-mask/history', methods=['GET'])
@login_requerido
def api_get_metal_mask_history():
    """Obtener historial de uso de Metal Mask"""
    try:
        # Parámetros de filtro
        mask_code = request.args.get('mask_code', '').strip()
        model_code = request.args.get('model_code', '').strip()
        linea = request.args.get('linea', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        limit = int(request.args.get('limit', 100))
        
        from .db_mysql import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # Construir consulta con filtros
        where_conditions = []
        params = []
        
        if mask_code:
            where_conditions.append('mask_code = %s')
            params.append(mask_code)
        
        if model_code:
            where_conditions.append('model_code = %s')
            params.append(model_code)
        
        if linea:
            where_conditions.append('linea = %s')
            params.append(linea)
        
        if date_from:
            where_conditions.append('scan_date >= %s')
            params.append(date_from)
        
        if date_to:
            where_conditions.append('scan_date <= %s')
            params.append(date_to + ' 23:59:59')
        
        where_clause = 'WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
        
        query = f"""
            SELECT id, mask_code, model_code, linea, quantity_used,
                   DATE_FORMAT(scan_date, '%%Y-%%m-%%d %%H:%%i:%%s') as scan_date,
                   usuario, plan_id, run_id, available_uses, total_uses,
                   status, notes
            FROM metal_mask_history
            {where_clause}
            ORDER BY scan_date DESC
            LIMIT %s
        """
        
        params.append(limit)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convertir a lista de diccionarios
        columns = ['id', 'mask_code', 'model_code', 'linea', 'quantity_used',
                  'scan_date', 'usuario', 'plan_id', 'run_id', 'available_uses',
                  'total_uses', 'status', 'notes']
        
        data = [dict(zip(columns, row)) for row in rows]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data)
        })
        
    except Exception as e:
        print('❌ Error en api_get_metal_mask_history:', e)
        print('❌ Traceback completo:')
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/metal-mask/update-used-count', methods=['POST'])
@login_requerido
def api_update_metal_mask_used_count():
    """Actualizar used_count de Metal Mask al finalizar plan"""
    try:
        data = request.get_json()
        plan_id = data.get('plan_id')
        cantidad_producida = int(data.get('cantidad_producida', 0))
        
        if not plan_id or cantidad_producida <= 0:
            return jsonify({'success': False, 'error': 'plan_id y cantidad_producida son requeridos'})
        
        from .db_mysql import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Obtener información del plan para saber el modelo y línea
        cursor.execute("""
            SELECT modelo, linea, nparte 
            FROM plan_smd 
            WHERE id = %s
        """, (plan_id,))
        plan_info = cursor.fetchone()
        
        if not plan_info:
            return jsonify({'success': False, 'error': 'Plan no encontrado'})
        
        modelo, linea, nparte = plan_info
        
        # 2. Buscar Metal Masks que se usaron para este modelo/línea
        # Prioridad 1: Buscar por plan_id específico
        cursor.execute("""
            SELECT DISTINCT mask_code, COUNT(*) as usage_count
            FROM metal_mask_history 
            WHERE plan_id = %s
            GROUP BY mask_code
            ORDER BY usage_count DESC, scan_date DESC
        """, (plan_id,))
        
        mask_codes = [row[0] for row in cursor.fetchall()]
        
        # Prioridad 2: Si no hay historial del plan, buscar por modelo/línea reciente
        if not mask_codes:
            cursor.execute("""
                SELECT DISTINCT mask_code, COUNT(*) as usage_count
                FROM metal_mask_history 
                WHERE model_code = %s AND linea = %s 
                AND scan_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY mask_code
                ORDER BY usage_count DESC, scan_date DESC
                LIMIT 3
            """, (modelo, linea))
            mask_codes = [row[0] for row in cursor.fetchall()]
            
        # Prioridad 3: Buscar cualquier mask para el modelo (último recurso)
        if not mask_codes:
            cursor.execute("""
                SELECT DISTINCT mask_code
                FROM metal_mask_history 
                WHERE model_code = %s 
                ORDER BY scan_date DESC
                LIMIT 1
            """, (modelo,))
            mask_codes = [row[0] for row in cursor.fetchall()]
        
        updated_count = 0
        
        # 3. Actualizar used_count en la tabla masks para cada mask_code encontrada
        for mask_code in mask_codes:
            cursor.execute("""
                UPDATE masks 
                SET used_count = used_count + %s 
                WHERE management_no = %s
            """, (cantidad_producida, mask_code))
            
            if cursor.rowcount > 0:
                updated_count += cursor.rowcount
                print(f"✅ Metal Mask {mask_code} - used_count incrementado en {cantidad_producida}")
        
        # 4. Registrar el update en el historial para cada mask actualizada
        for mask_code in mask_codes:
            # Obtener información actualizada de la mask
            cursor.execute("""
                SELECT used_count, max_count, allowance 
                FROM masks 
                WHERE management_no = %s
            """, (mask_code,))
            
            mask_info = cursor.fetchone()
            if mask_info:
                used_count, max_count, allowance = mask_info
                available_uses = max(0, (max_count + allowance) - used_count)
                
                cursor.execute("""
                    INSERT INTO metal_mask_history 
                    (mask_code, model_code, linea, quantity_used, plan_id, 
                     available_uses, total_uses, status, notes, usuario, scan_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    mask_code, modelo, linea, cantidad_producida, plan_id,
                    available_uses, used_count, 'END_PLAN',
                    f'Finalización de plan {plan_id} - Producido: {cantidad_producida}',
                    session.get('usuario', 'sistema')
                ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'updated_masks': updated_count,
            'cantidad_producida': cantidad_producida,
            'plan_id': plan_id,
            'masks_actualizadas': mask_codes
        })
        
    except Exception as e:
        print('❌ Error actualizando used_count:', e)
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/metal-mask/test', methods=['GET'])
def api_test_metal_mask():
    """Test endpoint para Metal Mask"""
    try:
        from .db_mysql import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM metal_mask_history")
        count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Metal Mask test OK',
            'total_records': count
        })
    except Exception as e:
        import traceback
        print('❌ Error en test:', e)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/historial-uso-mask-metal-ajax')
@login_requerido
def historial_uso_mask_metal_ajax():
    """Template para Historial de uso de mask de metal"""
    return render_template('Control de calidad/historial_uso_mask_metal_ajax.html')

@app.route('/historial-uso-squeegee-ajax')
@login_requerido
def historial_uso_squeegee_ajax():
    """Template para Historial de uso de squeegee"""
    return render_template('Control de calidad/historial_uso_squeegee_ajax.html')

@app.route('/process-interlock-history-ajax')
@login_requerido
def process_interlock_history_ajax():
    """Template para Process interlock History"""
    return render_template('Control de calidad/process_interlock_history_ajax.html')

@app.route('/control-master-sample-smt-ajax')
@login_requerido
def control_master_sample_smt_ajax():
    """Template para Control de Master Sample de SMT"""
    return render_template('Control de calidad/control_master_sample_smt_ajax.html')

@app.route('/historial-inspeccion-master-sample-smt-ajax')
@login_requerido
def historial_inspeccion_master_sample_smt_ajax():
    """Template para Historial de inspección de Master Sample de SMT"""
    return render_template('Control de calidad/historial_inspeccion_master_sample_smt_ajax.html')

@app.route('/control-inspeccion-oqc-ajax')
@login_requerido
def control_inspeccion_oqc_ajax():
    """Template para Control de inspección de OQC"""
    return render_template('Control de calidad/control_inspeccion_oqc_ajax.html')

# ============================================================================
# CONTROL DE MATERIAL - RUTAS AJAX
# ============================================================================

@app.route('/ajuste-numero-parte-ajax')
@login_requerido
def ajuste_numero_parte_ajax():
    """Template para Ajuste de número de parte"""
    return render_template('Control de material/ajuste_numero_parte_ajax.html')

@app.route('/consultar-peps-ajax')
@login_requerido
def consultar_peps_ajax():
    """Template para Consultar PEPS"""
    return render_template('Control de material/consultar_peps_ajax.html')

@app.route('/control-almacen-ajax')
@login_requerido
def control_almacen_ajax():
    """Template para Control de almacén"""
    return render_template('Control de material/control_almacen_ajax.html')

@app.route('/control-entrada-salida-material-ajax')
@login_requerido
def control_entrada_salida_material_ajax():
    """Template para Control de entrada y salida de material"""
    return render_template('Control de material/control_entrada_salida_material_ajax.html')

@app.route('/control-recibo-refacciones-ajax')
@login_requerido
def control_recibo_refacciones_ajax():
    """Template para Control de recibo de refacciones"""
    return render_template('Control de material/control_recibo_refacciones_ajax.html')

@app.route('/control-retorno-ajax')
@login_requerido
def control_retorno_ajax():
    """Template para Control de retorno"""
    return render_template('Control de material/control_retorno_ajax.html')

@app.route('/control-salida-ajax')
@login_requerido
def control_salida_ajax():
    """Template para Control de salida"""
    return render_template('Control de material/control_salida_ajax.html')

@app.route('/control-salida-refacciones-ajax')
@login_requerido
def control_salida_refacciones_ajax():
    """Template para Control de salida de refacciones"""
    return render_template('Control de material/control_salida_refacciones_ajax.html')

@app.route('/control-total-material-ajax')
@login_requerido
def control_total_material_ajax():
    """Template para Control total de material"""
    return render_template('Control de material/control_total_material_ajax.html')

@app.route('/estandares-refacciones-ajax')
@login_requerido
def estandares_refacciones_ajax():
    """Template para Estándares de refacciones"""
    return render_template('Control de material/estandares_refacciones_ajax.html')

@app.route('/estatus-inventario-refacciones-ajax')
@login_requerido
def estatus_inventario_refacciones_ajax():
    """Template para Estatus de inventario de refacciones"""
    return render_template('Control de material/estatus_inventario_refacciones_ajax.html')

@app.route('/estatus-material-ajax')
@login_requerido
def estatus_material_ajax():
    """Template para Estatus de material"""
    return render_template('Control de material/estatus_material_ajax.html')

@app.route('/estatus-material-msl-ajax')
@login_requerido
def estatus_material_msl_ajax():
    """Template para Estatus de material MSL"""
    return render_template('Control de material/estatus_material_msl_ajax.html')

@app.route('/historial-inventario-real-ajax')
@login_requerido
def historial_inventario_real_ajax():
    """Template para Historial de inventario real"""
    return render_template('Control de material/historial_inventario_real_ajax.html')

@app.route('/historial-material-ajax')
@login_requerido
def historial_material_ajax():
    """Template para Historial de material"""
    return render_template('Control de material/historial_material_ajax.html')

@app.route('/inventario-rollos-smd-ajax')
@login_requerido
def inventario_rollos_smd_ajax():
    """Template para Inventario de rollos SMD"""
    return render_template('Control de material/inventario_rollos_smd_ajax.html')

@app.route('/longterm-inventory-ajax')
@login_requerido
def longterm_inventory_ajax():
    """Template para Inventario a largo plazo"""
    return render_template('Control de material/longterm_inventory_ajax.html')

@app.route('/material-sustituto-ajax')
@login_requerido
def material_sustituto_ajax():
    """Template para Material sustituto"""
    return render_template('Control de material/material_sustituto_ajax.html')

@app.route('/recibo-pago-material-ajax')
@login_requerido
def recibo_pago_material_ajax():
    """Template para Recibo y pago de material"""
    return render_template('Control de material/recibo_pago_material_ajax.html')

@app.route('/registro-material-real-ajax')
@login_requerido
def registro_material_real_ajax():
    """Template para Registro de material real"""
    return render_template('Control de material/registro_material_real_ajax.html')

# ======== ENDPOINTS PARA INVENTARIO IMD TERMINADO ========

@app.route('/api/inventario_general', methods=['GET'])
def api_inventario_general():
    """Endpoint para inventario general IMD desde tabla inv_resumen_modelo"""
    try:
        q = request.args.get("q", "", type=str).strip()
        stock = request.args.get("stock", "", type=str).strip()  # "", ">0", "=0"

        where_conditions = []
        params = []
        
        if q:
            where_conditions.append("(modelo LIKE %s OR nparte LIKE %s)")
            params.extend([f"%{q}%", f"%{q}%"])
            
        if stock == ">0":
            where_conditions.append("stock_total > 0")
        elif stock == "=0":
            where_conditions.append("stock_total = 0")

        where_sql = ("WHERE " + " AND ".join(where_conditions)) if where_conditions else ""
        
        sql = f"""
            SELECT
              modelo,
              nparte,
              stock_total,
              ubicaciones,
              DATE_FORMAT(ultima_entrada, '%Y-%m-%d %H:%i:%s') AS ultima_entrada,
              DATE_FORMAT(ultima_salida,  '%Y-%m-%d %H:%i:%s') AS ultima_salida
            FROM inv_resumen_modelo
            {where_sql}
            ORDER BY modelo, nparte
            LIMIT 2000
        """
        
        results = execute_query(sql, params, fetch='all')
        
        return jsonify({
            'status': 'success',
            'items': results or []
        })
        
    except Exception as e:
        print(f"Error en api_inventario_general: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'items': []
        }), 500

@app.route('/api/ubicacion', methods=['GET'])
def api_ubicacion():
    """Endpoint para ubicaciones IMD desde tabla ubicacionimdinv"""
    try:
        desde = request.args.get("desde", "", type=str).strip()
        hasta = request.args.get("hasta", "", type=str).strip()
        q = request.args.get("q", "", type=str).strip()
        ubic = request.args.get("ubicacion", "", type=str).strip()
        carro = request.args.get("carro", "", type=str).strip()

        where_conditions = []
        params = []

        # Normalizamos fecha: usamos fecha_subida si existe, si no, parseamos 'fecha'
        fecha_expr = "COALESCE(DATE(fecha), STR_TO_DATE(fecha, '%Y-%m-%d'))"

        if desde:
            where_conditions.append(f"{fecha_expr} >= %s")
            params.append(desde)
        if hasta:
            where_conditions.append(f"{fecha_expr} <= %s")
            params.append(hasta)
        if q:
            where_conditions.append("(modelo LIKE %s OR nparte LIKE %s OR ubicacion LIKE %s OR carro LIKE %s)")
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"])
        if ubic:
            where_conditions.append("ubicacion = %s")
            params.append(ubic)
        if carro:
            where_conditions.append("carro = %s")
            params.append(carro)

        where_sql = ("WHERE " + " AND ".join(where_conditions)) if where_conditions else ""
        
        sql = f"""
            SELECT
              modelo,
              nparte,
              fecha,
              ubicacion,
              cantidad,
              carro
            FROM ubicacionimdinv
            {where_sql}
            ORDER BY {fecha_expr} DESC, modelo, nparte
            LIMIT 5000
        """
        
        results = execute_query(sql, params, fetch='all')
        
        return jsonify({
            'status': 'success',
            'items': results or []
        })
        
    except Exception as e:
        print(f"Error en api_ubicacion: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'items': []
        }), 500

@app.route('/api/movimientos', methods=['GET'])
def api_movimientos():
    """Endpoint para movimientos IMD desde tabla movimientosimd_smd"""
    try:
        desde = request.args.get("desde", "", type=str).strip()
        hasta = request.args.get("hasta", "", type=str).strip()
        q = request.args.get("q", "", type=str).strip()
        tipo = request.args.get("tipo", "", type=str).strip()  # ENTRADA / SALIDA / AJUSTE / ""

        where_conditions = []
        params = []
        
        # Filtros de fecha simplificados - usar directamente el campo fecha
        if desde:
            where_conditions.append("fecha >= %s")
            params.append(desde)
        if hasta:
            where_conditions.append("fecha <= %s")
            params.append(hasta + ' 23:59:59')
        if tipo:
            where_conditions.append("UPPER(tipo) = %s")
            params.append(tipo.upper())
        if q:
            # El modelo no está en la tabla de movimientos; lo deducimos con un subquery
            where_conditions.append("(nparte LIKE %s OR ubicacion LIKE %s OR carro LIKE %s)")
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

        where_sql = ("WHERE " + " AND ".join(where_conditions)) if where_conditions else ""
        
        sql = f"""
            SELECT
              fecha AS fecha_hora,
              UPPER(tipo) AS tipo,
              nparte,
              -- Deducimos el modelo de la última ubicación conocida para esa parte
              (SELECT u.modelo
                 FROM ubicacionimdinv u
                WHERE u.nparte = m.nparte
                ORDER BY u.fecha DESC
                LIMIT 1) AS modelo,
              cantidad,
              ubicacion,
              carro
            FROM movimientosimd_smd m
            {where_sql}
            ORDER BY fecha DESC
            LIMIT 5000
        """
        
        results = execute_query(sql, params, fetch='all')
        
        return jsonify({
            'status': 'success',
            'items': results or []
        })
        
    except Exception as e:
        print(f"Error en api_movimientos: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'items': []
        }), 500

# ===============================
# 🚀 RUTA SIMPLE PARA ANDROID - mysql-proxy.php
# ===============================

@app.route('/mysql-proxy.php', methods=['POST', 'GET', 'OPTIONS'])
def mysql_proxy_php():
    """
    Ruta simple para acceder al archivo PHP sin login requerido
    Compatible con tu aplicación Android existente
    """
    try:
        from flask import send_from_directory
        import os
        
        # Manejar preflight CORS
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
            response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
            return response
        
        # Ruta al archivo PHP
        php_dir = os.path.join(os.path.dirname(__file__), 'php')
        php_file = 'mysql-proxy.php'
        
        # Verificar que el archivo existe
        php_path = os.path.join(php_dir, php_file)
        if not os.path.exists(php_path):
            return jsonify({
                'success': False,
                'error': 'Archivo mysql-proxy.php no encontrado'
            }), 404
        
        print(f"📍 Redirigiendo a: {php_path}")
        
        # Servir el archivo PHP directamente
        return send_from_directory(php_dir, php_file)
        
    except Exception as e:
        print(f"❌ Error sirviendo mysql-proxy.php: {e}")
        response = jsonify({
            'success': False,
            'error': f'Error del servidor: {str(e)}'
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route('/api/mysql', methods=['POST', 'GET', 'OPTIONS'])
def api_mysql_simple():
    """
    Ruta API simple para consultas MySQL desde Android
    Sin autenticación requerida - equivalente a tu PHP
    """
    try:
        # Manejar preflight CORS
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
            response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
            return response
        
        # Obtener consulta SQL
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No se recibió JSON'
                }), 400
            sql_query = data.get('sql', '').strip()
        else:  # GET
            sql_query = request.args.get('sql', '').strip()
        
        # Si no hay consulta SQL, usar una consulta por defecto para test
        if not sql_query:
            sql_query = 'SELECT COUNT(*) as total_materiales FROM materiales'
            print(f"⚠️ No se proporcionó SQL, usando consulta por defecto: {sql_query}")
        
        print(f"🔍 Ejecutando consulta API simple: {sql_query}")
        
        # Validaciones básicas de seguridad
        sql_upper = sql_query.upper()
        if not sql_upper.startswith('SELECT') and not sql_upper.startswith('SHOW'):
            return jsonify({
                'success': False,
                'error': 'Solo se permiten consultas SELECT y SHOW'
            }), 403
        
        # Ejecutar consulta usando la función existente
        result = execute_query(sql_query, fetch='all')
        
        # Preparar respuesta
        response_data = {
            'success': True,
            'data': result if result else [],
            'count': len(result) if result else 0
        }
        
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        
        print(f"✅ API Simple - Consulta exitosa: {len(result) if result else 0} registros")
        return response
        
    except Exception as e:
        print(f"❌ Error en API MySQL Simple: {e}")
        
        error_response = jsonify({
            'success': False,
            'error': str(e)
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

@app.route('/api/status', methods=['GET'])
def api_status():
    """
    Endpoint simple para verificar el estado de la API
    """
    try:
        response_data = {
            'success': True,
            'status': 'API funcionando correctamente',
            'endpoints': [
                '/api/mysql - Consultas SQL directas',
                '/api/mysql-proxy - Proxy MySQL compatible',
                '/mysql-proxy.php - Archivo PHP original'
            ],
            'database': 'MySQL conectado',
            'timestamp': str(datetime.now())
        }
        
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        error_response = jsonify({
            'success': False,
            'error': str(e)
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500


# =============================
# Rutas para Plan SMD Diario
# =============================

@app.route("/plan-smd-diario")
def plan_smd_diario():
    """Página principal del Plan SMD Diario"""
    return render_template("Control de proceso/plan_smd_diario.html")


@app.route("/control-operacion-linea-smt")
def control_operacion_linea_smt():
    """Página de Control de Operación de Línea SMT con datos del plan SMD"""
    return render_template("Control de proceso/Control de operacion de linea SMT.html")


@app.route("/api/plan-smd-diario", methods=['GET'])
def api_plan_smd_diario():
    """
    Cruza PLAN (plan_smd) con AOI por (fecha, LINEA y MODELO) usando aoi_file_log.
    Params:
      ?date=YYYY-MM-DD (obligatorio)
      &shift=DIA|NOCHE|TIEMPO_EXTRA (opcional)
    Suposiciones:
      - EBR ≡ NParte (se compara en mayúsculas)
      - plan_smd.linea es tipo "SMT A", "SMT B", "SMT C"
      - aoi_file_log tiene columns: shift_date, shift, line_no, model, piece_w, board_side
    """
    date = request.args.get("date")
    shift = request.args.get("shift", "").strip()
    if not date:
        return jsonify({"error": "missing 'date' (YYYY-MM-DD)"}), 400

    # Armado dinámico de SQL compatible con MySQL 5.7+ (sin CTE)
    aoi_where = "WHERE shift_date = %s"
    params = [date]
    if shift:
        aoi_where += " AND shift = %s"
        params.append(shift)

    sql = f"""
    SELECT
      pd.id, pd.linea, pd.lote, pd.nparte, UPPER(pd.nparte) AS ebr,
      pd.modelo, pd.tipo, pd.turno, pd.ct, pd.uph,
      pd.qty, pd.fisico, pd.falta, pd.pct, pd.comentarios, pd.fecha_creacion, pd.usuario_creacion,
      COALESCE(a.producido, 0) AS producido,
      (COALESCE(a.producido,0) >= pd.qty) AS completo
    FROM
      (
        SELECT
          p.id, UPPER(p.linea) AS linea, p.lote, p.nparte, p.modelo, p.tipo, p.turno, p.ct, p.uph,
          p.qty, p.fisico, p.falta, p.pct, p.comentarios, p.fecha_creacion, p.usuario_creacion
        FROM plan_smd p
        WHERE DATE(p.fecha_creacion) = %s
      ) AS pd
    LEFT JOIN
      (
        SELECT
          shift_date,
          shift,
          CASE line_no
            WHEN 1 THEN 'SMT A'
            WHEN 2 THEN 'SMT B'
            WHEN 3 THEN 'SMT C'
            ELSE CONCAT('SMT ', line_no)
          END AS linea,
          UPPER(model) AS modelo,
          SUM(piece_w) AS producido
        FROM aoi_file_log
        {aoi_where}
        GROUP BY shift_date, shift, linea, UPPER(model)
      ) AS a
      ON a.modelo = UPPER(pd.nparte)
     AND a.linea  = pd.linea
    ORDER BY pd.linea, pd.modelo, pd.id;
    """

    # Inserta el parámetro de DATE(plan)
    params = [date] + params

    try:
        rows = execute_query(sql, params, fetch='all')
        if rows is None:
            rows = []

        # Normalizar tipos y strings
        for r in rows:
            r["qty"] = int(r.get("qty") or 0)
            r["fisico"] = int(r.get("fisico") or 0)
            r["falta"] = int(r.get("falta") or 0)
            r["pct"] = int(r.get("pct") or 0)
            r["producido"] = int(r.get("producido") or 0)
            if r.get("fecha_creacion"):
                r["fecha_creacion"] = str(r["fecha_creacion"])
        
        return jsonify(rows)
    
    except Exception as e:
        print(f"❌ Error en api_plan_smd_diario: {e}")
        return jsonify({"error": f"Error en consulta: {str(e)}"}), 500

# ===== VISOR MYSQL =====
@app.route('/visor-mysql')
def visor_mysql():
    """Visor de tablas MySQL con interfaz moderna"""
    table = request.args.get("table", "raw")
    # Validar nombre de tabla para seguridad
    if not re.match(r"^[A-Za-z0-9_]+$", table):
        table = "raw"
    return render_template("visor_mysql.html", table=table)

@app.route('/control-modelos-visor-ajax')
@login_requerido
def control_modelos_visor_ajax():
    """Ruta AJAX para cargar dinámicamente el visor MySQL para Control de modelos"""
    try:
        table = request.args.get("table", "raw")
        # Validar nombre de tabla para seguridad
        if not re.match(r"^[A-Za-z0-9_]+$", table):
            table = "raw"
        
        usuario_actual = session.get('nombre_completo', session.get('usuario', 'Usuario no identificado')).strip()
        
        return render_template('INFORMACION BASICA/control_modelos_visor_ajax.html', 
                             table=table, 
                             usuario=usuario_actual)
    except Exception as e:
        print(f"Error al cargar template de visor MySQL: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control-modelos-smt-ajax')
@login_requerido
def control_modelos_smt_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de Modelos SMT"""
    try:
        usuario_actual = session.get('nombre_completo', session.get('usuario', 'Usuario no identificado')).strip()
        return render_template('INFORMACION BASICA/control_modelos_smt_ajax.html', 
                             usuario=usuario_actual)
    except Exception as e:
        print(f"Error al cargar template Control de Modelos SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/api/mysql/columns')
def api_mysql_columns():
    """API para obtener columnas de una tabla"""
    try:
        table = request.args.get("table", "raw")
        if not re.match(r"^[A-Za-z0-9_]+$", table):
            return jsonify({"error": "Nombre de tabla inválido"}), 400
            
        query = """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s
        ORDER BY ORDINAL_POSITION
        """
        
        result = execute_query(query, (table,), fetch='all')
        if result is not None:
            columns = [row["COLUMN_NAME"] for row in result]
            return jsonify({"table": table, "columns": columns})
        else:
            return jsonify({"table": table, "columns": []})
            
    except Exception as e:
        print(f"❌ Error en api_mysql_columns: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/mysql/data')
def api_mysql_data():
    """API para obtener datos de una tabla con filtros y ordenamiento inteligente"""
    try:
        table = request.args.get("table", "raw")
        if not re.match(r"^[A-Za-z0-9_]+$", table):
            return jsonify({"error": "Nombre de tabla inválido"}), 400
            
        limit = min(max(int(request.args.get("limit", 200)), 1), 2000)
        offset = max(int(request.args.get("offset", 0)), 0)
        search = (request.args.get("search") or "").strip()
        
        # Obtener columnas primero
        cols_query = """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s
        ORDER BY ORDINAL_POSITION
        """
        cols_result = execute_query(cols_query, (table,), fetch='all')
        if not cols_result:
            return jsonify({"table": table, "columns": [], "rows": [], "total": 0})
            
        columns = [row["COLUMN_NAME"] for row in cols_result]
        
        # Construir consulta base con ordenamiento inteligente
        base_sql = f"SELECT * FROM `{table}`"
        where = ""
        params = []
        
        # Agregar filtro de búsqueda si existe
        if search:
            like_conditions = []
            for col in columns:
                like_conditions.append(f"CAST(`{col}` AS CHAR) LIKE %s")
            where = f" WHERE ({' OR '.join(like_conditions)})"
            params = [f"%{search}%"] * len(columns)
        
        # Ordenamiento inteligente para agrupar modelos similares
        # Buscar columnas que podrían contener códigos de modelo
        model_columns = []
        for col in columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['modelo', 'model', 'codigo', 'parte', 'part', 'ebr', 'product']):
                model_columns.append(col)
        
        # Construir ORDER BY inteligente
        order_by = ""
        if model_columns:
            # Usar la primera columna que parece ser de modelo/código
            main_col = model_columns[0]
            # Ordenar por la parte base del código (sin números finales) y luego por el código completo
            order_by = f" ORDER BY REGEXP_REPLACE(`{main_col}`, '[0-9]+$', ''), `{main_col}`"
        else:
            # Si no hay columnas obvias de modelo, ordenar por la primera columna
            if columns:
                order_by = f" ORDER BY `{columns[0]}`"
        
        # Consulta para contar total
        count_sql = f"SELECT COUNT(*) as total FROM `{table}`{where}"
        count_result = execute_query(count_sql, params, fetch='one')
        total = count_result["total"] if count_result else 0
        
        # Consulta para obtener datos paginados con ordenamiento
        data_sql = f"{base_sql}{where}{order_by} LIMIT %s OFFSET %s"
        data_params = params + [limit, offset]
        data_result = execute_query(data_sql, data_params, fetch='all')
        
        rows = data_result if data_result else []
        
        return jsonify({
            "table": table,
            "columns": columns,
            "rows": rows,
            "total": total,
            "limit": limit,
            "offset": offset,
            "search": search,
            "ordering": f"Ordenado por: {main_col if model_columns else columns[0] if columns else 'N/A'}"
        })
        
    except Exception as e:
        print(f"❌ Error en api_mysql_data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/mysql/update', methods=['POST'])
def api_mysql_update():
    """API para actualizar registros en tabla raw"""
    
    def clean_column_value(column_name, value):
        """Limpiar y validar valores según el tipo de columna"""
        if value is None or value == '':
            return None
        
        value = str(value).strip()
        
        # Columnas numéricas que pueden tener formato con comas
        numeric_columns = ['hora_dia', 'c_t', 'uph', 'price', 'st', 'neck_st', 'l_b', 'input', 'output']
        
        if column_name in numeric_columns:
            # Remover comas y convertir a formato numérico válido
            cleaned = value.replace(',', '').replace(' ', '')
            
            # Si está vacío después de limpiar, devolver None
            if not cleaned:
                return None
                
            try:
                # Intentar convertir a float para validar
                float(cleaned)
                return cleaned
            except ValueError:
                print(f"⚠️ Valor no numérico para columna {column_name}: {value}, usando NULL")
                return None
        
        # Para otras columnas, devolver el valor limpio
        return value if value != '' else None
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No se recibieron datos"}), 400
            
        # Por seguridad, solo permitir actualizar tabla raw
        table = "raw"
        
        # Obtener datos originales y nuevos
        original_data = data.get('original', {})
        new_data = data.get('new', {})
        
        if not original_data or not new_data:
            return jsonify({"error": "Faltan datos originales o nuevos"}), 400
        
        # Construir la cláusula WHERE basada en los datos originales
        # Usar solo campos clave para identificar el registro, no los campos que se están modificando
        
        # Definir campos clave que normalmente no cambian (identificadores únicos)
        key_fields = ['part_no', 'model', 'project', 'main_display', 'linea']
        
        where_conditions = []
        where_params = []
        
        # Usar solo los campos clave disponibles
        for key in key_fields:
            if key in original_data:
                value = original_data[key]
                if value is None or value == '' or value == 'NULL':
                    where_conditions.append(f"(`{key}` IS NULL OR `{key}` = '' OR `{key}` = 'NULL')")
                else:
                    where_conditions.append(f"`{key}` = %s")
                    where_params.append(value)
        
        # Si no hay suficientes campos clave, usar los primeros 5 campos no modificados
        if len(where_conditions) < 3:
            used_fields = set(key_fields)
            for key, value in original_data.items():
                if key not in used_fields and len(where_conditions) < 5:
                    # Solo usar si no es un campo que se está modificando
                    if key not in new_data or new_data[key] == value:
                        if value is None or value == '' or value == 'NULL':
                            where_conditions.append(f"(`{key}` IS NULL OR `{key}` = '' OR `{key}` = 'NULL')")
                        else:
                            where_conditions.append(f"`{key}` = %s")
                            where_params.append(value)
                        used_fields.add(key)
        
        if not where_conditions:
            return jsonify({"error": "No se pueden identificar los datos originales"}), 400
        
        # Construir la cláusula SET para los nuevos datos
        # Excluir columnas generadas y de solo lectura
        readonly_columns = ['Usuario', 'crea', 'upt']  # Columnas que no se pueden actualizar
        
        set_conditions = []
        set_params = []
        
        for key, value in new_data.items():
            # Saltar columnas de solo lectura/generadas
            if key in readonly_columns:
                print(f"⚠️ Saltando columna de solo lectura: {key}")
                continue
            
            # Limpiar y validar valores según el tipo de columna
            cleaned_value = clean_column_value(key, value)
            
            set_conditions.append(f"`{key}` = %s")
            set_params.append(cleaned_value)
        
        if not set_conditions:
            return jsonify({"error": "No hay datos válidos para actualizar (todas las columnas son de solo lectura)"}), 400
        
        # Construir y ejecutar la consulta UPDATE
        update_sql = f"""
            UPDATE `{table}` 
            SET {', '.join(set_conditions)}
            WHERE {' AND '.join(where_conditions)}
            LIMIT 1
        """
        
        params = set_params + where_params
        
        # Ejecutar la actualización
        result = execute_query(update_sql, params, fetch='none')
        
        # Verificar si se actualizó algún registro
        if result is not False:
            return jsonify({
                "success": True,
                "message": "Registro actualizado exitosamente"
            })
        else:
            return jsonify({"error": "No se pudo actualizar el registro"}), 500
            
    except Exception as e:
        print(f"❌ Error en api_mysql_update: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/mysql/create', methods=['POST'])
def api_mysql_create():
    """Crear nuevo registro en tabla raw"""
    try:
        # Obtener datos del request
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No se enviaron datos"}), 400
        
        new_data = data.get('data', {})
        
        if not new_data:
            return jsonify({"error": "No se enviaron datos para crear"}), 400
        
        # Tabla fija para este visor
        table = 'raw'
        
        # Función para limpiar valores de columnas
        def clean_column_value(column_name, value):
            if value is None:
                return None
            
            # Si es string vacío, convertir a None para enviar NULL
            if isinstance(value, str) and value.strip() == '':
                return None
                
            # Limpiar campos numéricos (remover comas)
            numeric_fields = ['hora_dia', 'c_t', 'uph', 'price', 'st', 'neck_st', 'l_b', 'input', 'output']
            if column_name in numeric_fields and isinstance(value, str):
                cleaned = value.replace(',', '').strip()
                if cleaned == '':
                    return None
                return cleaned
            
            return value
        
        # Preparar datos para inserción (excluir campos de solo lectura)
        readonly_fields = ['crea', 'upt', 'raw']  # Usuario ya no es columna generada
        insert_data = {}
        
        # Agregar usuario logueado si no está en los datos
        if 'Usuario' not in new_data:
            new_data['Usuario'] = session.get('nombre_completo', session.get('usuario', 'Sistema')).strip()
        
        for key, value in new_data.items():
            if key not in readonly_fields:
                cleaned_value = clean_column_value(key, value)
                # Incluir todos los campos, incluso si son NULL
                insert_data[key] = cleaned_value
        
        if not insert_data:
            return jsonify({"error": "No hay datos válidos para insertar"}), 400
        
        # Construir consulta INSERT
        columns = list(insert_data.keys())
        placeholders = ', '.join(['%s'] * len(columns))
        columns_str = ', '.join([f'`{col}`' for col in columns])
        
        insert_sql = f"""
            INSERT INTO `{table}` ({columns_str})
            VALUES ({placeholders})
        """
        
        values = list(insert_data.values())
        
        # Ejecutar la inserción
        result = execute_query(insert_sql, values, fetch='none')
        
        # Verificar si se insertó el registro
        if result is not False:
            return jsonify({
                "success": True,
                "message": "Registro creado exitosamente"
            })
        else:
            return jsonify({"error": "No se pudo crear el registro"}), 500
            
    except Exception as e:
        print(f"❌ Error en api_mysql_create: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/mysql/usuario-actual', methods=['GET'])
@login_requerido
def api_mysql_usuario_actual():
    """Obtener el usuario actualmente logueado"""
    try:
        usuario_id = session.get('usuario', 'Sistema')
        nombre_completo = session.get('nombre_completo', usuario_id).strip()
        return jsonify({
            "success": True,
            "usuario": usuario_id,
            "nombre_completo": nombre_completo,
            "usuario_display": nombre_completo  # El nombre que se mostrará en la UI
        })
    except Exception as e:
        print(f"❌ Error en api_mysql_usuario_actual: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/mysql/delete', methods=['POST'])
@login_requerido
def api_mysql_delete():
    """API para eliminar un registro de una tabla MySQL"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Datos no válidos"}), 400
            
        table = data.get("table", "raw")
        if not re.match(r"^[A-Za-z0-9_]+$", table):
            return jsonify({"error": "Nombre de tabla inválido"}), 400
        
        # Obtener el ID o identificador único del registro
        record_id = data.get("id")
        if not record_id:
            return jsonify({"error": "ID del registro requerido"}), 400
        
        # Verificar que la tabla tenga una columna 'id'
        cols_query = """
        SELECT COLUMN_NAME, COLUMN_KEY
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s
        ORDER BY ORDINAL_POSITION
        """
        cols_result = execute_query(cols_query, (table,), fetch='all')
        if not cols_result:
            return jsonify({"error": "Tabla no encontrada"}), 404
        
        # Buscar columna de clave primaria o 'id'
        id_column = None
        for col in cols_result:
            if col["COLUMN_KEY"] == "PRI" or col["COLUMN_NAME"].lower() == "id":
                id_column = col["COLUMN_NAME"]
                break
        
        if not id_column:
            return jsonify({"error": "No se encontró columna ID en la tabla"}), 400
        
        # Verificar que el registro existe antes de eliminar
        check_sql = f"SELECT COUNT(*) as count FROM `{table}` WHERE `{id_column}` = %s"
        check_result = execute_query(check_sql, (record_id,), fetch='one')
        
        if not check_result or check_result["count"] == 0:
            return jsonify({"error": "Registro no encontrado"}), 404
        
        # Ejecutar eliminación
        delete_sql = f"DELETE FROM `{table}` WHERE `{id_column}` = %s"
        result = execute_query(delete_sql, (record_id,), fetch=None)
        
        if result is not False:
            return jsonify({
                "success": True,
                "message": "Registro eliminado exitosamente",
                "deleted_id": record_id
            })
        else:
            return jsonify({"error": "No se pudo eliminar el registro"}), 500
            
    except Exception as e:
        print(f"❌ Error en api_mysql_delete: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
def crear_tabla_plan_smd_runs():
    """Crear tabla de ejecuciones del plan SMD (ciclos de producción)."""
    try:
        query = """
        CREATE TABLE IF NOT EXISTS plan_smd_runs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            plan_id INT,
            linea VARCHAR(32) NOT NULL,
            lot_no VARCHAR(32) NOT NULL,
            uph DECIMAL(20,6) DEFAULT 0,
            ct DECIMAL(20,6) DEFAULT 0,
            qty_plan INT DEFAULT 0,
            start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            end_time DATETIME NULL,
            status ENUM('RUNNING','ENDED') DEFAULT 'RUNNING',
            created_by VARCHAR(64) DEFAULT 'sistema',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_linea (linea),
            INDEX idx_lot (lot_no),
            INDEX idx_plan (plan_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        execute_query(query)
        # Asegurar estado PAUSED disponible
        try:
            execute_query("ALTER TABLE plan_smd_runs MODIFY status ENUM('RUNNING','PAUSED','ENDED') DEFAULT 'RUNNING'")
        except Exception as e:
            print(f"  (info) Status PAUSED: {str(e)[:60]}")
        # Columnas adicionales para baseline y conteo AOI
        try:
            execute_query("ALTER TABLE plan_smd_runs ADD COLUMN aoi_model VARCHAR(64) NULL")
        except Exception as e:
            print(f"  (info) aoi_model: {str(e)[:60]}")
        try:
            execute_query("ALTER TABLE plan_smd_runs ADD COLUMN aoi_line_no INT NULL")
        except Exception as e:
            print(f"  (info) aoi_line_no: {str(e)[:60]}")
        try:
            execute_query("ALTER TABLE plan_smd_runs ADD COLUMN aoi_baseline INT NULL")
        except Exception as e:
            print(f"  (info) aoi_baseline: {str(e)[:60]}")
        try:
            execute_query("ALTER TABLE plan_smd_runs ADD COLUMN aoi_baseline_shift_date DATE NULL")
        except Exception as e:
            print(f"  (info) aoi_baseline_shift_date: {str(e)[:60]}")
        try:
            execute_query("ALTER TABLE plan_smd_runs ADD COLUMN aoi_baseline_shift VARCHAR(16) NULL")
        except Exception as e:
            print(f"  (info) aoi_baseline_shift: {str(e)[:60]}")
        try:
            execute_query("ALTER TABLE plan_smd_runs ADD COLUMN aoi_produced_final INT NULL")
        except Exception as e:
            print(f"  (info) aoi_produced_final: {str(e)[:60]}")
        print(" Tabla plan_smd_runs creada/verificada")
    except Exception as e:
        print(f"⚠️  Error creando tabla plan_smd_runs (continuando): {str(e)[:100]}")

crear_tabla_plan_smd_runs()

@app.route('/api/plan-smd/list', methods=['GET'])
def api_plan_smd_list():
    """Listar renglones de plan_smd con filtros simples.

    Params opcionales: 
    - q (busca en modelo, nparte, lote)
    - linea, desde, hasta 
    - solo_pendientes: muestra planes del dia actual + planeados/iniciados de fechas anteriores
    - plan_id: consulta especifica de un plan
    """
    try:
        q = (request.args.get('q') or '').strip()
        linea = (request.args.get('linea') or '').strip()
        desde = (request.args.get('desde') or '').strip()
        hasta = (request.args.get('hasta') or '').strip()
        solo_pendientes = request.args.get('solo_pendientes') == 'true'
        plan_id = (request.args.get('plan_id') or '').strip()

        sql = [
            "SELECT p.id, p.linea, p.lote, p.nparte, p.modelo, p.tipo, p.turno, p.ct, p.uph, p.qty, p.fisico, p.falta, p.pct, p.comentarios, p.fecha_creacion, COALESCE(t.estado,'PLANEADO') AS estatus,",
            "r.status AS run_status, r.id AS run_id, r.start_time AS run_start_time, r.end_time AS run_end_time,",
            "r.aoi_model, r.aoi_line_no, r.aoi_baseline, r.aoi_baseline_shift_date, r.aoi_baseline_shift, r.aoi_produced_final",
            "FROM plan_smd p", 
            "LEFT JOIN (SELECT lot_no, MAX(updated_at) AS mx FROM trazabilidad GROUP BY lot_no) tm ON tm.lot_no = p.lote",
            "LEFT JOIN trazabilidad t ON t.lot_no = tm.lot_no AND t.updated_at = tm.mx",
            "LEFT JOIN (SELECT plan_id, status, id, start_time, end_time, aoi_model, aoi_line_no, aoi_baseline, aoi_baseline_shift_date, aoi_baseline_shift, aoi_produced_final, ROW_NUMBER() OVER (PARTITION BY plan_id ORDER BY start_time DESC) as rn FROM plan_smd_runs) r ON r.plan_id = p.id AND r.rn = 1",
            "WHERE 1=1"
        ]
        params = []
        
        # Si se especifica un plan_id especifico, solo buscar ese plan (ignorar todos los demas filtros)
        if plan_id:
            sql.append("AND p.id = %s")
            params.append(plan_id)
        else:
            # Logica para "Mostrar Pendientes": 
            # - Planes del dia actual (cualquier estado)
            # - Planes PLANEADOS de fechas anteriores (trabajo no iniciado)
            # - Planes INICIADOS de fechas anteriores (trabajo en progreso)
            if solo_pendientes:
                # Obtener fecha actual
                from datetime import datetime
                fecha_actual = datetime.now().strftime('%Y-%m-%d')
                
                # Condicion: (planes del dia actual de cualquier estado) OR (planes PLANEADOS/INICIADOS de fechas anteriores)
                sql.append("AND ((fecha_creacion >= %s AND fecha_creacion <= %s) OR (fecha_creacion < %s AND (COALESCE(t.estado,'PLANEADO') IN ('PLANEADO', 'INICIADO') OR r.status = 'RUNNING') AND (r.status IS NULL OR r.status != 'ENDED')))")
                params.extend([fecha_actual, fecha_actual + ' 23:59:59', fecha_actual])
            else:
                # Aplicar filtros de fecha normales cuando no es solo_pendientes
                if desde:
                    sql.append("AND fecha_creacion >= %s")
                    params.append(desde)
                if hasta:
                    sql.append("AND fecha_creacion <= %s")
                    # Incluir todo el dia hasta 23:59:59
                    params.append(hasta + ' 23:59:59')
            
            if q:
                sql.append("AND (modelo LIKE %s OR nparte LIKE %s OR lote LIKE %s)")
                params.extend([f"%{q}%", f"%{q}%", f"%{q}%"]) 
            if linea:
                sql.append("AND p.linea = %s")
                params.append(linea)
                print(f"Filtro de linea aplicado en API: '{linea}'")
            
        sql.append("ORDER BY fecha_creacion DESC, id DESC")

        rows = execute_query(" ".join(sql), tuple(params) if params else None, fetch='all') or []

        # Enriquecer con producido estimado desde runs
        try:
            if rows:
                lotes = [r.get('lote') for r in rows if r.get('lote')]
                if lotes:
                    placeholders = ','.join(['%s'] * len(lotes))
                    run_sql = f"""
                        SELECT lot_no, status, uph, qty_plan, start_time, end_time
                        FROM plan_smd_runs
                        WHERE lot_no IN ({placeholders})
                        ORDER BY start_time DESC
                    """
                    run_rows = execute_query(run_sql, tuple(lotes), fetch='all') or []
                    latest = {}
                    for rr in run_rows:
                        ln = rr.get('lot_no')
                        if ln and ln not in latest:
                            latest[ln] = rr
                    from datetime import datetime
                    now = datetime.now()
                    for r in rows:
                        lot = r.get('lote')
                        producido = 0
                        if lot and lot in latest:
                            rr = latest[lot]
                            try:
                                uph = float(rr.get('uph') or 0)
                            except Exception:
                                uph = 0.0
                            st = rr.get('start_time')
                            et = rr.get('end_time')
                            if uph and st:
                                elapsed_h = ((et or now) - st).total_seconds() / 3600.0
                                producido = int(min(int(r.get('qty') or 0), max(0.0, uph * elapsed_h)))
                        r['producido'] = producido
                        qty_val = int(r.get('qty') or 0)
                        r['falta'] = max(0, qty_val - producido)
                        r['pct'] = int(min(100, round((producido / qty_val)*100))) if qty_val else 0
        except Exception as e:
            print(f"?? Error enriqueciendo producido en api_plan_smd_list: {e}")

        # OVERRIDE: Producido por AOI usando baseline del run (si existe)
        try:
            if rows:
                shift_order = {'DIA': 1, 'TIEMPO_EXTRA': 2, 'NOCHE': 3}
                for r in rows:
                    qty_val = int(r.get('qty') or 0)
                    if r.get('run_id') and r.get('id') is not None:
                        aoi_model = (r.get('aoi_model') or '').upper()
                        aoi_line_no = r.get('aoi_line_no')
                        bl = r.get('aoi_baseline')
                        bl_date = r.get('aoi_baseline_shift_date')
                        bl_shift = (r.get('aoi_baseline_shift') or '').strip() if r.get('aoi_baseline_shift') else ''
                        final_val = r.get('aoi_produced_final')
                        if final_val is not None:
                            producido = int(final_val or 0)
                            r['producido'] = producido
                            r['falta'] = max(0, qty_val - producido)
                            r['pct'] = int(min(100, round((producido / qty_val) * 100))) if qty_val else 0
                        elif aoi_model and aoi_line_no and bl is not None and bl_date and bl_shift:
                            agg_sql = """
                                SELECT shift_date, shift, SUM(piece_w) AS total
                                FROM aoi_file_log
                                WHERE model=%s AND line_no=%s AND shift_date >= %s
                                GROUP BY shift_date, shift
                                ORDER BY shift_date ASC
                            """
                            agg_rows = execute_query(agg_sql, (aoi_model, int(aoi_line_no), bl_date), fetch='all') or []
                            total = 0
                            for ar in agg_rows:
                                sd = ar.get('shift_date')
                                sh = (ar.get('shift') or '').strip()
                                t = int(ar.get('total') or 0)
                                if not sd or not sh:
                                    continue
                                if str(sd) == str(bl_date) and sh == bl_shift:
                                    total += max(0, t - int(bl or 0))
                                else:
                                    if str(sd) == str(bl_date) and shift_order.get(sh, 0) < shift_order.get(bl_shift, 0):
                                        continue
                                    total += t
                            r['producido'] = int(min(qty_val, max(0, total)))
                            r['falta'] = max(0, qty_val - r['producido'])
                            r['pct'] = int(min(100, round((r['producido'] / qty_val) * 100))) if qty_val else 0
        except Exception as e:
            print(f"?? Error override producido AOI en api_plan_smd_list: {e}")

        return jsonify({'success': True, 'rows': rows, 'count': len(rows)})
    except Exception as e:
        print(f"? Error en api_plan_smd_list: {e}")
        return jsonify({'success': False, 'error': str(e)})


def generar_lot_no_secuencial(q, like, prefix, fecha):
    """Genera un numero de lote secuencial basado en la consulta"""
    last = execute_query(q, (like,), fetch='one')
    if last and last.get('lot_no'):
        try:
            seq = int(last['lot_no'].split('-')[-1]) + 1
        except Exception:
            seq = 1
    else:
        seq = 1
    return f"{prefix}{fecha}-{seq:04d}"


@app.route('/api/plan-run/start', methods=['POST'])
def api_plan_run_start():
    """Iniciar un run de producción desde un renglón del plan.
    Body: { plan_id, linea?, lot_prefix? }
    """
    try:
        data = request.get_json(force=True) or {}
        plan_id = int(data.get('plan_id'))
        linea = (data.get('linea') or '').strip()
        lot_prefix = (data.get('lot_prefix') or 'I').strip() or 'I'
        usuario = session.get('nombre_completo', session.get('usuario', 'Sistema')).strip()

        # Obtener datos del plan
        plan_row = execute_query("SELECT * FROM plan_smd WHERE id=%s", (plan_id,), fetch='one')
        if not plan_row:
            return jsonify({'success': False, 'error': 'Plan no encontrado'}), 404
        if not linea:
            linea = plan_row.get('linea', '')

        # VALIDACION CRITICA: Verificar que no haya otro run activo en la misma linea
        existing_run = execute_query(
            "SELECT id, lot_no, plan_id FROM plan_smd_runs WHERE linea=%s AND status IN ('RUNNING', 'PAUSED') ORDER BY start_time DESC LIMIT 1", 
            (linea,), 
            fetch='one'
        )
        if existing_run:
            existing_plan = execute_query("SELECT modelo, nparte FROM plan_smd WHERE id=%s", (existing_run['plan_id'],), fetch='one')
            modelo_info = f" ({existing_plan['modelo']} - {existing_plan['nparte']})" if existing_plan else ""
            return jsonify({
                'success': False, 
                'error': f'Ya hay un run activo en la lonea {linea}: {existing_run["lot_no"]}{modelo_info}. Debe finalizar el run actual antes de iniciar uno nuevo.'
            }), 409  # 409 Conflict

        # Verificar que este plan especofico no tenga ya un run activo
        plan_run_active = execute_query(
            "SELECT id, lot_no, status FROM plan_smd_runs WHERE plan_id=%s AND status IN ('RUNNING', 'PAUSED') ORDER BY start_time DESC LIMIT 1", 
            (plan_id,), 
            fetch='one'
        )
        if plan_run_active:
            return jsonify({
                'success': False, 
                'error': f'Este plan ya tiene un run activo: {plan_run_active["lot_no"]} (Status: {plan_run_active["status"]}). Debe finalizar el run actual antes de iniciar uno nuevo.'
            }), 409

        # Verificar que el plan no esto ya finalizado
        trazabilidad_actual = execute_query(
            "SELECT estado FROM trazabilidad WHERE lot_no=%s ORDER BY updated_at DESC LIMIT 1", 
            (plan_row.get('lote'),), 
            fetch='one'
        )
        if trazabilidad_actual and trazabilidad_actual.get('estado') == 'FINALIZADO':
            return jsonify({
                'success': False, 
                'error': f'Este plan ya esto finalizado (LOT: {plan_row.get("lote")}). No se puede reiniciar un plan finalizado.'
            }), 409

        # Usar LOT NO ya definido en el plan; no generar uno nuevo
        lot_no = plan_row.get('lote')
        if not lot_no:
            return jsonify({'success': False, 'error': 'El plan no tiene LOT asignado'}), 400
        uph = plan_row.get('uph') or 0
        ct = plan_row.get('ct') or 0
        qty_plan = plan_row.get('qty') or 0

        # Preparar baseline AOI al iniciar RUN
        aoi_model = (plan_row.get('nparte') or plan_row.get('modelo') or '').upper()
        def _map_line_no(s: str):
            try:
                ss = (s or '').upper().strip()
                if ss.startswith('SMT '):
                    ss = ss[4:].strip()
                if ss and ss[0].isalpha():
                    return max(1, min(26, ord(ss[0]) - ord('A') + 1))
                if ss.isdigit():
                    return int(ss)
            except Exception:
                pass
            return None
        aoi_line_no = _map_line_no(linea)
        from .aoi_api import classify_shift, compute_shift_date
        from .auth_system import AuthSystem as _AS
        now_mx = _AS.get_mexico_time()
        current_shift = classify_shift(now_mx)
        current_shift_date = compute_shift_date(now_mx, current_shift).strftime('%Y-%m-%d')
        aoi_baseline = None
        if aoi_model and aoi_line_no:
            baseline_sql = """
                SELECT COALESCE(SUM(piece_w),0) AS total
                FROM aoi_file_log
                WHERE shift_date=%s AND shift=%s AND model=%s AND line_no=%s
            """
            try:
                rowb = execute_query(baseline_sql, (current_shift_date, current_shift, aoi_model, aoi_line_no), fetch='one') or {}
                aoi_baseline = int(rowb.get('total') or 0)
            except Exception as e2:
                print(f"?? Error obteniendo baseline AOI: {e2}")
                aoi_baseline = 0

        insert = """
            INSERT INTO plan_smd_runs (plan_id, linea, lot_no, uph, ct, qty_plan, status, created_by,
                                       aoi_model, aoi_line_no, aoi_baseline, aoi_baseline_shift_date, aoi_baseline_shift)
            VALUES (%s,%s,%s,%s,%s,%s,'RUNNING',%s, %s,%s,%s,%s,%s)
        """
        execute_query(insert, (plan_id, linea, lot_no, uph, ct, qty_plan, usuario,
                               aoi_model, aoi_line_no, aoi_baseline, current_shift_date, current_shift))

        # Actualizar trazabilidad: INICIADO
        try:
            # Intentar INSERT primero
            try:
                execute_query("""
                    INSERT INTO trazabilidad (lot_no, estado, updated_at) 
                    VALUES (%s, 'INICIADO', NOW())
                """, (lot_no,))
            except Exception:
                # Si falla (probablemente duplicado), actualizar el mos reciente
                execute_query("""
                    UPDATE trazabilidad SET estado='INICIADO', updated_at=NOW() 
                    WHERE lot_no=%s AND updated_at = (
                        SELECT MAX(updated_at) FROM (SELECT updated_at FROM trazabilidad WHERE lot_no=%s) AS t
                    )
                """, (lot_no, lot_no))
        except Exception as e2:
            print(f"⚠️ Error actualizando trazabilidad (INICIADO): {e2}")

        run = execute_query("SELECT * FROM plan_smd_runs WHERE lot_no=%s", (lot_no,), fetch='one')
        return jsonify({'success': True, 'run': run})
    except Exception as e:
        print(f"❌ Error en api_plan_run_start: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/plan-run/end', methods=['POST'])
def api_plan_run_end():
    try:
        data = request.get_json(force=True) or {}
        run_id = int(data.get('run_id'))
        plan_id_req = data.get('plan_id')
        # Validar run existente y opcionalmente que corresponda al plan indicado
        run = execute_query("SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch='one')
        if not run:
            return jsonify({'success': False, 'error': 'Run no encontrado'}), 404
        if plan_id_req is not None and str(run.get('plan_id')) != str(plan_id_req):
            return jsonify({'success': False, 'error': 'El run no corresponde al plan indicado'}), 400
        # Cerrar el run si esto RUNNING
        update = "UPDATE plan_smd_runs SET status='ENDED', end_time=NOW() WHERE id=%s AND status='RUNNING'"
        execute_query(update, (run_id,))
        run = execute_query("SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch='one')
        # Calcular y guardar producido final basado en AOI (si hay baseline)
        try:
            if run:
                aoi_model = (run.get('aoi_model') or '').upper()
                aoi_line_no = run.get('aoi_line_no')
                bl = int(run.get('aoi_baseline') or 0)
                bl_date = run.get('aoi_baseline_shift_date')
                bl_shift = (run.get('aoi_baseline_shift') or '').strip() if run.get('aoi_baseline_shift') else ''
                if aoi_model and aoi_line_no and bl_date and bl_shift:
                    shift_order = {'DIA': 1, 'TIEMPO_EXTRA': 2, 'NOCHE': 3}
                    agg_sql = """
                        SELECT shift_date, shift, SUM(piece_w) AS total
                        FROM aoi_file_log
                        WHERE model=%s AND line_no=%s AND shift_date >= %s
                        GROUP BY shift_date, shift
                        ORDER BY shift_date ASC
                    """
                    agg_rows = execute_query(agg_sql, (aoi_model, int(aoi_line_no), bl_date), fetch='all') or []
                    total = 0
                    for ar in agg_rows:
                        sd = ar.get('shift_date')
                        sh = (ar.get('shift') or '').strip()
                        t = int(ar.get('total') or 0)
                        if not sd or not sh:
                            continue
                        if str(sd) == str(bl_date) and sh == bl_shift:
                            total += max(0, t - bl)
                        else:
                            if str(sd) == str(bl_date) and shift_order.get(sh, 0) < shift_order.get(bl_shift, 0):
                                continue
                            total += t
                    try:
                        execute_query("UPDATE plan_smd_runs SET aoi_produced_final=%s WHERE id=%s", (int(total), run_id))
                        run = execute_query("SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch='one')
                    except Exception as e3:
                        print(f"?? Error guardando aoi_produced_final: {e3}")
        except Exception as e2:
            print(f"?? Error calculando producido final AOI: {e2}")
        try:
            if run and run.get('lot_no'):
                # Intentar INSERT primero
                try:
                    execute_query("""
                        INSERT INTO trazabilidad (lot_no, estado, updated_at) 
                        VALUES (%s, 'FINALIZADO', NOW())
                    """, (run['lot_no'],))
                except Exception:
                    # Si falla (probablemente duplicado), actualizar el mos reciente
                    execute_query("""
                        UPDATE trazabilidad SET estado='FINALIZADO', updated_at=NOW() 
                        WHERE lot_no=%s AND updated_at = (
                            SELECT MAX(updated_at) FROM (SELECT updated_at FROM trazabilidad WHERE lot_no=%s) AS t
                        )
                    """, (run['lot_no'], run['lot_no']))
        except Exception as e2:
            print(f"⚠️ Error actualizando trazabilidad (FINALIZADO): {e2}")
        return jsonify({'success': True, 'run': run})
    except Exception as e:
        print(f"❌ Error en api_plan_run_end: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/plan-run/pause', methods=['POST'])
def api_plan_run_pause():
    try:
        data = request.get_json(force=True) or {}
        run_id = int(data.get('run_id'))
        update = "UPDATE plan_smd_runs SET status='PAUSED' WHERE id=%s AND status='RUNNING'"
        execute_query(update, (run_id,))
        run = execute_query("SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch='one')
        if run and run.get('lot_no'):
            try:
                # Intentar INSERT primero
                try:
                    execute_query("""
                        INSERT INTO trazabilidad (lot_no, estado, updated_at) 
                        VALUES (%s, 'PAUSA', NOW())
                    """, (run['lot_no'],))
                except Exception:
                    # Si falla (probablemente duplicado), actualizar el mos reciente
                    execute_query("""
                        UPDATE trazabilidad SET estado='PAUSA', updated_at=NOW() 
                        WHERE lot_no=%s AND updated_at = (
                            SELECT MAX(updated_at) FROM (SELECT updated_at FROM trazabilidad WHERE lot_no=%s) AS t
                        )
                    """, (run['lot_no'], run['lot_no']))
            except Exception as e2:
                print(f"?? Error actualizando trazabilidad (PAUSA): {e2}")
        return jsonify({'success': True, 'run': run})
    except Exception as e:
        print(f"? Error en api_plan_run_pause: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/plan-run/resume', methods=['POST'])
def api_plan_run_resume():
    try:
        data = request.get_json(force=True) or {}
        run_id = int(data.get('run_id'))
        run = execute_query("SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch='one')
        if not run:
            return jsonify({'success': False, 'error': 'Run no encontrado'}), 404
        linea = run.get('linea')
        exists = execute_query("SELECT id FROM plan_smd_runs WHERE linea=%s AND status='RUNNING' AND id<>%s LIMIT 1", (linea, run_id), fetch='one')
        if exists:
            return jsonify({'success': False, 'error': f'Ya existe un plan en progreso en {linea}'}), 400
        execute_query("UPDATE plan_smd_runs SET status='RUNNING' WHERE id=%s AND status='PAUSED'", (run_id,))
        if run.get('lot_no'):
            try:
                execute_query("UPDATE trazabilidad SET estado='INICIADO', updated_at=NOW() WHERE lot_no=%s", (run['lot_no'],))
            except Exception as e2:
                print(f"?? Error actualizando trazabilidad (INICIADO): {e2}")
        run = execute_query("SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch='one')
        return jsonify({'success': True, 'run': run})
    except Exception as e:
        print(f"? Error en api_plan_run_resume: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/plan-run/status', methods=['GET'])
def api_plan_run_status():
    """Estado del run por linea o run_id.
    Si está RUNNING, calcula progreso estimado usando UPH y tiempo transcurrido.
    """
    try:
        run_id = request.args.get('run_id')
        linea = request.args.get('linea')
        
        if run_id:
            row = execute_query("SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch='one')
        elif linea and linea.strip():
            row = execute_query("SELECT * FROM plan_smd_runs WHERE linea=%s AND status='RUNNING' ORDER BY start_time DESC LIMIT 1", (linea.strip(),), fetch='one')
        else:
            error_msg = 'Parometros insuficientes. Se requiere run_id o linea.'
            if linea == '':
                error_msg = 'Parometro linea esto vacoo'
            return jsonify({'success': False, 'error': error_msg}), 400

        if not row:
            return jsonify({'success': True, 'running': False})

        # Calcular progreso estimado
        from datetime import datetime
        start = row.get('start_time')
        end = row.get('end_time')
        uph = float(row.get('uph') or 0)
        qty_plan = int(row.get('qty_plan') or 0)
        producido = 0
        if start and not end and uph > 0:
            # elapsed hours
            now = datetime.utcnow()
            # MySQL datetime naive; asumir UTC-agnóstico
            elapsed_hours = max(0.0, (now - start).total_seconds() / 3600.0)
            producido = int(min(qty_plan, uph * elapsed_hours))
        return jsonify({'success': True, 'running': row['status']=='RUNNING', 'run': row, 'producido_est': producido})
    except Exception as e:
        print(f"❌ Error en api_plan_run_status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
def crear_tabla_trazabilidad():
    """Crear tabla de trazabilidad (LOTE por WO/LINEA con estados)."""
    try:
        query = """
        CREATE TABLE IF NOT EXISTS trazabilidad (
            id INT AUTO_INCREMENT PRIMARY KEY,
            linea VARCHAR(32) NOT NULL,
            lot_no VARCHAR(32) NOT NULL,
            plan_id INT NULL,
            codigo_wo VARCHAR(32) NULL,
            estado ENUM('PLANEADO','INICIADO','PAUSA','FINALIZADO') DEFAULT 'PLANEADO',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            usuario VARCHAR(64) DEFAULT 'sistema',
            INDEX idx_linea (linea),
            INDEX idx_lot (lot_no),
            INDEX idx_estado (estado)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        execute_query(query)
        print(" Tabla trazabilidad creada/verificada")
    except Exception as e:
        print(f"❌ Error creando tabla trazabilidad: {e}")

crear_tabla_trazabilidad()


###############################################
# Metal Mask: poginas y API (integracion)
###############################################

def init_metal_mask_tables():
    """Crea/ajusta tablas usadas por Metal Mask si no existen."""
    try:
        # Tabla principal de masks con nombres de columnas en inglos (usadas por el frontend)
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS masks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                management_no VARCHAR(64) UNIQUE,
                storage_box VARCHAR(64),
                pcb_code VARCHAR(64),
                side VARCHAR(16),
                production_date DATE,
                used_count INT DEFAULT 0,
                max_count INT DEFAULT 0,
                allowance INT DEFAULT 0,
                model_name VARCHAR(255),
                tension_min DECIMAL(6,2),
                tension_max DECIMAL(6,2),
                thickness DECIMAL(6,2),
                supplier VARCHAR(128),
                registration_date VARCHAR(64),
                disuse ENUM('Uso','Desuso','Scrap') DEFAULT 'Uso',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        # Asegurar valores del ENUM en caso de historiales previos (migracion suave)
        try:
            execute_query("ALTER TABLE masks MODIFY COLUMN disuse ENUM('Use','Disuse','Uso','Desuso','Scrap') DEFAULT 'Uso'")
            execute_query("UPDATE masks SET disuse='Uso' WHERE disuse='Use'")
            execute_query("UPDATE masks SET disuse='Desuso' WHERE disuse='Disuse'")
            execute_query("ALTER TABLE masks MODIFY COLUMN disuse ENUM('Uso','Desuso','Scrap') DEFAULT 'Uso'")
        except Exception as _:
            # Si falla (p.ej. por no existir la tabla/columna aon), continuar
            pass

        # Tabla de cajas de almacenamiento
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS storage_boxes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                management_no VARCHAR(64) UNIQUE,
                code VARCHAR(64),
                name VARCHAR(64),
                location VARCHAR(64),
                storage_status ENUM('Disponible','Ocupado','Mantenimiento') DEFAULT 'Disponible',
                used_status ENUM('Usado','No Usado') DEFAULT 'Usado',
                note TEXT,
                registration_date VARCHAR(64),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        print(" Tablas Metal Mask creadas/verificadas")
    except Exception as e:
        print(f"Error creando/verificando tablas Metal Mask: {e}")


# Inicializar tablas de Metal Mask
init_metal_mask_tables()


# Poginas nuevas (HTML integrados)
@app.route('/control/metal-mask')
@login_requerido
def pagina_control_metal_mask():
    try:
        return render_template('Control de produccion/control_mask_metal_ajax.html')
    except Exception as e:
        print(f"Error al renderizar Control de metal mask: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route('/control/metal-mask/caja')
@login_requerido
def pagina_control_caja_metal_mask():
    try:
        return render_template('Control de produccion/control_caja_mask_metal_ajax.html')
    except Exception as e:
        print(f"Error al renderizar Control de caja de metal mask: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# API: Masks
@app.route('/api/masks', methods=['GET'])
@login_requerido
def api_list_masks():
    try:
        disuse = request.args.get('disuse', 'ALL')
        sql = (
            "SELECT id, management_no, storage_box, pcb_code, side, "
            "COALESCE(DATE_FORMAT(production_date, '%Y-%m-%d'), '') AS production_date, "
            "used_count, max_count, allowance, model_name, tension_min, tension_max, thickness, "
            "supplier, registration_date, disuse FROM masks"
        )
        params = []
        if disuse and disuse != 'ALL':
            sql += " WHERE disuse=%s"
            params.append(disuse)
        sql += " ORDER BY id DESC"
        rows = execute_query(sql, tuple(params) if params else None, fetch='all') or []

        # Normalizacion ligera de tipos para JSON
        out = []
        for r in rows:
            r = dict(r)
            for k in ('used_count', 'max_count', 'allowance'):
                try:
                    r[k] = int(r.get(k) or 0)
                except Exception:
                    pass
            for k in ('tension_min', 'tension_max', 'thickness'):
                v = r.get(k)
                try:
                    r[k] = float(v) if v is not None else None
                except Exception:
                    pass
            out.append(r)
        return jsonify(out)
    except Exception as e:
        print(f"Error en api_list_masks: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/masks', methods=['POST'])
@login_requerido
def api_create_mask():
    try:
        data = request.get_json(force=True) or {}
        data.setdefault('used_count', 0)
        data.setdefault('max_count', 0)
        data.setdefault('allowance', 0)
        data.setdefault('disuse', 'Uso')

        pd = data.get('production_date')
        if isinstance(pd, str) and len(pd) >= 10:
            data['production_date'] = pd[:10]
        else:
            data['production_date'] = None

        cols = (
            'management_no','storage_box','pcb_code','side','production_date',
            'used_count','max_count','allowance','model_name','tension_min',
            'tension_max','thickness','supplier','registration_date','disuse'
        )
        placeholders = ','.join(['%s']*len(cols))
        values = [data.get(c) for c in cols]
        sql = f"INSERT INTO masks ({','.join(cols)}) VALUES ({placeholders})"
        execute_query(sql, tuple(values))
        return jsonify({'success': True, 'message': 'Registrado', 'data': data}), 201
    except Exception as e:
        msg = str(e)
        if 'Duplicate entry' in msg:
            return jsonify({'error': 'El Nomero de Gestion ya existe'}), 400
        print(f"Error en api_create_mask: {e}")
        return jsonify({'error': msg}), 500


@app.route('/api/masks/<int:mask_id>', methods=['PUT'])
@login_requerido
def api_update_mask(mask_id: int):
    try:
        p = request.get_json(force=True) or {}
        required = p.get('management_no', '').strip()
        if not required:
            return jsonify({'error': 'Nomero de Gestion es requerido'}), 400

        sql = (
            "UPDATE masks SET management_no=%s, storage_box=%s, pcb_code=%s, side=%s, "
            "production_date=%s, used_count=%s, max_count=%s, allowance=%s, "
            "model_name=%s, tension_min=%s, tension_max=%s, thickness=%s, "
            "supplier=%s, registration_date=%s, disuse=%s WHERE id=%s"
        )
        params = (
            p.get('management_no','').strip(),
            p.get('storage_box','').strip(),
            p.get('pcb_code','').strip(),
            p.get('side','').strip(),
            (p.get('production_date') or None),
            p.get('used_count',0),
            p.get('max_count',0),
            p.get('allowance',0),
            p.get('model_name','').strip(),
            p.get('tension_min',0),
            p.get('tension_max',0),
            p.get('thickness',0),
            p.get('supplier','').strip(),
            p.get('registration_date','').strip(),
            p.get('disuse','Uso'),
            mask_id
        )
        affected = execute_query(sql, params)
        if affected == 0:
            return jsonify({'error': 'Moscara no encontrada'}), 404
        return jsonify({'success': True, 'message': 'Actualizado'})
    except Exception as e:
        msg = str(e)
        if 'Duplicate entry' in msg:
            return jsonify({'error': 'El Nomero de Gestion ya existe'}), 400
        print(f"Error en api_update_mask: {e}")
        return jsonify({'error': msg}), 500


# API: Storage Boxes
@app.route('/api/storage', methods=['GET'])
@login_requerido
def api_get_storage():
    try:
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 100))
        search = (request.args.get('search', '') or '').strip()
        filter_storage_status = (request.args.get('filter_storage_status', '') or '').strip()
        filter_used_status = (request.args.get('filter_used_status', '') or '').strip()

        clauses = []
        params = []
        if search:
            like = f"%{search}%"
            clauses.append("(management_no LIKE %s OR code LIKE %s OR name LIKE %s OR location LIKE %s OR note LIKE %s)")
            params += [like, like, like, like, like]
        if filter_storage_status:
            clauses.append("storage_status=%s")
            params.append(filter_storage_status)
        if filter_used_status:
            clauses.append("used_status=%s")
            params.append(filter_used_status)
        where = ' AND '.join(clauses) if clauses else '1=1'

        total_row = execute_query(f"SELECT COUNT(*) AS total FROM storage_boxes WHERE {where}", tuple(params) if params else None, fetch='one') or {'total': 0}
        data = execute_query(
            f"""
            SELECT id, management_no, code, name, location, storage_status, used_status, note, registration_date
            FROM storage_boxes WHERE {where}
            ORDER BY id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset]) if params else (limit, offset),
            fetch='all'
        ) or []
        return jsonify({'data': data, 'total': total_row.get('total', 0)})
    except Exception as e:
        print(f"Error en api_get_storage: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/storage', methods=['POST'])
@login_requerido
def api_add_storage():
    try:
        p = request.get_json(force=True) or {}
        management_no = (p.get('management_no','') or '').strip()
        if not management_no:
            return jsonify({'error': 'Nomero de Gestion es requerido'}), 400
        sql = (
            "INSERT INTO storage_boxes (management_no, code, name, location, storage_status, used_status, note, registration_date) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
        )
        params = (
            management_no,
            (p.get('code','') or '').strip(),
            (p.get('name','') or '').strip(),
            (p.get('location','') or '').strip(),
            (p.get('storage_status','Disponible') or 'Disponible'),
            (p.get('used_status','Usado') or 'Usado'),
            (p.get('note','') or '').strip(),
            (p.get('registration_date','') or '').strip(),
        )
        execute_query(sql, params)
        return jsonify({'success': True, 'message': 'Caja de almacenamiento registrada exitosamente'})
    except Exception as e:
        msg = str(e)
        if 'Duplicate entry' in msg:
            return jsonify({'error': f'El Nomero de Gestion "{management_no}" ya existe. Por favor use un codigo/ubicacion diferente.'}), 400
        print(f"Error en api_add_storage: {e}")
        return jsonify({'error': msg}), 500


@app.route('/api/storage/<int:storage_id>', methods=['PUT'])
@login_requerido
def api_update_storage(storage_id: int):
    try:
        p = request.get_json(force=True) or {}
        management_no = (p.get('management_no','') or '').strip()
        if not management_no:
            return jsonify({'error': 'Nomero de Gestion es requerido'}), 400
        sql = (
            "UPDATE storage_boxes SET management_no=%s, code=%s, name=%s, location=%s, "
            "storage_status=%s, used_status=%s, note=%s, registration_date=%s WHERE id=%s"
        )
        params = (
            management_no,
            (p.get('code','') or '').strip(),
            (p.get('name','') or '').strip(),
            (p.get('location','') or '').strip(),
            (p.get('storage_status','Disponible') or 'Disponible'),
            (p.get('used_status','Usado') or 'Usado'),
            (p.get('note','') or '').strip(),
            (p.get('registration_date','') or '').strip(),
            storage_id,
        )
        affected = execute_query(sql, params)
        if affected == 0:
            return jsonify({'error': 'Caja de almacenamiento no encontrada'}), 404
        return jsonify({'success': True, 'message': 'Caja de almacenamiento actualizada exitosamente'})
    except Exception as e:
        msg = str(e)
        if 'Duplicate entry' in msg:
            return jsonify({'error': 'El Nomero de Gestion ya existe'}), 400
        print(f"Error en api_update_storage: {e}")
        return jsonify({'error': msg}), 500


@app.route('/api/bom-smt-data', methods=['GET'])
@login_requerido
def api_bom_smt_data():
    """API para obtener datos del BOM SMT basado en lonea y modelo"""
    try:
        # Obtener parometros
        linea = request.args.get('linea', '')
        model_code = request.args.get('model_code', '')
        
        if not linea or not model_code:
            return jsonify({'success': False, 'error': 'Lonea y modelo son requeridos'}), 400
            
        print(f"API BOM SMT - Filtros:")
        print(f"  Linea: {linea}")
        print(f"  Modelo: {model_code}")
        
        from .db_mysql import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Mapear lonea SMT a nomero de lonea
        mapeo_lineas = {
            'SMT A': '2',
            'SMT B': '2', 
            'SMT C': '3',
            'SMT D': '4',
            '1LINE': '2',
            '2LINE': '2',
            '3LINE': '3',
            '4LINE': '4'
        }
        
        linea_numero = mapeo_lineas.get(linea, '2')
        
        # Consultar ambas tablas (bom_smt_f y bom_smt_r) - solo elementos con cantidad > 0
        query_f = """
            SELECT 
                id, linea, model_code, mounter, slot, material_code, 
                description, feeder_info, qty, raw_filename, 
                created_at, updated_at, 'FRONT' as tabla_tipo
            FROM bom_smt_f 
            WHERE linea = %s AND model_code LIKE %s AND qty > 0
            ORDER BY mounter, slot
        """
        
        query_r = """
            SELECT 
                id, linea, model_code, mounter, slot, material_code, 
                description, feeder_info, qty, raw_filename, 
                created_at, updated_at, 'REAR' as tabla_tipo
            FROM bom_smt_r 
            WHERE linea = %s AND model_code LIKE %s AND qty > 0
            ORDER BY mounter, slot
        """
        
        # Buscar por modelo (puede contener EBR)
        model_pattern = f'%{model_code}%'
        
        # Ejecutar consultas
        cursor.execute(query_f, [linea_numero, model_pattern])
        resultados_f = cursor.fetchall()
        
        cursor.execute(query_r, [linea_numero, model_pattern])
        resultados_r = cursor.fetchall()
        
        # Combinar resultados
        todos_resultados = list(resultados_f) + list(resultados_r)
        
        print(f"Encontrados {len(todos_resultados)} registros BOM ({len(resultados_f)} F + {len(resultados_r)} R)")
        print(f"Parametros de busqueda - Linea numero: {linea_numero}, Patron modelo: {model_pattern}")
        
        # Formatear datos - solo incluir elementos con cantidad > 0
        formatted_data = []
        for row in todos_resultados:
            try:
                qty_value = row[8] if len(row) > 8 else 0
                
                # Solo incluir si qty > 0
                if qty_value <= 0:
                    continue
                    
                formatted_row = {
                    'id': row[0] if len(row) > 0 else '',
                    'linea': row[1] if len(row) > 1 else '',
                    'model_code': row[2] if len(row) > 2 else '',
                    'mounter': row[3] if len(row) > 3 else '',
                    'slot': row[4] if len(row) > 4 else '',
                    'material_code': row[5] if len(row) > 5 else '',
                    'description': row[6] if len(row) > 6 else '',
                    'feeder_info': row[7] if len(row) > 7 else '',
                    'qty': qty_value,
                    'raw_filename': row[9] if len(row) > 9 else '',
                    'created_at': str(row[10]) if len(row) > 10 and row[10] else '',
                    'updated_at': str(row[11]) if len(row) > 11 and row[11] else '',
                    'tabla_tipo': row[12] if len(row) > 12 else '',
                    'status': 'pending'  # Por defecto pendiente, se actualizaro con el mapeo
                }
                formatted_data.append(formatted_row)
                
            except Exception as row_error:
                print(f"Error procesando fila BOM: {row_error}")
                continue
        
        cursor.close()
        conn.close()
        
        print(f"BOM filtrado: {len(formatted_data)} elementos con qty > 0")
        
        return jsonify({
            'success': True,
            'data': formatted_data,
            'total': len(formatted_data),
            'linea': linea,
            'model_code': model_code,
            'total_raw': len(todos_resultados),
            'total_filtered': len(formatted_data)
        })
        
    except Exception as e:
        print(f"Error en api_bom_smt_data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ====== ENDPOINT DE PRUEBA PARA HISTORIAL SMT ======
@app.route('/api/test-historial-smt', methods=['GET'])
@login_requerido
def test_historial_smt():
    """
    Endpoint de prueba para verificar la consulta de historial SMT
    Uso: /api/test-historial-smt?linea=SMT%20B
    """
    try:
        linea_input = request.args.get('linea', 'SMT B').strip()
        # Convertir nombre de línea a formato de BD
        linea = convertir_linea_smt(linea_input)
        
        from .db_mysql import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # Primero verificamos si existen datos en la tabla
        test_query = """
            SELECT COUNT(*) as total,
                   COUNT(DISTINCT linea) as lineas,
                   COUNT(DISTINCT maquina) as maquinas
            FROM historial_cambio_material_smt
            WHERE linea = %s
        """
        
        cursor.execute(test_query, (linea,))
        stats = cursor.fetchone()
        
        # Consulta simple para ver los datos más recientes
        simple_query = """
            SELECT linea, maquina, SlotNo, PartName, FeederBase, 
                   ScanDate, ScanTime, fecha_subida
            FROM historial_cambio_material_smt
            WHERE linea = %s
            ORDER BY fecha_subida DESC
            LIMIT 10
        """
        
        cursor.execute(simple_query, (linea,))
        recent_data = cursor.fetchall()
        
        # Consulta para ver todas las líneas disponibles
        lines_query = "SELECT DISTINCT linea FROM historial_cambio_material_smt ORDER BY linea"
        cursor.execute(lines_query)
        available_lines = [row[0] for row in cursor.fetchall()]
        
        # Consulta de la estructura de la tabla
        structure_query = "DESCRIBE historial_cambio_material_smt"
        cursor.execute(structure_query)
        table_structure = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'linea_solicitada': linea_input,
            'linea_convertida_bd': linea,
            'estadisticas': {
                'total_registros': stats[0] if stats else 0,
                'lineas_distintas': stats[1] if stats else 0,
                'maquinas_distintas': stats[2] if stats else 0
            },
            'lineas_disponibles_bd': available_lines,
            'lineas_disponibles_convertidas': [convertir_linea_smt_reverso(line) for line in available_lines],
            'estructura_tabla': [
                {
                    'campo': row[0],
                    'tipo': row[1],
                    'nulo': row[2],
                    'clave': row[3],
                    'default': row[4]
                }
                for row in table_structure
            ],
            'datos_recientes': [
                {
                    'linea': row[0],
                    'maquina': row[1], 
                    'SlotNo': row[2],
                    'PartName': row[3],
                    'FeederBase': row[4],
                    'ScanDate': row[5],
                    'ScanTime': row[6],
                    'fecha_subida': str(row[7]) if row[7] else None
                }
                for row in recent_data
            ]
        })
        
    except Exception as e:
        import traceback
        print(f"Error en test_historial_smt: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False, 
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# ====== FUNCIÓN PARA CONVERTIR NOMBRES DE LÍNEA ======
def convertir_linea_smt(linea_nombre):
    """
    Convierte nombres de línea SMT a formato de BD
    SMT A = 1line
    SMT B = 2line  
    SMT C = 3line
    SMT D = 4line
    """
    conversion = {
        'SMT A': '1line',
        'SMT B': '2line', 
        'SMT C': '3line',
        'SMT D': '4line'
    }
    return conversion.get(linea_nombre, linea_nombre)

def convertir_linea_smt_reverso(linea_bd):
    """
    Convierte formato de BD a nombres de línea SMT
    1line = SMT A
    2line = SMT B
    3line = SMT C  
    4line = SMT D
    """
    conversion = {
        '1line': 'SMT A',
        '2line': 'SMT B',
        '3line': 'SMT C', 
        '4line': 'SMT D'
    }
    return conversion.get(linea_bd, linea_bd)

# ====== ENDPOINT SIMPLIFICADO PARA PROBAR LA CONSULTA V2 ======
@app.route('/api/test-historial-smt-v2', methods=['GET'])
@login_requerido
def test_historial_smt_v2():
    """
    Endpoint de prueba simplificado para la consulta v2 con conversión de líneas
    Uso: /api/test-historial-smt-v2?linea=SMT%20B
    """
    try:
        linea_input = request.args.get('linea', '').strip()
        linea_bd = convertir_linea_smt(linea_input)
        
        from .db_mysql import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # Primero ver todas las líneas disponibles
        all_lines_query = "SELECT DISTINCT linea FROM historial_cambio_material_smt ORDER BY linea"
        cursor.execute(all_lines_query)
        available_lines_bd = [row[0] for row in cursor.fetchall()]
        available_lines_converted = [convertir_linea_smt_reverso(line) for line in available_lines_bd]
        
        # Consulta simplificada para debug
        debug_query = """
            SELECT linea, maquina, SlotNo, FeederBase,
                   PartName, ScanDate, fecha_subida,
                   CASE WHEN UPPER(FeederBase) LIKE '%F%' THEN 'FRONT'
                        WHEN UPPER(FeederBase) LIKE '%R%' THEN 'REAR'
                        ELSE 'UNKNOWN' END AS side_norm
            FROM historial_cambio_material_smt
            WHERE linea = %s
            ORDER BY linea, maquina, SlotNo, fecha_subida DESC
            LIMIT 20
        """
        
        cursor.execute(debug_query, (linea_bd,))
        debug_data = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'linea_solicitada': linea_input,
            'linea_convertida_bd': linea_bd,
            'lineas_disponibles_bd': available_lines_bd,
            'lineas_disponibles_convertidas': available_lines_converted,
            'total_registros': len(debug_data),
            'datos_debug': [
                {
                    'linea_bd': row[0],
                    'linea_convertida': convertir_linea_smt_reverso(row[0]),
                    'maquina': row[1],
                    'SlotNo': row[2], 
                    'FeederBase': row[3],
                    'PartName': row[4],
                    'ScanDate': row[5],
                    'fecha_subida': str(row[6]) if row[6] else None,
                    'side_norm': row[7]
                }
                for row in debug_data
            ]
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# ====== ENDPOINT PARA CREAR DATOS DE PRUEBA ======
@app.route('/api/crear-datos-prueba-smt', methods=['POST'])
@login_requerido  
def crear_datos_prueba_smt():
    """
    Endpoint para crear datos de prueba en la tabla historial_cambio_material_smt
    """
    try:
        from .db_mysql import get_connection
        import random
        from datetime import datetime, timedelta
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Datos de prueba para diferentes líneas
        datos_prueba = []
        
        lineas = ['1line', '2line', '3line', '4line']  # BD format
        maquinas = ['NPM-DX', 'NPM-DX2', 'NPM-W2', 'CHIP-MOUNTER']
        part_names = ['C1608X7R1H104K', 'R1005-10K', 'L1608-100nH', 'IC-SOT23-5']
        vendors = ['MURATA', 'ROHM', 'TDK', 'SAMSUNG']
        
        fecha_base = datetime.now()
        
        for i, linea in enumerate(lineas):
            for j, maquina in enumerate(maquinas[:2]):  # 2 máquinas por línea
                for slot in range(1, 11):  # 10 slots por máquina
                    for side in ['F', 'R']:  # Front y Rear
                        feeder_base = f"{slot:02d}{side}"
                        
                        # Crear registro con fecha aleatoria en los últimos 7 días
                        fecha_random = fecha_base - timedelta(
                            days=random.randint(0, 7),
                            hours=random.randint(0, 23),
                            minutes=random.randint(0, 59)
                        )
                        
                        datos_prueba.append({
                            'linea': linea,
                            'maquina': f"{maquina}-{i+1}",
                            'archivo': f"setup_{fecha_random.strftime('%Y%m%d_%H%M%S')}.csv",
                            'ScanDate': fecha_random.strftime('%Y-%m-%d'),
                            'ScanTime': fecha_random.strftime('%H:%M:%S'),
                            'SlotNo': slot,
                            'Result': 'OK',
                            'PartName': random.choice(part_names),
                            'Quantity': random.randint(500, 5000),
                            'Vendor': random.choice(vendors),
                            'FeederBase': feeder_base,
                            'fecha_subida': fecha_random
                        })
        
        # Insertar datos de prueba
        insert_query = """
            INSERT INTO historial_cambio_material_smt 
            (linea, maquina, archivo, ScanDate, ScanTime, SlotNo, Result, 
             PartName, Quantity, Vendor, FeederBase, fecha_subida)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        insertados = 0
        for dato in datos_prueba:
            try:
                cursor.execute(insert_query, (
                    dato['linea'], dato['maquina'], dato['archivo'],
                    dato['ScanDate'], dato['ScanTime'], dato['SlotNo'],
                    dato['Result'], dato['PartName'], dato['Quantity'],
                    dato['Vendor'], dato['FeederBase'], dato['fecha_subida']
                ))
                insertados += 1
            except Exception as e:
                # Si hay duplicados o errores, continuar
                print(f"Error insertando registro: {e}")
                continue
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'mensaje': f'Datos de prueba creados exitosamente',
            'registros_insertados': insertados,
            'total_intentos': len(datos_prueba),
            'lineas_creadas': ['SMT A (1line)', 'SMT B (2line)', 'SMT C (3line)', 'SMT D (4line)']
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# ====== HISTORIAL ICT (FRONT FULL DEFECTS 2) ======
def _ict_format_row(row):
    """Convertir campos fecha/hora a cadenas serializables."""
    if not row:
        return {}

    formatted = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            formatted[key] = value.isoformat(sep=' ')
        elif isinstance(value, date):
            formatted[key] = value.isoformat()
        elif isinstance(value, dt_time):
            formatted[key] = value.strftime('%H:%M:%S')
        elif isinstance(value, timedelta):
            formatted[key] = str(value)
        else:
            formatted[key] = value
    return formatted


@app.route('/historial-ict')
@app.route('/ict/front-full-defects2')
@login_requerido
def ict_front_full_defects2():
    """Vista principal del historial ICT con defectos detallados."""
    try:
        return render_template('Control de resultados/history_ict.html')
    except Exception as e:
        print(f"Error al cargar History ICT: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route('/api/ict/data')
@login_requerido
def ict_data_api():
    """Obtener registros recientes del historial ICT con filtros opcionales."""
    try:
        fecha = request.args.get('fecha', '').strip()
        linea = request.args.get('linea', '').strip()
        resultado = request.args.get('resultado', '').strip()
        barcode_like = request.args.get('barcode_like', '').strip()

        sql = (
            "SELECT fecha, TIME(ts) AS hora, linea, ict, resultado, no_parte, barcode, "
            "ts, fuente_archivo, defect_code, defect_valor "
            "FROM history_ict WHERE 1=1"
        )
        params = []

        if fecha:
            sql += " AND fecha=%s"
            params.append(fecha)
        if linea:
            sql += " AND linea=%s"
            params.append(linea)
        if resultado:
            sql += " AND resultado=%s"
            params.append(resultado)
        if barcode_like:
            sql += " AND barcode LIKE %s"
            params.append(f"%{barcode_like}%")

        sql += " ORDER BY ts DESC LIMIT 500"
        rows = execute_query(sql, tuple(params), fetch='all') or []

        return jsonify([_ict_format_row(row) for row in rows])
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/ict/defects')
@login_requerido
def ict_defects_api():
    """Obtener defectos asociados a un barcode espec��fico."""
    barcode = request.args.get("barcode", "").strip()
    if not barcode:
        return jsonify([])

    try:
        sql = (
            "SELECT d.barcode, h.linea, h.ict, d.componente, d.pinref, d.act_value, d.act_unit, "
            "d.std_value, d.std_unit, d.meas_value, "
            "d.m_value, d.r_value, d.hlim_pct, d.llim_pct, "
            "d.hp_value, d.lp_value, d.ws_value, d.ds_value, d.rc_value, "
            "d.p_flag, d.j_flag, d.resultado_local, d.defecto_tipo, d.ts "
            "FROM history_ict_defects d "
            "LEFT JOIN history_ict h ON d.barcode COLLATE utf8mb4_unicode_ci = h.barcode COLLATE utf8mb4_unicode_ci "
            "AND d.ts = h.ts "
            "WHERE d.barcode=%s "
            "ORDER BY d.ts DESC, d.componente LIMIT 1000"
        )

        rows = execute_query(sql, (barcode,), fetch='all') or []
        return jsonify([_ict_format_row(row) for row in rows])
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/ict/export')
@login_requerido
def export_ict_excel():
    """Exportar el historial ICT filtrado a un archivo de Excel."""
    try:
        fecha = request.args.get("fecha", "").strip()
        linea = request.args.get("linea", "").strip()
        resultado = request.args.get("resultado", "").strip()
        barcode_like = request.args.get("barcode_like", "").strip()

        sql = (
            "SELECT fecha, TIME(ts) AS hora, linea, ict, resultado, no_parte, barcode, "
            "fuente_archivo, defect_code, defect_valor "
            "FROM history_ict WHERE 1=1"
        )
        params = []

        if fecha:
            sql += " AND fecha=%s"
            params.append(fecha)
        if linea:
            sql += " AND linea=%s"
            params.append(linea)
        if resultado:
            sql += " AND resultado=%s"
            params.append(resultado)
        if barcode_like:
            sql += " AND barcode LIKE %s"
            params.append(f"%{barcode_like}%")

        sql += " ORDER BY ts DESC LIMIT 500"
        rows = execute_query(sql, tuple(params), fetch='all') or []

        from io import BytesIO
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        wb = Workbook()
        ws = wb.active
        ws.title = "Historial ICT"

        header_fill = PatternFill(start_color="3f6b6e", end_color="3f6b6e", fill_type="solid")
        cell_fill = PatternFill(start_color="a1a09c", end_color="a1a09c", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=10)
        border = Border(
            left=Side(style='thin', color='000000'),
            right=Side(style='thin', color='000000'),
            top=Side(style='thin', color='000000'),
            bottom=Side(style='thin', color='000000')
        )

        headers = ["Fecha", "Hora", "L��nea", "ICT", "Resultado", "No Parte", "Barcode", "Fuente", "Defect Code", "Defect Valor"]

        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = border

        for row_idx, row in enumerate(rows, start=2):
            formatted = _ict_format_row(row)
            values = [
                formatted.get('fecha', ''),
                formatted.get('hora', ''),
                formatted.get('linea', ''),
                formatted.get('ict', ''),
                formatted.get('resultado', ''),
                formatted.get('no_parte', ''),
                formatted.get('barcode', ''),
                formatted.get('fuente_archivo', ''),
                formatted.get('defect_code', ''),
                formatted.get('defect_valor', ''),
            ]

            for col_num, value in enumerate(values, start=1):
                cell = ws.cell(row=row_idx, column=col_num, value=value)
                cell.fill = cell_fill
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border

        for col in range(1, len(headers) + 1):
            column_letter = ws.cell(row=1, column=col).column_letter
            ws.column_dimensions[column_letter].width = 16

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f"historial_ict_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/ict/export-defects')
@login_requerido
def export_ict_defects_excel():
    """Exportar detalles de defectos ICT a un archivo de Excel."""
    barcode = request.args.get("barcode", "").strip()
    resultado_filter = request.args.get("resultado", "").strip()

    if not barcode:
        return jsonify({"error": "Barcode requerido"}), 400

    try:
        sql = (
            "SELECT d.barcode, h.linea, h.ict, d.componente, d.pinref, d.act_value, d.act_unit, "
            "d.std_value, d.std_unit, d.meas_value, "
            "d.m_value, d.r_value, d.hlim_pct, d.llim_pct, "
            "d.hp_value, d.lp_value, d.ws_value, d.ds_value, d.rc_value, "
            "d.p_flag, d.j_flag, d.resultado_local, d.defecto_tipo, d.ts, "
            "DATE(d.ts) AS fecha, TIME(d.ts) AS hora "
            "FROM history_ict_defects d "
            "LEFT JOIN history_ict h ON d.barcode COLLATE utf8mb4_unicode_ci = h.barcode COLLATE utf8mb4_unicode_ci "
            "AND d.ts = h.ts "
            "WHERE d.barcode=%s "
        )
        params = [barcode]

        if resultado_filter:
            sql += " AND d.resultado_local=%s"
            params.append(resultado_filter)

        sql += " ORDER BY d.ts DESC, d.componente LIMIT 1000"

        rows = execute_query(sql, tuple(params), fetch='all') or []

        from io import BytesIO
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        wb = Workbook()
        ws = wb.active
        ws.title = f"Parametros {barcode[:20]}"

        header_fill = PatternFill(start_color="3f6b6e", end_color="3f6b6e", fill_type="solid")
        cell_fill = PatternFill(start_color="a1a09c", end_color="a1a09c", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=10)
        border = Border(
            left=Side(style='thin', color='000000'),
            right=Side(style='thin', color='000000'),
            top=Side(style='thin', color='000000'),
            bottom=Side(style='thin', color='000000')
        )

        headers = [
            "Fecha", "Hora", "L��nea", "ICT", "Barcode", "Componente", "Pinref",
            "ACT", "Unit", "STD", "Unit", "MEAS", "M", "R", "HLIM", "LLIM",
            "H.P", "L.P", "WS", "DS", "RC", "P", "J", "Resultado", "Tipo Defecto"
        ]

        for col_num, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = border

        for row_idx, row in enumerate(rows, start=2):
            formatted = _ict_format_row(row)
            hlim = formatted.get('hlim_pct', '')
            llim = formatted.get('llim_pct', '')

            row_values = [
                formatted.get('fecha', ''),
                formatted.get('hora', ''),
                formatted.get('linea', ''),
                formatted.get('ict', ''),
                formatted.get('barcode', ''),
                formatted.get('componente', ''),
                formatted.get('pinref', ''),
                formatted.get('act_value', ''),
                formatted.get('act_unit', ''),
                formatted.get('std_value', ''),
                formatted.get('std_unit', ''),
                formatted.get('meas_value', ''),
                formatted.get('m_value', ''),
                formatted.get('r_value', ''),
                f"{hlim}%" if hlim else '',
                f"{llim}%" if llim else '',
                formatted.get('hp_value', ''),
                formatted.get('lp_value', ''),
                formatted.get('ws_value', ''),
                formatted.get('ds_value', ''),
                formatted.get('rc_value', ''),
                formatted.get('p_flag', ''),
                formatted.get('j_flag', ''),
                formatted.get('resultado_local', ''),
                formatted.get('defecto_tipo', '')
            ]

            for col_num, value in enumerate(row_values, start=1):
                cell = ws.cell(row=row_idx, column=col_num, value=value)
                cell.fill = cell_fill
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border

        for col in range(1, len(headers) + 1):
            column_letter = ws.cell(row=1, column=col).column_letter
            ws.column_dimensions[column_letter].width = 12

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f"parametros_{barcode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500



