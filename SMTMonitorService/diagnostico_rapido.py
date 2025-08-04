#!/usr/bin/env python3
"""
Diagnóstico rápido del monitor SMT
"""

import os
import glob

# Verificar carpetas
base_path = r"C:\LOT CHECK  ALL"
carpetas = []

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
        carpetas.append(folder_path)

print("DIAGNÓSTICO SMT MONITOR")
print("=" * 50)

for i, carpeta in enumerate(carpetas, 1):
    print(f"\n{i}. {carpeta}")
    
    if os.path.exists(carpeta):
        archivos = glob.glob(os.path.join(carpeta, "*.csv"))
        print(f"   ✅ Existe - {len(archivos)} archivos CSV")
        
        if archivos:
            # Mostrar algunos archivos
            for archivo in sorted(archivos)[-2:]:
                nombre = os.path.basename(archivo)
                tamano = os.path.getsize(archivo)
                print(f"      📄 {nombre} ({tamano} bytes)")
    else:
        print(f"   ❌ NO EXISTE")

print(f"\n" + "=" * 50)
print("Si alguna carpeta no existe, créala antes de usar el servicio.")
