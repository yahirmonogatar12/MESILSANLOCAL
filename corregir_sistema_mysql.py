#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corregir incompatibilidades SQLite-MySQL en archivos específicos del sistema
"""

import os
import shutil
from datetime import datetime

def crear_backup(archivo_path):
    """Crear backup de un archivo"""
    backup_path = f"{archivo_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(archivo_path, backup_path)
    print(f"📁 Backup: {backup_path}")
    return backup_path

def corregir_routes_py():
    """Corregir routes.py"""
    archivo = "app/routes.py"
    print(f"🔧 Corrigiendo {archivo}")
    
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Crear backup
        crear_backup(archivo)
        
        # Correcciones específicas
        # 1. sqlite_master -> INFORMATION_SCHEMA
        contenido = contenido.replace(
            'cursor.execute("SELECT name FROM sqlite_master WHERE type=\'table\' AND name=\'salidas_material\'")',
            'cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = \'salidas_material\'")')
        
        contenido = contenido.replace(
            'cursor.execute("SELECT name FROM sqlite_master WHERE type=\'table\' AND name=\'control_material_almacen\'")',
            'cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = \'control_material_almacen\'")')
        
        # 2. datetime('now') -> NOW()
        contenido = contenido.replace("datetime('now')", "NOW()")
        
        # 3. INSERT OR REPLACE -> INSERT ... ON DUPLICATE KEY UPDATE
        contenido = contenido.replace(
            "INSERT OR REPLACE INTO inventario_general",
            "INSERT INTO inventario_general"
        )
        
        # Agregar ON DUPLICATE KEY UPDATE para inventario_general
        if "INSERT INTO inventario_general" in contenido and "ON DUPLICATE KEY UPDATE" not in contenido:
            contenido = contenido.replace(
                "INSERT INTO inventario_general \n            (numero_parte, cantidad_entradas, cantidad_salidas, cantidad_total, fecha_actualizacion)\n            VALUES (?, ?, ?, ?, NOW())",
                "INSERT INTO inventario_general \n            (numero_parte, cantidad_entradas, cantidad_salidas, cantidad_total, fecha_actualizacion)\n            VALUES (%s, %s, %s, %s, NOW()) ON DUPLICATE KEY UPDATE cantidad_entradas = VALUES(cantidad_entradas), cantidad_salidas = VALUES(cantidad_salidas), cantidad_total = VALUES(cantidad_total), fecha_actualizacion = VALUES(fecha_actualizacion)"
            )
        
        # 4. Placeholders ? -> %s
        contenido = contenido.replace("?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?", "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s")
        contenido = contenido.replace("?, ?, ?, ?, ?, ?, ?, ?", "%s, %s, %s, %s, %s, %s, %s, %s")
        contenido = contenido.replace("?, ?, ?, ?, ?, ?, ?", "%s, %s, %s, %s, %s, %s, %s")
        contenido = contenido.replace("?, ?, ?, ?, ?, ?", "%s, %s, %s, %s, %s, %s")
        contenido = contenido.replace("?, ?, ?, ?, ?", "%s, %s, %s, %s, %s")
        contenido = contenido.replace("?, ?, ?, ?", "%s, %s, %s, %s")
        contenido = contenido.replace("?, ?, ?", "%s, %s, %s")
        contenido = contenido.replace("?, ?", "%s, %s")
        contenido = contenido.replace("= ?", "= %s")
        contenido = contenido.replace("(?)", "(%s)")
        
        # Escribir archivo corregido
        with open(archivo, 'w', encoding='utf-8') as f:
            f.write(contenido)
        
        print(f"✅ {archivo} corregido")
        return True
        
    except Exception as e:
        print(f"❌ Error en {archivo}: {e}")
        return False

def corregir_admin_api_py():
    """Corregir admin_api.py"""
    archivo = "app/admin_api.py"
    print(f"🔧 Corrigiendo {archivo}")
    
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Crear backup
        crear_backup(archivo)
        
        # Correcciones
        contenido = contenido.replace("datetime('now')", "NOW()")
        contenido = contenido.replace("?, ?, datetime('now')", "%s, %s, NOW()")
        contenido = contenido.replace("?, ?", "%s, %s")
        contenido = contenido.replace("= ?", "= %s")
        
        # Escribir archivo corregido
        with open(archivo, 'w', encoding='utf-8') as f:
            f.write(contenido)
        
        print(f"✅ {archivo} corregido")
        return True
        
    except Exception as e:
        print(f"❌ Error en {archivo}: {e}")
        return False

def corregir_user_admin_py():
    """Corregir user_admin.py"""
    archivo = "app/user_admin.py"
    print(f"🔧 Corrigiendo {archivo}")
    
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Crear backup
        crear_backup(archivo)
        
        # Correcciones
        contenido = contenido.replace("datetime('now', '-15 minutes')", "DATE_SUB(NOW(), INTERVAL 15 MINUTE)")
        contenido = contenido.replace("?, ?, ?", "%s, %s, %s")
        contenido = contenido.replace("?, ?, ?, ?", "%s, %s, %s, %s")
        contenido = contenido.replace("?, ?", "%s, %s")
        contenido = contenido.replace("= ?", "= %s")
        contenido = contenido.replace("CURRENT_TIMESTAMP", "NOW()")
        
        # Escribir archivo corregido
        with open(archivo, 'w', encoding='utf-8') as f:
            f.write(contenido)
        
        print(f"✅ {archivo} corregido")
        return True
        
    except Exception as e:
        print(f"❌ Error en {archivo}: {e}")
        return False

def corregir_auth_system_py():
    """Corregir auth_system.py"""
    archivo = "app/auth_system.py"
    print(f"🔧 Corrigiendo {archivo}")
    
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Crear backup
        crear_backup(archivo)
        
        # Correcciones para SQLite fallback
        contenido = contenido.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "INT AUTO_INCREMENT PRIMARY KEY")
        contenido = contenido.replace("AUTOINCREMENT", "AUTO_INCREMENT")
        contenido = contenido.replace("?, ?, ?", "%s, %s, %s")
        contenido = contenido.replace("?, ?, ?, ?", "%s, %s, %s, %s")
        contenido = contenido.replace("?, ?", "%s, %s")
        contenido = contenido.replace("= ?", "= %s")
        contenido = contenido.replace("(?)", "(%s)")
        
        # Escribir archivo corregido
        with open(archivo, 'w', encoding='utf-8') as f:
            f.write(contenido)
        
        print(f"✅ {archivo} corregido")
        return True
        
    except Exception as e:
        print(f"❌ Error en {archivo}: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 Corrigiendo incompatibilidades SQLite-MySQL")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    archivos_corregidos = 0
    
    # Corregir archivos principales
    if corregir_routes_py():
        archivos_corregidos += 1
    
    if corregir_admin_api_py():
        archivos_corregidos += 1
    
    if corregir_user_admin_py():
        archivos_corregidos += 1
    
    if corregir_auth_system_py():
        archivos_corregidos += 1
    
    print("="*50)
    print(f"📊 Archivos corregidos: {archivos_corregidos}/4")
    print("✅ Corrección completada")
    
    if archivos_corregidos > 0:
        print("\n⚠️ IMPORTANTE:")
        print("• Se crearon backups de los archivos modificados")
        print("• Reinicia la aplicación para aplicar los cambios")

if __name__ == "__main__":
    main()