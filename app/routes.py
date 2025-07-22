import json
import os
import re
import traceback
import tempfile
import subprocess
from functools import wraps
from flask import Flask, request, render_template, redirect, url_for, session, jsonify, send_file
from .db import (get_db_connection, init_db, guardar_configuracion_usuario, cargar_configuracion_usuario,
                actualizar_inventario_general_entrada, actualizar_inventario_general_salida, 
                obtener_inventario_general, recalcular_inventario_general, insertar_bom_desde_dataframe,
                obtener_modelos_bom, listar_bom_por_modelo, exportar_bom_a_excel)
import sqlite3
import pandas as pd
from werkzeug.utils import secure_filename

# Importar sistema de autenticación mejorado
from .auth_system import AuthSystem
from .user_admin import user_admin_bp

app = Flask(__name__)
app.secret_key = 'alguna_clave_secreta'  # Necesario para usar sesiones

# Inicializar base de datos original
init_db()  # Esto crea la tabla si no existe

# Inicializar sistema de autenticación
auth_system = AuthSystem()
auth_system.init_database()

# Registrar Blueprint de administración
app.register_blueprint(user_admin_bp, url_prefix='/admin')

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
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT rol FROM usuarios WHERE username = ?', (username,))
        usuario = cursor.fetchone()
        if not usuario:
            conn.close()
            return False
            
        if usuario[0] == 'superadmin':
            conn.close()
            return True
        
        # Verificar permiso específico del botón
        cursor.execute('''
            SELECT 1 FROM usuarios u
            JOIN roles r ON u.rol = r.nombre
            JOIN rol_permisos_botones rpb ON r.id = rpb.rol_id
            JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
            WHERE u.username = ? AND pb.boton = ? AND pb.activo = 1
            LIMIT 1
        ''', (username, nombre_boton))
        
        resultado = cursor.fetchone()
        conn.close()
        
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
        print("⚠️ usuarios.json no encontrado, usando solo sistema de BD")
        return {}

# ACTUALIZADO: Usar el sistema de autenticación avanzado
def login_requerido(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        print("🔐 Verificando sesión avanzada:", session.get('usuario'))
        
        # Verificar si hay usuario en sesión
        if 'usuario' not in session:
            print("❌ No hay usuario en sesión")
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
            print(f"✅ Login exitoso con sistema BD: {user}")
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
                print(f"✅ Login exitoso con sistema JSON (fallback): {user}")
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
            print(f"⚠️ Error en fallback JSON: {e}")
        
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
        print(f"Error al cargar template {template_path}: {str(e)}")
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
    Busca materiales en inventario por número de parte
    """
    try:
        numero_parte = request.args.get('numero_parte', '').strip()
        
        if not numero_parte:
            return jsonify({'success': False, 'error': 'Número de parte requerido'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 🔄 NUEVO: Buscar inventario agregado por número de parte
        # Primero, obtener el total disponible por número de parte
        query_inventario = """
            SELECT numero_parte, codigo_material, especificacion, cantidad_total
            FROM inventario_general 
            WHERE numero_parte LIKE ? OR numero_parte = ?
            ORDER BY fecha_actualizacion DESC
        """
        
        cursor.execute(query_inventario, (f'%{numero_parte}%', numero_parte))
        inventario_general = cursor.fetchone()
        
        if inventario_general:
            # Si existe en inventario general, usar esa cantidad
            materiales = [{
                'codigo_material_recibido': f"AGG-{inventario_general[0]}", # Código agregado
                'codigo_material_original': inventario_general[1] or '',
                'codigo_material': inventario_general[1] or '',
                'especificacion': inventario_general[2] or '',
                'numero_parte': inventario_general[0],
                'cantidad_actual': inventario_general[3] or 0, # cantidad_total del inventario_general
                'numero_lote_material': 'AGREGADO',
                'fecha_recepcion': 'Varios',
                'proveedor': 'Agregado'
            }]
        else:
            # Fallback: buscar en registros individuales (para compatibilidad)
            query_individual = """
                SELECT codigo_material_recibido, codigo_material_original, codigo_material,
                    especificacion, numero_parte, cantidad_actual,
                    numero_lote_material, fecha_recibo, ''
                FROM control_material_almacen 
                WHERE numero_parte LIKE ? OR numero_parte = ?
                ORDER BY fecha_recibo DESC
            """
            
            cursor.execute(query_individual, (f'%{numero_parte}%', numero_parte))
            resultados = cursor.fetchall()
            
            materiales = []
            for row in resultados:
                materiales.append({
                    'codigo_material_recibido': row[0],
                    'codigo_material_original': row[1],
                    'codigo_material': row[2],
                    'especificacion': row[3],
                    'numero_parte': row[4],
                    'cantidad_actual': row[5] or 0,
                    'numero_lote_material': row[6] or '',
                    'fecha_recepcion': row[7] or '',
                    'proveedor': row[8] or 'N/A'
                })
        
        conn.close()
        
        if materiales:
            
            return jsonify({'success': True, 'materiales': materiales})
        else:
            return jsonify({'success': False, 'error': f'No se encontraron materiales con número de parte: {numero_parte}'})
            
    except Exception as e:
        print(f"Error al buscar material por número de parte: {e}")
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
        
        print(f"🔍 DEBUG - Cargando template: {template_path}")
        
        if not template_path:
            return jsonify({'error': 'No se especificó la ruta del template'}), 400
        
        # Validar que la ruta del template sea segura
        if '..' in template_path or template_path.startswith('/'):
            return jsonify({'error': 'Ruta de template no válida'}), 400
        
        print(f"🔍 DEBUG - Intentando renderizar: {template_path}")
        
        # Renderizar el template y devolver el HTML
        html_content = render_template(template_path)
        
        print(f"🔍 DEBUG - Template renderizado exitosamente, tamaño: {len(html_content)} caracteres")
        
        return html_content
        
    except Exception as e:
        error_msg = f"Error al cargar template {template_path}: {str(e)}"
        print(f"💥 DEBUG - {error_msg}")
        return jsonify({'error': error_msg}), 500


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

# Rutas para manejo de materiales
@app.route('/guardar_material', methods=['POST'])
def guardar_material():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Usar fecha actual para el registro manual
        from datetime import datetime
        fecha_actual = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        cursor.execute('''
            INSERT OR REPLACE INTO materiales (
                codigo_material, numero_parte, propiedad_material, classification,
                especificacion_material, unidad_empaque, ubicacion_material, vendedor,
                prohibido_sacar, reparable, nivel_msl, espesor_msl, fecha_registro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('codigoMaterial'),
            data.get('numeroParte'),
            data.get('propiedadMaterial'),
            data.get('classification'),
            data.get('especificacionMaterial'),
            data.get('unidadEmpaque'),
            data.get('ubicacionMaterial'),
            data.get('vendedor'),
            int(data.get('prohibidoSacar', 0)),  # Convertir a entero
            int(data.get('reparable', 0)),       # Convertir a entero
            data.get('nivelMSL'),
            data.get('espesorMSL'),
            fecha_actual  # Usar fecha actual en lugar de la del formulario
        ))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/listar_materiales')
def listar_materiales():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM materiales ORDER BY fecha_registro DESC')
        rows = cursor.fetchall()
        
        def convertir_a_entero_seguro(valor):
            """Convierte un valor a entero de forma segura"""
            if not valor:
                return 0
            
            # Si ya es entero, devolverlo
            if isinstance(valor, int):
                return valor
            
            # Si es string, intentar conversión
            if isinstance(valor, str):
                valor_str = valor.strip().lower()
                
                # Valores que se consideran como "true" o "checked"
                valores_true = ['1', 'true', 'yes', 'sí', 'si', 'checked', 'x', 'on', 'habilitado', 'activo']
                # Valores que se consideran como "false" o "unchecked"
                valores_false = ['0', 'false', 'no', 'unchecked', 'off', 'deshabilitado', 'inactivo', '']
                
                if valor_str in valores_true:
                    return 1
                elif valor_str in valores_false:
                    return 0
                else:
                    # Intentar conversión directa
                    try:
                        return int(float(valor_str))
                    except:
                        return 0
            
            # Para cualquier otro tipo, intentar conversión directa
            try:
                return int(valor)
            except:
                return 0
        
        materiales = []
        for row in rows:
            materiales.append({
                'codigoMaterial': row['codigo_material'],
                'numeroParte': row['numero_parte'],
                'propiedadMaterial': row['propiedad_material'],
                'classification': row['classification'],
                'especificacionMaterial': row['especificacion_material'],
                'unidadEmpaque': row['unidad_empaque'],
                'ubicacionMaterial': row['ubicacion_material'],
                'vendedor': row['vendedor'],
                'prohibidoSacar': convertir_a_entero_seguro(row['prohibido_sacar']),
                'reparable': convertir_a_entero_seguro(row['reparable']),
                'nivelMSL': row['nivel_msl'],
                'espesorMSL': row['espesor_msl'],
                'fechaRegistro': row['fecha_registro']
            })
        
        return jsonify(materiales)
        
    except Exception as e:
        print(f"Error en listar_materiales: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error al cargar materiales: {str(e)}'}), 500
        
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
        
        if not file or not file.filename.lower().endswith(('.xlsx', '.xls')):
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
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insertar los datos
        registros_insertados = 0
        errores = []
        
        # Obtener fecha y hora actual de importación
        from datetime import datetime
        fecha_importacion = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        for index, row in df.iterrows():
            try:
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
                prohibido_sacar = convertir_checkbox(obtener_valor_columna(row, 'prohibido_sacar'))
                reparable = convertir_checkbox(obtener_valor_columna(row, 'reparable'))
                
                nivel_msl = limpiar_numero(obtener_valor_columna(row, 'nivel_msl'))
                espesor_msl = obtener_valor_columna(row, 'espesor_msl')
                fecha_registro = fecha_importacion
                
                # Validar que al menos el código de material no esté vacío
                if not codigo_material:
                    errores.append(f"Fila {index + 1}: Código de material vacío")
                    continue
                
                cursor.execute('''
                    INSERT OR REPLACE INTO materiales (
                        codigo_material, numero_parte, propiedad_material, classification,
                        especificacion_material, unidad_empaque, ubicacion_material, vendedor,
                        prohibido_sacar, reparable, nivel_msl, espesor_msl, fecha_registro
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    codigo_material, numero_parte, propiedad_material, classification,
                    especificacion_material, unidad_empaque, ubicacion_material, vendedor,
                    prohibido_sacar, reparable, nivel_msl, espesor_msl, fecha_registro
                ))
                registros_insertados += 1
                
            except Exception as e:
                error_msg = f"Error en fila {index + 1}: {str(e)}"
                errores.append(error_msg)
                print(error_msg)
                continue
        
        # Commit de la transacción
        conn.commit()
        
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
        # Asegurar cierre de recursos
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
        
        # Actualizar en la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que el material existe
        cursor.execute('SELECT codigo_material FROM materiales WHERE codigo_material = ?', (codigo_material,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Material no encontrado'}), 404
        
        # Actualizar el campo
        sql = f'UPDATE materiales SET {columna_db} = ? WHERE codigo_material = ?'
        cursor.execute(sql, (int(valor), codigo_material))  # Convertir a entero
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Campo actualizado correctamente'})
        
    except Exception as e:
        print(f"Error al actualizar campo: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno del servidor: {str(e)}'}), 500

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
    """Endpoint para obtener códigos de material para el dropdown del control de almacén"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT codigo_material, numero_parte, especificacion_material, 
                   propiedad_material, unidad_empaque
            FROM materiales 
            WHERE codigo_material IS NOT NULL AND codigo_material != ''
            ORDER BY codigo_material ASC
        ''')
        rows = cursor.fetchall()
        
        codigos = []
        for row in rows:
            codigos.append({
                'codigo': row['codigo_material'],
                'nombre': row['numero_parte'] or '',
                'spec': row['especificacion_material'] or '',
                'numero_parte': row['numero_parte'] or '',
                'cantidad_estandarizada': row['unidad_empaque'] or '',
                'propiedad_material': row['propiedad_material'] or '',  # Campo correcto para propiedad
                'especificacion_material': row['especificacion_material'] or ''
            })
        
        return jsonify(codigos)
        
    except Exception as e:
        print(f"Error en obtener_codigos_material: {str(e)}")
        return jsonify({'error': f'Error al cargar códigos de material: {str(e)}'}), 500
        
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

@app.route('/control_almacen')
@login_requerido
def control_almacen():
    return render_template('Control de material/Control de material de almacen.html')

@app.route('/control_salida')
@login_requerido
def control_salida():
    return render_template('Control de material/Control de salida.html')

@app.route('/control_calidad')
@login_requerido
def control_calidad():
    return render_template('Control de material/Control de calidad.html')

@app.route('/guardar_control_almacen', methods=['POST'])
@login_requerido
def guardar_control_almacen():
    """Endpoint para guardar los datos del formulario de control de material de almacén"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        if not data.get('codigo_material_original'):
            return jsonify({'success': False, 'error': 'Código de material original es requerido'}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insertar datos en la tabla
        cursor.execute('''
            INSERT INTO control_material_almacen (
                forma_material, cliente, codigo_material_original, codigo_material,
                material_importacion_local, fecha_recibo, fecha_fabricacion, cantidad_actual,
                numero_lote_material, codigo_material_recibido, numero_parte, cantidad_estandarizada,
                codigo_material_final, propiedad_material, especificacion, material_importacion_local_final,
                estado_desecho, ubicacion_salida
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('forma_material', ''),
            data.get('cliente', ''),
            data.get('codigo_material_original', ''),
            data.get('codigo_material', ''),
            data.get('material_importacion_local', ''),
            data.get('fecha_recibo', ''),
            data.get('fecha_fabricacion', ''),
            data.get('cantidad_actual', 0),
            data.get('numero_lote_material', ''),
            data.get('codigo_material_recibido', ''),
            data.get('numero_parte', ''),
            data.get('cantidad_estandarizada', ''),
            data.get('codigo_material_final', ''),
            data.get('propiedad_material', ''),
            data.get('especificacion', ''),
            data.get('material_importacion_local_final', ''),
            data.get('estado_desecho', ''),
            data.get('ubicacion_salida', '')
        ))
        
        conn.commit()
        registro_id = cursor.lastrowid
        
        # Actualizar inventario general con la nueva entrada
        numero_parte = data.get('numero_parte', '').strip()
        cantidad_actual = float(data.get('cantidad_actual', 0))
        codigo_material = data.get('codigo_material', '')
        propiedad_material = data.get('propiedad_material', '')
        especificacion = data.get('especificacion', '')
        
        if numero_parte and cantidad_actual > 0:
            actualizar_inventario_general_entrada(
                numero_parte, codigo_material, propiedad_material, 
                especificacion, cantidad_actual
            )
            print(f"📦 Inventario general actualizado: +{cantidad_actual} para {numero_parte}")
        
        return jsonify({
            'success': True, 
            'message': 'Registro guardado exitosamente',
            'id': registro_id
        })
        
    except Exception as e:
        print(f"Error al guardar control de almacén: {str(e)}")
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
            query += ' AND date(fecha_recibo) >= ?'
            params.append(fecha_inicio)
            
        if fecha_fin:
            query += ' AND date(fecha_recibo) <= ?'
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
        cliente = cargar_configuracion_usuario(usuario, 'cliente_seleccionado', '')
        
        return jsonify({'success': True, 'cliente': cliente})
        
    except Exception as e:
        print(f"Error en cargar_cliente_seleccionado: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500

@app.route('/actualizar_estado_desecho_almacen', methods=['POST'])
@login_requerido
def actualizar_estado_desecho_almacen():
    """Actualizar el estado de desecho de un registro de control de almacén"""
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
            SET estado_desecho = ? 
            WHERE id = ?
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
        WHERE codigo_material_recibido LIKE ?
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
            
            print(f"📝 Analizando: codigo_material_recibido='{codigo_recibido}'")
            
            # Buscar patrón exacto: CODIGO_MATERIAL,YYYYMMDD0001
            match = re.match(patron_regex, codigo_recibido)
            
            if match:
                secuencial_encontrado = int(match.group(1))
                print(f"� Secuencial encontrado: {secuencial_encontrado}")
                
                if secuencial_encontrado > secuencial_mas_alto:
                    secuencial_mas_alto = secuencial_encontrado
                    print(f"📊 Nuevo secuencial más alto: {secuencial_mas_alto}")
            else:
                print(f"⚠️ No coincide con patrón esperado: {codigo_recibido}")
        
        siguiente_secuencial = secuencial_mas_alto + 1
        
        # Generar el próximo código de material recibido completo
        siguiente_codigo_completo = f"{codigo_material},{fecha_actual}{siguiente_secuencial:04d}"
        
        print(f"✅ Siguiente secuencial: {siguiente_secuencial}")
        print(f"✅ Próximo código completo: {siguiente_codigo_completo}")
        
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
        modelos = obtener_modelos_bom()
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
            query += ' AND (ig.codigo_material LIKE ? OR ig.numero_parte LIKE ?)'
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
        
        print(f"✅ Estatus de material consultado: {len(inventario)} items encontrados")
        
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
        cursor.execute('SELECT * FROM control_material_almacen WHERE codigo_material_recibido = ?', (codigo,))
        row = cursor.fetchone()
        
        if row:
            print("✅ SERVER: Registro encontrado en BD")
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
        cursor.execute('SELECT cantidad_actual FROM control_material_almacen WHERE codigo_material_recibido = ?', (codigo_material_recibido,))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({'success': False, 'error': 'Código no encontrado en almacén'})
        
        cantidad_actual = float(row[0]) if row[0] else 0
        cantidad_salida = float(cantidad_salida)
        
        if cantidad_salida > cantidad_actual:
            return jsonify({'success': False, 'error': f'Cantidad de salida ({cantidad_salida}) mayor a la disponible ({cantidad_actual})'})
        
        nueva_cantidad = cantidad_actual - cantidad_salida
        
        # Actualizar la cantidad en almacen
        cursor.execute('UPDATE control_material SET cantidad_actual = ? WHERE codigo_material_recibido = ?', 
                      (nueva_cantidad, codigo_material_recibido))
        
        # Registrar la salida en control_material_salida
        cursor.execute('''
            INSERT INTO control_material_salida (
                codigo_material_recibido, numero_lote, modelo, depto_salida, 
                proceso_salida, cantidad_salida, fecha_salida
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            codigo_material_recibido,
            data.get('numero_lote', ''),
            data.get('modelo', ''),
            data.get('depto_salida', ''),
            data.get('proceso_salida', ''),
            cantidad_salida,
            data.get('fecha_salida', '')
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Construir la consulta SQL con JOINs para obtener información completa
        query = '''
            SELECT 
                s.fecha_salida,
                s.proceso_salida,
                s.codigo_material_recibido,
                a.codigo_material,
                a.numero_parte,
                s.cantidad_salida as disp,
                0 as hist,
                a.codigo_material_original,
                s.numero_lote,
                s.modelo as maquina_linea,
                s.depto_salida as departamento
            FROM control_material_salida s
            LEFT JOIN control_material_almacen a ON s.codigo_material_recibido = a.codigo_material_recibido
            WHERE 1=1
        '''
        
        params = []
        
        if fecha_inicio:
            query += ' AND DATE(s.fecha_salida) >= ?'
            params.append(fecha_inicio)
        
        if fecha_fin:
            query += ' AND DATE(s.fecha_salida) <= ?'
            params.append(fecha_fin)
        
        if numero_lote:
            query += ' AND s.numero_lote LIKE ?'
            params.append(f'%{numero_lote}%')
            
        if codigo_material:
            query += ' AND (s.codigo_material_recibido LIKE ? OR a.codigo_material LIKE ? OR a.codigo_material_original LIKE ?)'
            params.extend([f'%{codigo_material}%', f'%{codigo_material}%', f'%{codigo_material}%'])
        
        query += ' ORDER BY s.fecha_salida DESC, s.fecha_registro DESC'
        
        print(f"📊 SQL Query: {query}")
        print(f"📊 SQL Params: {params}")
        
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        
        # Convertir a lista de diccionarios
        columnas = [desc[0] for desc in cursor.description]
        datos = []
        for fila in resultados:
            registro = dict(zip(columnas, fila))
            datos.append(registro)
        
        return jsonify(datos)
        
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
    """Buscar material en control_material_almacen por código de material recibido y calcular stock disponible real"""
    try:
        codigo_recibido = request.args.get('codigo_recibido', '').strip()
        
        if not codigo_recibido:
            return jsonify({'success': False, 'error': 'Código de material recibido no proporcionado'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar el material en almacén (sin filtro de cantidad)
        cursor.execute('''
            SELECT * FROM control_material_almacen 
            WHERE codigo_material_recibido = ?
        ''', (codigo_recibido,))
        
        material = cursor.fetchone()
        
        if not material:
            return jsonify({'success': False, 'error': 'Código de material no encontrado en almacén'})
        
        # Calcular el total de salidas para este código específico
        cursor.execute('''
            SELECT COALESCE(SUM(cantidad_salida), 0) as total_salidas
            FROM control_material_salida 
            WHERE codigo_material_recibido = ?
        ''', (codigo_recibido,))
        
        resultado_salidas = cursor.fetchone()
        total_salidas = float(resultado_salidas['total_salidas']) if resultado_salidas else 0.0
        
        # Calcular stock disponible real
        cantidad_original = float(material['cantidad_actual'])
        stock_disponible = cantidad_original - total_salidas
        
        print(f"📊 STOCK CALCULADO para {codigo_recibido}:")
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
            'fecha_registro': material['fecha_registro']
        }
        
        return jsonify({'success': True, 'material': material_data})
    
    except Exception as e:
        print(f"Error al buscar material por código: {str(e)}")
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

@app.route('/procesar_salida_material', methods=['POST'])
@login_requerido
def procesar_salida_material():
    """Procesar salida de material con respuesta inmediata y actualización de inventario en background"""
    import threading
    conn = None
    cursor = None
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        required_fields = ['codigo_material_recibido', 'cantidad_salida']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Campo requerido: {field}'}), 400
        
        codigo_recibido = data['codigo_material_recibido']
        cantidad_salida = float(data['cantidad_salida'])
        numero_lote = data.get('numero_lote', '')
        modelo = data.get('modelo', '')
        depto_salida = data.get('depto_salida', '')
        proceso_salida = data.get('proceso_salida', '')
        fecha_salida = data.get('fecha_salida', '')
        
        if cantidad_salida <= 0:
            return jsonify({'success': False, 'error': 'La cantidad de salida debe ser mayor a 0'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Iniciar transacción SOLO para validaciones y registro de salida
        conn.execute('BEGIN TRANSACTION')
        
        # Buscar el material en almacén para obtener información completa
        cursor.execute('''
            SELECT id, cantidad_actual, numero_parte FROM control_material_almacen 
            WHERE codigo_material_recibido = ?
        ''', (codigo_recibido,))
        
        material = cursor.fetchone()
        
        if not material:
            conn.rollback()
            return jsonify({'success': False, 'error': 'Material no encontrado en almacén'}), 400
        
        cantidad_original = material['cantidad_actual']
        material_id = material['id']
        numero_parte = material['numero_parte'] or ''
        
        # Calcular el total de salidas existentes para este código específico
        cursor.execute('''
            SELECT COALESCE(SUM(cantidad_salida), 0) as total_salidas
            FROM control_material_salida 
            WHERE codigo_material_recibido = ?
        ''', (codigo_recibido,))
        
        resultado_salidas = cursor.fetchone()
        total_salidas_previas = float(resultado_salidas['total_salidas']) if resultado_salidas else 0.0
        
        # Calcular stock disponible real
        stock_disponible = cantidad_original - total_salidas_previas
        
        print(f"📊 VERIFICACIÓN STOCK PARA SALIDA {codigo_recibido}:")
        print(f"   - Cantidad original: {cantidad_original}")
        print(f"   - Salidas previas: {total_salidas_previas}")
        print(f"   - Stock disponible: {stock_disponible}")
        print(f"   - Cantidad solicitada: {cantidad_salida}")
        
        if stock_disponible <= 0:
            conn.rollback()
            return jsonify({'success': False, 'error': f'Sin stock disponible. Original: {cantidad_original}, Salidas previas: {total_salidas_previas}'}), 400
        
        if cantidad_salida > stock_disponible:
            conn.rollback()
            return jsonify({'success': False, 'error': f'Cantidad insuficiente. Stock disponible: {stock_disponible}, solicitado: {cantidad_salida}'}), 400
        
        # Registrar la salida en control_material_salida
        from datetime import datetime
        fecha_registro = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO control_material_salida (
                codigo_material_recibido, numero_lote, modelo, depto_salida,
                proceso_salida, cantidad_salida, fecha_salida, fecha_registro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            codigo_recibido, numero_lote, modelo, depto_salida,
            proceso_salida, cantidad_salida, fecha_salida, fecha_registro
        ))
        
        nueva_cantidad = stock_disponible - cantidad_salida
        
        # Confirmar transacción INMEDIATAMENTE
        conn.commit()
        
        # ✅ OPTIMIZACIÓN: Actualizar inventario general en BACKGROUND THREAD
        def actualizar_inventario_background():
            """Función para actualizar inventario en segundo plano"""
            try:
                if numero_parte:
                    print(f"🔄 BACKGROUND: Actualizando inventario para {numero_parte}")
                    resultado = actualizar_inventario_general_salida(numero_parte, cantidad_salida)
                    if resultado:
                        print(f"✅ BACKGROUND: Inventario actualizado exitosamente: -{cantidad_salida} para {numero_parte}")
                    else:
                        print(f"❌ BACKGROUND: Error al actualizar inventario para {numero_parte}")
            except Exception as e:
                print(f"❌ BACKGROUND ERROR: {e}")
        
        # Ejecutar actualización de inventario en hilo separado
        if numero_parte:
            inventario_thread = threading.Thread(target=actualizar_inventario_background)
            inventario_thread.daemon = True  # Se cierra con la aplicación
            inventario_thread.start()
            print(f"🚀 OPTIMIZADO: Salida registrada, inventario actualizándose en background")
        
        # ✅ RESPUESTA INMEDIATA AL USUARIO
        return jsonify({
            'success': True,
            'message': f'Salida registrada exitosamente. Cantidad: {cantidad_salida}',
            'nueva_cantidad_disponible': nueva_cantidad,
            'optimized': True,  # Indicador de que se está usando optimización
            'numero_parte': numero_parte,  # Para debugging
            'inventario_actualizado_en_background': True
        })
        
    except Exception as e:
        print(f"❌ ERROR GENERAL en procesar_salida_material: {e}")
        if 'conn' in locals():
            conn.rollback()
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/forzar_actualizacion_inventario/<numero_parte>', methods=['POST'])
@login_requerido  
def forzar_actualizacion_inventario(numero_parte):
    """
    Endpoint para forzar la actualización del inventario general para un número de parte específico
    """
    try:
        print(f"🔄 FORZANDO actualización de inventario para: {numero_parte}")
        
        # Recalcular inventario para este número de parte específico
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener todas las entradas para este número de parte
        cursor.execute('''
            SELECT SUM(cantidad_recibida) as total_entradas
            FROM control_material_almacen 
            WHERE numero_parte = ?
        ''', (numero_parte,))
        entradas_result = cursor.fetchone()
        total_entradas = entradas_result[0] if entradas_result and entradas_result[0] else 0
        
        # Obtener todas las salidas para este número de parte
        cursor.execute('''
            SELECT SUM(cantidad_salida) as total_salidas
            FROM control_material_salida cms
            JOIN control_material_almacen cma ON cms.codigo_material_recibido = cma.codigo_material_recibido
            WHERE cma.numero_parte = ?
        ''', (numero_parte,))
        salidas_result = cursor.fetchone()
        total_salidas = salidas_result[0] if salidas_result and salidas_result[0] else 0
        
        # Calcular cantidad total actual
        cantidad_total_actual = total_entradas - total_salidas
        
        # Actualizar o insertar en inventario_general
        cursor.execute('''
            INSERT OR REPLACE INTO inventario_general 
            (numero_parte, cantidad_entradas, cantidad_salidas, cantidad_total, fecha_actualizacion)
            VALUES (?, ?, ?, ?, datetime('now'))
        ''', (numero_parte, total_entradas, total_salidas, cantidad_total_actual))
        
        conn.commit()
        conn.close()
        
        print(f"✅ FORZADO: Inventario actualizado para {numero_parte}: {cantidad_total_actual}")
        
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
            WHERE numero_parte = ?
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
            print("✅ ZEBRA RED: Conexión establecida")
            
            # Enviar comando ZPL
            comando_bytes = comando_zpl.encode('utf-8')
            sock.send(comando_bytes)
            print(f"📤 ZEBRA RED: Comando enviado ({len(comando_bytes)} bytes)")
            
            # Pequeña pausa para procesamiento
            import time
            time.sleep(1)
            
            # Cerrar conexión
            sock.close()
            print("✅ ZEBRA RED: Etiqueta enviada exitosamente")
            
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
        
        print(f"🎯 IMPRESIÓN DIRECTA: Código={codigo}, Método={metodo}")
        
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
                print("✅ Impresión exitosa vía LPT1")
                return jsonify({
                    'success': True,
                    'message': 'Etiqueta enviada directamente a impresora USB',
                    'metodo': 'copy_lpt1',
                    'codigo': codigo,
                    'timestamp': datetime.now().isoformat()
                })
                
        except Exception as e1:
            print(f"⚠️ LPT1 falló: {str(e1)}")
        
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
                print("✅ Impresión exitosa vía print command")
                return jsonify({
                    'success': True,
                    'message': 'Etiqueta enviada directamente a impresora USB',
                    'metodo': 'windows_print',
                    'codigo': codigo,
                    'timestamp': datetime.now().isoformat()
                })
                
        except Exception as e2:
            print(f"⚠️ Windows print falló: {str(e2)}")
        
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
                print("✅ Impresión exitosa vía PowerShell")
                return jsonify({
                    'success': True,
                    'message': 'Etiqueta enviada directamente a impresora Zebra',
                    'metodo': 'powershell',
                    'codigo': codigo,
                    'timestamp': datetime.now().isoformat()
                })
                
        except Exception as e3:
            print(f"⚠️ PowerShell falló: {str(e3)}")
        
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
        
        print(f"✅ Etiqueta enviada exitosamente a {ip}")
        
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
    """Endpoint para consultar el inventario general basado en la tabla inventario_general"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        filtros = data if data else {}
        
        print(f"🔍 Consultando inventario general con filtros: {filtros}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query base para obtener el inventario
        query = '''
            SELECT 
                ig.numero_parte,
                ig.codigo_material,
                ig.propiedad_material,
                ig.especificacion,
                ig.cantidad_entradas,
                ig.cantidad_salidas,
                ig.cantidad_total,
                ig.fecha_creacion,
                ig.fecha_actualizacion,
                ROW_NUMBER() OVER (ORDER BY ig.fecha_actualizacion DESC) as id
            FROM inventario_general ig
            WHERE 1=1
        '''
        
        params = []
        
        # Aplicar filtros
        if filtros.get('numeroParte'):
            query += ' AND ig.numero_parte LIKE ?'
            params.append(f"%{filtros['numeroParte']}%")
            
        if filtros.get('propiedad'):
            query += ' AND ig.propiedad_material = ?'
            params.append(filtros['propiedad'])
            
        if filtros.get('cantidadMinima') and float(filtros['cantidadMinima']) > 0:
            query += ' AND ig.cantidad_total >= ?'
            params.append(float(filtros['cantidadMinima']))
        
        query += ' ORDER BY ig.fecha_actualizacion DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        inventario = []
        for row in rows:
            inventario.append({
                'id': row[9],  # ROW_NUMBER
                'numero_parte': row[0],
                'codigo_material': row[1] or row[0],  # Usar numero_parte si no hay codigo_material
                'propiedad_material': row[2] or 'COMMON USE',
                'especificacion': row[3] or '',
                'cantidad_entradas': float(row[4]) if row[4] else 0.0,
                'cantidad_salidas': float(row[5]) if row[5] else 0.0,
                'cantidad_total': float(row[6]) if row[6] else 0.0,
                'fecha_creacion': row[7],
                'fecha_actualizacion': row[8]
            })
        
        print(f"✅ Inventario consultado: {len(inventario)} items encontrados")
        
        return jsonify({
            'success': True,
            'inventario': inventario,
            'total': len(inventario),
            'filtros_aplicados': filtros
        })
        
    except Exception as e:
        print(f"❌ Error al consultar inventario general: {e}")
        return jsonify({
            'success': False,
            'error': f'Error al consultar inventario: {str(e)}'
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
        
        pagina = request.form.get('pagina', '').strip()
        seccion = request.form.get('seccion', '').strip() 
        boton = request.form.get('boton', '').strip()
        
        if not all([pagina, seccion, boton]):
            return jsonify({'tiene_permiso': False, 'error': 'Parámetros incompletos'}), 400
        
        username = session['username']
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si es superadmin
        cursor.execute('SELECT rol FROM usuarios WHERE username = ?', (username,))
        usuario = cursor.fetchone()
        
        if not usuario:
            return jsonify({'tiene_permiso': False, 'error': 'Usuario no encontrado'}), 404
        
        # Superadmin tiene todos los permisos
        if usuario[0] == 'superadmin':
            return jsonify({'tiene_permiso': True, 'motivo': 'superadmin'})
        
        # Verificar permiso específico
        cursor.execute('''
            SELECT COUNT(*) FROM rol_permisos_botones rpb
            JOIN permisos_botones pb ON rpb.id_permiso = pb.id
            WHERE rpb.rol = ? AND pb.pagina = ? AND pb.seccion = ? AND pb.boton = ?
        ''', (usuario[0], pagina, seccion, boton))
        
        tiene_permiso = cursor.fetchone()[0] > 0
        conn.close()
        
        return jsonify({
            'tiene_permiso': tiene_permiso,
            'usuario': username,
            'rol': usuario[0],
            'permiso': f"{pagina} > {seccion} > {boton}"
        })
        
    except Exception as e:
        print(f"Error verificando permiso: {e}")
        return jsonify({'tiene_permiso': False, 'error': str(e)}), 500

@app.route('/obtener_permisos_usuario_actual', methods=['GET'])
def obtener_permisos_usuario_actual():
    """
    Obtener todos los permisos del usuario actual para caché en frontend
    """
    try:
        if 'username' not in session:
            return jsonify({'permisos': [], 'error': 'Usuario no autenticado'}), 401
        
        username = session['username']
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener rol del usuario
        cursor.execute('SELECT rol FROM usuarios WHERE username = ?', (username,))
        usuario = cursor.fetchone()
        
        if not usuario:
            return jsonify({'permisos': [], 'error': 'Usuario no encontrado'}), 404
        
        # Superadmin tiene todos los permisos
        if usuario[0] == 'superadmin':
            cursor.execute('SELECT pagina, seccion, boton FROM permisos_botones ORDER BY pagina, seccion, boton')
            permisos = cursor.fetchall()
        else:
            # Obtener permisos específicos del rol
            cursor.execute('''
                SELECT pb.pagina, pb.seccion, pb.boton 
                FROM rol_permisos_botones rpb
                JOIN permisos_botones pb ON rpb.id_permiso = pb.id
                WHERE rpb.rol = ?
                ORDER BY pb.pagina, pb.seccion, pb.boton
            ''', (usuario[0],))
            permisos = cursor.fetchall()
        
        conn.close()
        
        # Formatear permisos para JavaScript
        permisos_formateados = []
        for pagina, seccion, boton in permisos:
            permisos_formateados.append({
                'pagina': pagina,
                'seccion': seccion, 
                'boton': boton,
                'clave': f"{pagina}|{seccion}|{boton}"
            })
        
        return jsonify({
            'permisos': permisos_formateados,
            'usuario': username,
            'rol': usuario[0],
            'total': len(permisos_formateados)
        })
        
    except Exception as e:
        print(f"Error obteniendo permisos: {e}")
        return jsonify({'permisos': [], 'error': str(e)}), 500