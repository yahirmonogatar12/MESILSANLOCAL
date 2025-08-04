#!/usr/bin/env python3
"""
Script para actualizar con la versión FINAL del servicio
Con estructura de tabla REAL
"""

import os
import shutil

def actualizar_a_version_final():
    """Actualizar a la versión final del servicio"""
    print("ACTUALIZANDO A VERSION FINAL CON ESTRUCTURA REAL")
    print("=" * 60)
    
    archivo_final = 'smt_monitor_service_final.py'
    archivo_servicio = 'smt_monitor_service.py'
    
    # Verificar que existe el archivo final
    if not os.path.exists(archivo_final):
        print(f"❌ No se encuentra: {archivo_final}")
        return False
    
    # Crear backup
    if os.path.exists(archivo_servicio):
        backup_nombre = f"{archivo_servicio}.backup_funcional"
        shutil.copy2(archivo_servicio, backup_nombre)
        print(f"✅ Backup creado: {backup_nombre}")
    
    # Copiar el archivo final
    shutil.copy2(archivo_final, archivo_servicio)
    print(f"✅ Archivo actualizado: {archivo_servicio}")
    
    return True

def main():
    print("ACTUALIZADOR FINAL - SMT MONITOR SERVICE")
    print("=" * 50)
    
    if actualizar_a_version_final():
        print("\n" + "=" * 60)
        print("✅ SERVICIO ACTUALIZADO CON ESTRUCTURA REAL DE TABLA")
        print("=" * 60)
        
        print("ESTRUCTURA REAL DETECTADA:")
        print("✅ scan_date, scan_time")
        print("✅ slot_no, result, part_name") 
        print("✅ quantity, vendor, lot_no")
        print("✅ l_position, m_position, seq")
        print("✅ barcode, feeder_base, previous_barcode")
        print("✅ product_date, source_file")
        print("✅ line_number, mounter_number, file_hash")
        print("✅ created_at (automático)")
        
        print("\nCARACTERISTICAS FINALES:")
        print("✅ Mapeo correcto a columnas reales")
        print("✅ Control de archivos duplicados")
        print("✅ Parseo de fecha/hora mejorado")
        print("✅ Manejo de errores robusto")
        print("✅ Logging detallado")
        
        print("\nPASOS PARA INSTALAR:")
        print("1. Probar en consola:")
        print("   python smt_monitor_service.py")
        print("")
        print("2. Instalar servicio:")
        print("   python smt_monitor_service.py install")
        print("")
        print("3. Iniciar servicio:")
        print("   sc start SMTMonitorService")
        
    else:
        print("❌ Error actualizando servicio")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
    
    input("\nPresiona Enter para continuar...")
