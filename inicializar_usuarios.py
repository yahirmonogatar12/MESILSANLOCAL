"""
Script de inicialización del sistema de usuarios
Crear admin por defecto y configurar roles básicos
"""

import sys
import os

# Añadir el directorio app al path para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.auth_system import AuthSystem

def inicializar_sistema_usuarios():
    """Inicializa la base de datos de usuarios y crea admin por defecto"""
    
    print("🔐 Inicializando Sistema de Usuarios ILSAN MES")
    print("=" * 50)
    
    # Crear instancia del sistema de auth
    auth_system = AuthSystem()
    
    # Inicializar base de datos
    print("📦 Creando estructura de base de datos...")
    auth_system.init_database()
    print("✅ Base de datos inicializada")
    
    # Crear usuario administrador por defecto
    print("\n👤 Creando usuario administrador por defecto...")
    
    try:
        auth_system.create_default_admin()
        print("✅ Usuario administrador creado/verificado exitosamente")
        print("   Usuario: admin")
        print("   Contraseña: admin123")
    except Exception as e:
        print(f"❌ Error creando admin: {str(e)}")
    
    print("\n🎉 Inicialización completada!")
    print("\n📋 Credenciales de acceso:")
    print("=" * 30)
    print("👤 Administrador:")
    print("   Usuario: admin")
    print("   Contraseña: admin123")
    print("\n🔧 Panel Admin: http://localhost:5000/admin/panel")
    print("📊 Auditoría: http://localhost:5000/admin/auditoria")
    print("\n⚠️  IMPORTANTE: Cambie la contraseña del administrador en producción!")

if __name__ == '__main__':
    try:
        inicializar_sistema_usuarios()
    except Exception as e:
        print(f"❌ Error durante la inicialización: {str(e)}")
        import traceback
        traceback.print_exc()
