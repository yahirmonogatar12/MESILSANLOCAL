#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnóstico y solución de problemas de importación de Excel
"""

import os
import sys
import subprocess
import importlib.util

def check_python_version():
    """Verificar versión de Python"""
    print("=== VERIFICACIÓN DE PYTHON ===")
    version = sys.version_info
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("⚠️  Se recomienda Python 3.7 o superior")
        return False
    return True

def check_dependencies():
    """Verificar dependencias requeridas"""
    print("\n=== VERIFICACIÓN DE DEPENDENCIAS ===")
    
    required_packages = {
        'flask': 'Flask',
        'pandas': 'pandas', 
        'openpyxl': 'openpyxl',
        'xlrd': 'xlrd',
        'werkzeug': 'Werkzeug'
    }
    
    missing_packages = []
    installed_packages = []
    
    for package, display_name in required_packages.items():
        try:
            spec = importlib.util.find_spec(package)
            if spec is not None:
                print(f"✓ {display_name} instalado")
                installed_packages.append(package)
            else:
                print(f"✗ {display_name} NO instalado")
                missing_packages.append(package)
        except Exception as e:
            print(f"✗ {display_name} ERROR: {str(e)}")
            missing_packages.append(package)
    
    return missing_packages, installed_packages

def install_missing_packages(missing_packages):
    """Instalar paquetes faltantes"""
    if not missing_packages:
        return True
    
    print(f"\n=== INSTALANDO PAQUETES FALTANTES ===")
    
    try:
        for package in missing_packages:
            print(f"Instalando {package}...")
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', package], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✓ {package} instalado correctamente")
            else:
                print(f"✗ Error instalando {package}: {result.stderr}")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error durante la instalación: {str(e)}")
        return False

def test_pandas_excel():
    """Probar lectura de Excel con pandas"""
    print("\n=== PRUEBA DE LECTURA EXCEL ===")
    
    try:
        import pandas as pd
        
        # Crear datos de prueba
        data = {
            'Codigo de material': ['TEST001', 'TEST002'],
            'Numero de parte': ['PART001', 'PART002'],
            'Propiedad de material': ['PART', 'ETC'],
            'Classification': ['CHIP', 'CAP'],
            'Especificacion de material': ['Test spec 1', 'Test spec 2'],
            'Unidad de empaque': ['1000', '2000'],
            'Ubicacion de material': ['A1', 'B2'],
            'Vendedor': ['Vendor1', 'Vendor2'],
            'Prohibido sacar': ['No', 'Si'],
            'Reparable': ['Si', 'No'],
            'Nivel de MSL': ['1', '2'],
            'Espesor de MSL': ['0.5', '1.0'],
            'Fecha de registro': ['2024-01-01', '2024-01-02']
        }
        
        df = pd.DataFrame(data)
        
        # Guardar como Excel
        test_file = 'test_excel_functionality.xlsx'
        df.to_excel(test_file, index=False)
        print(f"✓ Archivo de prueba creado: {test_file}")
        
        # Intentar leer el archivo
        df_read = pd.read_excel(test_file, engine='openpyxl')
        print(f"✓ Archivo leído correctamente")
        print(f"  - Filas: {len(df_read)}")
        print(f"  - Columnas: {len(df_read.columns)}")
        
        # Verificar contenido
        if len(df_read) == len(df) and len(df_read.columns) == len(df.columns):
            print("✓ Contenido verificado correctamente")
        else:
            print("⚠️  Contenido no coincide completamente")
        
        # Limpiar archivo de prueba
        os.remove(test_file)
        print("✓ Archivo de prueba eliminado")
        
        return True
        
    except Exception as e:
        print(f"✗ Error en prueba de Excel: {str(e)}")
        return False

def check_database():
    """Verificar acceso a base de datos"""
    print("\n=== VERIFICACIÓN DE BASE DE DATOS ===")
    
    try:
        # Intentar importar la función de conexión
        app_path = os.path.join(os.path.dirname(__file__), 'app')
        sys.path.insert(0, app_path)
        
        try:
            from db import get_db_connection
        except ImportError:
            # Si no se puede importar, intentar con ruta absoluta
            import sqlite3
            def get_db_connection():
                db_path = os.path.join(app_path, 'database', 'ISEMM_MES.db')
                if not os.path.exists(db_path):
                    db_path = os.path.join(os.path.dirname(__file__), 'app', 'database', 'ISEMM_MES.db')
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                return conn
        
        # Probar conexión
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar tabla materiales
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='materiales'")
        result = cursor.fetchone()
        
        if result:
            print("✓ Tabla 'materiales' existe")
            
            # Contar registros
            cursor.execute("SELECT COUNT(*) FROM materiales")
            count = cursor.fetchone()[0]
            print(f"✓ Registros en tabla: {count}")
            
        else:
            print("⚠️  Tabla 'materiales' no existe")
            print("   Se creará automáticamente al ejecutar la aplicación")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error de base de datos: {str(e)}")
        return False

def check_file_permissions():
    """Verificar permisos de archivos"""
    print("\n=== VERIFICACIÓN DE PERMISOS ===")
    
    try:
        # Verificar directorio actual
        current_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"✓ Directorio de trabajo: {current_dir}")
        
        # Verificar escritura
        test_file = os.path.join(current_dir, 'test_permissions.txt')
        with open(test_file, 'w') as f:
            f.write('test')
        
        os.remove(test_file)
        print("✓ Permisos de escritura OK")
        
        # Verificar directorio de la aplicación
        app_dir = os.path.join(current_dir, 'app')
        if os.path.exists(app_dir):
            print(f"✓ Directorio app encontrado: {app_dir}")
        else:
            print(f"⚠️  Directorio app no encontrado: {app_dir}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error de permisos: {str(e)}")
        return False

def generate_report():
    """Generar reporte de diagnóstico"""
    print("\n=== GENERANDO REPORTE ===")
    
    try:
        report_content = f"""
REPORTE DE DIAGNÓSTICO - IMPORTACIÓN EXCEL
==========================================

Fecha: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Python: {sys.version}
Directorio: {os.path.dirname(os.path.abspath(__file__))}

VERIFICACIONES REALIZADAS:
- Versión de Python
- Dependencias instaladas
- Funcionalidad de Excel
- Acceso a base de datos
- Permisos de archivos

Si hay problemas, consulte el archivo SOLUCION_EXCEL.md
"""
        
        with open('diagnostico_excel.txt', 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print("✓ Reporte guardado en: diagnostico_excel.txt")
        return True
        
    except Exception as e:
        print(f"✗ Error generando reporte: {str(e)}")
        return False

def main():
    """Función principal de diagnóstico"""
    print("=" * 60)
    print("DIAGNÓSTICO DE IMPORTACIÓN DE EXCEL")
    print("=" * 60)
    
    # Lista de verificaciones
    checks = [
        ("Versión de Python", check_python_version),
        ("Dependencias", lambda: check_dependencies()[0] == []),
        ("Funcionalidad Excel", test_pandas_excel),
        ("Base de datos", check_database),
        ("Permisos de archivo", check_file_permissions)
    ]
    
    results = []
    
    # Ejecutar verificaciones
    for name, check_func in checks:
        try:
            if name == "Dependencias":
                missing, installed = check_dependencies()
                if missing:
                    print(f"\n⚠️  Instalando dependencias faltantes...")
                    if install_missing_packages(missing):
                        print("✓ Todas las dependencias están instaladas")
                        results.append((name, True))
                    else:
                        print("✗ Error instalando dependencias")
                        results.append((name, False))
                else:
                    results.append((name, True))
            else:
                result = check_func()
                results.append((name, result))
        except Exception as e:
            print(f"✗ Error en {name}: {str(e)}")
            results.append((name, False))
    
    # Mostrar resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE DIAGNÓSTICO")
    print("=" * 60)
    
    passed = 0
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")
        if result:
            passed += 1
    
    print(f"\nPruebas pasadas: {passed}/{len(results)}")
    
    if passed == len(results):
        print("\n🎉 ¡Todo está configurado correctamente!")
        print("   La importación de Excel debería funcionar sin problemas.")
    else:
        print(f"\n⚠️  Se encontraron {len(results) - passed} problemas.")
        print("   Consulte el archivo SOLUCION_EXCEL.md para más detalles.")
    
    # Generar reporte
    generate_report()
    
    print("\n" + "=" * 60)
    print("ARCHIVOS ÚTILES CREADOS:")
    print("- SOLUCION_EXCEL.md: Guía de solución de problemas")
    print("- diagnostico_excel.txt: Reporte de este diagnóstico")
    print("- crear_plantilla.py: Script para crear plantillas Excel")
    print("- test_importacion.py: Script para probar importación")
    print("=" * 60)

if __name__ == "__main__":
    main()
