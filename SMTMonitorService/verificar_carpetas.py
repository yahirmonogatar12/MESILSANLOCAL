#!/usr/bin/e    base_path = r"C:\LOT CHECK ALL"
    folders_to_monitor = []
    
    # Configurar todas las subcarpetas por línea
    lines_config = {
        "1line": ["L1 m1", "L1 m2", "L1 m3"],
        "2line": ["L2 m1", "L2 m2", "L2 m3"], 
        "3line": ["L3 m1", "L3 m2", "L3 m3"],
        "4line": ["L4 m1", "L4 m2", "L4 m3"]
    }
    
    # Crear la lista completa de carpetas a monitorear
    for line, mounters in lines_config.items():
        for mounter in mounters:
            folder_path = os.path.join(base_path, line, mounter)
            folders_to_monitor.append(folder_path)
Script de prueba para verificar el monitoreo de carpetas SMT
"""

import os
import glob
from datetime import datetime

def verificar_carpetas():
    """Verificar todas las carpetas y archivos CSV"""
    
    base_path = r"C:\LOT CHECK  ALL"
    folders_to_monitor = [
        os.path.join(base_path, "1line", "L1 m1"),
        os.path.join(base_path, "1line", "L1 m2"),
        os.path.join(base_path, "1line", "L1 m3"),
        os.path.join(base_path, "2line", "L2 m1"),
        os.path.join(base_path, "2line", "L2 m2"),
        os.path.join(base_path, "2line", "L2 m3"),
        os.path.join(base_path, "3line", "L3 m1"),
        os.path.join(base_path, "3line", "L3 m2"),
        os.path.join(base_path, "3line", "L3 m3"),
        os.path.join(base_path, "4line", "L4 m1"),
        os.path.join(base_path, "4line", "L4 m2"),
        os.path.join(base_path, "4line", "L4 m3")
    ]
    
    print("=" * 60)
    print(f"VERIFICACIÓN DE CARPETAS SMT - {datetime.now()}")
    print("=" * 60)
    
    total_archivos = 0
    
    for i, folder in enumerate(folders_to_monitor, 1):
        print(f"\n{i}. Carpeta: {folder}")
        
        if os.path.exists(folder):
            print(f"   ✅ Carpeta existe")
            
            # Buscar archivos CSV
            csv_files = glob.glob(os.path.join(folder, "*.csv"))
            csv_files.sort()
            
            if csv_files:
                print(f"   📁 Archivos CSV encontrados: {len(csv_files)}")
                total_archivos += len(csv_files)
                
                # Mostrar últimos archivos
                for csv_file in csv_files[-3:]:  # Últimos 3 archivos
                    archivo_nombre = os.path.basename(csv_file)
                    tamano = os.path.getsize(csv_file)
                    modificado = datetime.fromtimestamp(os.path.getmtime(csv_file))
                    print(f"      - {archivo_nombre} ({tamano} bytes, {modificado.strftime('%Y-%m-%d %H:%M:%S')})")
                    
                if len(csv_files) > 3:
                    print(f"      ... y {len(csv_files) - 3} archivos más")
            else:
                print(f"   ⚠️  No se encontraron archivos CSV")
        else:
            print(f"   ❌ Carpeta NO existe")
    
    print(f"\n" + "=" * 60)
    print(f"RESUMEN:")
    print(f"- Total de carpetas configuradas: {len(folders_to_monitor)}")
    print(f"- Carpetas existentes: {sum(1 for folder in folders_to_monitor if os.path.exists(folder))}")
    print(f"- Total de archivos CSV: {total_archivos}")
    print("=" * 60)

def verificar_archivo_especifico():
    """Verificar contenido de un archivo específico"""
    
    # Buscar el archivo más reciente en L1 m2
    folder_m2 = r"C:\LOT CHECK  ALL\1line\L1 m2"
    
    if os.path.exists(folder_m2):
        csv_files = glob.glob(os.path.join(folder_m2, "*.csv"))
        if csv_files:
            archivo_mas_reciente = max(csv_files, key=os.path.getmtime)
            
            print(f"\n📄 ANÁLISIS DEL ARCHIVO MÁS RECIENTE EN L1 m2:")
            print(f"   Archivo: {os.path.basename(archivo_mas_reciente)}")
            print(f"   Ruta: {archivo_mas_reciente}")
            print(f"   Tamaño: {os.path.getsize(archivo_mas_reciente)} bytes")
            print(f"   Modificado: {datetime.fromtimestamp(os.path.getmtime(archivo_mas_reciente))}")
            
            # Leer primeras líneas
            try:
                with open(archivo_mas_reciente, 'r', encoding='utf-8') as file:
                    lineas = file.readlines()
                    
                print(f"   Total de líneas: {len(lineas)}")
                print(f"\n   📝 Primeras 3 líneas:")
                for i, linea in enumerate(lineas[:3], 1):
                    cols = linea.strip().split(',')
                    print(f"      {i}: {len(cols)} columnas - {linea.strip()[:100]}...")
                    
            except Exception as e:
                print(f"   ❌ Error leyendo archivo: {e}")
        else:
            print(f"\n⚠️  No hay archivos CSV en {folder_m2}")
    else:
        print(f"\n❌ La carpeta {folder_m2} no existe")

if __name__ == "__main__":
    verificar_carpetas()
    verificar_archivo_especifico()
    
    print(f"\n🔧 RECOMENDACIONES:")
    print(f"   1. Asegúrate de que todas las carpetas existen")
    print(f"   2. Verifica que los archivos CSV tienen el formato correcto (14 columnas)")
    print(f"   3. Comprueba los permisos de lectura en las carpetas")
    print(f"   4. Revisa los logs del servicio para errores específicos")
