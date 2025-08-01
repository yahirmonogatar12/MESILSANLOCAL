#!/usr/bin/env python3
"""
Script para diagnosticar y resolver conflictos de dependencias en el hosting
"""

import subprocess
import sys
import os

def run_command(command):
    """Ejecuta un comando y retorna el resultado"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_python_version():
    """Verifica la versión de Python"""
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    
def install_minimal_requirements():
    """Instala dependencias mínimas una por una"""
    minimal_packages = [
        "Flask>=2.3.0",
        "Werkzeug>=2.3.0",
        "pymysql>=1.0.0",
        "python-dotenv>=1.0.0",
        "flask-cors>=4.0.0",
        "requests>=2.30.0"
    ]
    
    print("\n=== Instalando dependencias mínimas ===")
    for package in minimal_packages:
        print(f"\nInstalando {package}...")
        success, stdout, stderr = run_command(f"pip install '{package}'")
        if success:
            print(f"✓ {package} instalado correctamente")
        else:
            print(f"✗ Error instalando {package}:")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")

def check_installed_packages():
    """Verifica qué paquetes están instalados"""
    print("\n=== Paquetes instalados ===")
    success, stdout, stderr = run_command("pip list")
    if success:
        lines = stdout.split('\n')
        relevant_packages = ['Flask', 'Werkzeug', 'pymysql', 'python-dotenv', 'flask-cors', 'requests']
        for line in lines:
            for package in relevant_packages:
                if package.lower() in line.lower():
                    print(line)
    else:
        print(f"Error obteniendo lista de paquetes: {stderr}")

def check_conflicts():
    """Verifica conflictos de dependencias"""
    print("\n=== Verificando conflictos ===")
    success, stdout, stderr = run_command("pip check")
    if success:
        print("✓ No se encontraron conflictos de dependencias")
    else:
        print(f"✗ Conflictos encontrados:")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")

def test_imports():
    """Prueba importar los módulos principales"""
    print("\n=== Probando imports ===")
    modules_to_test = [
        'flask',
        'pymysql',
        'dotenv',
        'flask_cors',
        'requests'
    ]
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✓ {module} importado correctamente")
        except ImportError as e:
            print(f"✗ Error importando {module}: {e}")

def main():
    print("=== DIAGNÓSTICO DE DEPENDENCIAS PARA HOSTING ===")
    print("Este script ayuda a resolver conflictos de dependencias\n")
    
    # Verificar versión de Python
    check_python_version()
    
    # Verificar paquetes instalados
    check_installed_packages()
    
    # Verificar conflictos
    check_conflicts()
    
    # Preguntar si instalar dependencias mínimas
    response = input("\n¿Deseas instalar las dependencias mínimas? (y/n): ")
    if response.lower() in ['y', 'yes', 's', 'si']:
        install_minimal_requirements()
        
        # Verificar nuevamente después de la instalación
        check_installed_packages()
        check_conflicts()
    
    # Probar imports
    test_imports()
    
    print("\n=== INSTRUCCIONES PARA EL HOSTING ===")
    print("1. Sube este script al hosting")
    print("2. Ejecuta: python fix_hosting_dependencies.py")
    print("3. Si hay errores, instala manualmente:")
    print("   pip install Flask==2.3.3")
    print("   pip install pymysql==1.1.0")
    print("   pip install python-dotenv==1.0.0")
    print("   pip install flask-cors==4.0.0")
    print("   pip install requests==2.31.0")
    print("4. Usa requirements_hosting.txt en lugar de requirements.txt")

if __name__ == "__main__":
    main()