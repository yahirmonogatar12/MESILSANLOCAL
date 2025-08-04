#!/usr/bin/env python3
"""
Script para corregir el archivo original smt_monitor_service.py en la carpeta actual
"""

import os
import shutil

def corregir_archivo_original():
    """Corregir el conflicto de nombres en el archivo original"""
    
    # Archivo en la carpeta actual
    archivo_original = r'c:\Users\yahir\OneDrive\Escritorio\ISEMM_MES\SMTMonitorService\smt_monitor_service.py'
    archivo_backup = r'c:\Users\yahir\OneDrive\Escritorio\ISEMM_MES\SMTMonitorService\smt_monitor_service_backup.py'
    
    print("CORRIGIENDO ARCHIVO ORIGINAL PARA REINSTALACIÓN")
    print("=" * 60)
    
    # Verificar que el archivo existe
    if not os.path.exists(archivo_original):
        print(f"❌ Archivo no encontrado: {archivo_original}")
        return False
    
    print(f"📄 Archivo encontrado: {archivo_original}")
    
    # Crear backup
    shutil.copy2(archivo_original, archivo_backup)
    print(f"✅ Backup creado: {archivo_backup}")
    
    # Leer el archivo
    with open(archivo_original, 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    print("🔧 Aplicando correcciones al archivo original...")
    
    # Realizar todas las correcciones necesarias
    contenido_corregido = contenido
    
    # 1. Cambiar self.monitor_folders por self.folders_to_monitor
    contenido_corregido = contenido_corregido.replace(
        'self.monitor_folders = [',
        'self.folders_to_monitor = ['
    )
    
    # 2. Actualizar todas las referencias a la lista en el logging
    contenido_corregido = contenido_corregido.replace(
        'self.logger.info(f"Carpetas a monitorear: {len(self.monitor_folders)}")',
        'self.logger.info(f"Carpetas a monitorear: {len(self.folders_to_monitor)}")'
    )
    
    # 3. Actualizar la referencia en el loop del logging inicial
    contenido_corregido = contenido_corregido.replace(
        'for folder in self.monitor_folders:\n            self.logger.info(f"  - {folder}")',
        'for folder in self.folders_to_monitor:\n            self.logger.info(f"  - {folder}")'
    )
    
    # 4. Actualizar la referencia en verify_folders
    contenido_corregido = contenido_corregido.replace(
        'for folder in self.monitor_folders:',
        'for folder in self.folders_to_monitor:'
    )
    
    # 5. Actualizar la referencia en monitor_folders method
    contenido_corregido = contenido_corregido.replace(
        'for folder in self.monitor_folders:\n                    if not self.is_running:\n                        break',
        'for folder in self.folders_to_monitor:\n                    if not self.is_running:\n                        break'
    )
    
    # Verificar que se realizaron cambios
    if contenido == contenido_corregido:
        print("⚠️  No se detectaron cambios necesarios - archivo ya podría estar correcto")
    else:
        print("✅ Cambios detectados y aplicados")
    
    # Escribir el archivo corregido
    with open(archivo_original, 'w', encoding='utf-8') as f:
        f.write(contenido_corregido)
    
    print("✅ Archivo original corregido exitosamente")
    
    # Mostrar resumen
    print("\nCambios realizados:")
    print("- self.monitor_folders → self.folders_to_monitor (variable lista)")
    print("- Mantenido: def monitor_folders(self): (método)")
    print("- Actualizadas todas las referencias a la lista")
    
    return True

def verificar_sintaxis():
    """Verificar que el archivo tiene sintaxis correcta"""
    
    archivo_original = r'c:\Users\yahir\OneDrive\Escritorio\ISEMM_MES\SMTMonitorService\smt_monitor_service.py'
    
    print("\nVERIFICANDO SINTAXIS...")
    print("=" * 30)
    
    try:
        # Intentar compilar el archivo para verificar sintaxis
        with open(archivo_original, 'r', encoding='utf-8') as f:
            codigo = f.read()
        
        compile(codigo, archivo_original, 'exec')
        print("✅ Sintaxis verificada - archivo válido")
        return True
        
    except SyntaxError as e:
        print(f"❌ Error de sintaxis: {e}")
        return False
    except Exception as e:
        print(f"❌ Error verificando sintaxis: {e}")
        return False

def main():
    print("CORRECTOR PARA REINSTALACIÓN - SERVICIO SMT")
    print("=" * 60)
    
    if corregir_archivo_original():
        if verificar_sintaxis():
            print("\n" + "=" * 60)
            print("✅ ARCHIVO ORIGINAL CORREGIDO PARA REINSTALACIÓN")
            print("\nPasos siguientes:")
            print("1. Ejecutar como administrador: instalar_servicio_corregido.bat")
            print("2. O reinstalar manualmente:")
            print("   sc stop SMTMonitorService")
            print("   sc delete SMTMonitorService")
            print("   python smt_monitor_service.py install")
            print("   sc start SMTMonitorService")
        else:
            print("\n❌ ERROR DE SINTAXIS - Revisa el backup y corrige manualmente")
    else:
        print("\n❌ CORRECCIÓN FALLÓ")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error en script: {e}")
    
    input("\nPresiona Enter para continuar...")
