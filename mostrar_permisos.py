#!/usr/bin/env python3
"""
Script para mostrar todos los permisos_botones disponibles
"""

import sqlite3
import os

def mostrar_permisos_botones():
    db_path = os.path.join('app', 'database', 'ISEMM_MES.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("📋 PERMISOS DE BOTONES/DROPDOWNS DISPONIBLES:")
        print("=" * 60)
        
        cursor.execute('''
            SELECT pagina, seccion, boton, descripcion, id
            FROM permisos_botones 
            WHERE activo = 1
            ORDER BY pagina, seccion, boton
        ''')
        
        permisos = cursor.fetchall()
        pagina_actual = None
        seccion_actual = None
        
        for permiso in permisos:
            pagina, seccion, boton, descripcion, id_permiso = permiso
            
            if pagina != pagina_actual:
                print(f'\n🗂️  {pagina}')
                pagina_actual = pagina
                seccion_actual = None
            
            if seccion != seccion_actual:
                print(f'   📁 {seccion}')
                seccion_actual = seccion
            
            print(f'      ✅ {boton}')
        
        print(f'\n📊 TOTAL: {len(permisos)} permisos de botones')
        
        # Verificar que no hay permisos generales
        cursor.execute('SELECT COUNT(*) FROM permisos')
        count_generales = cursor.fetchone()[0]
        print(f"🗑️  Permisos generales eliminados: {count_generales} (debe ser 0)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    mostrar_permisos_botones()
