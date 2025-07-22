#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GESTIÓN SIMPLIFICADA DE PERMISOS DE DROPDOWNS
============================================
Herramienta para administrar solo los permisos de dropdowns de información básica
"""

import sqlite3
import sys

class GestorPermisosDropdowns:
    def __init__(self):
        self.conn = sqlite3.connect('app/database/ISEMM_MES.db')
        self.cursor = self.conn.cursor()
    
    def listar_dropdowns_disponibles(self):
        """Listar todos los dropdowns de información básica disponibles"""
        print("=== DROPDOWNS DE INFORMACIÓN BÁSICA DISPONIBLES ===")
        
        self.cursor.execute('''
            SELECT id, boton, descripcion 
            FROM permisos_botones 
            WHERE pagina = 'informacion_basica' 
            ORDER BY boton
        ''')
        
        dropdowns = self.cursor.fetchall()
        print(f"Total de dropdowns: {len(dropdowns)}\n")
        
        for i, d in enumerate(dropdowns, 1):
            print(f"{i:2d}. {d[1]} - {d[2] or 'Sin descripción'}")
        
        return dropdowns
    
    def listar_roles(self):
        """Listar roles disponibles"""
        print("\n=== ROLES DISPONIBLES ===")
        
        self.cursor.execute('SELECT id, nombre, descripcion FROM roles ORDER BY nivel DESC')
        roles = self.cursor.fetchall()
        
        for i, r in enumerate(roles, 1):
            print(f"{i:2d}. {r[1]} - {r[2]}")
        
        return roles
    
    def ver_permisos_rol(self, rol_nombre):
        """Ver permisos actuales de un rol específico"""
        print(f"\n=== PERMISOS DE DROPDOWNS PARA: {rol_nombre.upper()} ===")
        
        self.cursor.execute('''
            SELECT pb.boton, pb.descripcion
            FROM rol_permisos_botones rpb
            JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
            JOIN roles r ON rpb.rol_id = r.id
            WHERE r.nombre = ? AND pb.pagina = 'informacion_basica'
            ORDER BY pb.boton
        ''', (rol_nombre,))
        
        permisos = self.cursor.fetchall()
        
        if permisos:
            print(f"Dropdowns habilitados ({len(permisos)}):")
            for p in permisos:
                print(f"   ✅ {p[0]} - {p[1] or 'Sin descripción'}")
        else:
            print("   ❌ Sin permisos de dropdowns asignados")
        
        return permisos
    
    def asignar_permiso_dropdown(self, rol_nombre, dropdown_boton):
        """Asignar un permiso de dropdown específico a un rol"""
        try:
            # Obtener IDs
            self.cursor.execute('SELECT id FROM roles WHERE nombre = ?', (rol_nombre,))
            rol_result = self.cursor.fetchone()
            if not rol_result:
                print(f"❌ Rol '{rol_nombre}' no encontrado")
                return False
            rol_id = rol_result[0]
            
            self.cursor.execute('''
                SELECT id FROM permisos_botones 
                WHERE pagina = 'informacion_basica' AND boton = ?
            ''', (dropdown_boton,))
            permiso_result = self.cursor.fetchone()
            if not permiso_result:
                print(f"❌ Dropdown '{dropdown_boton}' no encontrado")
                return False
            permiso_id = permiso_result[0]
            
            # Verificar si ya existe
            self.cursor.execute('''
                SELECT COUNT(*) FROM rol_permisos_botones 
                WHERE rol_id = ? AND permiso_boton_id = ?
            ''', (rol_id, permiso_id))
            
            if self.cursor.fetchone()[0] > 0:
                print(f"⚠️ El rol '{rol_nombre}' ya tiene el permiso '{dropdown_boton}'")
                return True
            
            # Asignar permiso
            self.cursor.execute('''
                INSERT INTO rol_permisos_botones (rol_id, permiso_boton_id) 
                VALUES (?, ?)
            ''', (rol_id, permiso_id))
            
            self.conn.commit()
            print(f"✅ Permiso '{dropdown_boton}' asignado a '{rol_nombre}'")
            return True
            
        except Exception as e:
            print(f"❌ Error asignando permiso: {e}")
            return False
    
    def remover_permiso_dropdown(self, rol_nombre, dropdown_boton):
        """Remover un permiso de dropdown específico de un rol"""
        try:
            self.cursor.execute('''
                DELETE FROM rol_permisos_botones 
                WHERE rol_id = (SELECT id FROM roles WHERE nombre = ?)
                AND permiso_boton_id = (
                    SELECT id FROM permisos_botones 
                    WHERE pagina = 'informacion_basica' AND boton = ?
                )
            ''', (rol_nombre, dropdown_boton))
            
            if self.cursor.rowcount > 0:
                self.conn.commit()
                print(f"✅ Permiso '{dropdown_boton}' removido de '{rol_nombre}'")
                return True
            else:
                print(f"⚠️ El rol '{rol_nombre}' no tenía el permiso '{dropdown_boton}'")
                return False
                
        except Exception as e:
            print(f"❌ Error removiendo permiso: {e}")
            return False
    
    def configurar_supervisor_almacen(self):
        """Configuración rápida para supervisor de almacén"""
        print("\n=== CONFIGURACIÓN RÁPIDA: SUPERVISOR DE ALMACÉN ===")
        
        # Dropdowns recomendados para supervisor de almacén
        dropdowns_supervisor = [
            'info_control_bom',
            'info_informacion_material', 
            'info_numero_parte_material',
            'info_configuracion_msls'  # Agregar este importante
        ]
        
        print("Asignando permisos recomendados...")
        for dropdown in dropdowns_supervisor:
            self.asignar_permiso_dropdown('supervisor_almacen', dropdown)
        
        print("\nPermisos finales:")
        self.ver_permisos_rol('supervisor_almacen')
    
    def menu_interactivo(self):
        """Menú interactivo para administrar permisos"""
        while True:
            print("\n" + "="*60)
            print("GESTIÓN DE PERMISOS DE DROPDOWNS")
            print("="*60)
            print("1. Ver dropdowns disponibles")
            print("2. Ver roles disponibles") 
            print("3. Ver permisos de un rol")
            print("4. Asignar permiso a rol")
            print("5. Remover permiso de rol")
            print("6. Configuración rápida: Supervisor de Almacén")
            print("7. Configuración rápida: Operador de Almacén")
            print("0. Salir")
            print("-"*60)
            
            try:
                opcion = input("Selecciona una opción: ").strip()
                
                if opcion == "0":
                    break
                elif opcion == "1":
                    self.listar_dropdowns_disponibles()
                elif opcion == "2":
                    self.listar_roles()
                elif opcion == "3":
                    rol = input("Nombre del rol: ").strip()
                    if rol:
                        self.ver_permisos_rol(rol)
                elif opcion == "4":
                    rol = input("Nombre del rol: ").strip()
                    dropdown = input("Nombre del dropdown (info_xxx): ").strip()
                    if rol and dropdown:
                        self.asignar_permiso_dropdown(rol, dropdown)
                elif opcion == "5":
                    rol = input("Nombre del rol: ").strip()
                    dropdown = input("Nombre del dropdown (info_xxx): ").strip()
                    if rol and dropdown:
                        self.remover_permiso_dropdown(rol, dropdown)
                elif opcion == "6":
                    self.configurar_supervisor_almacen()
                elif opcion == "7":
                    self.configurar_operador_almacen()
                else:
                    print("❌ Opción no válida")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Saliendo...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def configurar_operador_almacen(self):
        """Configuración rápida para operador de almacén"""
        print("\n=== CONFIGURACIÓN RÁPIDA: OPERADOR DE ALMACÉN ===")
        
        # Dropdowns básicos para operador
        dropdowns_operador = [
            'info_informacion_material',
            'info_numero_parte_material'
        ]
        
        print("Asignando permisos básicos...")
        for dropdown in dropdowns_operador:
            self.asignar_permiso_dropdown('operador_almacen', dropdown)
        
        print("\nPermisos finales:")
        self.ver_permisos_rol('operador_almacen')
    
    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()

def main():
    gestor = GestorPermisosDropdowns()
    
    if len(sys.argv) > 1:
        comando = sys.argv[1]
        if comando == "supervisor":
            gestor.configurar_supervisor_almacen()
        elif comando == "operador":
            gestor.configurar_operador_almacen()
        elif comando == "ver":
            if len(sys.argv) > 2:
                gestor.ver_permisos_rol(sys.argv[2])
            else:
                print("Uso: python gestionar_dropdowns.py ver <nombre_rol>")
    else:
        gestor.menu_interactivo()

if __name__ == "__main__":
    main()
