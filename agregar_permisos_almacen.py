#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para agregar permisos de botones para Control de Material de Almacén
"""

from app.auth_system import AuthSystem

def agregar_permisos_almacen():
    """Agrega los permisos de botones para la página de Control de Material de Almacén"""
    auth = AuthSystem()
    
    # Permisos para Control de Material de Almacén
    permisos_almacen = [
        {
            'nombre_boton': 'control_almacen_guardar',
            'descripcion': 'Botón Guardar en Control de Material de Almacén',
            'pagina': 'control_material_almacen'
        },
        {
            'nombre_boton': 'control_almacen_imprimir',
            'descripcion': 'Botón Imprimir en Control de Material de Almacén',
            'pagina': 'control_material_almacen'
        },
        {
            'nombre_boton': 'control_almacen_config_impresora',
            'descripcion': 'Botón Configurar Impresora en Control de Material de Almacén',
            'pagina': 'control_material_almacen'
        },
        {
            'nombre_boton': 'control_almacen_consultar',
            'descripcion': 'Botón Consultar en Control de Material de Almacén',
            'pagina': 'control_material_almacen'
        },
        {
            'nombre_boton': 'control_almacen_exportar_excel',
            'descripcion': 'Botón Exportar Excel en Control de Material de Almacén',
            'pagina': 'control_material_almacen'
        }
    ]
    
    print("Agregando permisos de botones para Control de Material de Almacén...")
    
    for permiso in permisos_almacen:
        try:
            auth.agregar_permiso_boton(
                nombre_boton=permiso['nombre_boton'],
                descripcion=permiso['descripcion'],
                pagina=permiso['pagina']
            )
            print(f"✅ Permiso agregado: {permiso['nombre_boton']}")
        except Exception as e:
            print(f"⚠️ Error agregando permiso {permiso['nombre_boton']}: {str(e)}")
    
    # Asignar todos los permisos al rol superadmin
    try:
        print("\nAsignando permisos a superadmin...")
        for permiso in permisos_almacen:
            auth.asignar_permiso_boton_a_rol('superadmin', permiso['nombre_boton'])
        print("✅ Permisos asignados a superadmin")
    except Exception as e:
        print(f"⚠️ Error asignando permisos a superadmin: {str(e)}")

if __name__ == "__main__":
    agregar_permisos_almacen()
    print("✅ Proceso completado")
