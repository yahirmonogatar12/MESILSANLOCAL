#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Desbloquear y resetear usuario admin
"""

import sqlite3
import sys
sys.path.append('.')

from app.auth_system import AuthSystem

def verificar_estado_usuario():
    """Verificar estado completo del usuario admin"""
    print("🔍 VERIFICANDO ESTADO DEL USUARIO ADMIN")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect('app/database/ISEMM_MES.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, password_hash, activo, intentos_fallidos, 
                   bloqueado_hasta, fecha_creacion, ultimo_acceso
            FROM usuarios_sistema 
            WHERE username = ?
        ''', ('admin',))
        
        user_data = cursor.fetchone()
        if user_data:
            print("📊 Estado actual del usuario:")
            print(f"   ID: {user_data[0]}")
            print(f"   Username: {user_data[1]}")
            print(f"   Password Hash: {user_data[2][:20]}...")
            print(f"   Activo: {user_data[3]}")
            print(f"   Intentos fallidos: {user_data[4]}")
            print(f"   Bloqueado hasta: {user_data[5]}")
            print(f"   Fecha creación: {user_data[6]}")
            print(f"   Último acceso: {user_data[7]}")
            
            return user_data
        else:
            print("❌ Usuario admin no encontrado")
            return None
            
    except Exception as e:
        print(f"❌ Error verificando estado: {e}")
        return None
    finally:
        conn.close()

def desbloquear_usuario():
    """Desbloquear usuario admin"""
    print("\n🔓 DESBLOQUEANDO USUARIO ADMIN")
    print("=" * 40)
    
    try:
        conn = sqlite3.connect('app/database/ISEMM_MES.db')
        cursor = conn.cursor()
        
        # Resetear intentos fallidos y desbloquear
        cursor.execute('''
            UPDATE usuarios_sistema 
            SET intentos_fallidos = 0, bloqueado_hasta = NULL
            WHERE username = ?
        ''', ('admin',))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            print("✅ Usuario admin desbloqueado exitosamente")
            return True
        else:
            print("❌ No se pudo desbloquear el usuario")
            return False
            
    except Exception as e:
        print(f"❌ Error desbloqueando usuario: {e}")
        return False
    finally:
        conn.close()

def cambiar_password():
    """Cambiar password del usuario admin"""
    print("\n🔑 CAMBIANDO PASSWORD DEL USUARIO ADMIN")
    print("=" * 50)
    
    try:
        auth = AuthSystem()
        
        # Usar método interno para cambiar password sin verificación
        import bcrypt
        nueva_password = 'admin123'
        password_hash = bcrypt.hashpw(nueva_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        conn = sqlite3.connect('app/database/ISEMM_MES.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE usuarios_sistema 
            SET password_hash = ?, intentos_fallidos = 0, bloqueado_hasta = NULL
            WHERE username = ?
        ''', (password_hash, 'admin'))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            print("✅ Password cambiado exitosamente a 'admin123'")
            return True
        else:
            print("❌ No se pudo cambiar el password")
            return False
            
    except Exception as e:
        print(f"❌ Error cambiando password: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def test_login_despues():
    """Test de login después de desbloquear"""
    print("\n🧪 TEST DE LOGIN DESPUÉS DE DESBLOQUEAR")
    print("=" * 50)
    
    auth = AuthSystem()
    
    resultado = auth.verificar_usuario('admin', 'admin123')
    print(f"Resultado del login: {resultado}")
    
    if isinstance(resultado, tuple):
        success, message = resultado
        if success:
            print("✅ Login exitoso después de desbloquear")
            return True
        else:
            print(f"❌ Login sigue fallando: {message}")
            return False
    
    return False

if __name__ == "__main__":
    print("🔧 REPARACIÓN DEL USUARIO ADMIN")
    print("=" * 50)
    
    # 1. Verificar estado actual
    estado = verificar_estado_usuario()
    
    # 2. Desbloquear usuario
    if estado:
        if estado[4] > 0 or estado[5]:  # Si hay intentos fallidos o está bloqueado
            print("\n⚠️ Usuario tiene intentos fallidos o está bloqueado")
            desbloquear_usuario()
        
        # 3. Cambiar password por si acaso
        cambiar_password()
        
        # 4. Verificar estado después
        print("\n📊 Estado después de la reparación:")
        verificar_estado_usuario()
        
        # 5. Test de login
        test_login_despues()
    
    print("\n🔍 PRÓXIMOS PASOS:")
    print("1. El usuario admin debería estar desbloqueado")
    print("2. Password: admin123") 
    print("3. Probar login nuevamente en el sistema web")
