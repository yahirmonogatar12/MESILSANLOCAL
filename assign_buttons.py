#!/usr/bin/env python3
"""Script para asignar permisos de botones al rol superadmin"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.db_mysql import get_db_connection
    print("✅ Importación exitosa")

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()

        # Ver qué botones existen
        cursor.execute("SELECT pagina, seccion, boton, descripcion FROM permisos_botones LIMIT 20")
        botones = cursor.fetchall()
        print(f"🔘 Botones disponibles: {len(botones)}")
        for boton in botones[:10]:  # Mostrar primeros 10
            print(f"  - {boton[0]}.{boton[1]}.{boton[2]}: {boton[3]}")

        # Obtener ID del rol superadmin
        cursor.execute("SELECT id FROM roles WHERE nombre = 'superadmin'")
        rol = cursor.fetchone()
        if not rol:
            print("❌ Rol 'superadmin' no encontrado")
            conn.close()
            sys.exit(1)

        rol_id = rol[0]
        print(f"🎭 ID del rol superadmin: {rol_id}")

        # Ver qué botones ya están asignados al superadmin
        cursor.execute("""
            SELECT pb.pagina, pb.seccion, pb.boton
            FROM rol_permisos_botones rpb
            JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
            WHERE rpb.rol_id = %s
        """, (rol_id,))
        asignados = cursor.fetchall()
        print(f"✅ Botones ya asignados al superadmin: {len(asignados)}")

        # Si no hay botones asignados, asignar todos los botones al superadmin
        if len(asignados) == 0:
            print("🔧 Asignando todos los botones al rol superadmin...")

            # Obtener todos los IDs de botones
            cursor.execute("SELECT id FROM permisos_botones")
            boton_ids = [row[0] for row in cursor.fetchall()]

            # Asignar cada botón al superadmin
            asignados_count = 0
            for boton_id in boton_ids:
                try:
                    cursor.execute("""
                        INSERT IGNORE INTO rol_permisos_botones (rol_id, permiso_boton_id)
                        VALUES (%s, %s)
                    """, (rol_id, boton_id))
                    asignados_count += 1
                except Exception as e:
                    print(f"Error asignando botón {boton_id}: {e}")

            conn.commit()
            print(f"✅ Asignados {asignados_count} botones al rol superadmin")

            # Verificar asignación
            cursor.execute("""
                SELECT pb.pagina, pb.seccion, pb.boton
                FROM rol_permisos_botones rpb
                JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
                WHERE rpb.rol_id = %s
                LIMIT 10
            """, (rol_id,))
            nuevos_asignados = cursor.fetchall()
            print(f"🔍 Nuevos botones asignados (primeros 10): {[f'{b[0]}.{b[1]}.{b[2]}' for b in nuevos_asignados]}")

        else:
            print("ℹ️ El rol superadmin ya tiene botones asignados")

        conn.close()

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()