#!/usr/bin/env python3
"""
Script para forzar actualización de ruta en servicio corriendo
Modifica directamente la configuración del servicio sin reinstalar
"""

import os
import sys
import time
import subprocess
import win32service
import win32serviceutil

def detener_servicio():
    print("Deteniendo servicio SMT Monitor...")
    try:
        win32serviceutil.StopService("SMTMonitorService")
        time.sleep(3)
        print("✓ Servicio detenido")
        return True
    except Exception as e:
        print(f"Error deteniendo servicio: {e}")
        return False

def verificar_archivo_servicio():
    """Verificar y corregir el archivo del servicio directamente"""
    service_file = r"C:\SMTMonitorService\smt_monitor_service.py"
    
    print(f"Verificando archivo: {service_file}")
    
    if not os.path.exists(service_file):
        print("✗ Archivo del servicio no encontrado")
        return False
    
    print("✓ Archivo encontrado")
    
    # Leer el archivo
    with open(service_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar si tiene la ruta incorrecta
    if r'C:\LOT CHECK ALL' in content and r'C:\LOT CHECK  ALL' not in content:
        print("⚠️  Encontrada ruta incorrecta en el archivo del servicio")
        print("Corrigiendo ruta...")
        
        # Corregir la ruta
        new_content = content.replace(r'C:\LOT CHECK ALL', r'C:\LOT CHECK  ALL')
        
        # Crear backup
        backup_file = service_file + ".backup"
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Backup creado: {backup_file}")
        
        # Escribir archivo corregido
        with open(service_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("✓ Archivo corregido")
        return True
    
    elif r'C:\LOT CHECK  ALL' in content:
        print("✓ Ruta ya está correcta en el archivo")
        return True
    
    else:
        print("⚠️  No se encontró ninguna ruta en el archivo")
        return False

def iniciar_servicio():
    print("Iniciando servicio SMT Monitor...")
    try:
        win32serviceutil.StartService("SMTMonitorService")
        time.sleep(2)
        print("✓ Servicio iniciado")
        return True
    except Exception as e:
        print(f"Error iniciando servicio: {e}")
        return False

def verificar_logs():
    """Verificar si los logs muestran la ruta correcta"""
    log_file = r"C:\SMTMonitorService\smt_monitor_service.log"
    
    print(f"Verificando logs: {log_file}")
    
    if os.path.exists(log_file):
        print("Esperando logs nuevos...")
        time.sleep(10)  # Esperar a que el servicio genere logs
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            print("Últimas 10 líneas del log:")
            for line in lines[-10:]:
                print(f"  {line.strip()}")
                
            # Verificar si menciona la ruta correcta
            recent_lines = ''.join(lines[-20:])
            if 'C:\\LOT CHECK  ALL' in recent_lines:
                print("✓ Servicio usando ruta correcta")
                return True
            elif 'C:\\LOT CHECK ALL' in recent_lines:
                print("✗ Servicio aún usa ruta incorrecta")
                return False
            else:
                print("? No se encontraron referencias a rutas en logs recientes")
                return None
                
        except Exception as e:
            print(f"Error leyendo logs: {e}")
            return False
    else:
        print("✗ Archivo de log no encontrado")
        return False

def main():
    print("FORZAR CORRECCIÓN DE RUTA EN SERVICIO SMT")
    print("=" * 50)
    
    # Paso 1: Detener servicio
    if not detener_servicio():
        print("No se pudo detener el servicio")
        return
    
    # Paso 2: Verificar y corregir archivo
    if not verificar_archivo_servicio():
        print("No se pudo corregir el archivo del servicio")
        return
    
    # Paso 3: Reiniciar servicio
    if not iniciar_servicio():
        print("No se pudo iniciar el servicio")
        return
    
    # Paso 4: Verificar logs
    resultado = verificar_logs()
    
    print("\n" + "=" * 50)
    if resultado:
        print("✅ ÉXITO: Servicio corregido y funcionando con ruta correcta")
    elif resultado is False:
        print("❌ FALLO: Servicio aún tiene problemas")
        print("\nOPCIONES ADICIONALES:")
        print("1. Ejecutar script de diagnóstico: python test_directo.py")
        print("2. Verificar permisos: ejecutar como administrador")
        print("3. Reinstalar completamente el servicio")
    else:
        print("⚠️  INCIERTO: No se pudo determinar el estado")
        print("Revisa manualmente el log del servicio")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error en script: {e}")
    
    input("\nPresiona Enter para continuar...")
