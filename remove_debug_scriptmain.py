#!/usr/bin/env python3
"""
Script para eliminar líneas de console.log de debugging en scriptMain.js
manteniendo console.error y console.warn
"""
import re

def remove_debug_logs(file_path):
    """
    Elimina líneas de console.log de debugging de un archivo JavaScript
    """
    # Leer el archivo
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Patrón para console.log (pero NO console.error ni console.warn)
    debug_pattern = re.compile(r'^\s*console\.log\(')
    
    # Filtrar líneas
    filtered_lines = []
    removed_count = 0
    
    for line in lines:
        if debug_pattern.search(line):
            removed_count += 1
            print(f"Eliminando: {line.strip()}")
        else:
            filtered_lines.append(line)
    
    # Escribir de vuelta al archivo
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(filtered_lines)
    
    print(f"\n✅ Total de líneas console.log eliminadas: {removed_count}")
    print(f"✅ Archivo actualizado: {file_path}")

if __name__ == "__main__":
    file_path = r"c:\Users\yahir\OneDrive\Escritorio\MES\MES\MESILSANLOCAL\app\static\js\scriptMain.js"
    remove_debug_logs(file_path)
