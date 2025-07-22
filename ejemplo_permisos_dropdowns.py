#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EJEMPLO DE USO DEL SISTEMA DE PERMISOS DE DROPDOWNS
==================================================

Este script demuestra cómo usar el nuevo sistema de permisos
específicos para dropdowns en las listas AJAX.

Ejecutar: python ejemplo_permisos_dropdowns.py
"""

import sqlite3
from app.db import get_db_connection

def mostrar_permisos_dropdowns():
    """Mostrar todos los permisos de dropdowns disponibles"""
    print("\n" + "="*60)
    print("📋 PERMISOS DE DROPDOWNS DISPONIBLES")
    print("="*60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener todos los permisos de botones agrupados
        cursor.execute('''
            SELECT pagina, seccion, boton, descripcion
            FROM permisos_botones
            WHERE activo = 1
            ORDER BY pagina, seccion, boton
        ''')
        
        permisos = cursor.fetchall()
        conn.close()
        
        # Agrupar por página
        permisos_agrupados = {}
        for permiso in permisos:
            pagina = permiso['pagina']
            if pagina not in permisos_agrupados:
                permisos_agrupados[pagina] = {}
                
            seccion = permiso['seccion']
            if seccion not in permisos_agrupados[pagina]:
                permisos_agrupados[pagina][seccion] = []
                
            permisos_agrupados[pagina][seccion].append({
                'boton': permiso['boton'],
                'descripcion': permiso['descripcion']
            })
        
        # Mostrar permisos organizados
        for pagina, secciones in permisos_agrupados.items():
            nombre_lista = pagina.replace('LISTA_', '').replace('_', ' ')
            print(f"\n🗂️ {nombre_lista}")
            print("-" * 40)
            
            for seccion, botones in secciones.items():
                print(f"  📁 {seccion}")
                for boton in botones:
                    print(f"    ✓ {boton['boton']}")
                    print(f"      └─ {boton['descripcion']}")
                print()
        
        print(f"\n📊 Total de permisos de dropdowns: {len(permisos)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def mostrar_roles_con_permisos():
    """Mostrar roles y sus permisos de dropdowns"""
    print("\n" + "="*60)
    print("👥 ROLES Y SUS PERMISOS DE DROPDOWNS")
    print("="*60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener roles con sus permisos de botones
        cursor.execute('''
            SELECT r.nombre, r.descripcion, r.nivel,
                   COUNT(rpb.permiso_boton_id) as total_permisos
            FROM roles r
            LEFT JOIN rol_permisos_botones rpb ON r.id = rpb.rol_id
            WHERE r.activo = 1
            GROUP BY r.id
            ORDER BY r.nivel DESC
        ''')
        
        roles = cursor.fetchall()
        
        for rol in roles:
            print(f"\n🎭 {rol['nombre']} (Nivel {rol['nivel']})")
            print(f"   {rol['descripcion']}")
            print(f"   📊 Permisos de dropdowns: {rol['total_permisos']}")
            
            # Mostrar permisos específicos de este rol
            cursor.execute('''
                SELECT pb.pagina, pb.seccion, pb.boton
                FROM permisos_botones pb
                JOIN rol_permisos_botones rpb ON pb.id = rpb.permiso_boton_id
                JOIN roles r ON rpb.rol_id = r.id
                WHERE r.nombre = ? AND pb.activo = 1
                ORDER BY pb.pagina, pb.seccion, pb.boton
                LIMIT 5
            ''', (rol['nombre'],))
            
            permisos_rol = cursor.fetchall()
            
            if permisos_rol:
                print("   🔑 Algunos permisos:")
                for permiso in permisos_rol:
                    lista = permiso['pagina'].replace('LISTA_', '').replace('_', ' ')
                    print(f"      • {lista} > {permiso['seccion']} > {permiso['boton']}")
                
                if rol['total_permisos'] > 5:
                    print(f"      ... y {rol['total_permisos'] - 5} más")
            else:
                print("   ⚠️  Sin permisos de dropdowns asignados")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")


def ejemplo_asignar_permisos_rol():
    """Ejemplo de cómo asignar permisos específicos a un rol"""
    print("\n" + "="*60)
    print("🔧 EJEMPLO: ASIGNAR PERMISOS A UN ROL")
    print("="*60)
    
    print("""
Para asignar permisos específicos de dropdowns a un rol, puedes usar:

1. 📊 Panel Web: http://localhost:5000/admin/panel
   - Ir a "Ver permisos de dropdowns" de un usuario
   - Clic en "Editar Permisos de Dropdowns"
   - Seleccionar el rol y marcar/desmarcar permisos

2. 🐍 Código Python:
   
   from app.db import get_db_connection
   
   conn = get_db_connection()
   cursor = conn.cursor()
   
   # Obtener ID del rol
   cursor.execute('SELECT id FROM roles WHERE nombre = ?', ('operador_almacen',))
   rol_id = cursor.fetchone()[0]
   
   # Obtener IDs de permisos específicos
   cursor.execute('''
       SELECT id FROM permisos_botones 
       WHERE pagina = 'LISTA_DE_MATERIALES' 
       AND seccion = 'Control de material'
       AND boton IN ('Control de material de almacén', 'Control de salida')
   ''')
   permisos_ids = [row[0] for row in cursor.fetchall()]
   
   # Asignar permisos al rol
   for permiso_id in permisos_ids:
       cursor.execute('''
           INSERT OR IGNORE INTO rol_permisos_botones (rol_id, permiso_boton_id)
           VALUES (?, ?)
       ''', (rol_id, permiso_id))
   
   conn.commit()
   conn.close()

3. 🌐 API REST:
   
   POST /admin/actualizar_permisos_dropdowns_rol
   Content-Type: application/json
   
   {
       "rol_id": 5,
       "permisos_ids": [1, 2, 3, 4]
   }
""")


def main():
    """Función principal del ejemplo"""
    print("🔐 SISTEMA DE PERMISOS DE DROPDOWNS - ILSAN MES")
    print("=" * 60)
    print("Este sistema permite configurar permisos específicos")
    print("para cada dropdown/botón en las listas AJAX del sistema.")
    print()
    
    while True:
        print("\n📋 OPCIONES DISPONIBLES:")
        print("1. Ver todos los permisos de dropdowns disponibles")
        print("2. Ver roles y sus permisos asignados")
        print("3. Ver ejemplo de asignación de permisos")
        print("4. Salir")
        
        opcion = input("\n🔧 Seleccione una opción (1-4): ").strip()
        
        if opcion == "1":
            mostrar_permisos_dropdowns()
        elif opcion == "2":
            mostrar_roles_con_permisos()
        elif opcion == "3":
            ejemplo_asignar_permisos_rol()
        elif opcion == "4":
            print("\n✅ ¡Hasta luego!")
            break
        else:
            print("\n❌ Opción inválida. Intente de nuevo.")


if __name__ == "__main__":
    main()
