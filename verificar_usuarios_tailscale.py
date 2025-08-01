#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar usuarios en la base de datos MySQL de Tailscale
"""

import requests
import json
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

def ejecutar_query(query, params=None):
    """Ejecutar query usando el proxy MySQL"""
    try:
        url = 'http://localhost:5001/execute'
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': 'ISEMM_PROXY_2024_SUPER_SECRETO'
        }
        
        data = {
            'query': query,
            'params': params or [],
            'fetch': 'all'
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('result', [])
        else:
            print(f"❌ Error en query: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error ejecutando query: {e}")
        return None

def verificar_usuarios():
    """Verificar usuarios en la base de datos MySQL de Tailscale"""
    print("🔍 Verificando usuarios en MySQL Tailscale...")
    print("=" * 60)
    
    # Listar todos los usuarios
    query_usuarios = "SELECT id, username, email, activo FROM usuarios_sistema ORDER BY id"
    usuarios = ejecutar_query(query_usuarios)
    
    if usuarios:
        print(f"✅ Se encontraron {len(usuarios)} usuarios:")
        print()
        
        for usuario in usuarios:
            if isinstance(usuario, dict):
                user_id = usuario.get('id')
                username = usuario.get('username')
                email = usuario.get('email')
                activo = usuario.get('activo')
            else:
                user_id = usuario[0]
                username = usuario[1]
                email = usuario[2]
                activo = usuario[3]
            
            estado = "🟢 ACTIVO" if activo else "🔴 INACTIVO"
            print(f"   ID: {user_id} | Username: {username} | Email: {email} | {estado}")
            
            # Obtener roles del usuario
            query_roles = '''
                SELECT r.nombre, r.nivel
                FROM usuario_roles ur
                JOIN roles r ON ur.rol_id = r.id
                WHERE ur.usuario_id = %s AND r.activo = 1
                ORDER BY r.nivel DESC
            '''
            
            roles = ejecutar_query(query_roles, [user_id])
            if roles:
                roles_nombres = []
                for rol in roles:
                    if isinstance(rol, dict):
                        roles_nombres.append(f"{rol.get('nombre')} (nivel {rol.get('nivel')})")
                    else:
                        roles_nombres.append(f"{rol[0]} (nivel {rol[1]})")
                print(f"      Roles: {', '.join(roles_nombres)}")
            else:
                print(f"      Roles: Sin roles asignados")
            print()
    else:
        print("❌ No se encontraron usuarios")

def verificar_usuario_especifico(username):
    """Verificar un usuario específico"""
    print(f"\n🔍 Verificando usuario específico: {username}")
    print("-" * 50)
    
    query = "SELECT id, username, email, activo FROM usuarios_sistema WHERE username = %s"
    resultado = ejecutar_query(query, [username])
    
    if resultado:
        usuario = resultado[0]
        if isinstance(usuario, dict):
            user_id = usuario.get('id')
            username_db = usuario.get('username')
            email = usuario.get('email')
            activo = usuario.get('activo')
        else:
            user_id = usuario[0]
            username_db = usuario[1]
            email = usuario[2]
            activo = usuario[3]
        
        estado = "🟢 ACTIVO" if activo else "🔴 INACTIVO"
        print(f"✅ Usuario encontrado:")
        print(f"   ID: {user_id}")
        print(f"   Username: {username_db}")
        print(f"   Email: {email}")
        print(f"   Estado: {estado}")
        
        # Obtener roles
        query_roles = '''
            SELECT r.nombre, r.nivel
            FROM usuario_roles ur
            JOIN roles r ON ur.rol_id = r.id
            WHERE ur.usuario_id = %s AND r.activo = 1
            ORDER BY r.nivel DESC
        '''
        
        roles = ejecutar_query(query_roles, [user_id])
        if roles:
            print(f"   Roles:")
            for rol in roles:
                if isinstance(rol, dict):
                    print(f"     - {rol.get('nombre')} (nivel {rol.get('nivel')})")
                else:
                    print(f"     - {rol[0]} (nivel {rol[1]})")
        else:
            print(f"   Roles: Sin roles asignados")
        
        return True
    else:
        print(f"❌ Usuario '{username}' no encontrado")
        return False

def main():
    print("🚀 Verificando usuarios en MySQL Tailscale...")
    print("=" * 60)
    
    # Verificar conexión al proxy
    try:
        response = requests.get('http://localhost:5001/health')
        if response.status_code == 200:
            print("✅ Proxy MySQL funcionando correctamente")
        else:
            print("❌ Proxy MySQL no responde correctamente")
            return
    except:
        print("❌ No se puede conectar al proxy MySQL")
        return
    
    # Verificar todos los usuarios
    verificar_usuarios()
    
    # Verificar usuarios específicos
    usuarios_test = ['admin', 'ADMIN', 'Admin', 'superadmin', 'yahir']
    
    for username in usuarios_test:
        verificar_usuario_especifico(username)
    
    print("\n🔚 Verificación completada")

if __name__ == "__main__":
    main()