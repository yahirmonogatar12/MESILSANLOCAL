#!/usr/bin/env python3
"""
Script para agregar la columna usuario_registro a la tabla materiales si no existe
"""
import sys
import os

# Agregar el directorio de la aplicación al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db_mysql import agregar_columna_usuario_registro

if __name__ == "__main__":
    print("🔧 Ejecutando migración: Agregar columna usuario_registro")
    resultado = agregar_columna_usuario_registro()
    
    if resultado:
        print("✅ Migración completada exitosamente")
    else:
        print("❌ Error en la migración")
        sys.exit(1)
