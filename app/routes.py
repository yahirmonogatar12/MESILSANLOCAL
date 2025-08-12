import json
import os
import re
import traceback
import tempfile
import subprocess
import threading
import socket
import time
from functools import wraps
from flask import Flask, request, render_template, redirect, url_for, session, jsonify, send_file
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
    obtener_po_por_codigo, obtener_wo_por_codigo, listar_pos_por_estado, listar_wos_por_po
)

app = Flask(__name__)
app.secret_key = 'alguna_clave_secreta'  # Necesario para usar sesiones

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
            return redirect(url_for('login'))
        
        usuario = session.get('usuario')
        
        # Actualizar actividad de sesión
        auth_system._actualizar_actividad_sesion(usuario)
        
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
            
            # NUEVO: Redirigir usuarios administradores al panel de admin
            if user == "admin" or (isinstance(permisos, dict) and 'sistema' in permisos and 'usuarios' in permisos['sistema']):
                print(f"🔑 Usuario administrador detectado: {user}, redirigiendo al panel admin")
                return redirect('/admin/panel')
            
            # Redirigir según el usuario (lógica original para usuarios operacionales)
            elif user.startswith("Materiales") or user == "1111":
                return redirect(url_for('material'))
            elif user.startswith("Produccion") or user == "2222":
                return redirect(url_for('produccion'))
            elif user.startswith("DDESARROLLO") or user == "3333":
                return redirect(url_for('desarrollo'))
            else:
                # Usuario nuevo - redirigir al material por defecto
                return redirect(url_for('material'))
        
        # FALLBACK: Intentar con el sistema antiguo (usuarios.json)
        try:
            usuarios_json = cargar_usuarios()
            if user in usuarios_json and usuarios_json[user] == pw:
                print(f" Login exitoso con sistema JSON (fallback): {user}")
                session['usuario'] = user
                
                # Registrar auditoría del fallback
                auth_system.registrar_auditoria(
                    usuario=user,
                    modulo='sistema', 
                    accion='login_json',
                    descripcion='Inicio de sesión con sistema JSON (fallback)',
                    resultado='EXITOSO'
                )
                
                # Redirigir según el usuario (lógica original)
                if user.startswith("Materiales") or user == "1111":
                    return redirect(url_for('material'))
                elif user.startswith("Produccion") or user == "2222":
                    return redirect(url_for('produccion'))
                elif user.startswith("DDESARROLLO") or user == "3333":
                    return redirect(url_for('desarrollo'))
        except Exception as e:
            print(f" Error en fallback JSON: {e}")
        
        # Si llega aquí, login falló
        print(f"❌ Login fallido: {user}")
        auth_system.registrar_auditoria(
            usuario=user,
            modulo='sistema',
            accion='login_failed',
            descripcion='Intento de login fallido - credenciales incorrectas',
            resultado='ERROR'
        )
        
        return render_template('login.html', error="Usuario o contraseña incorrectos. Por favor, intente de nuevo")
    
    return render_template('login.html')

@app.route('/ILSAN-ELECTRONICS')
@login_requerido
def material():
    usuario = session.get('usuario', 'Invitado')
    permisos = session.get('permisos', {})
    
    # Verificar si tiene permisos de administración de usuarios
    tiene_permisos_usuarios = False
    if isinstance(permisos, dict) and 'sistema' in permisos:
        tiene_permisos_usuarios = 'usuarios' in permisos['sistema']
    
    return render_template('MaterialTemplate.html', 
                        usuario=usuario, 
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
    
    return redirect(url_for('login'))

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
    Lista los registros de BOM, opcionalmente filtrados por modelo
    """
    try:
        data = request.get_json()
        modelo = data.get('modelo', 'todos') if data else 'todos'
        
        bom_data = listar_bom_por_modelo(modelo)
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

@app.route('/exportar_excel_bom', methods=['GET'])
@login_requerido
def exportar_excel_bom():
    """
    Exporta datos de BOM a un archivo Excel, filtrados por modelo si se especifica
    """
    try:
        # Obtener el modelo del parámetro de consulta
        modelo = request.args.get('modelo', None)
        
        if modelo and modelo.strip() and modelo != 'todos':
            # Exportar solo el modelo específico
            archivo_temp = exportar_bom_a_excel(modelo)
            download_name = f'bom_export_{modelo}_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        else:
            # Exportar todos los datos (comportamiento anterior)
            archivo_temp = exportar_bom_a_excel()
            download_name = f'bom_export_todos_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
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
        
        print(f"🔍 Consultando detalles de lotes para número de parte: {numero_parte}")
        
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
                    cma.codigo_material_recibido,
                    cma.numero_lote_material,
                    cma.cantidad_actual,
                    COALESCE(salidas_lote.total_salidas, 0) as total_salidas,
                    (cma.cantidad_actual - COALESCE(salidas_lote.total_salidas, 0)) as cantidad_disponible,
                    cma.fecha_recibo,
                    cma.fecha_fabricacion,
                    cma.especificacion,
                    cma.propiedad_material,
                    cma.ubicacion_salida,
                    cma.codigo_material,
                    cma.codigo_material_original
                FROM control_material_almacen cma
                LEFT JOIN (
                    SELECT 
                        cms.codigo_material_recibido,
                        SUM(cms.cantidad_salida) as total_salidas
                    FROM control_material_salida cms
                    GROUP BY cms.codigo_material_recibido
                ) salidas_lote ON cma.codigo_material_recibido = salidas_lote.codigo_material_recibido
                WHERE cma.numero_parte = %s 
                  AND (cma.cantidad_actual - COALESCE(salidas_lote.total_salidas, 0)) > 0
                ORDER BY cma.fecha_recibo DESC
            '''
            print(f"🔍 Ejecutando consulta de lotes con parámetro: {numero_parte}")
            cursor.execute(query, [numero_parte])
        else:
            # Fallback para SQLite (aunque no lo usamos)
            return jsonify({
                'success': False,
                'error': 'Solo MySQL soportado'
            }), 500
        rows = cursor.fetchall()
        print(f"🔍 Filas obtenidas de la consulta: {len(rows)}")
        
        lotes_detalle = []
        for i, row in enumerate(rows):
            try:
                print(f"🔍 Procesando fila {i+1}: {row['codigo_material_recibido']}...")
                lote_data = {
                    'codigo_material_recibido': row['codigo_material_recibido'],
                    'numero_lote': row['numero_lote_material'],
                    'cantidad_original': float(row['cantidad_actual']) if row['cantidad_actual'] else 0.0,
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
        print("Iniciando exportación de Excel...")
        conn = get_db_connection()
        
        # Obtener todos los materiales
        materiales = conn.execute('''
            SELECT codigo_material, numero_parte, propiedad_material, classification, 
                   especificacion_material, unidad_empaque, ubicacion_material, vendedor, 
                   prohibido_sacar, reparable, nivel_msl, espesor_msl, fecha_registro
            FROM materiales
            ORDER BY fecha_registro DESC
        ''').fetchall()
        
        conn.close()
        print(f"Se encontraron {len(materiales)} materiales")
        
        if not materiales:
            # Crear un DataFrame vacío con headers
            df = pd.DataFrame(columns=[
                'Código de material', 'Número de parte', 'Propiedad de material', 
                'Classification', 'Especificación de material', 'Unidad de empaque', 
                'Ubicación de material', 'Vendedor', 'Prohibido sacar', 'Reparable', 
                'Nivel de MSL', 'Espesor de MSL', 'Fecha de registro'
            ])
            print("Creando Excel con datos vacíos")
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
        from datetime import datetime
        fecha_actual = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
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
            # TODO: Implementar actualización de inventario general si es necesario
            # Por ahora comentamos esta función que no existe
            # numero_parte = data.get('numero_parte', '').strip()
            # cantidad_actual = float(data.get('cantidad_actual', 0))
            # codigo_material = data.get('codigo_material', '')
            # propiedad_material = data.get('propiedad_material', '')
            # especificacion = data.get('especificacion', '')
            
            # if numero_parte and cantidad_actual > 0:
            #     actualizar_inventario_general_entrada(
            #         numero_parte, codigo_material, propiedad_material, 
            #         especificacion, cantidad_actual
            #     )
            #     print(f"📦 Inventario general actualizado: +{cantidad_actual} para {numero_parte}")
            
            return jsonify({
                'success': True, 
                'message': 'Registro guardado exitosamente'
            })
        else:
            return jsonify({'success': False, 'error': 'Error al guardar en la base de datos'}), 500
        
    except Exception as e:
        print(f"Error al guardar control de almacén: {str(e)}")
        return jsonify({'success': False, 'error': f'Error al guardar: {str(e)}'}), 500

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
    Formato correcto: CODIGO_MATERIAL,YYYYMMDD0001 (donde 0001 incrementa por cada registro del mismo código y fecha)
    
    Ejemplos:
    - OCH1223K678,202507080001 (primer registro del día)
    - OCH1223K678,202507080002 (segundo registro del día)  
    - OCH1223K678,202507080003 (tercer registro del día)
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
        
        # Obtener la fecha actual en formato YYYYMMDD
        from datetime import datetime
        fecha_actual = datetime.now().strftime('%Y%m%d')
        
        print(f"🔍 Buscando secuenciales para código: '{codigo_material}' y fecha: {fecha_actual}")
        
        # Buscar registros específicos para este código de material y fecha exacta
        # El formato buscado es: CODIGO_MATERIAL,YYYYMMDD0001 en el campo codigo_material_recibido
        query = """
        SELECT codigo_material_recibido, fecha_registro
        FROM control_material_almacen 
        WHERE codigo_material_recibido LIKE %s
        ORDER BY fecha_registro DESC
        """
        
        # Patrón de búsqueda: CODIGO,YYYYMMDD seguido de 4 dígitos (CORRECTO: con coma)
        patron_busqueda = f"{codigo_material},{fecha_actual}%"
        
        cursor.execute(query, (patron_busqueda,))
        resultados = cursor.fetchall()
        
        print(f"🔍 Encontrados {len(resultados)} registros para el patrón '{patron_busqueda}'")
        
        # Buscar el secuencial más alto para este código de material y fecha específica
        secuencial_mas_alto = 0
        patron_regex = rf'^{re.escape(codigo_material)},{fecha_actual}(\d{{4}})$'
        
        for resultado in resultados:
            codigo_recibido = resultado['codigo_material_recibido'] or ''
            
            print(f" Analizando: codigo_material_recibido='{codigo_recibido}'")
            
            # Buscar patrón exacto: CODIGO_MATERIAL,YYYYMMDD0001
            match = re.match(patron_regex, codigo_recibido)
            
            if match:
                secuencial_encontrado = int(match.group(1))
                print(f"� Secuencial encontrado: {secuencial_encontrado}")
                
                if secuencial_encontrado > secuencial_mas_alto:
                    secuencial_mas_alto = secuencial_encontrado
                    print(f"📊 Nuevo secuencial más alto: {secuencial_mas_alto}")
            else:
                print(f" No coincide con patrón esperado: {codigo_recibido}")
        
        siguiente_secuencial = secuencial_mas_alto + 1
        
        # Generar el próximo código de material recibido completo
        siguiente_codigo_completo = f"{codigo_material},{fecha_actual}{siguiente_secuencial:04d}"
        
        print(f" Siguiente secuencial: {siguiente_secuencial}")
        print(f" Próximo código completo: {siguiente_codigo_completo}")
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'siguiente_secuencial': siguiente_secuencial,
            'fecha_actual': fecha_actual,
            'codigo_material': codigo_material,
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
        return render_template('Control de produccion/Control de embarquehtml')
    except Exception as e:
        print(f"Error al cargar template Control de embarque AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control_produccion/crear_plan')
@login_requerido
def crear_plan_produccion():
    """Cargar la página de Crear Plan de Producción"""
    try:
        return render_template('Control de produccion/Crear plan de produccion.html')
    except Exception as e:
        print(f"Error al cargar Crear Plan de Producción: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control_proceso/control_produccion_smt')
@login_requerido
def control_produccion_smt_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de produccion SMT"""
    try:
        return render_template('Control de proceso/Control de produccion SMT.html')
    except Exception as e:
        print(f"Error al cargar template Control de produccion SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route('/control_proceso/control_operacion_linea_smt')
@login_requerido
def control_operacion_linea_smt_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de operacion de linea SMT"""
    try:
        return render_template('Control de proceso/control_operacion_linea_smt_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Control de operacion de linea SMT AJAX: {e}")
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
        
        # Consultar la fila original
        cursor.execute('SELECT cantidad_actual FROM control_material_almacen WHERE codigo_material_recibido = %s', (codigo_material_recibido,))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({'success': False, 'error': 'Código no encontrado en almacén'})
        
        cantidad_actual = float(row[0]) if row[0] else 0
        cantidad_salida = float(cantidad_salida)
        
        if cantidad_salida > cantidad_actual:
            return jsonify({'success': False, 'error': f'Cantidad de salida ({cantidad_salida}) mayor a la disponible ({cantidad_actual})'})
        
        nueva_cantidad = cantidad_actual - cantidad_salida
        
        # Actualizar la cantidad en almacen
        cursor.execute('UPDATE control_material SET cantidad_actual = %s WHERE codigo_material_recibido = %s', 
                      (nueva_cantidad, codigo_material_recibido))
        
        # Registrar la salida en control_material_salida
        cursor.execute('''
            INSERT INTO control_material_salida (
                codigo_material_recibido, numero_lote, modelo, depto_salida, 
                proceso_salida, cantidad_salida, fecha_salida, especificacion_material
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            codigo_material_recibido,
            data.get('numero_lote', ''),
            data.get('modelo', ''),
            data.get('depto_salida', ''),
            data.get('proceso_salida', ''),
            cantidad_salida,
            data.get('fecha_salida', ''),
            data.get('especificacion_material', '')
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
        
        print(f"� SQL Query ULTRA-OPTIMIZADO: {query}")
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
            'fecha_salida': data.get('fecha_salida', ''),
            'especificacion_material': data.get('especificacion_material', '')
        }
        
        # Registrar la salida usando MySQL
        if not registrar_salida_material_mysql(salida_data):
            return jsonify({'success': False, 'error': 'Error al registrar la salida en la base de datos'}), 500
        
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
            SELECT SUM(cantidad_recibida) as total_entradas
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
    """Endpoint para recalcular todo el inventario general desde cero"""
    try:
        resultado = recalcular_inventario_general()
        
        if resultado:
            return jsonify({
                'success': True,
                'message': 'Inventario general recalculado exitosamente'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Error al recalcular inventario general'
            }), 500
            
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
        inventario = obtener_inventario_general()
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
            print(f"📊 ZEBRA LOG: {datetime.now()} - Usuario: {session.get('usuario')} - Código: {codigo} - IP: {ip_impresora}")
            
            return jsonify({
                'success': True,
                'message': f'Etiqueta enviada a impresora Zebra {ip_impresora}',
                'metodo': 'red',
                'codigo': codigo,
                'timestamp': datetime.now().isoformat()
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
        timestamp = datetime.now().isoformat()
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
        
        print(f"🔍 Consultando inventario consolidado con filtros: {filtros}")
        
        # Usar específicamente la conexión MySQL del hosting
        from .config_mysql import get_mysql_connection
        
        conn = get_mysql_connection()
        using_mysql = True
        print(f"🗄️ Usando MySQL: {using_mysql}")
        
        if conn is None:
            print("❌ No se pudo obtener conexión a MySQL")
            return jsonify({
                'success': False,
                'error': 'No se pudo conectar a la base de datos MySQL'
            }), 500
            
        cursor = conn.cursor()
        
        # Verificar que la tabla inventario_consolidado existe en MySQL
        try:
            cursor.execute("SHOW TABLES LIKE 'inventario_consolidado'")
            
            if not cursor.fetchone():
                print("❌ Tabla inventario_consolidado no existe en MySQL")
                return jsonify({
                    'success': False,
                    'error': 'Tabla inventario_consolidado no encontrada en MySQL'
                }), 500
                print(" Tabla inventario_consolidado encontrada en MySQL")
        except Exception as table_error:
            print(f"❌ Error verificando tablas en MySQL: {table_error}")
            return jsonify({
                'success': False,
                'error': f'Error verificando tablas: {str(table_error)}'
            }), 500
        
        print(" Tabla inventario_consolidado verificada en MySQL")
        
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
        
        print(f"🔍 Ejecutando consulta optimizada: {query}")
        print(f"🔍 Con parámetros: {params}")
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        print(f"🔍 Filas obtenidas: {len(rows) if rows else 0}")
        
        inventario = []
        for i, row in enumerate(rows):
            try:
                print(f"🔍 Procesando fila {i}: {row}")
                
                # Verificar si row es un diccionario o una tupla
                if hasattr(row, 'keys'):  # Es un diccionario
                    cantidad_total = float(row.get('cantidad_total', 0)) if row.get('cantidad_total') else 0.0
                    numero_parte = row.get('numero_parte', '')
                    total_entradas = float(row.get('total_entradas', 0)) if row.get('total_entradas') else 0.0
                    total_salidas = float(row.get('total_salidas', 0)) if row.get('total_salidas') else 0.0
                    total_lotes = int(row.get('total_lotes', 0)) if row.get('total_lotes') else 0
                    codigo_material = row.get('codigo_material', '') or numero_parte
                    especificacion = row.get('especificacion', '') or ''
                    propiedad_material = row.get('propiedad_material', '') or 'COMMON USE'
                    fecha_ultimo_recibo = row.get('fecha_ultimo_recibo')
                    fecha_primer_recibo = row.get('fecha_primer_recibo')
                else:  # Es una tupla - procesar por índices
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
                print(f"❌ Error procesando fila {i}: {row_error}")
                print(f"❌ Datos de la fila: {row}")
                continue
        
        print(f" Inventario consultado: {len(inventario)} números de parte encontrados")
        
        return jsonify({
            'success': True,
            'inventario': inventario,
            'total': len(inventario),
            'filtros_aplicados': filtros,
            'modo': 'agrupado_por_numero_parte'
        })
        
    except Exception as e:
        print(f"❌ Error al consultar inventario general: {e}")
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
        
        print(f"🔍 Consultando historial para número de parte: {numero_parte}")
        
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
        
        # Obtener todas las salidas usando JOIN con control_material_almacen para obtener numero_parte
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
            return jsonify({'permisos': {}, 'error': 'Usuario no encontrado o sin roles'}), 404
        
        rol_nombre = usuario_rol[0]
        
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
        
        for pagina, seccion, boton in permisos:
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
            'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
            'port': 11550,
            'user': 'db_rrpq0erbdujn',
            'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
            'database': 'db_rrpq0erbdujn',
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
        
        print(f"� Encontrados {len(resultados)} registros en MySQL")
        
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
            'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
            'port': 11550,
            'user': 'db_rrpq0erbdujn',
            'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
            'database': 'db_rrpq0erbdujn',
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
            'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
            'port': 11550,
            'user': 'db_rrpq0erbdujn',
            'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
            'database': 'db_rrpq0erbdujn',
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
                'diferencia': cantidad_actual - cantidad_requerida,
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
                     propiedad_material, fecha_recibo, cantidad_recibida, ubicacion)
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
                     cantidad_recibida, proveedor, estado_recepcion)
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
            os.remove(temp_path)@app.route('/api/historial_smt_data')
def api_historial_smt_data():
    """
    API endpoint para obtener datos del historial de cambio de material SMT
    Consulta la tabla historial_cambio_material_smt en MySQL
    """
    try:
        # Obtener parámetros de filtro opcionales
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin') 
        carpeta = request.args.get('carpeta')
        barcode = request.args.get('barcode')
        part_name = request.args.get('part_name')
        
        # Importar la conexión MySQL directamente
        import mysql.connector
        
        # Configuración de conexión MySQL (misma que en SMTMonitorService)
        mysql_config = {
            'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
            'port': 11550,
            'user': 'db_rrpq0erbdujn',
            'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
            'database': 'db_rrpq0erbdujn',
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci'
        }
        
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor(dictionary=True)
        
        # Construir query base
        query = """
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
        WHERE 1=1
        """
        
        params = []
        
        # Agregar filtros si se proporcionan
        if fecha_inicio:
            query += " AND ScanDate >= %s"
            params.append(fecha_inicio)
            
        if fecha_fin:
            query += " AND ScanDate <= %s"
            params.append(fecha_fin)
            
        if carpeta:
            query += " AND source_file LIKE %s"
            params.append(f"%{carpeta}%")
            
        if barcode:
            query += " AND barcode LIKE %s"
            params.append(f"%{barcode}%")
            
        if part_name:
            query += " AND part_name LIKE %s"
            params.append(f"%{part_name}%")
        
        # Ordenar por fecha más reciente primero
        query += " ORDER BY ScanDate DESC, ScanTime DESC LIMIT 1000"
        
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        
        # Convertir datos para JSON (manejar fechas y decimales)
        for resultado in resultados:
            for key, value in resultado.items():
                if hasattr(value, 'isoformat'):  # Es una fecha/datetime
                    resultado[key] = value.isoformat()
                elif isinstance(value, (int, float)):
                    resultado[key] = value
                elif value is None:
                    resultado[key] = ''
                else:
                    resultado[key] = str(value)
        
        return jsonify({
            'success': True,
            'data': resultados,
            'total': len(resultados)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al consultar datos SMT: {str(e)}'
        }), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# =====================================================
# SISTEMA PO → WO - RUTAS DE API REST
# =====================================================

from .db_mysql import execute_query
from datetime import datetime, date

# --- PURCHASE ORDERS (PO) ---

@app.route('/api/po/crear', methods=['POST'])
@login_requerido
def crear_po():
    """Crear nueva Purchase Order (PO)"""
    try:
        data = request.get_json()
        
        # Validar campos obligatorios
        if not data.get('cliente') and not data.get('proveedor'):
            return jsonify({
                'success': False,
                'error': 'El campo cliente o proveedor es obligatorio'
            }), 400
        
        # Generar código PO único
        codigo_po = generar_codigo_po()
        if not codigo_po:
            return jsonify({
                'success': False,
                'error': 'Error generando código PO'
            }), 500
        
        # Validar código generado
        valido, mensaje = validar_codigo_po(codigo_po)
        if not valido:
            return jsonify({
                'success': False,
                'error': f'Código PO inválido: {mensaje}'
            }), 400
        
        # Verificar que no exista duplicado (doble verificación)
        if verificar_po_existe(codigo_po):
            return jsonify({
                'success': False,
                'error': 'El código PO ya existe'
            }), 409
        
        # Generar código de entrega automáticamente
        codigo_entrega = f"{codigo_po}-01"
        
        # Insertar nueva PO con todos los campos
        usuario = session.get('username', 'sistema')
        query = """
        INSERT INTO embarques (
            codigo_po, cliente, fecha_registro, estado, usuario_creacion,
            nombre_po, modelo, proveedor, total_cantidad_entregada, 
            codigo_entrega, fecha_entrega, cantidad_entregada
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Preparar datos
        cliente = data.get('cliente') or data.get('proveedor')  # Usar proveedor como cliente si no hay cliente
        fecha_registro = data.get('fecha_registro') or date.today()
        estado = data.get('estado', 'PLAN')
        nombre_po = data.get('nombre_po', '')
        modelo = data.get('modelo', '')
        proveedor = data.get('proveedor', '')
        total_cantidad_entregada = data.get('total_cantidad_entregada', 0)
        fecha_entrega = data.get('fecha_entrega')
        cantidad_entregada = data.get('cantidad_entregada', 0)
        
        # Convertir fecha_entrega a objeto date si es string
        if isinstance(fecha_entrega, str):
            try:
                fecha_entrega = datetime.strptime(fecha_entrega, '%Y-%m-%d').date()
            except:
                fecha_entrega = None
        
        execute_query(query, (
            codigo_po, cliente, fecha_registro, estado, usuario,
            nombre_po, modelo, proveedor, total_cantidad_entregada,
            codigo_entrega, fecha_entrega, cantidad_entregada
        ))
        
        # Obtener PO creada
        po_creada = obtener_po_por_codigo(codigo_po)
        
        return jsonify({
            'success': True,
            'message': 'PO creada exitosamente',
            'data': po_creada
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error creando PO: {str(e)}'
        }), 500

@app.route('/api/po/<codigo_po>', methods=['GET'])
@login_requerido
def obtener_po(codigo_po):
    """Obtener información de una PO específica"""
    try:
        # Validar formato del código
        valido, mensaje = validar_codigo_po(codigo_po)
        if not valido:
            return jsonify({
                'success': False,
                'error': f'Código PO inválido: {mensaje}'
            }), 400
        
        po = obtener_po_por_codigo(codigo_po)
        if not po:
            return jsonify({
                'success': False,
                'error': 'PO no encontrada'
            }), 404
        
        return jsonify({
            'success': True,
            'data': po
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error obteniendo PO: {str(e)}'
        }), 500

@app.route('/api/po/<codigo_po>/estado', methods=['PUT'])
@login_requerido
def actualizar_estado_po(codigo_po):
    """Actualizar estado de una PO"""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        # Validar estado
        estados_validos = ['PLAN', 'PREPARACION', 'EMBARCADO', 'EN_TRANSITO', 'ENTREGADO']
        if nuevo_estado not in estados_validos:
            return jsonify({
                'success': False,
                'error': f'Estado inválido. Debe ser uno de: {", ".join(estados_validos)}'
            }), 400
        
        # Verificar que la PO existe
        if not verificar_po_existe(codigo_po):
            return jsonify({
                'success': False,
                'error': 'PO no encontrada'
            }), 404
        
        # Actualizar estado
        query = "UPDATE embarques SET estado = %s WHERE codigo_po = %s"
        execute_query(query, (nuevo_estado, codigo_po))
        
        # Obtener PO actualizada
        po_actualizada = obtener_po_por_codigo(codigo_po)
        
        return jsonify({
            'success': True,
            'message': 'Estado de PO actualizado exitosamente',
            'data': po_actualizada
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error actualizando estado de PO: {str(e)}'
        }), 500

@app.route('/api/po/listar', methods=['GET'])
@login_requerido
def listar_pos():
    """Listar todas las POs con filtros opcionales"""
    try:
        estado = request.args.get('estado')
        pos = listar_pos_por_estado(estado)
        
        return jsonify({
            'success': True,
            'data': pos,
            'total': len(pos)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error listando POs: {str(e)}'
        }), 500

# --- WORK ORDERS (WO) ---

@app.route('/api/wo/crear', methods=['POST'])
@login_requerido
def crear_wo():
    """Crear nueva Work Order (WO)"""
    try:
        data = request.get_json()
        
        # Validar campos obligatorios
        campos_requeridos = ['codigo_po', 'modelo', 'cantidad_planeada', 'fecha_operacion']
        for campo in campos_requeridos:
            if not data.get(campo):
                return jsonify({
                    'success': False,
                    'error': f'El campo {campo} es obligatorio'
                }), 400
        
        # Usar código WO proporcionado o generar uno nuevo
        codigo_wo = data.get('codigo_wo')
        if not codigo_wo:
            # Generar código WO único si no se proporciona
            codigo_wo = generar_codigo_wo()
        
        # Obtener otros campos
        codigo_po = data['codigo_po']
        orden_proceso = data.get('orden_proceso', 'NORMAL')
        
        # Validar cantidad
        cantidad = data['cantidad_planeada']
        if not isinstance(cantidad, int) or cantidad <= 0:
            return jsonify({
                'success': False,
                'error': 'La cantidad planeada debe ser un número entero positivo'
            }), 400
        
        # Validar código
        if not codigo_wo:
            return jsonify({
                'success': False,
                'error': 'Error generando código WO'
            }), 500
        
        # Validar código generado
        valido, mensaje = validar_codigo_wo(codigo_wo)
        if not valido:
            return jsonify({
                'success': False,
                'error': f'Código WO inválido: {mensaje}'
            }), 400
        
        # Verificar que no exista duplicado
        if verificar_wo_existe(codigo_wo):
            return jsonify({
                'success': False,
                'error': 'El código WO ya existe'
            }), 409
        
        # Insertar nueva WO
        usuario = session.get('username', 'sistema')
        query = """
        INSERT INTO work_orders (codigo_wo, codigo_po, modelo, orden_proceso, cantidad_planeada, 
                               fecha_operacion, modificador, estado, usuario_creacion)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        estado = data.get('estado', 'CREADA')
        
        execute_query(query, (
            codigo_wo, codigo_po, data['modelo'], orden_proceso, cantidad,
            data['fecha_operacion'], usuario, estado, usuario
        ))
        
        # Obtener WO creada
        wo_creada = obtener_wo_por_codigo(codigo_wo)
        
        return jsonify({
            'success': True,
            'message': 'WO creada exitosamente',
            'data': wo_creada
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error creando WO: {str(e)}'
        }), 500

@app.route('/api/wo/<codigo_wo>', methods=['GET'])
@login_requerido
def obtener_wo(codigo_wo):
    """Obtener información de una WO específica"""
    try:
        # Validar formato del código
        valido, mensaje = validar_codigo_wo(codigo_wo)
        if not valido:
            return jsonify({
                'success': False,
                'error': f'Código WO inválido: {mensaje}'
            }), 400
        
        wo = obtener_wo_por_codigo(codigo_wo)
        if not wo:
            return jsonify({
                'success': False,
                'error': 'WO no encontrada'
            }), 404
        
        return jsonify({
            'success': True,
            'data': wo
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error obteniendo WO: {str(e)}'
        }), 500

@app.route('/api/wo/<codigo_wo>/estado', methods=['PUT'])
@login_requerido
def actualizar_estado_wo(codigo_wo):
    """Actualizar estado de una WO"""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        # Validar estado
        estados_validos = ['CREADA', 'PLANIFICADA', 'EN_PRODUCCION', 'CERRADA']
        if nuevo_estado not in estados_validos:
            return jsonify({
                'success': False,
                'error': f'Estado inválido. Debe ser uno de: {", ".join(estados_validos)}'
            }), 400
        
        # Verificar que la WO existe
        if not verificar_wo_existe(codigo_wo):
            return jsonify({
                'success': False,
                'error': 'WO no encontrada'
            }), 404
        
        # Actualizar estado
        usuario = session.get('username', 'sistema')
        query = "UPDATE work_orders SET estado = %s, modificador = %s WHERE codigo_wo = %s"
        execute_query(query, (nuevo_estado, usuario, codigo_wo))
        
        # Obtener WO actualizada
        wo_actualizada = obtener_wo_por_codigo(codigo_wo)
        
        return jsonify({
            'success': True,
            'message': 'Estado de WO actualizado exitosamente',
            'data': wo_actualizada
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error actualizando estado de WO: {str(e)}'
        }), 500

@app.route('/api/wo/listar', methods=['GET'])
@login_requerido
def listar_wos():
    """Listar todas las WOs con filtros opcionales"""
    try:
        codigo_po = request.args.get('codigo_po')
        wos = listar_wos_por_po(codigo_po)
        
        return jsonify({
            'success': True,
            'data': wos,
            'total': len(wos)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error listando WOs: {str(e)}'
        }), 500

@app.route('/api/bom/modelos', methods=['GET'])
@login_requerido
def obtener_modelos_bom_api():
    """Obtener lista de modelos únicos de la tabla BOM"""
    try:
        from .po_wo_models import obtener_modelos_unicos_bom
        modelos = obtener_modelos_unicos_bom()
        
        return jsonify({
            'success': True,
            'data': modelos,
            'total': len(modelos)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error obteniendo modelos BOM: {str(e)}'
        }), 500

# --- RUTAS DE CONVERSIÓN PO → WO ---

@app.route('/api/po/<codigo_po>/convertir-wo', methods=['POST'])
@login_requerido
def convertir_po_a_wo(codigo_po):
    """Convertir una PO en WO automáticamente"""
    try:
        data = request.get_json() or {}
        
        # Verificar que la PO existe
        po = obtener_po_por_codigo(codigo_po)
        if not po:
            return jsonify({
                'success': False,
                'error': 'PO no encontrada'
            }), 404
        
        # Validar campos requeridos para WO
        if not data.get('modelo'):
            return jsonify({
                'success': False,
                'error': 'El campo modelo es obligatorio para crear WO'
            }), 400
        
        if not data.get('cantidad_planeada'):
            return jsonify({
                'success': False,
                'error': 'El campo cantidad_planeada es obligatorio para crear WO'
            }), 400
        
        # Usar fecha actual si no se especifica
        fecha_operacion = data.get('fecha_operacion', date.today().isoformat())
        
        # Crear WO usando el endpoint interno
        wo_data = {
            'codigo_po': codigo_po,
            'modelo': data['modelo'],
            'cantidad_planeada': data['cantidad_planeada'],
            'fecha_operacion': fecha_operacion,
            'estado': data.get('estado', 'CREADA')
        }
        
        # Generar código WO
        codigo_wo = generar_codigo_wo()
        if not codigo_wo:
            return jsonify({
                'success': False,
                'error': 'Error generando código WO'
            }), 500
        
        # Insertar WO
        usuario = session.get('username', 'sistema')
        query = """
        INSERT INTO work_orders (codigo_wo, codigo_po, modelo, cantidad_planeada, 
                               fecha_operacion, modificador, estado, usuario_creacion)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        execute_query(query, (
            codigo_wo, codigo_po, wo_data['modelo'], wo_data['cantidad_planeada'],
            wo_data['fecha_operacion'], usuario, wo_data['estado'], usuario
        ))
        
        # Obtener WO creada
        wo_creada = obtener_wo_por_codigo(codigo_wo)
        
        return jsonify({
            'success': True,
            'message': f'PO {codigo_po} convertida exitosamente a WO {codigo_wo}',
            'data': {
                'po': po,
                'wo': wo_creada
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error convirtiendo PO a WO: {str(e)}'
        }), 500

# --- RUTAS DE VALIDACIÓN Y VERIFICACIÓN ---

@app.route('/api/validar/codigo-po/<codigo_po>', methods=['GET'])
@login_requerido
def validar_codigo_po_endpoint(codigo_po):
    """Validar formato y existencia de código PO"""
    try:
        # Validar formato
        valido, mensaje = validar_codigo_po(codigo_po)
        if not valido:
            return jsonify({
                'success': False,
                'valido': False,
                'mensaje': mensaje
            })
        
        # Verificar existencia
        existe = verificar_po_existe(codigo_po)
        
        return jsonify({
            'success': True,
            'valido': True,
            'existe': existe,
            'mensaje': 'Código válido' if not existe else 'Código válido pero ya existe'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error validando código PO: {str(e)}'
        }), 500

@app.route('/api/validar/codigo-wo/<codigo_wo>', methods=['GET'])
@login_requerido
def validar_codigo_wo_endpoint(codigo_wo):
    """Validar formato y existencia de código WO"""
    try:
        # Validar formato
        valido, mensaje = validar_codigo_wo(codigo_wo)
        if not valido:
            return jsonify({
                'success': False,
                'valido': False,
                'mensaje': mensaje
            })
        
        # Verificar existencia
        existe = verificar_wo_existe(codigo_wo)
        
        return jsonify({
            'success': True,
            'valido': True,
            'existe': existe,
            'mensaje': 'Código válido' if not existe else 'Código válido pero ya existe'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error validando código WO: {str(e)}'
        }), 500

@app.route('/api/wo/exportar', methods=['GET'])
@login_requerido
def exportar_wos_excel():
    """Exportar WOs a Excel"""
    try:
        import io
        from openpyxl import Workbook
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
        
        # Definir encabezados
        headers = [
            'Código WO', 'Fecha Operación', 'Código Modelo', 'Nombre Modelo',
            'Orden Proceso', 'Cantidad Planeada', 'Código PO', 'Registrado',
            'Modificador', 'Fecha Modificación', 'Fecha Creación'
        ]
        
        # Escribir encabezados
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)
        
        # Escribir datos
        for row, wo in enumerate(wos, 2):
            ws.cell(row=row, column=1, value=wo.get('codigo_wo', ''))
            ws.cell(row=row, column=2, value=wo.get('fecha_operacion', ''))
            ws.cell(row=row, column=3, value=wo.get('codigo_modelo', ''))
            ws.cell(row=row, column=4, value=wo.get('nombre_modelo', ''))
            ws.cell(row=row, column=5, value=wo.get('orden_proceso', ''))
            ws.cell(row=row, column=6, value=wo.get('cantidad_planeada', 0))
            ws.cell(row=row, column=7, value=wo.get('codigo_po', ''))
            ws.cell(row=row, column=8, value='Sí' if wo.get('registrado') else 'No')
            ws.cell(row=row, column=9, value=wo.get('modificador', ''))
            ws.cell(row=row, column=10, value=wo.get('fecha_modificacion', ''))
            ws.cell(row=row, column=11, value=wo.get('fecha_creacion', ''))
        
        # Ajustar ancho de columnas
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
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
        return jsonify({
            'success': False,
            'error': f'Error exportando WOs: {str(e)}'
        }), 500

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

        print(f"DEBUG: desde={desde}, hasta={hasta}, q={q}, tipo={tipo}")

        where_conditions = []
        params = []
        
        # Filtros de fecha simplificados - usar directamente el campo fecha
        if desde:
            where_conditions.append("fecha >= %s")
            params.append(desde)
            print(f"DEBUG: Agregando filtro desde: {desde}")
        if hasta:
            where_conditions.append("fecha <= %s")
            params.append(hasta + ' 23:59:59')
            print(f"DEBUG: Agregando filtro hasta: {hasta}")
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
        
        print(f"DEBUG: SQL generado: {sql}")
        print(f"DEBUG: Parámetros: {params}")
        
        results = execute_query(sql, params, fetch='all')
        
        print(f"DEBUG: Resultados obtenidos: {len(results or [])}")
        
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
