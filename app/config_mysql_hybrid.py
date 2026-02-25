#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración híbrida de MySQL
Usa conexión directa cuando está disponible, HTTP proxy cuando no
"""

import os
from contextlib import contextmanager
from dotenv import load_dotenv
import logging

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)

# Intentar importar pymysql para conexión directa
try:
    import pymysql
    pymysql.install_as_MySQLdb()
    import MySQLdb
    MYSQL_DIRECT_AVAILABLE = True
    print(" pymysql disponible para conexión directa")
except ImportError:
    MYSQL_DIRECT_AVAILABLE = False
    print(" pymysql no disponible - usando solo modo HTTP")

# Importar cliente HTTP
try:
    from .mysql_http_client import MySQLHTTPClient
    HTTP_CLIENT_AVAILABLE = True
    print(" Cliente HTTP disponible")
except ImportError:
    try:
        from mysql_http_client import MySQLHTTPClient
        HTTP_CLIENT_AVAILABLE = True
        print(" Cliente HTTP disponible")
    except ImportError:
        HTTP_CLIENT_AVAILABLE = False
        print(" Cliente HTTP no disponible")

# Configuración de modo de conexión
USE_HTTP_PROXY = os.getenv('USE_HTTP_PROXY', 'auto').lower()
MYSQL_PROXY_URL = os.getenv('MYSQL_PROXY_URL', 'http://localhost:5001')
PROXY_API_KEY = os.getenv('PROXY_API_KEY', 'tu_clave_api_super_secreta_2024')

def get_mysql_connection_string():
    """Construir cadena de conexión para MySQL directo"""
    if not MYSQL_DIRECT_AVAILABLE:
        return None
        
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = int(os.getenv('MYSQL_PORT', '3306'))
    database = os.getenv('MYSQL_DATABASE', '')
    # Soportar ambos nombres: MYSQL_USER y MYSQL_USERNAME
    username = os.getenv('MYSQL_USER') or os.getenv('MYSQL_USERNAME', '')
    password = os.getenv('MYSQL_PASSWORD', '')
    
    return {
        'host': host,
        'port': port,
        'user': username,
        'passwd': password,
        'db': database,
        'charset': 'utf8mb4',
        'autocommit': True,
        'ssl_disabled': False,
        'connect_timeout': 30,
        'read_timeout': 30,
        'write_timeout': 30
    }

def get_mysql_connection():
    """Obtener conexión directa a MySQL"""
    if not MYSQL_DIRECT_AVAILABLE:
        return None
    
    try:
        config = get_mysql_connection_string()
        if not config:
            return None
        
        connection = pymysql.connect(**config)
        return connection
    except Exception as e:
        logger.error(f"Error conectando directamente a MySQL: {e}")
        return None

def get_http_client():
    """Obtener cliente HTTP para MySQL"""
    if not HTTP_CLIENT_AVAILABLE:
        return None
    
    try:
        client = MySQLHTTPClient(
            proxy_url=MYSQL_PROXY_URL,
            api_key=PROXY_API_KEY
        )
        return client
    except Exception as e:
        logger.error(f"Error creando cliente HTTP: {e}")
        return None

def determine_connection_mode():
    """Determinar qué modo de conexión usar"""
    if USE_HTTP_PROXY == 'true':
        return 'http'
    elif USE_HTTP_PROXY == 'false':
        return 'direct'
    else:  # auto
        # Intentar conexión directa primero
        if MYSQL_DIRECT_AVAILABLE:
            try:
                conn = get_mysql_connection()
                if conn:
                    conn.close()
                    return 'direct'
            except:
                pass
        
        # Si falla, intentar HTTP
        if HTTP_CLIENT_AVAILABLE:
            try:
                client = get_http_client()
                if client and client.health_check():
                    return 'http'
            except:
                pass
        
        return None

@contextmanager
def get_db_connection():
    """Context manager para conexión a base de datos (híbrido)"""
    mode = determine_connection_mode()
    
    if mode == 'direct':
        connection = get_mysql_connection()
        if connection:
            try:
                yield connection
            finally:
                connection.close()
        else:
            raise Exception("No se pudo establecer conexión directa a MySQL")
    
    elif mode == 'http':
        client = get_http_client()
        if client:
            yield client
        else:
            raise Exception("No se pudo establecer conexión HTTP a MySQL")
    
    else:
        raise Exception("No hay métodos de conexión disponibles")

def execute_query(query, params=None, fetch=None):
    """Ejecutar consulta usando el método disponible"""
    mode = determine_connection_mode()
    
    if mode == 'direct':
        return execute_query_direct(query, params, fetch)
    elif mode == 'http':
        return execute_query_http(query, params, fetch)
    else:
        logger.error("No hay métodos de conexión disponibles")
        return None

def execute_query_direct(query, params=None, fetch=None):
    """Ejecutar consulta con conexión directa"""
    if not MYSQL_DIRECT_AVAILABLE:
        return None
    
    try:
        connection = get_mysql_connection()
        if not connection:
            return None
        
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch == 'one':
                result = cursor.fetchone()
            elif fetch == 'all':
                result = cursor.fetchall()
            else:
                result = None
            
            # Commit para operaciones de escritura
            if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP')):
                connection.commit()
            
            return result
        
        finally:
            cursor.close()
            connection.close()
    
    except Exception as e:
        logger.error(f"Error en execute_query_direct: {e}")
        return None

def execute_query_http(query, params=None, fetch=None):
    """Ejecutar consulta con cliente HTTP"""
    if not HTTP_CLIENT_AVAILABLE:
        return None
    
    try:
        client = get_http_client()
        if not client:
            return None
        
        fetch_type = fetch or 'all'
        result = client.execute_query(query, params, fetch_type)
        return result
    
    except Exception as e:
        logger.error(f"Error en execute_query_http: {e}")
        return None

def test_connection():
    """Probar conexión usando el método disponible"""
    mode = determine_connection_mode()
    
    print(f" Probando conexión MySQL en modo: {mode}")
    
    if mode == 'direct':
        return test_direct_connection()
    elif mode == 'http':
        return test_http_connection()
    else:
        print(" No hay métodos de conexión disponibles")
        return False

def test_direct_connection():
    """Probar conexión directa"""
    try:
        connection = get_mysql_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            
            if result:
                print(" Conexión directa exitosa")
                return True
        
        print(" Error en conexión directa")
        return False
    
    except Exception as e:
        print(f" Error en conexión directa: {e}")
        return False

def test_http_connection():
    """Probar conexión HTTP"""
    try:
        client = get_http_client()
        if client and client.health_check():
            result = client.execute_query("SELECT 1 as test", fetch='one')
            if result and result.get('test') == 1:
                print(" Conexión HTTP exitosa")
                return True
        
        print(" Error en conexión HTTP")
        return False
    
    except Exception as e:
        print(f" Error en conexión HTTP: {e}")
        return False

def get_connection_info():
    """Obtener información sobre el método de conexión actual"""
    mode = determine_connection_mode()
    
    info = {
        'mode': mode,
        'direct_available': MYSQL_DIRECT_AVAILABLE,
        'http_available': HTTP_CLIENT_AVAILABLE,
        'proxy_url': MYSQL_PROXY_URL if mode == 'http' else None,
        'mysql_host': os.getenv('MYSQL_HOST', 'localhost'),
        'mysql_database': os.getenv('MYSQL_DATABASE', '')
    }
    
    return info

if __name__ == "__main__":
    print(" Probando configuración híbrida de MySQL...")
    
    info = get_connection_info()
    print(f" Modo de conexión: {info['mode']}")
    print(f"🔗 Conexión directa disponible: {info['direct_available']}")
    print(f"🌐 Conexión HTTP disponible: {info['http_available']}")
    
    if test_connection():
        print(" Conexión exitosa")
    else:
        print(" Error de conexión")