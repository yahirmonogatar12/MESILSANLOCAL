#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Script para corregir los placeholders en smt_csv_handler.py

with open('app/smt_csv_handler.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Mostrar las líneas problemáticas antes
print("ANTES:")
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'DATE_FORMAT' in line or 'TIME_FORMAT' in line:
        print(f"Línea {i+1}: {line}")

# Corregir los placeholders
old_date = "DATE_FORMAT(scan_date, '%Y-%m-%d')"
new_date = "DATE_FORMAT(scan_date, '%%Y-%%m-%%d')"

old_time = "TIME_FORMAT(scan_time, '%H:%i:%s')"
new_time = "TIME_FORMAT(scan_time, '%%H:%%i:%%s')"

content = content.replace(old_date, new_date)
content = content.replace(old_time, new_time)

# Escribir archivo corregido
with open('app/smt_csv_handler.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\nDESPUÉS:")
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'DATE_FORMAT' in line or 'TIME_FORMAT' in line:
        print(f"Línea {i+1}: {line}")

print("\nArchivo corregido exitosamente")
