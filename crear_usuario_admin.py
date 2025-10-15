#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear usuario administrador en MySQL
Úsalo para crear tu primer usuario admin
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db_mysql import crear_usuario
from werkzeug.security import generate_password_hash

def crear_admin():
    """Crear usuario administrador"""
    print("=" * 60)
    print("CREAR USUARIO ADMINISTRADOR")
    print("=" * 60)
    
    # Solicitar datos
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    nombre_completo = input("Nombre completo: ").strip()
    email = input("Email: ").strip()
    departamento = input("Departamento (opcional): ").strip() or "Sistemas"
    
    if not username or not password:
        print("❌ Username y password son obligatorios")
        return
    
    # Generar hash de la contraseña
    password_hash = generate_password_hash(password)
    
    print(f"\n📝 Creando usuario:")
    print(f"   Username: {username}")
    print(f"   Nombre: {nombre_completo}")
    print(f"   Email: {email}")
    print(f"   Departamento: {departamento}")
    
    try:
        # Crear el usuario
        resultado = crear_usuario(
            username=username,
            password_hash=password_hash,
            area=departamento
        )
        
        if resultado:
            print(f"\n✅ Usuario '{username}' creado exitosamente!")
            print(f"\n🔑 Puedes iniciar sesión con:")
            print(f"   Username: {username}")
            print(f"   Password: {password}")
        else:
            print(f"\n❌ Error creando usuario. ¿Ya existe?")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    crear_admin()
