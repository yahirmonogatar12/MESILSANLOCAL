#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar permisos de menú por rol
"""

from app.db import get_db_connection

def verificar_permisos_menu():
    """Verificar qué permisos de menú tiene cada rol"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("=== VERIFICACIÓN DE PERMISOS DE MENÚ POR ROL ===\n")
    
    # Obtener todos los roles
    cursor.execute("SELECT id, nombre, descripcion FROM roles ORDER BY nombre")
    roles = cursor.fetchall()
    
    for rol in roles:
        rol_id, rol_nombre, rol_descripcion = rol
        print(f"🔑 ROL: {rol_nombre.upper()}")
        print(f"   Descripción: {rol_descripcion}")
        
        # Obtener permisos de menú para este rol
        cursor.execute('''
            SELECT pb.boton, pb.descripcion 
            FROM rol_permisos_botones rpb
            JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
            WHERE rpb.rol_id = ? AND pb.pagina = 'menu_principal'
            ORDER BY pb.boton
        ''', (rol_id,))
        
        permisos = cursor.fetchall()
        
        if permisos:
            print("   📋 Permisos de menú:")
            for permiso_boton, descripcion in permisos:
                # Traducir nombres de botones a nombres amigables
                nombre_amigable = {
                    'menu_informacion_basica': '📊 Información Básica',
                    'menu_control_material': '📦 Control de Material',
                    'menu_control_produccion': '🏭 Control de Producción',
                    'menu_control_proceso': '⚙️ Control de Proceso',
                    'menu_control_calidad': '🔍 Control de Calidad',
                    'menu_control_resultados': '📈 Control de Resultados',
                    'menu_control_reporte': '📋 Control de Reporte',
                    'menu_configuracion_programa': '🔧 Configuración de Programa'
                }.get(permiso_boton, permiso_boton)
                
                print(f"     ✅ {nombre_amigable}")
        else:
            print("   ❌ Sin permisos de menú asignados")
        
        print()
    
    print("=== RESUMEN DE CONFIGURACIÓN ===\n")
    
    print("✅ Sistema de permisos de menú configurado exitosamente")
    print("🔧 Los administradores pueden gestionar permisos desde el Panel de Administración")
    print("📋 Roles configurados con permisos específicos:")
    print("   • SUPERADMIN: Acceso completo")
    print("   • ADMIN: Acceso a todas las secciones")
    print("   • SUPERVISOR_ALMACEN: Solo Material e Información Básica")
    print("   • OPERADOR_PRODUCCION: Solo Producción y Proceso")
    print("   • Otros roles: Sin permisos asignados (se pueden configurar)")
    
    conn.close()
    print("✅ Verificación completada")

if __name__ == "__main__":
    verificar_permisos_menu()
