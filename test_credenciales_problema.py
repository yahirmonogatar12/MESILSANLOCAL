#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar diferentes credenciales del usuario Problema
"""

import requests
import pymysql
from app.config_mysql import get_mysql_connection_string

def get_db_connection():
    """Crear conexión a MySQL"""
    try:
        config = get_mysql_connection_string()
        if not config:
            print("Error: No se pudo obtener configuración de MySQL")
            return None
            
        connection = pymysql.connect(
            host=config['host'],
            user=config['user'],
            password=config['passwd'],
            database=config['db'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"Error conectando a MySQL: {e}")
        return None

def verificar_credenciales_bd():
    """Verificar las credenciales almacenadas en la base de datos"""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        print("=== Verificación de credenciales en BD ===")
        
        # Buscar usuario Problema
        cursor.execute("SELECT * FROM usuarios_sistema WHERE username = %s", ('Problema',))
        usuario = cursor.fetchone()
        
        if usuario:
            print(f"✓ Usuario encontrado:")
            print(f"  - ID: {usuario['id']}")
            print(f"  - Username: {usuario['username']}")
            print(f"  - Activo: {usuario['activo']}")
            print(f"  - Password hash: {usuario['password_hash'][:20]}...")
            
            # Verificar si hay tabla usuarios legacy
            try:
                cursor.execute("SELECT * FROM usuarios WHERE username = %s", ('Problema',))
                usuario_legacy = cursor.fetchone()
                if usuario_legacy:
                    print(f"\n✓ Usuario legacy encontrado:")
                    print(f"  - Username: {usuario_legacy['username']}")
                    print(f"  - Password: {usuario_legacy.get('password', 'N/A')}")
            except:
                print("\n📝 No hay tabla usuarios legacy")
        else:
            print("❌ Usuario 'Problema' no encontrado")
        
    except Exception as e:
        print(f"Error verificando credenciales: {e}")
    finally:
        conn.close()

def probar_credenciales():
    """Probar diferentes combinaciones de credenciales"""
    print("\n=== Probando diferentes credenciales ===")
    
    credenciales = [
        ('Problema', 'Problema123'),
        ('Problema', 'problema'),
        ('Problema', 'Problema'),
        ('Problema', '123456'),
        ('Problema', 'admin'),
        ('Problema', 'password')
    ]
    
    for username, password in credenciales:
        try:
            session = requests.Session()
            
            login_data = {
                'username': username,
                'password': password
            }
            
            response = session.post(
                'http://127.0.0.1:5000/login',
                data=login_data,
                allow_redirects=False,
                timeout=5
            )
            
            print(f"Probando {username}:{password} -> código {response.status_code}")
            
            if response.status_code == 302:
                print(f"  ✅ ¡Login exitoso con {username}:{password}!")
                return session, username, password
            elif response.status_code == 200:
                # Verificar si hay mensaje de error en el HTML
                if 'incorrectos' in response.text.lower():
                    print(f"  ❌ Credenciales incorrectas")
                else:
                    print(f"  ⚠️ Respuesta 200 inesperada")
            else:
                print(f"  ❌ Error: {response.status_code}")
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    return None, None, None

def probar_endpoint_con_credenciales_correctas(session):
    """Probar el endpoint de modelos con credenciales correctas"""
    try:
        response = session.get('http://127.0.0.1:5000/listar_modelos_bom')
        
        print(f"\nEndpoint /listar_modelos_bom: código {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✓ Respuesta JSON válida")
                print(f"📊 Modelos devueltos: {len(data)}")
                
                if len(data) > 0:
                    print(f"🏷️ Primeros 5 modelos:")
                    for i, modelo in enumerate(data[:5]):
                        print(f"  {i+1}. {modelo}")
                    return True
                else:
                    print("⚠️ Lista de modelos vacía")
                    return False
                    
            except Exception as e:
                print(f"❌ Error parseando JSON: {e}")
                print(f"Respuesta: {response.text[:200]}...")
                return False
        else:
            print(f"❌ Error: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    print("Probando credenciales para usuario Problema...\n")
    
    # 1. Verificar credenciales en BD
    verificar_credenciales_bd()
    
    # 2. Probar diferentes credenciales
    session, username, password = probar_credenciales()
    
    if session:
        print(f"\n🎉 Credenciales correctas encontradas: {username}:{password}")
        
        # 3. Probar endpoint con credenciales correctas
        endpoint_ok = probar_endpoint_con_credenciales_correctas(session)
        
        if endpoint_ok:
            print("\n✅ ¡Todo funciona correctamente!")
        else:
            print("\n❌ El endpoint de modelos aún tiene problemas")
    else:
        print("\n❌ No se encontraron credenciales válidas")
        print("💡 Sugerencia: Verificar la configuración del sistema de autenticación")

if __name__ == '__main__':
    main()