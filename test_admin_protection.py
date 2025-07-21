#!/usr/bin/env python3
"""
Script para probar que el usuario admin está completamente protegido
"""

import requests
import json

def test_admin_protection():
    """Probar que el usuario admin no se puede modificar"""
    
    print("🛡️ PROBANDO PROTECCIÓN DEL USUARIO ADMIN")
    print("=" * 50)
    
    session = requests.Session()
    
    # 1. Login con un usuario que tenga permisos de administración
    print("🔐 Haciendo login...")
    login_data = {
        'username': 'Yahir',  # O cualquier usuario con permisos de sistema
        'password': 'Yahir123'
    }
    
    response = session.post("http://localhost:5000/login", data=login_data)
    if response.status_code == 200 and "login" in response.text.lower():
        print("❌ Login falló - verificar credenciales")
        return False
    
    print("✅ Login exitoso")
    
    # 2. Intentar editar el usuario admin
    print("\n🧪 Probando modificación del usuario admin...")
    
    edit_data = {
        'username': 'admin',
        'nombre_completo': 'Administrador Modificado',
        'email': 'admin_modificado@test.com',
        'departamento': 'Hackeo',
        'activo': True,
        'roles': ['superadmin']
    }
    
    response = session.post(
        "http://localhost:5000/admin/guardar_usuario",
        json=edit_data,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 403:
        result = response.json()
        if 'protegido' in result.get('error', '').lower():
            print("✅ Modificación del admin BLOQUEADA correctamente")
            print(f"   Mensaje: {result.get('error')}")
        else:
            print("⚠️  Bloqueado pero mensaje inesperado")
    else:
        print(f"❌ ERROR: Modificación del admin NO fue bloqueada (Status: {response.status_code})")
        return False
    
    # 3. Intentar cambiar estado del admin
    print("\n🧪 Probando cambio de estado del admin...")
    
    status_data = {
        'username': 'admin',
        'activo': False
    }
    
    response = session.post(
        "http://localhost:5000/admin/cambiar_estado_usuario",
        json=status_data,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 403:
        result = response.json()
        if 'protegido' in result.get('error', '').lower():
            print("✅ Cambio de estado del admin BLOQUEADO correctamente")
            print(f"   Mensaje: {result.get('error')}")
        else:
            print("⚠️  Bloqueado pero mensaje inesperado")
    else:
        print(f"❌ ERROR: Cambio de estado del admin NO fue bloqueado (Status: {response.status_code})")
        return False
    
    # 4. Verificar que sí se puede consultar la información (solo lectura)
    print("\n🧪 Probando consulta de información del admin (solo lectura)...")
    
    response = session.get("http://localhost:5000/admin/obtener_usuario/admin")
    
    if response.status_code == 200:
        user_data = response.json()
        if user_data.get('username') == 'admin':
            print("✅ Consulta de información permitida (solo lectura)")
        else:
            print("⚠️  Respuesta inesperada en consulta")
    else:
        print(f"❌ ERROR: No se pudo consultar información del admin (Status: {response.status_code})")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 ¡PROTECCIÓN DEL ADMIN COMPLETAMENTE FUNCIONAL!")
    print("✅ Modificación: BLOQUEADA")
    print("✅ Cambio de estado: BLOQUEADO") 
    print("✅ Consulta información: PERMITIDA")
    print("🛡️  El usuario admin está completamente protegido")
    
    return True

def test_other_user_still_works():
    """Probar que otros usuarios sí se pueden modificar"""
    
    print("\n🧪 PROBANDO QUE OTROS USUARIOS SÍ SE PUEDEN MODIFICAR")
    print("=" * 50)
    
    session = requests.Session()
    
    # Login
    login_data = {
        'username': 'Yahir',
        'password': 'Yahir123'
    }
    
    session.post("http://localhost:5000/login", data=login_data)
    
    # Intentar modificar usuario Yahir (debería funcionar)
    edit_data = {
        'username': 'Yahir',
        'nombre_completo': 'Yahir Montes de Oca',
        'email': 'yahir@ilsan.com',
        'departamento': 'Sistemas',
        'activo': True,
        'roles': ['administrador']
    }
    
    response = session.post(
        "http://localhost:5000/admin/guardar_usuario",
        json=edit_data,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        print("✅ Otros usuarios SÍ se pueden modificar normalmente")
        return True
    else:
        print(f"❌ ERROR: Otros usuarios no se pueden modificar (Status: {response.status_code})")
        return False

def main():
    """Función principal"""
    
    try:
        # Test 1: Protección del admin
        admin_protected = test_admin_protection()
        
        # Test 2: Otros usuarios funcionan normal
        others_work = test_other_user_still_works()
        
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE PRUEBAS")
        print("=" * 60)
        
        if admin_protected and others_work:
            print("🎉 ¡TODAS LAS PRUEBAS PASARON!")
            print("🛡️  Sistema de protección funcionando perfectamente")
            print("✅ Admin protegido: SÍ")
            print("✅ Otros usuarios funcionan: SÍ")
        else:
            print("⚠️  Algunas pruebas fallaron")
            print(f"❌ Admin protegido: {'SÍ' if admin_protected else 'NO'}")
            print(f"❌ Otros usuarios funcionan: {'SÍ' if others_work else 'NO'}")
            
    except Exception as e:
        print(f"❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
