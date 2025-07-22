#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test directo del sistema de autenticación
"""

import sys
sys.path.append('.')

from app.auth_system import AuthSystem

def test_auth_system():
    """Test directo del sistema de autenticación"""
    print("🔐 TEST DIRECTO DEL SISTEMA DE AUTENTICACIÓN")
    print("=" * 50)
    
    auth = AuthSystem()
    
    # Test con credenciales correctas
    print("1️⃣ Probando credenciales admin/admin123...")
    resultado = auth.verificar_usuario('admin', 'admin123')
    print(f"   Resultado: {resultado}")
    print(f"   Tipo: {type(resultado)}")
    
    if isinstance(resultado, tuple):
        success, message = resultado
        print(f"   Success: {success}")
        print(f"   Message: {message}")
    
    # Test obtener permisos
    print("\n2️⃣ Obteniendo permisos del usuario...")
    permisos_resultado = auth.obtener_permisos_usuario('admin')
    print(f"   Permisos resultado: {permisos_resultado}")
    print(f"   Tipo: {type(permisos_resultado)}")
    
    if isinstance(permisos_resultado, tuple):
        permisos, rol_id = permisos_resultado
        print(f"   Permisos: {permisos}")
        print(f"   Rol ID: {rol_id}")
    
    # Test con credenciales incorrectas
    print("\n3️⃣ Probando credenciales incorrectas...")
    resultado_malo = auth.verificar_usuario('admin', 'password_malo')
    print(f"   Resultado: {resultado_malo}")

if __name__ == "__main__":
    test_auth_system()
