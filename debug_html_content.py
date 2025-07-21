#!/usr/bin/env python3
"""
Script para ver exactamente qué está en el HTML
"""

import requests
import re

# Session para mantener cookies
session = requests.Session()

def debug_html_content():
    """Ver exactamente qué hay en el HTML"""
    
    print("🔍 Analizando contenido HTML...")
    
    # Login
    login_data = {
        'usuario': 'admin',
        'password': 'admin123'
    }
    
    response = session.post("http://localhost:5000/login", data=login_data)
    
    # Obtener la página principal
    main_page = session.get("http://localhost:5000/ILSAN-ELECTRONICS")
    
    if main_page.status_code == 200:
        content = main_page.text
        
        print(f"📏 Tamaño del HTML: {len(content)} caracteres")
        
        # Buscar el área donde debería estar el botón
        lines = content.split('\n')
        
        print("\n🔍 Buscando el área de botones de navegación...")
        for i, line in enumerate(lines):
            if 'Configuración de programa' in line:
                print(f"✅ Línea {i}: {line.strip()}")
                
                # Mostrar las líneas siguientes
                for j in range(1, 10):
                    if i + j < len(lines):
                        next_line = lines[i + j].strip()
                        if next_line:
                            print(f"   Línea {i+j}: {next_line}")
                        if "Panel de Administración" in next_line:
                            print("✅ ¡ENCONTRADO!")
                            break
                        if "header>" in next_line:
                            print("❌ Se acabó el header sin encontrar el botón")
                            break
                break
        
        # Buscar cualquier referencia a administración
        print("\n🔍 Buscando cualquier referencia a 'admin'...")
        admin_lines = []
        for i, line in enumerate(lines):
            if 'admin' in line.lower():
                admin_lines.append((i, line.strip()))
        
        for line_num, line_content in admin_lines[:5]:  # Mostrar primeras 5
            print(f"   Línea {line_num}: {line_content}")
        
        # Buscar variables Jinja2
        print("\n🔍 Buscando variables Jinja2...")
        jinja_vars = re.findall(r'\{\{\s*([^}]+)\s*\}\}', content)
        unique_vars = list(set(jinja_vars))[:10]  # Primeras 10 únicas
        print(f"Variables encontradas: {unique_vars}")
        
        # Buscar bloques if
        print("\n🔍 Buscando bloques condicionales Jinja2...")
        if_blocks = re.findall(r'\{%\s*if\s+([^%]+)\s*%\}', content)
        print(f"Condicionales encontrados: {if_blocks}")
        
        # Buscar específicamente el botón que esperamos
        print("\n🔍 Buscando patrón específico del botón...")
        if "nav-button admin-only" in content:
            print("✅ Clase 'nav-button admin-only' ENCONTRADA")
        else:
            print("❌ Clase 'nav-button admin-only' NO encontrada")
            
        if "engrane.png" in content:
            print("✅ Icono 'engrane.png' ENCONTRADO")
        else:
            print("❌ Icono 'engrane.png' NO encontrado")
            
    else:
        print(f"❌ Error al obtener página: {main_page.status_code}")

if __name__ == "__main__":
    try:
        debug_html_content()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
