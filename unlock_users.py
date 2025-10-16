#!/usr/bin/env python3
"""Script para desbloquear usuarios"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.db_mysql import get_db_connection
    print("✅ Importación exitosa")

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()

        # Desbloquear usuarios
        cursor.execute("""
            UPDATE usuarios_sistema
            SET intentos_fallidos = 0, bloqueado_hasta = NULL
            WHERE username IN ('admin', 'Yahir', 'Jesus')
        """)

        print(f"✅ {cursor.rowcount} usuarios desbloqueados")

        # Verificar estado
        cursor.execute("SELECT username, activo, intentos_fallidos, bloqueado_hasta FROM usuarios_sistema WHERE username IN ('admin', 'Yahir', 'Jesus')")
        users = cursor.fetchall()
        print("👤 Estado de usuarios:")
        for user in users:
            print(f"  - {user[0]}: activo={user[1]}, intentos={user[2]}, bloqueado={user[3]}")

        conn.commit()
        conn.close()

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()