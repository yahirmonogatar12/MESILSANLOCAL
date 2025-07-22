#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para agregar permisos de los botones principales del menú
"""

from app.auth_system import AuthSystem

def agregar_permisos_menu_principal():
    """Agrega los permisos para los botones principales del menú"""
    auth = AuthSystem()
    
    # Permisos para botones principales del menú
    permisos_menu = [
        {
            'nombre_boton': 'menu_informacion_basica',
            'descripcion': 'Acceso a la sección Información Básica',
            'pagina': 'menu_principal'
        },
        {
            'nombre_boton': 'menu_control_material',
            'descripcion': 'Acceso a la sección Control de Material',
            'pagina': 'menu_principal'
        },
        {
            'nombre_boton': 'menu_control_produccion',
            'descripcion': 'Acceso a la sección Control de Producción',
            'pagina': 'menu_principal'
        },
        {
            'nombre_boton': 'menu_control_proceso',
            'descripcion': 'Acceso a la sección Control de Proceso',
            'pagina': 'menu_principal'
        },
        {
            'nombre_boton': 'menu_control_calidad',
            'descripcion': 'Acceso a la sección Control de Calidad',
            'pagina': 'menu_principal'
        },
        {
            'nombre_boton': 'menu_control_resultados',
            'descripcion': 'Acceso a la sección Control de Resultados',
            'pagina': 'menu_principal'
        },
        {
            'nombre_boton': 'menu_control_reporte',
            'descripcion': 'Acceso a la sección Control de Reporte',
            'pagina': 'menu_principal'
        },
        {
            'nombre_boton': 'menu_configuracion_programa',
            'descripcion': 'Acceso a la sección Configuración de Programa',
            'pagina': 'menu_principal'
        }
    ]
    
    print("Agregando permisos de botones del menú principal...")
    
    for permiso in permisos_menu:
        try:
            auth.agregar_permiso_boton(
                nombre_boton=permiso['nombre_boton'],
                descripcion=permiso['descripcion'],
                pagina=permiso['pagina'],
                seccion='Menu Principal'
            )
            print(f"✅ Permiso agregado: {permiso['nombre_boton']}")
        except Exception as e:
            print(f"⚠️ Error agregando permiso {permiso['nombre_boton']}: {str(e)}")
    
    # Asignar todos los permisos al rol superadmin
    try:
        print("\nAsignando permisos a superadmin...")
        for permiso in permisos_menu:
            auth.asignar_permiso_boton_a_rol('superadmin', permiso['nombre_boton'])
        print("✅ Permisos asignados a superadmin")
    except Exception as e:
        print(f"⚠️ Error asignando permisos a superadmin: {str(e)}")
    
    # Configurar permisos por rol
    configurar_permisos_por_rol(auth, permisos_menu)

def configurar_permisos_por_rol(auth, permisos_menu):
    """Configurar permisos predeterminados por rol"""
    try:
        print("\nConfigurando permisos por rol...")
        
        # Configuración de permisos por rol
        permisos_roles = {
            'admin': [
                'menu_informacion_basica',
                'menu_control_material',
                'menu_control_produccion',
                'menu_control_proceso',
                'menu_control_calidad',
                'menu_control_resultados',
                'menu_control_reporte',
                'menu_configuracion_programa'
            ],
            'supervisor_almacen': [
                'menu_informacion_basica',
                'menu_control_material'
            ],
            'operador_produccion': [
                'menu_control_produccion',
                'menu_control_proceso'
            ],
            'supervisor_calidad': [
                'menu_informacion_basica',
                'menu_control_calidad',
                'menu_control_resultados'
            ],
            'operador_calidad': [
                'menu_control_calidad'
            ],
            'supervisor_proceso': [
                'menu_informacion_basica',
                'menu_control_proceso',
                'menu_control_reporte'
            ]
        }
        
        for rol, permisos in permisos_roles.items():
            print(f"\n🔧 Configurando permisos para rol '{rol}':")
            for permiso in permisos:
                try:
                    auth.asignar_permiso_boton_a_rol(rol, permiso)
                    print(f"  ✅ {permiso}")
                except Exception as e:
                    print(f"  ⚠️ Error en {permiso}: {str(e)}")
        
        print("\n✅ Configuración de permisos por rol completada")
        
    except Exception as e:
        print(f"⚠️ Error configurando permisos por rol: {str(e)}")

if __name__ == "__main__":
    agregar_permisos_menu_principal()
    print("✅ Proceso completado")
