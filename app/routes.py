import json
import os
from functools import wraps
from flask import Flask, request, render_template, redirect, url_for, session, jsonify, send_file
from .db import get_db_connection, init_db
import sqlite3
import pandas as pd
from werkzeug.utils import secure_filename

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

@app.route('/INICIO')
@login_requerido
def material():
    usuario = session.get('usuario', 'Invitado')
    return render_template('MaterialTemplate.html', usuario=usuario)

@app.route('/produccion')
@login_requerido
def produccion():
    usuario = session.get('usuario', 'Invitado')
    return render_template('CONTROL_DE_MATERIAL.html', usuario=usuario)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

@app.route('/control_material')
@login_requerido
def control_material():
    return render_template('INFORMACION BASICA/CONTROL_DE_MATERIAL.html')


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
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM materiales ORDER BY fecha_registro DESC')
    rows = cursor.fetchall()
    conn.close()
    
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
            'prohibidoSacar': int(row['prohibido_sacar']) if row['prohibido_sacar'] else 0,
            'reparable': int(row['reparable']) if row['reparable'] else 0,
            'nivelMSL': row['nivel_msl'],
            'espesorMSL': row['espesor_msl'],
            'fechaRegistro': row['fecha_registro']
        })
    
    return jsonify(materiales)

@app.route('/importar_excel', methods=['POST'])
def importar_excel():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No se proporcionó archivo'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400
    
    if file and file.filename.lower().endswith(('.xlsx', '.xls')):
        try:
            # Guardar el archivo temporalmente
            filename = secure_filename(file.filename)
            temp_path = os.path.join(os.path.dirname(__file__), 'temp_' + filename)
            file.save(temp_path)
            
            # Leer el archivo Excel
            try:
                df = pd.read_excel(temp_path, engine='openpyxl' if filename.endswith('.xlsx') else 'xlrd')
            except Exception as e:
                # Intentar con diferentes engines
                try:
                    df = pd.read_excel(temp_path)
                except Exception as e2:
                    return jsonify({'success': False, 'error': f'Error al leer el archivo Excel: {str(e2)}'}), 500
            
            # Limpiar archivo temporal
            try:
                os.remove(temp_path)
            except:
                pass
            
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
                # Fecha de registro se genera automáticamente, no se mapea desde Excel
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
                    unidad_empaque = obtener_valor_columna(row, 'unidad_empaque')
                    ubicacion_material = obtener_valor_columna(row, 'ubicacion_material')
                    vendedor = obtener_valor_columna(row, 'vendedor')
                    prohibido_sacar = obtener_valor_columna(row, 'prohibido_sacar')
                    reparable = obtener_valor_columna(row, 'reparable')
                    nivel_msl = obtener_valor_columna(row, 'nivel_msl')
                    espesor_msl = obtener_valor_columna(row, 'espesor_msl')
                    # NO usar la fecha del Excel, usar la fecha actual de importación
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
            
            conn.commit()
            conn.close()
            
            # Preparar respuesta
            mensaje = f'Se importaron {registros_insertados} registros exitosamente'
            if errores:
                mensaje += f'. Se encontraron {len(errores)} errores'
                if len(errores) <= 5:  # Mostrar solo los primeros 5 errores
                    mensaje += f': {"; ".join(errores)}'
            
            return jsonify({'success': True, 'message': mensaje})
            
        except Exception as e:
            print(f"Error general: {str(e)}")
            # Limpiar archivo temporal en caso de error
            try:
                temp_path = os.path.join(os.path.dirname(__file__), 'temp_' + secure_filename(file.filename))
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass
            return jsonify({'success': False, 'error': f'Error al procesar el archivo: {str(e)}'}), 500
    
    return jsonify({'success': False, 'error': 'Formato de archivo no válido. Use .xlsx o .xls'}), 400

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
