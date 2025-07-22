#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extraer todos los permisos de los archivos LISTA_
"""

import os
import re
import json

def extraer_permisos_de_listas():
    """Extraer todos los permisos definidos en los archivos LISTA_"""
    permisos = []
    listas_dir = 'app/templates/LISTAS'
    
    # Buscar todos los archivos LISTA_
    for filename in os.listdir(listas_dir):
        if filename.startswith('LISTA_') and filename.endswith('.html'):
            filepath = os.path.join(listas_dir, filename)
            print(f"📄 Procesando: {filename}")
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Buscar elementos con data-permiso-*
                pattern = r'data-permiso-pagina="([^"]*)"[^>]*data-permiso-seccion="([^"]*)"[^>]*data-permiso-boton="([^"]*)"'
                matches = re.findall(pattern, content)
                
                for match in matches:
                    pagina, seccion, boton = match
                    permiso = {
                        'pagina': pagina,
                        'seccion': seccion,
                        'boton': boton
                    }
                    
                    # Evitar duplicados
                    if permiso not in permisos:
                        permisos.append(permiso)
                        print(f"   ✅ {pagina} > {seccion} > {boton}")
                
            except Exception as e:
                print(f"   ❌ Error procesando {filename}: {e}")
    
    print(f"\n📊 RESUMEN:")
    print(f"   Total permisos encontrados: {len(permisos)}")
    
    # Agrupar por página
    por_pagina = {}
    for permiso in permisos:
        pagina = permiso['pagina']
        if pagina not in por_pagina:
            por_pagina[pagina] = {}
        
        seccion = permiso['seccion']
        if seccion not in por_pagina[pagina]:
            por_pagina[pagina][seccion] = []
        
        por_pagina[pagina][seccion].append(permiso['boton'])
    
    print(f"\n📋 PERMISOS POR PÁGINA:")
    for pagina in sorted(por_pagina.keys()):
        print(f"\n📄 {pagina}:")
        for seccion in sorted(por_pagina[pagina].keys()):
            print(f"   📁 {seccion}:")
            for boton in sorted(por_pagina[pagina][seccion]):
                print(f"      🔘 {boton}")
    
    # Guardar como JSON para usar en el frontend
    with open('permisos_extraidos.json', 'w', encoding='utf-8') as f:
        json.dump(permisos, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Permisos guardados en: permisos_extraidos.json")
    
    # Generar código JavaScript para el frontend
    js_code = "const allDropdowns = " + json.dumps(permisos, indent=4, ensure_ascii=False) + ";"
    
    with open('permisos_dropdowns.js', 'w', encoding='utf-8') as f:
        f.write(js_code)
    
    print(f"💾 Código JavaScript guardado en: permisos_dropdowns.js")
    
    return permisos

if __name__ == "__main__":
    print("🔍 EXTRAYENDO PERMISOS DE ARCHIVOS LISTA_")
    print("=" * 50)
    
    permisos = extraer_permisos_de_listas()
    
    print(f"\n✅ Proceso completado. Se encontraron {len(permisos)} permisos únicos.")
