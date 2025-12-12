# -*- coding: utf-8 -*-
"""
Rutas de BOM (Bill of Materials)
APIs para gestión del Bill of Materials
"""

import os
import tempfile
import traceback
import pandas as pd
from flask import Blueprint, request, jsonify, session, send_file

from .utils import login_requerido, obtener_fecha_hora_mexico
from ..database.db_mysql import (
    execute_query, get_connection, obtener_modelos_bom,
    insertar_bom_desde_dataframe, listar_bom_por_modelo
)
from ..database.db import get_db_connection

bom_bp = Blueprint('bom', __name__)


# ============== IMPORTAR BOM ==============

@bom_bp.route('/importar_excel_bom', methods=['POST'])
@login_requerido
def importar_excel_bom():
    """Importar datos de BOM desde archivo Excel"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No se encontró el archivo'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No se seleccionó ningún archivo'})

    try:
        print("--- Iniciando importación de BOM ---")
        df = pd.read_excel(file)
        
        print(f"Columnas detectadas en el Excel: {df.columns.tolist()}")
        
        registrador = session.get('usuario', 'desconocido')
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


# ============== LISTAR BOM ==============

@bom_bp.route('/listar_modelos_bom', methods=['GET'])
@login_requerido
def listar_modelos_bom():
    """Devuelve la lista de modelos únicos disponibles en la tabla BOM"""
    try:
        modelos = obtener_modelos_bom()
        return jsonify(modelos)
    except Exception as e:
        print(f"Error al obtener modelos BOM: {e}")
        return jsonify({'error': str(e)}), 500


@bom_bp.route('/listar_bom', methods=['POST'])
@login_requerido
def listar_bom():
    """Lista los registros de BOM, opcionalmente filtrados por modelo y classification"""
    try:
        data = request.get_json()
        modelo = data.get('modelo', 'todos') if data else 'todos'
        classification = data.get('classification', None) if data else None
        
        bom_data = listar_bom_por_modelo(modelo, classification)
        return jsonify(bom_data)
        
    except Exception as e:
        print(f"Error al listar BOM: {e}")
        return jsonify({'error': str(e)}), 500


@bom_bp.route('/consultar_bom', methods=['GET'])
@login_requerido
def consultar_bom():
    """Consulta datos de BOM con filtros GET para la interfaz de Control de salida"""
    try:
        modelo = request.args.get('modelo', '').strip()
        numero_parte = request.args.get('numero_parte', '').strip()
        
        if not modelo and not numero_parte:
            bom_data = listar_bom_por_modelo('todos')
        else:
            bom_data = listar_bom_por_modelo(modelo if modelo else 'todos')
            
            if numero_parte and bom_data:
                bom_data = [
                    item for item in bom_data 
                    if numero_parte.lower() in str(item.get('numero_parte', '')).lower()
                ]
        
        return jsonify(bom_data)
        
    except Exception as e:
        print(f"Error al consultar BOM: {e}")
        return jsonify({'error': str(e)}), 500


# ============== ACTUALIZAR BOM ==============

@bom_bp.route('/api/bom/update', methods=['POST'])
@login_requerido
def api_bom_update():
    """Actualiza un registro de BOM existente"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
        
        codigo_material = data.get('codigoMaterial')
        modelo = data.get('modelo')
        
        if not codigo_material or not modelo:
            return jsonify({'error': 'Código de material y modelo son requeridos'}), 400
        
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
        
        campos_update = {k: v for k, v in campos_actualizables.items() if v is not None}
        
        if not campos_update:
            return jsonify({'error': 'No hay campos para actualizar'}), 400
        
        set_clauses = []
        values = []
        
        for campo, valor in campos_update.items():
            set_clauses.append(f"`{campo}` = %s")
            values.append(valor)
        
        values.append(codigo_material)
        values.append(modelo)
        
        query = f"""
            UPDATE bom
            SET {', '.join(set_clauses)}
            WHERE codigo_material = %s AND modelo = %s
        """
        
        print(f"🔄 Actualizando BOM: codigo_material={codigo_material}, modelo={modelo}")
        
        result = execute_query(query, tuple(values), fetch=None)
        
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


@bom_bp.route('/api/bom/update-posiciones-assy', methods=['POST'])
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
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        try:
            valores = []
            for cambio in cambios:
                codigo_material = cambio.get('codigoMaterial')
                modelo = cambio.get('modelo')
                posicion_assy = cambio.get('posicionAssy', '')
                
                if codigo_material and modelo:
                    valores.append((posicion_assy, codigo_material, modelo))
            
            if not valores:
                return jsonify({'error': 'No hay valores válidos para actualizar'}), 400
            
            query = """
                UPDATE bom 
                SET posicion_assy = %s
                WHERE codigo_material = %s AND modelo = %s
            """
            
            cursor.executemany(query, valores)
            connection.commit()
            
            actualizados = cursor.rowcount
            print(f"✅ Total actualizado: {actualizados} registros")
            
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


# ============== EXPORTAR BOM ==============

def exportar_bom_a_excel(modelo=None, classification=None):
    """Función auxiliar para exportar datos de BOM a Excel con filtros opcionales"""
    try:
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
        
        result = execute_query(base_query, tuple(params) if params else (), fetch='all')
        
        if not result:
            print(f"No se encontraron datos de BOM para exportar")
            return None
        
        df = pd.DataFrame(result)
        
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
        
        temp_file = tempfile.NamedTemporaryFile(
            suffix='.xlsx', 
            delete=False, 
            mode='wb'
        )
        
        with pd.ExcelWriter(temp_file.name, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='BOM_Data', index=False)
            
            workbook = writer.book
            worksheet = writer.sheets['BOM_Data']
            
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        temp_file.close()
        return temp_file.name
        
    except Exception as e:
        print(f"Error en exportar_bom_a_excel: {e}")
        traceback.print_exc()
        return None


@bom_bp.route('/exportar_excel_bom', methods=['GET'])
@login_requerido
def exportar_excel_bom():
    """Exporta datos de BOM a un archivo Excel, filtrados por modelo y classification"""
    try:
        modelo = request.args.get('modelo', None)
        classification = request.args.get('classification', None)
        
        if modelo and modelo.strip() and modelo != 'todos':
            archivo_temp = exportar_bom_a_excel(modelo, classification)
            
            nombre_base = f'bom_export_{modelo}'
            if classification and classification != 'TODOS':
                nombre_base += f'_{classification}'
            download_name = f'{nombre_base}_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        else:
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
