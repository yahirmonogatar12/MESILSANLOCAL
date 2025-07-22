#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para agregar atributos de permisos a todos los archivos de templates LISTA
"""

import os
import re
from typing import List, Tuple, Dict

def extraer_sidebar_links(contenido: str, nombre_pagina: str) -> str:
    """
    Extrae todos los sidebar-links de un archivo HTML y les agrega atributos de permisos
    """
    
    # Patrón para encontrar las secciones completas con sus dropdowns
    patron_seccion = r'<li class="sidebar-section">(.*?)</li>\s*(?=<li class="sidebar-section"|</ul>\s*</aside>)'
    
    # Patrón para extraer el nombre de la sección del botón
    patron_nombre_seccion = r'<button[^>]*>(.*?)</button>'
    
    # Patrón para los links individuales
    patron_link = r'<li class="sidebar-link"[^>]*(?:onclick="([^"]*)")?[^>]*>([^<]+)</li>'
    
    contenido_modificado = contenido
    
    # Encontrar todas las secciones
    secciones = re.finditer(patron_seccion, contenido, re.DOTALL | re.IGNORECASE)
    
    for match_seccion in secciones:
        seccion_completa = match_seccion.group(1)
        
        # Extraer nombre de la sección
        match_nombre = re.search(patron_nombre_seccion, seccion_completa, re.IGNORECASE | re.DOTALL)
        if match_nombre:
            nombre_seccion = re.sub(r'<[^>]+>', '', match_nombre.group(1)).strip()
            nombre_seccion = re.sub(r'\s+', ' ', nombre_seccion)
            
            # Buscar y reemplazar todos los links en esta sección
            def reemplazar_link(match):
                onclick = match.group(1) if match.group(1) else ""
                texto_link = match.group(2).strip()
                
                if onclick:
                    return f'''<li class="sidebar-link" tabindex="0" onclick="{onclick}" 
                            data-permiso-pagina="{nombre_pagina}" 
                            data-permiso-seccion="{nombre_seccion}" 
                            data-permiso-boton="{texto_link}">{texto_link}</li>'''
                else:
                    return f'''<li class="sidebar-link" tabindex="0" 
                            data-permiso-pagina="{nombre_pagina}" 
                            data-permiso-seccion="{nombre_seccion}" 
                            data-permiso-boton="{texto_link}">{texto_link}</li>'''
            
            # Reemplazar todos los links en esta sección
            nueva_seccion = re.sub(patron_link, reemplazar_link, seccion_completa)
            contenido_modificado = contenido_modificado.replace(seccion_completa, nueva_seccion)
    
    # Agregar el script de permisos al final si no existe
    if 'permisos-dropdowns.js' not in contenido_modificado:
        script_permisos = '''
<script src="{{ url_for('static', filename='js/permisos-dropdowns.js') }}"></script>
<script>
    // Inicializar el sistema de permisos cuando se carga el documento
    document.addEventListener('DOMContentLoaded', function() {
        if (typeof PermisosDropdowns !== 'undefined') {
            PermisosDropdowns.inicializar();
        }
    });
</script>'''
        
        # Buscar el final del div principal y agregar el script antes del cierre
        if '</div>' in contenido_modificado:
            partes = contenido_modificado.rsplit('</div>', 1)
            contenido_modificado = partes[0] + '</div>' + script_permisos + (('\n</div>' + partes[1]) if len(partes) > 1 else '')
        else:
            contenido_modificado += script_permisos
    
    return contenido_modificado

def procesar_archivo_lista(ruta_archivo: str) -> bool:
    """
    Procesa un archivo LISTA individual
    """
    try:
        print(f"Procesando: {ruta_archivo}")
        
        # Leer el archivo
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Extraer nombre de página del nombre del archivo
        nombre_archivo = os.path.basename(ruta_archivo)
        nombre_pagina = nombre_archivo.replace('.html', '')
        
        # Verificar si ya tiene permisos
        if 'data-permiso-pagina' in contenido:
            print(f"  ✓ Ya tiene permisos configurados")
            return True
        
        # Procesar el contenido
        contenido_nuevo = extraer_sidebar_links(contenido, nombre_pagina)
        
        # Verificar si hubo cambios
        if contenido_nuevo != contenido:
            # Guardar el archivo modificado
            with open(ruta_archivo, 'w', encoding='utf-8') as f:
                f.write(contenido_nuevo)
            print(f"  ✓ Permisos agregados exitosamente")
            return True
        else:
            print(f"  ! No se encontraron cambios para hacer")
            return False
            
    except Exception as e:
        print(f"  ✗ Error procesando {ruta_archivo}: {e}")
        return False

def main():
    """
    Función principal
    """
    print("=== Actualizador de Permisos para Templates LISTA ===")
    
    # Lista de archivos a procesar
    archivos_lista = [
        'app/templates/LISTAS/LISTA_CONTROL_DE_CALIDAD.html',
        'app/templates/LISTAS/LISTA_CONTROLDEPRODUCCION.html', 
        'app/templates/LISTAS/LISTA_CONTROL_DE_PROCESO.html',
        'app/templates/LISTAS/LISTA_DE_CONTROL_DE_REPORTE.html',
        'app/templates/LISTAS/LISTA_DE_CONTROL_DE_RESULTADOS.html',
        'app/templates/LISTAS/LISTA_DE_CONFIGPG.html'
    ]
    
    procesados = 0
    exitosos = 0
    
    for archivo in archivos_lista:
        if os.path.exists(archivo):
            if procesar_archivo_lista(archivo):
                exitosos += 1
            procesados += 1
        else:
            print(f"! Archivo no encontrado: {archivo}")
    
    print(f"\n=== Resumen ===")
    print(f"Archivos procesados: {procesados}")
    print(f"Exitosos: {exitosos}")
    print(f"Errores: {procesados - exitosos}")
    print(f"\n¡Actualización completada!")

if __name__ == "__main__":
    main()
