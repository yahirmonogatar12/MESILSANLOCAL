#!/usr/bin/env python3
"""
Script para configurar acceso a carpetas remotas SMT en otra PC
"""

import os
import subprocess
import sys
from pathlib import Path

def verificar_conectividad(ip_remota):
    """Verificar si la PC remota está accesible"""
    print(f"🔍 Verificando conectividad con {ip_remota}...")
    
    try:
        # Ping a la PC remota
        result = subprocess.run(
            ['ping', '-n', '1', ip_remota], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        
        if result.returncode == 0:
            print(f"✅ PC remota {ip_remota} accesible")
            return True
        else:
            print(f"❌ PC remota {ip_remota} NO accesible")
            return False
            
    except Exception as e:
        print(f"❌ Error verificando conectividad: {e}")
        return False

def mapear_unidad_red(ip_remota, carpeta_remota, usuario=None, password=None):
    """Mapear unidad de red para acceder a carpetas remotas"""
    
    print(f"\n🔗 MAPEANDO UNIDAD DE RED...")
    print(f"   Origen: \\\\{ip_remota}\\{carpeta_remota}")
    
    # Buscar una letra de unidad disponible
    letras_disponibles = []
    for letra in "ZYXWVUTSRQPONMLKJIHGFED":
        if not os.path.exists(f"{letra}:"):
            letras_disponibles.append(letra)
    
    if not letras_disponibles:
        print("❌ No hay letras de unidad disponibles")
        return None
    
    letra_unidad = letras_disponibles[0]
    ruta_unc = f"\\\\{ip_remota}\\{carpeta_remota}"
    
    try:
        # Comando para mapear unidad
        cmd = ['net', 'use', f'{letra_unidad}:', ruta_unc]
        
        if usuario and password:
            cmd.extend([f'/user:{usuario}', password])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Unidad {letra_unidad}: mapeada exitosamente")
            print(f"   Ruta local: {letra_unidad}:\\")
            return f"{letra_unidad}:"
        else:
            print(f"❌ Error mapeando unidad: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error en mapeo: {e}")
        return None

def configurar_servicio_smt(nueva_ruta):
    """Actualizar la configuración del servicio SMT con la nueva ruta"""
    
    print(f"\n⚙️ ACTUALIZANDO CONFIGURACIÓN DEL SERVICIO...")
    
    # Ruta del archivo de configuración del servicio
    archivo_servicio = "SMTMonitorService/smt_monitor_service.py"
    
    if not os.path.exists(archivo_servicio):
        print(f"❌ Archivo del servicio no encontrado: {archivo_servicio}")
        return False
    
    try:
        # Leer archivo actual
        with open(archivo_servicio, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Reemplazar la ruta de carpetas
        ruta_anterior = "C:\\LOT CHECK  ALL"
        contenido_actualizado = contenido.replace(ruta_anterior, nueva_ruta)
        
        # Guardar archivo actualizado
        with open(archivo_servicio, 'w', encoding='utf-8') as f:
            f.write(contenido_actualizado)
        
        print(f"✅ Configuración actualizada:")
        print(f"   Ruta anterior: {ruta_anterior}")
        print(f"   Ruta nueva: {nueva_ruta}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error actualizando configuración: {e}")
        return False

def crear_script_mapeo_persistente(ip_remota, carpeta_remota, letra_unidad, usuario=None):
    """Crear script para mapear automáticamente al inicio"""
    
    script_content = f"""@echo off
echo Mapeando unidad de red para SMT Monitor...
net use {letra_unidad}: \\\\{ip_remota}\\{carpeta_remota}"""
    
    if usuario:
        script_content += f" /user:{usuario} /persistent:yes"
    else:
        script_content += " /persistent:yes"
    
    script_content += """
if %errorlevel% == 0 (
    echo ✅ Unidad mapeada exitosamente
) else (
    echo ❌ Error mapeando unidad
)
pause
"""
    
    script_path = "mapear_unidad_smt.bat"
    
    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        print(f"\n📄 Script de mapeo creado: {script_path}")
        print(f"   Ejecuta este script al inicio de Windows para mapeo automático")
        
        return script_path
        
    except Exception as e:
        print(f"❌ Error creando script: {e}")
        return None

def main():
    """Función principal de configuración"""
    
    print("🔧 CONFIGURADOR DE CARPETAS REMOTAS SMT")
    print("=" * 50)
    
    # Solicitar información de la PC remota
    print("\n📋 INFORMACIÓN DE LA PC REMOTA:")
    ip_remota = input("   IP o nombre de la PC remota: ").strip()
    carpeta_compartida = input("   Nombre de la carpeta compartida (ej: LOT_CHECK_ALL): ").strip()
    
    print("\n🔐 CREDENCIALES (opcional, presiona Enter para omitir):")
    usuario = input("   Usuario: ").strip() or None
    password = input("   Contraseña: ").strip() or None
    
    # Verificar conectividad
    if not verificar_conectividad(ip_remota):
        print("\n❌ No se puede conectar a la PC remota")
        print("   Verifica:")
        print("   - Que la PC esté encendida")
        print("   - Que la IP sea correcta")
        print("   - Que el firewall permita conexiones")
        return
    
    # Mapear unidad de red
    letra_unidad = mapear_unidad_red(ip_remota, carpeta_compartida, usuario, password)
    
    if not letra_unidad:
        print("\n❌ No se pudo mapear la unidad de red")
        return
    
    # Actualizar configuración del servicio
    nueva_ruta = f"{letra_unidad}\\LOT CHECK  ALL"
    if configurar_servicio_smt(nueva_ruta):
        print(f"\n✅ CONFIGURACIÓN COMPLETADA")
        print(f"   Nueva ruta: {nueva_ruta}")
        
        # Crear script de mapeo persistente
        crear_script_mapeo_persistente(ip_remota, carpeta_compartida, letra_unidad, usuario)
        
        print(f"\n🚀 PRÓXIMOS PASOS:")
        print(f"   1. Ejecuta el script 'mapear_unidad_smt.bat' al inicio")
        print(f"   2. Reinicia el servicio SMT Monitor")
        print(f"   3. Verifica que los archivos se procesen correctamente")
        
    else:
        print(f"\n❌ Error en la configuración")

if __name__ == "__main__":
    main()
