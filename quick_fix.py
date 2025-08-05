#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

# Leer archivo
with open('app/smt_csv_handler.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Reemplazar la línea específica del regex
content = content.replace(
    "match = re.search(r'(\\d+)Line.*M(\\d+)', folder_name)",
    "match = re.search(r'(\\d+)line[/\\\\]?.*?L(\\d+)\\s*m(\\d+)', folder_name, re.IGNORECASE)"
)

# Reemplazar el return
content = content.replace(
    "return int(match.group(1)), int(match.group(2))",
    "return int(match.group(1)), int(match.group(3))"
)

# Escribir archivo
with open('app/smt_csv_handler.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Función parse_folder_name corregida")
