#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UTILIDAD PARA GESTIÓN DE PERMISOS DE DROPDOWNS
==============================================

Esta utilidad permite gestionar fácilmente los permisos de dropdowns
desde la línea de comandos.

Uso: python gestionar_permisos_dropdowns.py [comando] [argumentos]
"""

import sys
import json
from app.db import get_db_connection

class GestorPermisosDropdowns:
    def __init__(self):
        self.conn = None
    
    def conectar_db(self):
        """Establecer conexión con la base de datos"""
        try:
            self.conn = get_db_connection()
            return True
        except Exception as e:
            print(f"❌ Error conectando a la base de datos: {e}")
            return False
    
    def cerrar_db(self):
        """Cerrar conexión con la base de datos"""
        if self.conn:
            self.conn.close()
    
    def listar_roles(self):
        """Listar todos los roles disponibles"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, nombre, descripcion, nivel FROM roles WHERE activo = 1 ORDER BY nivel DESC')
        roles = cursor.fetchall()
        
        print("\n🎭 ROLES DISPONIBLES:")
        print("-" * 50)
        for rol in roles:
            print(f"{rol['id']:2d}. {rol['nombre']} (Nivel {rol['nivel']})")
            print(f"    {rol['descripcion']}")
    
    def listar_permisos_rol(self, rol_nombre):
        """Listar permisos de dropdowns de un rol específico"""
        cursor = self.conn.cursor()
        
        # Verificar que el rol existe
        cursor.execute('SELECT id, nombre, descripcion FROM roles WHERE nombre = ? AND activo = 1', (rol_nombre,))
        rol = cursor.fetchone()
        
        if not rol:
            print(f"❌ Rol '{rol_nombre}' no encontrado")
            return
        
        # Obtener permisos del rol
        cursor.execute('''
            SELECT pb.pagina, pb.seccion, pb.boton, pb.descripcion
            FROM permisos_botones pb
            JOIN rol_permisos_botones rpb ON pb.id = rpb.permiso_boton_id
            WHERE rpb.rol_id = ? AND pb.activo = 1
            ORDER BY pb.pagina, pb.seccion, pb.boton
        ''', (rol['id'],))
        
        permisos = cursor.fetchall()
        
        print(f"\n🔑 PERMISOS DE DROPDOWNS PARA ROL: {rol['nombre']}")
        print(f"📝 {rol['descripcion']}")
        print("-" * 60)
        
        if not permisos:
            print("⚠️  Este rol no tiene permisos de dropdowns asignados")
            return
        
        # Agrupar por página y sección
        permisos_agrupados = {}
        for permiso in permisos:
            pagina = permiso['pagina']
            if pagina not in permisos_agrupados:
                permisos_agrupados[pagina] = {}
            
            seccion = permiso['seccion']
            if seccion not in permisos_agrupados[pagina]:
                permisos_agrupados[pagina][seccion] = []
            
            permisos_agrupados[pagina][seccion].append(permiso)
        
        for pagina, secciones in permisos_agrupados.items():
            nombre_pagina = pagina.replace('LISTA_', '').replace('_', ' ')
            print(f"\n📋 {nombre_pagina}")
            
            for seccion, botones in secciones.items():
                print(f"  📁 {seccion}")
                for boton in botones:
                    print(f"    ✓ {boton['boton']}")
        
        print(f"\n📊 Total de permisos: {len(permisos)}")
    
    def asignar_permisos_lista_completa(self, rol_nombre, lista_nombre):
        """Asignar todos los permisos de una lista específica a un rol"""
        cursor = self.conn.cursor()
        
        # Verificar que el rol existe
        cursor.execute('SELECT id FROM roles WHERE nombre = ? AND activo = 1', (rol_nombre,))
        rol = cursor.fetchone()
        
        if not rol:
            print(f"❌ Rol '{rol_nombre}' no encontrado")
            return
        
        # Obtener todos los permisos de la lista
        cursor.execute('''
            SELECT id, pagina, seccion, boton 
            FROM permisos_botones 
            WHERE pagina = ? AND activo = 1
        ''', (lista_nombre,))
        
        permisos = cursor.fetchall()
        
        if not permisos:
            print(f"❌ No se encontraron permisos para la lista '{lista_nombre}'")
            return
        
        # Asignar permisos al rol
        permisos_asignados = 0
        for permiso in permisos:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO rol_permisos_botones (rol_id, permiso_boton_id)
                    VALUES (?, ?)
                ''', (rol['id'], permiso['id']))
                
                if cursor.rowcount > 0:
                    permisos_asignados += 1
                    
            except Exception as e:
                print(f"⚠️  Error asignando permiso {permiso['boton']}: {e}")
        
        self.conn.commit()
        
        print(f"✅ Se asignaron {permisos_asignados} permisos de la lista '{lista_nombre}' al rol '{rol_nombre}'")
        print(f"📊 Total de permisos disponibles en la lista: {len(permisos)}")
    
    def remover_todos_permisos_rol(self, rol_nombre):
        """Remover todos los permisos de dropdowns de un rol"""
        cursor = self.conn.cursor()
        
        # Verificar que el rol existe
        cursor.execute('SELECT id FROM roles WHERE nombre = ? AND activo = 1', (rol_nombre,))
        rol = cursor.fetchone()
        
        if not rol:
            print(f"❌ Rol '{rol_nombre}' no encontrado")
            return
        
        # Contar permisos actuales
        cursor.execute('SELECT COUNT(*) FROM rol_permisos_botones WHERE rol_id = ?', (rol['id'],))
        total_permisos = cursor.fetchone()[0]
        
        # Remover todos los permisos
        cursor.execute('DELETE FROM rol_permisos_botones WHERE rol_id = ?', (rol['id'],))
        self.conn.commit()
        
        print(f"✅ Se removieron {total_permisos} permisos del rol '{rol_nombre}'")
    
    def exportar_permisos_rol(self, rol_nombre, archivo_salida=None):
        """Exportar permisos de un rol a archivo JSON"""
        cursor = self.conn.cursor()
        
        # Verificar que el rol existe
        cursor.execute('SELECT id, nombre, descripcion FROM roles WHERE nombre = ? AND activo = 1', (rol_nombre,))
        rol = cursor.fetchone()
        
        if not rol:
            print(f"❌ Rol '{rol_nombre}' no encontrado")
            return
        
        # Obtener permisos del rol
        cursor.execute('''
            SELECT pb.pagina, pb.seccion, pb.boton, pb.descripcion
            FROM permisos_botones pb
            JOIN rol_permisos_botones rpb ON pb.id = rpb.permiso_boton_id
            WHERE rpb.rol_id = ? AND pb.activo = 1
            ORDER BY pb.pagina, pb.seccion, pb.boton
        ''', (rol['id'],))
        
        permisos = cursor.fetchall()
        
        # Preparar datos para exportación
        datos_exportacion = {
            'rol': {
                'nombre': rol['nombre'],
                'descripcion': rol['descripcion']
            },
            'permisos_dropdowns': [dict(permiso) for permiso in permisos],
            'total_permisos': len(permisos),
            'fecha_exportacion': None  # Se puede agregar fecha actual
        }
        
        # Determinar nombre del archivo
        if not archivo_salida:
            archivo_salida = f"permisos_dropdowns_{rol_nombre}.json"
        
        # Escribir archivo
        try:
            with open(archivo_salida, 'w', encoding='utf-8') as f:
                json.dump(datos_exportacion, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Permisos del rol '{rol_nombre}' exportados a '{archivo_salida}'")
            print(f"📊 Total de permisos exportados: {len(permisos)}")
            
        except Exception as e:
            print(f"❌ Error escribiendo archivo: {e}")
    
    def mostrar_estadisticas(self):
        """Mostrar estadísticas generales del sistema de permisos"""
        cursor = self.conn.cursor()
        
        # Contar totales
        cursor.execute('SELECT COUNT(*) FROM permisos_botones WHERE activo = 1')
        total_permisos = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM roles WHERE activo = 1')
        total_roles = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT pagina) FROM permisos_botones WHERE activo = 1')
        total_listas = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM rol_permisos_botones')
        total_asignaciones = cursor.fetchone()[0]
        
        print("\n📊 ESTADÍSTICAS DEL SISTEMA DE PERMISOS DE DROPDOWNS")
        print("=" * 60)
        print(f"🔑 Total de permisos de dropdowns: {total_permisos}")
        print(f"🎭 Total de roles activos: {total_roles}")
        print(f"📋 Total de listas con permisos: {total_listas}")
        print(f"🔗 Total de asignaciones rol-permiso: {total_asignaciones}")
        
        # Mostrar distribución por lista
        cursor.execute('''
            SELECT pagina, COUNT(*) as cantidad
            FROM permisos_botones 
            WHERE activo = 1 
            GROUP BY pagina 
            ORDER BY cantidad DESC
        ''')
        
        distribucion = cursor.fetchall()
        
        print("\n📋 DISTRIBUCIÓN DE PERMISOS POR LISTA:")
        print("-" * 40)
        for lista in distribucion:
            nombre_lista = lista['pagina'].replace('LISTA_', '').replace('_', ' ')
            print(f"{nombre_lista:30s} {lista['cantidad']:3d} permisos")


def mostrar_ayuda():
    """Mostrar información de ayuda"""
    print("""
🔐 GESTOR DE PERMISOS DE DROPDOWNS - ILSAN MES

COMANDOS DISPONIBLES:

  roles                     - Listar todos los roles
  permisos <rol_nombre>     - Listar permisos de un rol
  asignar <rol> <lista>     - Asignar todos los permisos de una lista a un rol
  remover <rol_nombre>      - Remover todos los permisos de un rol
  exportar <rol> [archivo]  - Exportar permisos de un rol a JSON
  estadisticas              - Mostrar estadísticas del sistema
  ayuda                     - Mostrar esta ayuda

EJEMPLOS:

  python gestionar_permisos_dropdowns.py roles
  python gestionar_permisos_dropdowns.py permisos operador_almacen
  python gestionar_permisos_dropdowns.py asignar operador_almacen LISTA_DE_MATERIALES
  python gestionar_permisos_dropdowns.py exportar superadmin admin_permisos.json
  python gestionar_permisos_dropdowns.py estadisticas

LISTAS DISPONIBLES:
  - LISTA_DE_MATERIALES
  - LISTA_INFORMACIONBASICA  
  - LISTA_CONTROLDEPRODUCCION
  - LISTA_CONTROL_DE_PROCESO
  - LISTA_CONTROL_DE_CALIDAD
  - LISTA_DE_CONTROL_DE_RESULTADOS
  - LISTA_DE_CONTROL_DE_REPORTE
  - LISTA_DE_CONFIGPG
""")


def main():
    """Función principal"""
    if len(sys.argv) < 2:
        mostrar_ayuda()
        return
    
    comando = sys.argv[1].lower()
    gestor = GestorPermisosDropdowns()
    
    if not gestor.conectar_db():
        return
    
    try:
        if comando == "ayuda" or comando == "help":
            mostrar_ayuda()
            
        elif comando == "roles":
            gestor.listar_roles()
            
        elif comando == "permisos":
            if len(sys.argv) < 3:
                print("❌ Falta el nombre del rol")
                print("Uso: python gestionar_permisos_dropdowns.py permisos <rol_nombre>")
                return
            gestor.listar_permisos_rol(sys.argv[2])
            
        elif comando == "asignar":
            if len(sys.argv) < 4:
                print("❌ Faltan argumentos")
                print("Uso: python gestionar_permisos_dropdowns.py asignar <rol> <lista>")
                return
            gestor.asignar_permisos_lista_completa(sys.argv[2], sys.argv[3])
            
        elif comando == "remover":
            if len(sys.argv) < 3:
                print("❌ Falta el nombre del rol")
                print("Uso: python gestionar_permisos_dropdowns.py remover <rol_nombre>")
                return
            gestor.remover_todos_permisos_rol(sys.argv[2])
            
        elif comando == "exportar":
            if len(sys.argv) < 3:
                print("❌ Falta el nombre del rol")
                print("Uso: python gestionar_permisos_dropdowns.py exportar <rol> [archivo]")
                return
            archivo = sys.argv[3] if len(sys.argv) > 3 else None
            gestor.exportar_permisos_rol(sys.argv[2], archivo)
            
        elif comando == "estadisticas" or comando == "stats":
            gestor.mostrar_estadisticas()
            
        else:
            print(f"❌ Comando '{comando}' no reconocido")
            mostrar_ayuda()
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Operación cancelada por el usuario")
        
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        
    finally:
        gestor.cerrar_db()


if __name__ == "__main__":
    main()
