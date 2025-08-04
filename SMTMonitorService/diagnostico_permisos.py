#!/usr/bin/env python3
"""
Diagnóstico de permisos y acceso a carpetas
"""

import os
import sys
import getpass
import subprocess

def diagnosticar_sistema():
    print("=== DIAGNÓSTICO DE SISTEMA ===")
    print(f"Usuario actual: {getpass.getuser()}")
    print(f"Python ejecutándose desde: {sys.executable}")
    print(f"Directorio de trabajo: {os.getcwd()}")
    print()

def verificar_ruta_base():
    print("=== VERIFICACIÓN RUTA BASE ===")
    base_path = r"C:\LOT CHECK  ALL"
    
    print(f"Ruta base: {base_path}")
    print(f"Existe: {os.path.exists(base_path)}")
    
    if os.path.exists(base_path):
        print(f"Es directorio: {os.path.isdir(base_path)}")
        try:
            contenido = os.listdir(base_path)
            print(f"Contenido ({len(contenido)} elementos):")
            for item in sorted(contenido):
                item_path = os.path.join(base_path, item)
                tipo = "DIR" if os.path.isdir(item_path) else "FILE"
                print(f"  {tipo}: {item}")
        except PermissionError:
            print("ERROR: Sin permisos para listar el contenido")
        except Exception as e:
            print(f"ERROR: {e}")
    else:
        print("La ruta base no existe o no es accesible")
    print()

def verificar_carpetas_linea():
    print("=== VERIFICACIÓN CARPETAS POR LÍNEA ===")
    base_path = r"C:\LOT CHECK  ALL"
    
    lines = ["1line", "2line", "3line", "4line"]
    
    for line in lines:
        line_path = os.path.join(base_path, line)
        print(f"\n{line}: {line_path}")
        print(f"  Existe: {os.path.exists(line_path)}")
        
        if os.path.exists(line_path):
            try:
                subcarpetas = os.listdir(line_path)
                print(f"  Subcarpetas ({len(subcarpetas)}):")
                for sub in sorted(subcarpetas):
                    sub_path = os.path.join(line_path, sub)
                    if os.path.isdir(sub_path):
                        print(f"    DIR: {sub}")
                    else:
                        print(f"    FILE: {sub}")
            except Exception as e:
                print(f"  ERROR: {e}")

def verificar_unidades():
    print("=== VERIFICACIÓN DE UNIDADES ===")
    try:
        # Verificar si C: es una unidad local o de red
        result = subprocess.run(['wmic', 'logicaldisk', 'get', 'caption,description,drivetype'], 
                              capture_output=True, text=True)
        print("Unidades disponibles:")
        print(result.stdout)
    except Exception as e:
        print(f"No se pudo verificar unidades: {e}")
    print()

def main():
    diagnosticar_sistema()
    verificar_unidades()
    verificar_ruta_base() 
    verificar_carpetas_linea()
    
    print("=== RECOMENDACIONES ===")
    print("1. Si las carpetas existen pero no se ven:")
    print("   - Ejecutar como administrador")
    print("   - Verificar permisos de la carpeta")
    print("2. Si C:\\LOT CHECK ALL es una unidad de red:")
    print("   - Mapear la unidad para SYSTEM")
    print("   - O usar UNC path (\\\\servidor\\carpeta)")
    print("3. Si las subcarpetas no aparecen:")
    print("   - Verificar nombres exactos (espacios, mayúsculas)")
    print("   - Crear carpetas faltantes manualmente")

if __name__ == "__main__":
    main()
    input("\nPresiona Enter para continuar...")
