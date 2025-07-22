#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para revisar los permisos dropdown y identificar problemas
"""
import sqlite3
import sys

def revisar_permisos():
    try:
        conn = sqlite3.connect('app/database/ISEMM_MES.db')
        cursor = conn.cursor()
        
        print('=' * 60)
        print('🔍 ANÁLISIS DE PERMISOS DROPDOWN')
        print('=' * 60)
        
        # Obtener todos los permisos
        cursor.execute('''
            SELECT id, pagina, seccion, boton, descripcion 
            FROM permisos_dropdown 
            ORDER BY pagina, seccion, boton
        ''')
        permisos = cursor.fetchall()
        
        print(f'\n📊 TOTAL DE PERMISOS: {len(permisos)}')
        
        # Agrupar por página y sección
        pagina_actual = None
        seccion_actual = None
        contador_pagina = 0
        contador_seccion = 0
        
        for permiso in permisos:
            id_permiso, pagina, seccion, boton, descripcion = permiso
            
            if pagina != pagina_actual:
                if pagina_actual is not None:
                    print(f'   📈 Total en página: {contador_pagina} permisos')
                print(f'\n📁 PÁGINA: {pagina}')
                pagina_actual = pagina
                seccion_actual = None
                contador_pagina = 0
            
            if seccion != seccion_actual:
                if seccion_actual is not None:
                    print(f'     📈 Total en sección: {contador_seccion} permisos')
                print(f'  📂 SECCIÓN: {seccion}')
                seccion_actual = seccion
                contador_seccion = 0
            
            desc = descripcion if descripcion else "Sin descripción"
            print(f'    • {boton} ({desc})')
            contador_pagina += 1
            contador_seccion += 1
        
        # Mostrar último total
        if seccion_actual is not None:
            print(f'     📈 Total en sección: {contador_seccion} permisos')
        if pagina_actual is not None:
            print(f'   📈 Total en página: {contador_pagina} permisos')
        
        # Análisis de grupos con más permisos
        print('\n' + '=' * 60)
        print('📈 ANÁLISIS DE DENSIDAD DE PERMISOS')
        print('=' * 60)
        
        cursor.execute('''
            SELECT pagina, seccion, COUNT(*) as total 
            FROM permisos_dropdown 
            GROUP BY pagina, seccion 
            ORDER BY total DESC
        ''')
        grupos = cursor.fetchall()
        
        print('\n🔥 Secciones con más permisos:')
        for i, grupo in enumerate(grupos[:15], 1):
            pagina, seccion, total = grupo
            emoji = "🚨" if total > 10 else "⚠️" if total > 5 else "✅"
            print(f'  {i:2d}. {emoji} {pagina} > {seccion}: {total} permisos')
        
        # Buscar permisos potencialmente problemáticos
        print('\n' + '=' * 60)
        print('🔍 PERMISOS POTENCIALMENTE PROBLEMÁTICOS')
        print('=' * 60)
        
        # Buscar botones con nombres genéricos o confusos
        cursor.execute('''
            SELECT pagina, seccion, boton, descripcion 
            FROM permisos_dropdown 
            WHERE boton LIKE '%test%' 
               OR boton LIKE '%debug%' 
               OR boton LIKE '%temp%'
               OR boton LIKE '%ejemplo%'
               OR boton LIKE '%prueba%'
               OR descripcion IS NULL
               OR descripcion = ''
            ORDER BY pagina, seccion, boton
        ''')
        problematicos = cursor.fetchall()
        
        if problematicos:
            print('\n⚠️ Permisos con nombres sospechosos o sin descripción:')
            for permiso in problematicos:
                pagina, seccion, boton, descripcion = permiso
                motivo = ""
                if not descripcion:
                    motivo += "sin descripción "
                if any(word in boton.lower() for word in ['test', 'debug', 'temp', 'ejemplo', 'prueba']):
                    motivo += "nombre sospechoso "
                print(f'  🚨 {pagina} > {seccion} > {boton} ({motivo.strip()})')
        else:
            print('\n✅ No se encontraron permisos con nombres obviamente problemáticos')
        
        # Buscar duplicados
        print('\n' + '=' * 60)
        print('🔄 VERIFICACIÓN DE DUPLICADOS')
        print('=' * 60)
        
        cursor.execute('''
            SELECT pagina, seccion, boton, COUNT(*) as cantidad
            FROM permisos_dropdown 
            GROUP BY pagina, seccion, boton 
            HAVING COUNT(*) > 1
        ''')
        duplicados = cursor.fetchall()
        
        if duplicados:
            print('\n🚨 Permisos duplicados encontrados:')
            for dup in duplicados:
                pagina, seccion, boton, cantidad = dup
                print(f'  ❌ {pagina} > {seccion} > {boton} (aparece {cantidad} veces)')
        else:
            print('\n✅ No se encontraron permisos duplicados')
        
        # Estadísticas finales
        print('\n' + '=' * 60)
        print('📋 RESUMEN ESTADÍSTICO')
        print('=' * 60)
        
        cursor.execute('SELECT COUNT(DISTINCT pagina) FROM permisos_dropdown')
        total_paginas = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT seccion) FROM permisos_dropdown')
        total_secciones = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM permisos_dropdown WHERE descripcion IS NULL OR descripcion = ""')
        sin_descripcion = cursor.fetchone()[0]
        
        print(f'📄 Total de páginas: {total_paginas}')
        print(f'📂 Total de secciones: {total_secciones}')
        print(f'📝 Permisos sin descripción: {sin_descripcion}')
        print(f'📊 Promedio de permisos por página: {len(permisos) / total_paginas:.1f}')
        print(f'📊 Promedio de permisos por sección: {len(permisos) / total_secciones:.1f}')
        
        conn.close()
        print('\n✅ Análisis completado')
        
    except Exception as e:
        print(f'❌ Error durante el análisis: {e}')
        return False
    
    return True

if __name__ == '__main__':
    revisar_permisos()
