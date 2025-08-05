#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificar configuración SMT Simple
"""

import os

def verificar_archivos():
    """Verificar que todos los archivos estén creados"""
    archivos = [
        'app/smt_routes_simple.py',
        'app/templates/smt_simple.html',
        'recreate_simple_smt.py',
        'activate_smt_simple.py'
    ]
    
    print("🔍 Verificando archivos...")
    
    for archivo in archivos:
        if os.path.exists(archivo):
            size = os.path.getsize(archivo)
            print(f"✅ {archivo} ({size} bytes)")
        else:
            print(f"❌ {archivo} - NO EXISTE")
    
    return all(os.path.exists(f) for f in archivos)

def main():
    print("🚀 Verificación SMT Simple\n")
    
    if verificar_archivos():
        print("\n✅ Todos los archivos están listos")
        print("\n📋 Siguiente paso:")
        print("1. Ejecuta: python recreate_simple_smt.py")
        print("2. Reinicia el servidor: python run.py")
        print("3. Ve a: http://127.0.0.1:5000/smt-simple")
        print("\n🎯 URL directa: http://127.0.0.1:5000/smt-simple")
    else:
        print("\n❌ Faltan archivos")

if __name__ == "__main__":
    main()
