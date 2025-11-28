"""
Rutas de API para SMT CSV Historial
Integración con MySQL para consulta en tiempo real
"""

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import logging
from .smt_csv_handler import SMTCSVHandler

logger = logging.getLogger(__name__)

# Crear blueprint
smt_api = Blueprint('smt_api', __name__)

# Configuración de base de datos (usar la misma que el monitor)
try:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
    from config import DATABASE
    DB_CONFIG = DATABASE
except ImportError:
    # Configuración por defecto - variables de entorno obligatorias
    DB_CONFIG = {
        'host': os.getenv('MYSQL_HOST'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'user': os.getenv('MYSQL_USER'),
        'password': os.getenv('MYSQL_PASSWORD'),
        'database': os.getenv('MYSQL_DATABASE'),
        'charset': 'utf8mb4'
    }

# Inicializar handler
smt_handler = SMTCSVHandler(DB_CONFIG)

@smt_api.route('/api/smt/historial/data', methods=['GET'])
def get_historial_data():
    """Obtiene datos del historial con filtros opcionales"""
    try:
        # Obtener filtros de query parameters
        filters = {}
        
        if request.args.get('folder'):
            filters['folder'] = request.args.get('folder')
        
        if request.args.get('part_name'):
            filters['part_name'] = request.args.get('part_name')
        
        if request.args.get('result'):
            filters['result'] = request.args.get('result')
        
        if request.args.get('date_from'):
            filters['date_from'] = request.args.get('date_from')
        
        if request.args.get('date_to'):
            filters['date_to'] = request.args.get('date_to')
        
        # Obtener datos
        result = smt_handler.get_historial_data(filters)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error en /api/smt/historial/data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@smt_api.route('/api/smt/historial/export', methods=['GET'])
def export_historial_data():
    """Exporta datos del historial para descarga"""
    try:
        # Mismos filtros que la consulta normal
        filters = {}
        
        if request.args.get('folder'):
            filters['folder'] = request.args.get('folder')
        
        if request.args.get('part_name'):
            filters['part_name'] = request.args.get('part_name')
        
        if request.args.get('result'):
            filters['result'] = request.args.get('result')
        
        if request.args.get('date_from'):
            filters['date_from'] = request.args.get('date_from')
        
        if request.args.get('date_to'):
            filters['date_to'] = request.args.get('date_to')
        
        # Obtener datos (sin límite para exportación)
        result = smt_handler.get_historial_data(filters)
        
        if result['success']:
            logger.info(f"Exportando {len(result['data'])} registros")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error en /api/smt/historial/export: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@smt_api.route('/api/smt/historial/upload', methods=['POST'])
def upload_csv_file():
    """Sube archivo CSV a la base de datos"""
    try:
        # Verificar que se subió un archivo
        if 'csvFile' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No se seleccionó archivo'
            }), 400
        
        file = request.files['csvFile']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No se seleccionó archivo'
            }), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({
                'success': False,
                'error': 'Solo se permiten archivos CSV'
            }), 400
        
        # Leer contenido del archivo
        file_content = file.read().decode('utf-8-sig')
        filename = secure_filename(file.filename)
        
        # Obtener línea y mounter de los campos del formulario (opcional)
        line_number = request.form.get('lineNumber')
        mounter_number = request.form.get('mounterNumber')
        
        if line_number:
            line_number = int(line_number)
        if mounter_number:
            mounter_number = int(mounter_number)
        
        # Procesar archivo
        result = smt_handler.upload_csv_file(
            file_content, filename, line_number, mounter_number
        )
        
        if result['success']:
            logger.info(f"Archivo {filename} procesado exitosamente: {result['records_inserted']} registros")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error en /api/smt/historial/upload: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@smt_api.route('/api/smt/folders', methods=['GET'])
def get_available_folders():
    """Obtiene lista de carpetas/líneas disponibles"""
    try:
        result = smt_handler.get_available_folders()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error en /api/smt/folders: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@smt_api.route('/api/smt/stats', methods=['GET'])
def get_general_stats():
    """Obtiene estadísticas generales del sistema"""
    try:
        # Estadísticas sin filtros
        stats = smt_handler.get_statistics()
        
        # Agregar información adicional
        folders_result = smt_handler.get_available_folders()
        
        result = {
            'success': True,
            'stats': stats,
            'total_lines': len(folders_result.get('folders', [])) if folders_result['success'] else 0
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error en /api/smt/stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Función para registrar el blueprint en la aplicación principal
def register_smt_routes(app):
    """Registra las rutas SMT en la aplicación Flask"""
    app.register_blueprint(smt_api)
    logger.info("Rutas SMT API registradas exitosamente")
