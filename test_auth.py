#!/usr/bin/env python3
"""Script para probar autenticación de usuarios"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.auth_system import AuthSystem
    from app.db_mysql import get_db_connection
    print("✅ Importación exitosa")

    # Crear instancia del sistema de auth
    auth = AuthSystem()
    print("🔐 Sistema de autenticación creado")

    # Probar conexión directa a la tabla
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()

        # Ver algunos usuarios con sus hashes
        cursor.execute("SELECT username, password_hash, activo FROM usuarios_sistema LIMIT 3")
        users = cursor.fetchall()
        print("👤 Usuarios en BD:")
        for user in users:
            hash_preview = user[1][:20] + "..." if len(user[1]) > 20 else user[1]
            print(f"  - {user[0]}: {hash_preview} (activo: {user[1]})")

        conn.close()

    # Probar login con credenciales conocidas
    print("\n🔑 Probando login...")

    # Intentar con admin/admin (credenciales comunes)
    result = auth.verificar_usuario("admin", "admin")
    print(f"Login admin/admin: {result}")

    # Intentar con admin/123456
    result = auth.verificar_usuario("admin", "123456")
    print(f"Login admin/123456: {result}")

    # Intentar con Yahir/admin
    result = auth.verificar_usuario("Yahir", "admin")
    print(f"Login Yahir/admin: {result}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()