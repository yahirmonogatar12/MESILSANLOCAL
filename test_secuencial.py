#!/usr/bin/env python3
"""
Script de prueba para verificar el funcionamiento del siguiente secuencial
"""

import sys
import os
import sqlite3
import re
from datetime import datetime

# Agregar el directorio de la aplicación al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import get_db_connection

def test_siguiente_secuencial(codigo_material="0RH5602C522"):
    """
    Probar la función de siguiente secuencial
    """
    print(f"🔍 Probando siguiente secuencial para código: {codigo_material}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener la fecha actual en formato YYYYMMDD
        fecha_actual = datetime.now().strftime('%Y%m%d')
        
        print(f"📅 Fecha actual: {fecha_actual}")
        
        # Buscar registros específicos para este código de material y fecha exacta
        query = """
        SELECT codigo_material_recibido, fecha_registro
        FROM control_material_almacen 
        WHERE codigo_material_recibido LIKE ?
        ORDER BY fecha_registro DESC
        """
        
        # Patrón de búsqueda: CODIGO-YYYYMMDD seguido de 4 dígitos
        patron_busqueda = f"{codigo_material},{fecha_actual}%"
        
        print(f"🔍 Patrón de búsqueda: {patron_busqueda}")
        
        cursor.execute(query, (patron_busqueda,))
        resultados = cursor.fetchall()
        
        print(f"📊 Encontrados {len(resultados)} registros:")
        
        for i, resultado in enumerate(resultados):
            print(f"  {i+1}. {resultado['codigo_material_recibido']} - {resultado['fecha_registro']}")
        
        # Buscar el secuencial más alto para este código de material y fecha específica
        secuencial_mas_alto = 0
        patron_regex = rf'^{re.escape(codigo_material)},{fecha_actual}(\d{{4}})$'
        
        print(f"🔍 Patrón regex: {patron_regex}")
        
        for resultado in resultados:
            codigo_recibido = resultado['codigo_material_recibido'] or ''
            
            print(f"📝 Analizando: {codigo_recibido}")
            
            # Buscar patrón exacto: CODIGO_MATERIAL,YYYYMMDD0001
            match = re.match(patron_regex, codigo_recibido)
            
            if match:
                secuencial_encontrado = int(match.group(1))
                print(f"✅ Secuencial encontrado: {secuencial_encontrado}")
                
                if secuencial_encontrado > secuencial_mas_alto:
                    secuencial_mas_alto = secuencial_encontrado
                    print(f"📊 Nuevo secuencial más alto: {secuencial_mas_alto}")
            else:
                print(f"❌ No coincide con patrón: {codigo_recibido}")
        
        siguiente_secuencial = secuencial_mas_alto + 1
        
        # Generar el próximo código de material recibido completo
        siguiente_codigo_completo = f"{codigo_material},{fecha_actual}{siguiente_secuencial:04d}"
        
        print(f"\n🎯 RESULTADO:")
        print(f"   - Secuencial más alto encontrado: {secuencial_mas_alto}")
        print(f"   - Siguiente secuencial: {siguiente_secuencial}")
        print(f"   - Próximo código completo: {siguiente_codigo_completo}")
        
        cursor.close()
        conn.close()
        
        return {
            'success': True,
            'siguiente_secuencial': siguiente_secuencial,
            'fecha_actual': fecha_actual,
            'codigo_material': codigo_material,
            'secuencial_mas_alto_encontrado': secuencial_mas_alto,
            'patron_busqueda': patron_busqueda,
            'proximo_codigo_completo': siguiente_codigo_completo
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'siguiente_secuencial': 1
        }

if __name__ == "__main__":
    # Probar con el código de la imagen
    result = test_siguiente_secuencial("0RH5602C522")
    print(f"\n📋 Resultado final: {result}")
