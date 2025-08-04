#!/usr/bin/env python3
"""
Script para corregir el error de conflicto de nombres en smt_monitor_service.py
"""

import os
import shutil

def corregir_archivo():
    """Corregir el conflicto de nombres en el archivo del servicio"""
    
    archivo_servicio = r'C:\SMTMonitorService\smt_monitor_service.py'
    archivo_backup = r'C:\SMTMonitorService\smt_monitor_service.py.backup'
    
    print("CORRIGIENDO ERROR DE CONFLICTO DE NOMBRES")
    print("=" * 50)
    
    # Verificar que el archivo existe
    if not os.path.exists(archivo_servicio):
        print(f"❌ Archivo no encontrado: {archivo_servicio}")
        return False
    
    print(f"📄 Archivo encontrado: {archivo_servicio}")
    
    # Crear backup
    shutil.copy2(archivo_servicio, archivo_backup)
    print(f"✅ Backup creado: {archivo_backup}")
    
    # Leer el archivo
    with open(archivo_servicio, 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    # Realizar las correcciones
    print("🔧 Aplicando correcciones...")
    
    # 1. Cambiar self.monitor_folders por self.folders_to_monitor
    contenido_corregido = contenido.replace(
        'self.monitor_folders = [',
        'self.folders_to_monitor = ['
    )
    
    # 2. Actualizar todas las referencias a la lista
    contenido_corregido = contenido_corregido.replace(
        'for folder in self.monitor_folders:',
        'for folder in self.folders_to_monitor:'
    )
    
    contenido_corregido = contenido_corregido.replace(
        'self.logger.info(f"Carpetas a monitorear: {len(self.monitor_folders)}")',
        'self.logger.info(f"Carpetas a monitorear: {len(self.folders_to_monitor)}")'
    )
    
    contenido_corregido = contenido_corregido.replace(
        'for folder in self.monitor_folders:',
        'for folder in self.folders_to_monitor:'
    )
    
    # Verificar que se realizaron cambios
    if contenido == contenido_corregido:
        print("⚠️  No se detectaron cambios necesarios")
        return True
    
    # Escribir el archivo corregido
    with open(archivo_servicio, 'w', encoding='utf-8') as f:
        f.write(contenido_corregido)
    
    print("✅ Archivo corregido exitosamente")
    
    # Mostrar un resumen de los cambios
    print("\nCambios realizados:")
    print("- self.monitor_folders → self.folders_to_monitor")
    print("- Actualizada referencia en el ciclo de monitoreo")
    print("- Actualizada referencia en el logging")
    
    return True

def verificar_correccion():
    """Verificar que la corrección se aplicó correctamente"""
    
    archivo_servicio = r'C:\SMTMonitorService\smt_monitor_service.py'
    
    print("\nVERIFICANDO CORRECCIÓN...")
    print("=" * 30)
    
    try:
        with open(archivo_servicio, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Verificar que no hay conflictos
        if 'self.monitor_folders = [' in contenido:
            print("❌ ERROR: Aún existe self.monitor_folders como variable")
            return False
        
        if 'self.folders_to_monitor = [' in contenido:
            print("✅ Variable renombrada correctamente")
        else:
            print("❌ ERROR: No se encuentra la nueva variable")
            return False
        
        if 'def monitor_folders(self):' in contenido:
            print("✅ Método monitor_folders conservado")
        else:
            print("❌ ERROR: Método monitor_folders no encontrado")
            return False
        
        print("✅ Corrección verificada exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error verificando: {e}")
        return False

def main():
    print("CORRECTOR DE CONFLICTO DE NOMBRES - SERVICIO SMT")
    print("=" * 60)
    
    if corregir_archivo():
        if verificar_correccion():
            print("\n" + "=" * 60)
            print("✅ CORRECCIÓN COMPLETADA EXITOSAMENTE")
            print("\nAhora puedes:")
            print("1. Reiniciar el servicio: sc stop SMTMonitorService && sc start SMTMonitorService")
            print("2. O ejecutar en modo consola: python C:\\SMTMonitorService\\smt_monitor_service.py")
        else:
            print("\n❌ VERIFICACIÓN FALLÓ - Revisa manualmente el archivo")
    else:
        print("\n❌ CORRECCIÓN FALLÓ")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error en script: {e}")
    
    input("\nPresiona Enter para continuar...")
