#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar que todas las dependencias se instalen correctamente
y no haya conflictos de versiones.
"""

import sys
import subprocess
import importlib

def test_import(module_name, package_name=None):
    """Prueba importar un módulo y muestra su versión."""
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, '__version__', 'Versión no disponible')
        print(f"✓ {package_name or module_name}: {version}")
        return True
    except ImportError as e:
        print(f"✗ {package_name or module_name}: Error - {e}")
        return False

def main():
    print("=" * 50)
    print("PRUEBA DE DEPENDENCIAS - ISEMM MES")
    print("=" * 50)
    
    # Lista de módulos a probar
    modules_to_test = [
        ('flask', 'Flask'),
        ('werkzeug', 'Werkzeug'),
        ('pymysql', 'PyMySQL'),
        ('dotenv', 'python-dotenv'),
        ('pandas', 'Pandas'),
        ('openpyxl', 'OpenPyXL'),
        ('xlrd', 'XLRD'),
        ('bs4', 'BeautifulSoup4'),
        ('flask_cors', 'Flask-CORS'),
        ('requests', 'Requests'),
        ('psutil', 'PSUtil'),
        ('pytz', 'PyTZ')
    ]
    
    success_count = 0
    total_count = len(modules_to_test)
    
    print("\nProbando importaciones:")
    print("-" * 30)
    
    for module_name, package_name in modules_to_test:
        if test_import(module_name, package_name):
            success_count += 1
    
    print("-" * 30)
    print(f"Resultado: {success_count}/{total_count} módulos importados correctamente")
    
    if success_count == total_count:
        print("\n🎉 ¡Todas las dependencias están instaladas correctamente!")
        return True
    else:
        print(f"\n⚠️  Faltan {total_count - success_count} dependencias por instalar")
        print("\nPara instalar las dependencias faltantes, ejecuta:")
        print("pip install -r requirements.txt")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)