#!/usr/bin/env python3
"""
Script para reemplazar el servicio con la versión funcional
"""

import os
import shutil

def reemplazar_servicio():
    """Reemplazar smt_monitor_service.py con la versión funcional"""
    print("REEMPLAZANDO SERVICIO CON VERSION FUNCIONAL")
    print("=" * 60)
    
    archivo_funcional = 'smt_monitor_service_funcional.py'
    archivo_servicio = 'smt_monitor_service.py'
    
    # Verificar que existe el archivo funcional
    if not os.path.exists(archivo_funcional):
        print(f"❌ No se encuentra: {archivo_funcional}")
        return False
    
    # Crear backup del archivo actual
    if os.path.exists(archivo_servicio):
        backup_nombre = f"{archivo_servicio}.backup_original"
        shutil.copy2(archivo_servicio, backup_nombre)
        print(f"✅ Backup creado: {backup_nombre}")
    
    # Copiar el archivo funcional
    shutil.copy2(archivo_funcional, archivo_servicio)
    print(f"✅ Archivo reemplazado: {archivo_servicio}")
    
    # También actualizar archivos instalados si existen
    rutas_instalados = [
        r'C:\SMTMonitorService\smt_monitor_service.py',
        r'C:\SMTMonitor\smt_monitor_service.py'
    ]
    
    for ruta in rutas_instalados:
        if os.path.exists(ruta):
            backup_instalado = f"{ruta}.backup"
            shutil.copy2(ruta, backup_instalado)
            shutil.copy2(archivo_funcional, ruta)
            print(f"✅ Archivo instalado actualizado: {ruta}")
    
    return True

def main():
    print("ACTUALIZADOR DE SERVICIO SMT")
    print("=" * 40)
    
    if reemplazar_servicio():
        print("\n" + "=" * 60)
        print("✅ SERVICIO ACTUALIZADO CON VERSION FUNCIONAL")
        print("=" * 60)
        
        print("CARACTERISTICAS DE LA VERSION FUNCIONAL:")
        print("✅ Credenciales correctas")
        print("✅ Tabla: historial_cambio_material_smt")
        print("✅ Control de archivos procesados")
        print("✅ Estructura de 15 columnas correcta")
        print("✅ Mapeo CSV corregido")
        
        print("\nPASOS SIGUIENTES:")
        print("1. Reinstalar servicio:")
        print("   sc stop SMTMonitorService")
        print("   sc delete SMTMonitorService")
        print("   python smt_monitor_service.py install")
        print("   sc start SMTMonitorService")
        
        print("\n2. Probar en modo consola:")
        print("   python smt_monitor_service.py")
        
        print("\n3. Verificar datos:")
        print("   python verificar_tabla_existente.py")
        
    else:
        print("❌ Error actualizando servicio")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
    
    input("\nPresiona Enter para continuar...")
