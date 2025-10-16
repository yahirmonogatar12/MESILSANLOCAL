#!/usr/bin/env python3
"""Script para probar conexión MySQL y verificar tablas"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.db_mysql import get_db_connection
    print("✅ Importación exitosa")

    conn = get_db_connection()
    print(f"🔗 Conexión obtenida: {conn is not None}")

    if conn:
        cursor = conn.cursor()
        print("🖱️ Cursor creado")

        # Verificar todas las tablas
        cursor.execute("SHOW TABLES")
        all_tables = cursor.fetchall()
        print(f"📋 Todas las tablas: {[table[0] for table in all_tables]}")

        # Verificar tablas de usuarios específicamente
        cursor.execute("SHOW TABLES LIKE 'usuarios%'")
        user_tables = cursor.fetchall()
        print(f"👤 Tablas de usuarios: {[table[0] for table in user_tables]}")

        # Verificar si existe la tabla usuarios_sistema
        if user_tables:
            cursor.execute("SELECT COUNT(*) as total FROM usuarios_sistema")
            count = cursor.fetchone()
            print(f"👥 Total usuarios en usuarios_sistema: {count[0] if count else 0}")

            if count and count[0] > 0:
                cursor.execute("SELECT username, activo FROM usuarios_sistema LIMIT 5")
                users = cursor.fetchall()
                print("👤 Usuarios encontrados:")
                for user in users:
                    print(f"  - {user[0]} (activo: {user[1]})")

        conn.close()
        print("🔌 Conexión cerrada")
    else:
        print("❌ No se pudo obtener conexión")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()