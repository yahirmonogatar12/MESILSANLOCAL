# -*- coding: utf-8 -*-
"""
Rutas de Materiales e Inventario
APIs para gestión de materiales, control de almacén, salidas y movimientos de inventario
"""

import os
import time
import traceback
import pandas as pd
from flask import Blueprint, request, jsonify, session, render_template, send_file
from werkzeug.utils import secure_filename
from io import BytesIO

from .utils import login_requerido, obtener_fecha_hora_mexico
from ..database.db_mysql import (
    execute_query, get_connection,
    guardar_material, obtener_materiales, actualizar_material_completo,
    buscar_material_por_numero_parte_mysql, calcular_inventario_general_mysql,
    guardar_configuracion, cargar_configuracion
)
from ..database.db import (
    get_db_connection, is_mysql_connection, 
    agregar_control_material_almacen, obtener_control_material_almacen
)

materiales_bp = Blueprint('materiales', __name__)


# ============== MATERIALES BASE ==============

@materiales_bp.route('/guardar_material', methods=['POST'])
def guardar_material_route():
    """Guardar un nuevo material en la base de datos"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    try:
        usuario_actual = session.get('usuario', 'USUARIO_MANUAL')
        
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
        
        print(f"🔍 Material registrado manualmente por: {usuario_actual}")
        success = guardar_material(material_data, usuario_registro=usuario_actual)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Error al guardar material'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@materiales_bp.route('/listar_materiales')
def listar_materiales():
    """Listar todos los materiales"""
    try:
        materiales = obtener_materiales() or []
        return jsonify(materiales)
    except Exception as e:
        print(f"Error obteniendo materiales: {e}")
        return jsonify({'error': str(e)}), 500


@materiales_bp.route('/actualizar_campo_material', methods=['POST'])
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
        
        campos_permitidos = ['prohibidoSacar', 'reparable']
        if campo not in campos_permitidos:
            return jsonify({'success': False, 'error': 'Campo no permitido para actualización'}), 400
        
        mapeo_campos = {
            'prohibidoSacar': 'prohibido_sacar',
            'reparable': 'reparable'
        }
        
        columna_db = mapeo_campos.get(campo)
        if not columna_db:
            return jsonify({'success': False, 'error': 'Campo no válido'}), 400
        
        query_verificar = 'SELECT codigo_material FROM materiales WHERE codigo_material = %s'
        material_existe = execute_query(query_verificar, (codigo_material,), fetch='one')
        
        if not material_existe:
            return jsonify({'success': False, 'error': 'Material no encontrado'}), 404
        
        query_actualizar = f'UPDATE materiales SET {columna_db} = %s WHERE codigo_material = %s'
        rows_affected = execute_query(query_actualizar, (int(valor), codigo_material))
        
        if rows_affected == 0:
            return jsonify({'success': False, 'error': 'No se pudo actualizar el material'}), 500
        
        return jsonify({'success': True, 'message': 'Campo actualizado correctamente'})
        
    except Exception as e:
        print(f"Error al actualizar campo: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno del servidor: {str(e)}'}), 500


@materiales_bp.route('/actualizar_material_completo', methods=['POST'])
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
        
        codigo_limpio = str(codigo_original).strip()
        resultado = actualizar_material_completo(codigo_limpio, nuevos_datos)
        
        if resultado['success']:
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error en actualizar_material_completo_route: {error_msg}")
        return jsonify({'success': False, 'error': f'Error interno del servidor: {error_msg}'}), 500


@materiales_bp.route('/buscar_material_por_numero_parte', methods=['GET'])
@login_requerido
def buscar_material_por_numero_parte():
    """Busca materiales en inventario por número de parte usando MySQL"""
    try:
        numero_parte = request.args.get('numero_parte', '').strip()
        
        if not numero_parte:
            return jsonify({'success': False, 'error': 'Número de parte requerido'})
        
        materiales = buscar_material_por_numero_parte_mysql(numero_parte)
        inventario_info = calcular_inventario_general_mysql(numero_parte)
        
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
                'database_type': 'MySQL'
            }
            response_data.append(material_data)
        
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


# ============== IMPORTAR/EXPORTAR EXCEL ==============

@materiales_bp.route('/importar_excel', methods=['POST'])
def importar_excel():
    """Importar materiales desde archivo Excel"""
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
        
        filename = secure_filename(file.filename)
        temp_path = os.path.join(os.path.dirname(__file__), '..', 'temp_' + filename)
        file.save(temp_path)
        
        try:
            df = pd.read_excel(temp_path, engine='openpyxl' if filename.endswith('.xlsx') else 'xlrd')
        except Exception as e:
            try:
                df = pd.read_excel(temp_path)
            except Exception as e2:
                return jsonify({'success': False, 'error': f'Error al leer el archivo Excel: {str(e2)}'}), 500
        
        if df.empty:
            return jsonify({'success': False, 'error': 'El archivo Excel está vacío'}), 400
        
        columnas_excel = df.columns.tolist()
        print(f"Columnas detectadas en Excel: {columnas_excel}")
        
        mapeo_columnas = {
            'codigo_material': ['Codigo de material', 'Código de material', 'codigo_material'],
            'numero_parte': ['Numero de parte', 'Número de parte', 'numero_parte'],
            'propiedad_material': ['Propiedad de material', 'propiedad_material'],
            'classification': ['Classification', 'classification', 'Clasificación'],
            'especificacion_material': ['Especificacion de material', 'Especificación de material', 'especificacion_material'],
            'unidad_empaque': ['Unidad de empaque', 'unidad_empaque'],
            'ubicacion_material': ['Ubicacion de material', 'Ubicación de material', 'ubicacion_material'],
            'vendedor': ['Vendedor', 'vendedor', 'Proveedor'],
            'prohibido_sacar': ['Prohibido sacar', 'prohibido_sacar'],
            'reparable': ['Reparable', 'reparable'],
            'nivel_msl': ['Nivel de MSL', 'nivel_msl'],
            'espesor_msl': ['Espesor de MSL', 'espesor_msl']
        }
        
        def obtener_valor_columna(row, campo):
            posibles_nombres = mapeo_columnas.get(campo, [campo])
            for nombre in posibles_nombres:
                if nombre in row:
                    valor = row[nombre]
                    if pd.isna(valor) or valor is None:
                        return ''
                    return str(valor).strip()
            return ''
        
        def convertir_checkbox(valor):
            if not valor or pd.isna(valor):
                return '0'
            valor_str = str(valor).strip().lower()
            valores_true = ['1', 'true', 'yes', 'sí', 'si', 'checked', 'x', 'on']
            if valor_str in valores_true:
                return '1'
            return '0'
        
        def limpiar_numero(valor):
            if not valor or pd.isna(valor):
                return ''
            try:
                numero = float(valor)
                if numero % 1 == 0:
                    return str(int(numero))
                else:
                    return str(numero)
            except (ValueError, TypeError):
                return str(valor).strip()
        
        registros_insertados = 0
        errores = []
        
        for index, row in df.iterrows():
            try:
                row_number = int(index) + 1 if isinstance(index, (int, float)) else len(errores) + registros_insertados + 1
                
                codigo_material = obtener_valor_columna(row, 'codigo_material')
                numero_parte = obtener_valor_columna(row, 'numero_parte')
                propiedad_material = obtener_valor_columna(row, 'propiedad_material')
                classification = obtener_valor_columna(row, 'classification')
                especificacion_material = obtener_valor_columna(row, 'especificacion_material')
                unidad_empaque = limpiar_numero(obtener_valor_columna(row, 'unidad_empaque'))
                ubicacion_material = obtener_valor_columna(row, 'ubicacion_material')
                vendedor = obtener_valor_columna(row, 'vendedor')
                prohibido_sacar = int(convertir_checkbox(obtener_valor_columna(row, 'prohibido_sacar')))
                reparable = int(convertir_checkbox(obtener_valor_columna(row, 'reparable')))
                nivel_msl = limpiar_numero(obtener_valor_columna(row, 'nivel_msl'))
                espesor_msl = obtener_valor_columna(row, 'espesor_msl')
                
                if not codigo_material:
                    errores.append(f"Fila {row_number}: Código de material vacío")
                    continue
                
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
                
                usuario_actual = session.get('usuario', 'USUARIO_MANUAL')
                success = guardar_material(material_data, usuario_registro=usuario_actual)
                
                if success:
                    registros_insertados += 1
                else:
                    errores.append(f"Fila {row_number}: Error al guardar en base de datos")
                
            except Exception as e:
                row_number = int(index) + 1 if isinstance(index, (int, float)) else len(errores) + registros_insertados + 1
                errores.append(f"Error en fila {row_number}: {str(e)}")
                continue
        
        mensaje = f'Se importaron {registros_insertados} registros exitosamente'
        if errores:
            mensaje += f'. Se encontraron {len(errores)} errores'
            if len(errores) <= 5:
                mensaje += f': {"; ".join(errores)}'
        
        return jsonify({'success': True, 'message': mensaje})
        
    except Exception as e:
        print(f"Error general en importar_excel: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error al procesar el archivo: {str(e)}'}), 500
        
    finally:
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass


@materiales_bp.route('/exportar_excel', methods=['GET'])
@login_requerido
def exportar_excel():
    """Exportar materiales a Excel"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
            df = pd.DataFrame(columns=[
                'Código de material', 'Número de parte', 'Propiedad de material', 
                'Classification', 'Especificación de material', 'Unidad de empaque', 
                'Ubicación de material', 'Vendedor', 'Prohibido sacar', 'Reparable', 
                'Nivel de MSL', 'Espesor de MSL', 'Fecha de registro'
            ])
        else:
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
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Materiales')
        
        output.seek(0)
        fecha_actual = obtener_fecha_hora_mexico().strftime('%Y-%m-%d_%H-%M-%S')
        nombre_archivo = f'materiales_export_{fecha_actual}.xlsx'
        
        return send_file(
            output,
            as_attachment=True,
            download_name=nombre_archivo,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        print(f"Error en exportar_excel: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============== CÓDIGOS DE MATERIAL ==============

@materiales_bp.route('/obtener_codigos_material')
def obtener_codigos_material():
    """Obtener códigos de material para dropdown con búsqueda inteligente"""
    conn = None
    cursor = None
    try:
        busqueda = request.args.get('busqueda', '').strip()
        
        conn = get_db_connection()
        if not conn:
            return jsonify([])
        
        cursor = conn.cursor()
        
        if busqueda:
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
                f'{busqueda}%', f'{busqueda}%', f'%{busqueda}%', f'%{busqueda}%',
                f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%'
            ))
        else:
            cursor.execute('''
                SELECT codigo_material, numero_parte, especificacion_material, 
                       propiedad_material, unidad_empaque
                FROM materiales 
                WHERE codigo_material IS NOT NULL AND codigo_material != ''
                ORDER BY codigo_material ASC
                LIMIT 1000
            ''')
        
        rows = cursor.fetchall()
        
        codigos = []
        for row in rows:
            material = {
                'codigo': row['codigo_material'] if row['codigo_material'] else '',
                'nombre': row['numero_parte'] if row['numero_parte'] else row['codigo_material'] if row['codigo_material'] else '',
                'spec': row['especificacion_material'] if row['especificacion_material'] else '',
                'numero_parte': row['numero_parte'] if row['numero_parte'] else '',
                'cantidad_estandarizada': str(row['unidad_empaque']) if row['unidad_empaque'] else '',
                'propiedad_material': row['propiedad_material'] if row['propiedad_material'] else '',
                'especificacion_material': row['especificacion_material'] if row['especificacion_material'] else ''
            }
            codigos.append(material)
        
        return jsonify(codigos)
        
    except Exception as e:
        print(f"❌ Error en obtener_codigos_material: {str(e)}")
        return jsonify([])
        
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


# ============== CONTROL DE ALMACÉN ==============

@materiales_bp.route('/control_almacen')
@login_requerido
def control_almacen():
    """Vista de Control de almacén"""
    return render_template('Control de material/Control de material de almacen.html')


@materiales_bp.route('/control_salida')
@login_requerido
def control_salida():
    """Vista de Control de salida de material"""
    try:
        usuario = session.get('usuario', 'Usuario')
        user_info = {
            'username': usuario,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'module': 'Control de Salida'
        }
        
        print(f"✅ Control de Salida cargado para usuario: {usuario}")
        
        return render_template('Control de material/Control de salida.html', 
                             usuario=usuario,
                             user_info=user_info)
                             
    except Exception as e:
        print(f"❌ Error al cargar Control de Salida: {e}")
        return render_template('Control de material/Control de salida.html', 
                             usuario='Usuario',
                             error='Error al cargar el módulo')


@materiales_bp.route('/control_calidad')
@login_requerido
def control_calidad():
    """Vista de Control de calidad de material"""
    return render_template('Control de material/Control de calidad.html')


@materiales_bp.route('/guardar_control_almacen', methods=['POST'])
@login_requerido
def guardar_control_almacen():
    """Guardar datos del formulario de control de material de almacén"""
    try:
        data = request.get_json()
        
        if not data.get('codigo_material_original'):
            return jsonify({'success': False, 'error': 'Código de material original es requerido'}), 400
        
        resultado = agregar_control_material_almacen(data)
        
        if resultado:
            print(f"✅ Registro de almacén guardado para {data.get('numero_parte', 'N/A')}")
            return jsonify({'success': True, 'message': 'Registro guardado exitosamente'})
        else:
            return jsonify({'success': False, 'error': 'Error al guardar en la base de datos'}), 500
        
    except Exception as e:
        print(f"Error al guardar control de almacén: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@materiales_bp.route('/obtener_secuencial_lote_interno', methods=['POST'])
@login_requerido
def obtener_secuencial_lote_interno():
    """Obtener el siguiente secuencial para lote interno del día"""
    try:
        data = request.get_json()
        fecha = data.get('fecha', '')
        
        if not fecha:
            return jsonify({'siguiente_secuencial': 1}), 200
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
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
            
            if result:
                if isinstance(result, dict):
                    max_seq = result.get('seq', 0) or 0
                else:
                    max_seq = result[1] if len(result) > 1 and result[1] else 0
            else:
                max_seq = 0
            
            siguiente_secuencial = max_seq + 1
            conn.close()
            return jsonify({'siguiente_secuencial': siguiente_secuencial}), 200
            
        except Exception as e:
            print(f"Error consultando secuencial: {e}")
            conn.close()
            return jsonify({'siguiente_secuencial': 1}), 200
            
    except Exception as e:
        print(f"Error en obtener_secuencial_lote_interno: {str(e)}")
        return jsonify({'error': str(e), 'siguiente_secuencial': 1}), 500


@materiales_bp.route('/consultar_control_almacen', methods=['GET'])
@login_requerido
def consultar_control_almacen():
    """Consultar registros de control de material de almacén"""
    conn = None
    cursor = None
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM control_material_almacen WHERE 1=1'
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


@materiales_bp.route('/actualizar_control_almacen', methods=['POST'])
@login_requerido
def actualizar_control_almacen():
    """Actualizar un registro de control de material de almacén"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        
        if not data or 'id' not in data:
            return jsonify({'success': False, 'error': 'ID no proporcionado'}), 400
        
        registro_id = data['id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM control_material_almacen WHERE id = %s", (registro_id,))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({'success': False, 'error': 'Registro no encontrado'}), 404
        
        columns = [desc[0] for desc in cursor.description]
        valores_actuales = dict(zip(columns, row))
        
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
            if campo in data:
                valor_nuevo = data[campo]
                valor_actual = valores_actuales.get(campo)
                
                if campo in ['fecha_recibo', 'fecha_fabricacion']:
                    if valor_nuevo == '':
                        valor_nuevo = None
                    if valor_actual is not None:
                        valor_actual = str(valor_actual)
                
                if campo == 'estado_desecho':
                    if valor_nuevo == 'Activo' or valor_nuevo == '1' or valor_nuevo == 1:
                        valor_nuevo = 1
                    elif valor_nuevo == 'Inactivo' or valor_nuevo == 'Desecho' or valor_nuevo == '0' or valor_nuevo == 0:
                        valor_nuevo = 0
                    else:
                        valor_nuevo = 1 if valor_nuevo else 0
                
                valor_nuevo_str = str(valor_nuevo) if valor_nuevo is not None else ''
                valor_actual_str = str(valor_actual) if valor_actual is not None else ''
                
                if valor_nuevo_str != valor_actual_str:
                    sets.append(f"{campo} = %s")
                    params.append(valor_nuevo)
                    campos_modificados.append(campo)
        
        if not sets:
            return jsonify({
                'success': True, 
                'message': 'No hay cambios que guardar',
                'campos_modificados': []
            })
        
        params.append(registro_id)
        query = f"UPDATE control_material_almacen SET {', '.join(sets)} WHERE id = %s"
        
        cursor.execute(query, params)
        conn.commit()
        
        if cursor.rowcount > 0:
            return jsonify({
                'success': True, 
                'message': f'Registro actualizado. Campos modificados: {", ".join(campos_modificados)}',
                'campos_modificados': campos_modificados
            })
        else:
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


@materiales_bp.route('/actualizar_estado_desecho_almacen', methods=['POST'])
@login_requerido
def actualizar_estado_desecho_almacen():
    """Actualizar el estado de desecho de un registro"""
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


# ============== CONFIGURACIÓN CLIENTE ==============

@materiales_bp.route('/guardar_cliente_seleccionado', methods=['POST'])
@login_requerido
def guardar_cliente_seleccionado():
    """Guardar la selección de cliente del usuario"""
    try:
        data = request.get_json()
        if not data or 'cliente' not in data:
            return jsonify({'success': False, 'error': 'Cliente no proporcionado'}), 400
            
        cliente = data['cliente']
        usuario = session.get('usuario', 'default')
        
        if guardar_configuracion_usuario(usuario, 'cliente_seleccionado', cliente):
            return jsonify({'success': True, 'message': 'Cliente guardado exitosamente'})
        else:
            return jsonify({'success': False, 'error': 'Error al guardar cliente'}), 500
            
    except Exception as e:
        print(f"Error en guardar_cliente_seleccionado: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500


@materiales_bp.route('/cargar_cliente_seleccionado', methods=['GET'])
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


# ============== INVENTARIO / LOTES ==============

@materiales_bp.route('/api/inventario/lotes_detalle', methods=['POST'])
@login_requerido
def consultar_lotes_detalle():
    """Obtener detalles específicos de lotes por número de parte"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        numero_parte = data.get('numero_parte', '').strip()
        
        if not numero_parte:
            return jsonify({'success': False, 'error': 'Número de parte requerido'}), 400
        
        using_mysql = is_mysql_connection()
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos'}), 500
            
        cursor = conn.cursor()
        
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
            return jsonify({'success': False, 'error': 'Solo MySQL soportado'}), 500
            
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
                continue
        
        return jsonify({
            'success': True,
            'numero_parte': numero_parte,
            'lotes': lotes_detalle,
            'total_lotes': len(lotes_detalle)
        })
        
    except Exception as e:
        print(f"❌ Error al consultar detalles de lotes: {e}")
        return jsonify({'success': False, 'error': f'Error al consultar detalles de lotes: {str(e)}'}), 500
        
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


@materiales_bp.route('/obtener_siguiente_secuencial', methods=['GET'])
def obtener_siguiente_secuencial():
    """Obtiene el siguiente número secuencial para el código de material recibido"""
    try:
        codigo_material = request.args.get('codigo_material', '')
        
        if not codigo_material:
            return jsonify({
                'success': False,
                'error': 'Código de material es requerido',
                'siguiente_secuencial': 1
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar número de parte
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
        else:
            numero_parte = codigo_material
        
        fecha_actual = obtener_fecha_hora_mexico().strftime('%Y%m%d')
        
        # Buscar máximo secuencial existente
        query = """
        SELECT codigo_material_recibido, fecha_registro
        FROM control_material_almacen 
        WHERE codigo_material_recibido LIKE %s
        ORDER BY fecha_registro DESC
        """
        
        cursor.execute(query, (f'{numero_parte},{fecha_actual}%',))
        rows = cursor.fetchall()
        
        max_seq = 0
        for row in rows:
            codigo_recibido = row['codigo_material_recibido']
            try:
                partes = codigo_recibido.split(',')
                if len(partes) >= 2:
                    secuencial_str = partes[-1][-4:]
                    secuencial = int(secuencial_str)
                    if secuencial > max_seq:
                        max_seq = secuencial
            except:
                continue
        
        siguiente_secuencial = max_seq + 1
        
        conn.close()
        
        return jsonify({
            'success': True,
            'siguiente_secuencial': siguiente_secuencial,
            'numero_parte': numero_parte,
            'fecha': fecha_actual
        })
        
    except Exception as e:
        print(f"❌ Error en obtener_siguiente_secuencial: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'siguiente_secuencial': 1
        }), 500
