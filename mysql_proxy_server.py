#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxy Server para MySQL sobre HTTP
Permite que un hosting sin Tailscale acceda a MySQL local a través de HTTP
"""

import json
import pymysql
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
CORS(app)  # Permitir CORS para requests desde el hosting

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mysql_proxy.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuración de seguridad
API_KEY = os.getenv('PROXY_API_KEY', 'tu_clave_api_super_secreta_2024')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',') if os.getenv('ALLOWED_HOSTS') else []

def get_mysql_connection():
    """Crear conexión a MySQL local"""
    try:
        connection = pymysql.connect(
            host=os.getenv('MYSQL_HOST', '100.111.108.116'),
            port=int(os.getenv('MYSQL_PORT', '3306')),
            user=os.getenv('MYSQL_USERNAME', 'ILSANMES'),
            password=os.getenv('MYSQL_PASSWORD', 'ISEMM2025'),
            database=os.getenv('MYSQL_DATABASE', 'isemm2025'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=30,
            read_timeout=30,
            write_timeout=30
        )
        return connection
    except Exception as e:
        logger.error(f"Error conectando a MySQL: {e}")
        return None

def validate_request(request):
    """Validar que la request sea autorizada"""
    # Verificar API Key
    api_key = request.headers.get('X-API-Key') or request.json.get('api_key') if request.json else None
    if api_key != API_KEY:
        return False, "API Key inválida"
    
    # Verificar host permitido (opcional)
    if ALLOWED_HOSTS and request.remote_addr not in ALLOWED_HOSTS:
        logger.warning(f"Request desde host no permitido: {request.remote_addr}")
        # No bloquear por ahora, solo logear
    
    return True, "OK"

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de salud"""
    try:
        conn = get_mysql_connection()
        if conn:
            conn.close()
            return jsonify({
                'status': 'healthy',
                'mysql': 'connected',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'status': 'unhealthy',
                'mysql': 'disconnected',
                'timestamp': datetime.now().isoformat()
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/execute', methods=['POST'])
def execute_query():
    """Ejecutar consulta SQL"""
    try:
        # Validar request
        valid, message = validate_request(request)
        if not valid:
            return jsonify({'error': message}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON requerido'}), 400
        
        query = data.get('query')
        params = data.get('params', [])
        fetch_type = data.get('fetch', 'all')  # 'all', 'one', 'none'
        
        if not query:
            return jsonify({'error': 'Query requerido'}), 400
        
        logger.info(f"Ejecutando query: {query[:100]}...")
        
        conn = get_mysql_connection()
        if not conn:
            return jsonify({'error': 'No se pudo conectar a MySQL'}), 500
        
        try:
            cursor = conn.cursor()
            
            # Ejecutar query
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Obtener resultados según el tipo
            result = None
            if fetch_type == 'all':
                result = cursor.fetchall()
            elif fetch_type == 'one':
                result = cursor.fetchone()
            elif fetch_type == 'none':
                result = None
            
            # Commit si es necesario
            if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP')):
                conn.commit()
                affected_rows = cursor.rowcount
                logger.info(f"Query ejecutado exitosamente. Filas afectadas: {affected_rows}")
                
                return jsonify({
                    'success': True,
                    'result': result,
                    'affected_rows': affected_rows,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                logger.info(f"Query SELECT ejecutado exitosamente. Filas: {len(result) if result else 0}")
                
                return jsonify({
                    'success': True,
                    'result': result,
                    'timestamp': datetime.now().isoformat()
                })
        
        finally:
            cursor.close()
            conn.close()
    
    except Exception as e:
        logger.error(f"Error ejecutando query: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/batch', methods=['POST'])
def execute_batch():
    """Ejecutar múltiples consultas en una transacción"""
    try:
        # Validar request
        valid, message = validate_request(request)
        if not valid:
            return jsonify({'error': message}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON requerido'}), 400
        
        queries = data.get('queries', [])
        if not queries:
            return jsonify({'error': 'Lista de queries requerida'}), 400
        
        logger.info(f"Ejecutando batch de {len(queries)} queries")
        
        conn = get_mysql_connection()
        if not conn:
            return jsonify({'error': 'No se pudo conectar a MySQL'}), 500
        
        try:
            cursor = conn.cursor()
            results = []
            
            # Ejecutar todas las queries en una transacción
            for i, query_data in enumerate(queries):
                query = query_data.get('query')
                params = query_data.get('params', [])
                fetch_type = query_data.get('fetch', 'none')
                
                if not query:
                    raise Exception(f"Query {i+1} está vacío")
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                # Obtener resultado si es necesario
                result = None
                if fetch_type == 'all':
                    result = cursor.fetchall()
                elif fetch_type == 'one':
                    result = cursor.fetchone()
                
                results.append({
                    'query_index': i,
                    'result': result,
                    'affected_rows': cursor.rowcount
                })
            
            # Commit toda la transacción
            conn.commit()
            logger.info(f"Batch ejecutado exitosamente")
            
            return jsonify({
                'success': True,
                'results': results,
                'timestamp': datetime.now().isoformat()
            })
        
        except Exception as e:
            # Rollback en caso de error
            conn.rollback()
            raise e
        
        finally:
            cursor.close()
            conn.close()
    
    except Exception as e:
        logger.error(f"Error ejecutando batch: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/info', methods=['GET'])
def server_info():
    """Información del servidor proxy"""
    return jsonify({
        'name': 'MySQL Proxy Server',
        'version': '1.0.0',
        'mysql_host': os.getenv('MYSQL_HOST', 'localhost'),
        'mysql_port': os.getenv('MYSQL_PORT', '3306'),
        'mysql_database': os.getenv('MYSQL_DATABASE', ''),
        'timestamp': datetime.now().isoformat(),
        'endpoints': [
            '/health - Verificar estado',
            '/execute - Ejecutar query individual',
            '/batch - Ejecutar múltiples queries',
            '/info - Información del servidor'
        ]
    })

if __name__ == '__main__':
    print("🚀 Iniciando MySQL Proxy Server...")
    print(f"📊 MySQL Host: {os.getenv('MYSQL_HOST', 'localhost')}")
    print(f"🔑 API Key configurada: {'Sí' if API_KEY != 'tu_clave_api_super_secreta_2024' else 'No (usando default)'}")
    print(f"🌐 Hosts permitidos: {ALLOWED_HOSTS if ALLOWED_HOSTS else 'Todos'}")
    print("\n📋 Endpoints disponibles:")
    print("  GET  /health - Verificar estado")
    print("  POST /execute - Ejecutar query individual")
    print("  POST /batch - Ejecutar múltiples queries")
    print("  GET  /info - Información del servidor")
    print("\n⚠️  IMPORTANTE: Configura PROXY_API_KEY en .env para seguridad")
    print("\n🔥 Servidor iniciando en puerto 5001...")
    
    app.run(
        host='0.0.0.0',  # Escuchar en todas las interfaces
        port=5001,       # Puerto diferente al de la app principal
        debug=False,     # No debug en producción
        threaded=True    # Permitir múltiples conexiones
    )