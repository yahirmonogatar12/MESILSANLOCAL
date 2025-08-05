#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

def fix_parse_folder_function():
    # Leer el archivo
    with open('app/smt_csv_handler.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Patrón para encontrar toda la función parse_folder_name
    pattern = r'(    def parse_folder_name\(self, folder_name\):.*?        return 1, 1)'
    
    # Nueva función
    new_function = '''    def parse_folder_name(self, folder_name):
        """Parsea nombre de carpeta para extraer línea y mounter"""
        # Formato esperado: "1line/L1 m1", "2line/L2 m1", etc.
        import re
        
        # Primero intentar formato: "1line/L1 m1"
        match = re.search(r'(\\d+)line[/\\\\]?.*?L(\\d+)\\s*m(\\d+)', folder_name, re.IGNORECASE)
        if match:
            line_num = int(match.group(1))
            mounter_num = int(match.group(3))  # El número después de 'm'
            return line_num, mounter_num
        
        # Formato alternativo: "1Line_M1", "2Line_M2", etc.
        match = re.search(r'(\\d+)Line.*M(\\d+)', folder_name)
        if match:
            return int(match.group(1)), int(match.group(2))
        
        # Fallback
        return 1, 1'''
    
    # Reemplazar usando DOTALL para incluir saltos de línea
    updated_content = re.sub(pattern, new_function, content, flags=re.DOTALL)
    
    # Escribir el archivo actualizado
    with open('app/smt_csv_handler.py', 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print("Función parse_folder_name actualizada correctamente")

if __name__ == '__main__':
    fix_parse_folder_function()
