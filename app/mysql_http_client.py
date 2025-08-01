#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente HTTP para MySQL
Permite conectar a MySQL a través del proxy HTTP cuando no hay acceso directo
"""

import requests
import json
import os
from datetime import datetime
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)

class MySQLHTTPClient:
    """Cliente HTTP para MySQL que simula una conexión directa"""
    
    def __init__(self, proxy_url=None, api_key=None, timeout=30):
        self.proxy_url = proxy_url or os.getenv('MYSQL_PROXY_URL', 'http://localhost:5001')
        self.api_key = api_key or os.getenv('PROXY_API_KEY', 'tu_clave_api_super_secreta_2024')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-API-Key': self.api_key
        })
    
    def _make_request(self, endpoint, data=None, method='POST'):
        """Hacer request al proxy"""
        try:
            url = f"{self.proxy_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            if method == 'GET':
                response = self.session.get(url, timeout=self.timeout)
            else:
                response = self.session.post(url, json=data, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Error en request: {error_msg}")
                raise Exception(error_msg)
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión al proxy: {e}")
            raise Exception(f"No se pudo conectar al proxy MySQL: {e}")
    
    def health_check(self):
        """Verificar estado del proxy"""
        try:
            result = self._make_request('health', method='GET')
            return result.get('status') == 'healthy'
        except:
            return False
    
    def execute_query(self, query, params=None, fetch='all'):
        """Ejecutar una consulta SQL"""
        data = {
            'query': query,
            'params': params or [],
            'fetch': fetch,
            'api_key': self.api_key
        }
        
        result = self._make_request('execute', data)
        
        if result.get('success'):
            return result.get('result')
        else:
            raise Exception(result.get('error', 'Error desconocido'))
    
    def execute_batch(self, queries):
        """Ejecutar múltiples consultas en una transacción"""
        data = {
            'queries': queries,
            'api_key': self.api_key
        }
        
        result = self._make_request('batch', data)
        
        if result.get('success'):
            return result.get('results')
        else:
            raise Exception(result.get('error', 'Error desconocido'))
    
    def get_info(self):
        """Obtener información del servidor proxy"""
        return self._make_request('info', method='GET')

# Función de compatibilidad para reemplazar execute_query original
def execute_query_http(query, params=None, fetch='all'):
    """Función de compatibilidad que usa el cliente HTTP"""
    try:
        client = MySQLHTTPClient()
        return client.execute_query(query, params, fetch)
    except Exception as e:
        logger.error(f"Error en execute_query_http: {e}")
        return None

# Función para probar la conexión
def test_http_connection():
    """Probar la conexión HTTP al proxy MySQL"""
    try:
        client = MySQLHTTPClient()
        
        print("🧪 Probando conexión HTTP al proxy MySQL...")
        
        # Verificar salud
        if client.health_check():
            print("✅ Proxy MySQL está saludable")
        else:
            print("❌ Proxy MySQL no responde")
            return False
        
        # Obtener información
        info = client.get_info()
        print(f"📊 Servidor: {info.get('name', 'N/A')}")
        print(f"🔗 MySQL Host: {info.get('mysql_host', 'N/A')}")
        print(f"🗄️ Base de datos: {info.get('mysql_database', 'N/A')}")
        
        # Probar consulta simple
        result = client.execute_query("SELECT 1 as test", fetch='one')
        if result and result.get('test') == 1:
            print("✅ Consulta de prueba exitosa")
            return True
        else:
            print("❌ Error en consulta de prueba")
            return False
    
    except Exception as e:
        print(f"❌ Error probando conexión HTTP: {e}")
        return False

if __name__ == "__main__":
    test_http_connection()