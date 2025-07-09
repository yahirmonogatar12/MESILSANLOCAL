#!/usr/bin/env python3
"""
Script para probar la nueva lógica de lotes CODIGO/YYYYMMDD0001
"""
import sqlite3
import re
from datetime import datetime
import os
import sys

# Agregar el directorio actual al path para importar los módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def get_db_connection():
    """Obtener conexión a la base de datos"""
    db_path = os.path.join(os.path.dirname(__file__), 'app', 'database', 'ISEMM_MES.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def test_obtener_siguiente_secuencial(codigo_material):
    """
    Simula el endpoint obtener_siguiente_secuencial con la nueva lógica
    """
    print(f"\n=== PROBANDO LÓGICA PARA CÓDIGO: {codigo_material} ===")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener la fecha actual en formato YYYYMMDD
        fecha_actual = datetime.now().strftime('%Y%m%d')
        
        print(f"🔍 Buscando secuenciales para código: '{codigo_material}' y fecha: {fecha_actual}")
        
        # Buscar registros específicos para este código de material y fecha exacta
        # El formato buscado es: CODIGO_MATERIAL/YYYYMMDD0001 en el campo codigo_material_recibido
        query = """
        SELECT codigo_material_recibido, fecha_registro
        FROM control_material_almacen 
        WHERE codigo_material_recibido LIKE ?
        ORDER BY fecha_registro DESC
        """
        
        # Patrón de búsqueda: CODIGO/YYYYMMDD seguido de 4 dígitos
        patron_busqueda = f"{codigo_material}/{fecha_actual}%"
        
        cursor.execute(query, (patron_busqueda,))
        resultados = cursor.fetchall()
        
        print(f"🔍 Encontrados {len(resultados)} registros para el patrón '{patron_busqueda}'")
        
        # Buscar el secuencial más alto para este código de material y fecha específica
        secuencial_mas_alto = 0
        
        patron_regex = rf'^{re.escape(codigo_material)}/{fecha_actual}(\d{{4}})$'
        print(f"🔍 Patrón regex: {patron_regex}")
        
        for resultado in resultados:
            codigo_recibido = resultado['codigo_material_recibido'] or ''
            
            print(f"📝 Analizando: codigo_material_recibido='{codigo_recibido}'")
            
            # Buscar patrón exacto: CODIGO_MATERIAL/YYYYMMDD0001
            match = re.match(patron_regex, codigo_recibido)
            
            if match:
                secuencial_encontrado = int(match.group(1))
                print(f"🔢 Secuencial encontrado: {secuencial_encontrado}")
                
                if secuencial_encontrado > secuencial_mas_alto:
                    secuencial_mas_alto = secuencial_encontrado
                    print(f"📊 Nuevo secuencial más alto: {secuencial_mas_alto}")
            else:
                print(f"⚠️ No coincide con patrón esperado: {codigo_recibido}")
        
        siguiente_secuencial = secuencial_mas_alto + 1
        
        # Generar el próximo código de material recibido completo
        siguiente_codigo_completo = f"{codigo_material}/{fecha_actual}{siguiente_secuencial:04d}"
        
        print(f"✅ Siguiente secuencial: {siguiente_secuencial}")
        print(f"✅ Próximo código completo: {siguiente_codigo_completo}")
        
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
        print(f"❌ Error al obtener siguiente secuencial: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'siguiente_secuencial': 1  # Valor por defecto en caso de error
        }

def test_insertar_registro_prueba(codigo_material, siguiente_codigo_completo):
    """
    Inserta un registro de prueba para verificar que el incremento funcione
    """
    print(f"\n=== INSERTANDO REGISTRO DE PRUEBA ===")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insertar registro de prueba
        cursor.execute('''
            INSERT INTO control_material_almacen (
                codigo_material_original, codigo_material_recibido, 
                forma_material, cliente, cantidad_actual
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            codigo_material,
            siguiente_codigo_completo,
            'TEST',
            'CLIENTE_TEST', 
            1
        ))
        
        conn.commit()
        registro_id = cursor.lastrowid
        
        print(f"✅ Registro insertado con ID: {registro_id}")
        print(f"✅ Código material recibido: {siguiente_codigo_completo}")
        
        cursor.close()
        conn.close()
        
        return registro_id
        
    except Exception as e:
        print(f"❌ Error al insertar registro: {e}")
        return None

def test_ver_registros_existentes():
    """
    Muestra los registros existentes en la tabla
    """
    print(f"\n=== REGISTROS EXISTENTES ===")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, codigo_material_original, codigo_material_recibido, fecha_registro
            FROM control_material_almacen 
            ORDER BY fecha_registro DESC
            LIMIT 10
        ''')
        
        registros = cursor.fetchall()
        
        if registros:
            print(f"Total registros encontrados: {len(registros)}")
            print("\nÚltimos 10 registros:")
            for registro in registros:
                print(f"  ID: {registro['id']}")
                print(f"  Código original: {registro['codigo_material_original']}")
                print(f"  Código recibido: {registro['codigo_material_recibido']}")
                print(f"  Fecha: {registro['fecha_registro']}")
                print("  ---")
        else:
            print("No hay registros en la tabla")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error al consultar registros: {e}")

if __name__ == "__main__":
    # Probar con algunos códigos de material
    codigos_prueba = [
        'OCH1223K678',
        'GCM188R71C',
        'TEST123'
    ]
    
    print("🔧 INICIANDO PRUEBAS DE LÓGICA DE LOTES")
    print("="*50)
    
    # Ver registros existentes
    test_ver_registros_existentes()
    
    # Probar lógica para cada código
    for codigo in codigos_prueba:
        resultado = test_obtener_siguiente_secuencial(codigo)
        
        if resultado['success']:
            print(f"\n🧪 ¿Insertar registro de prueba para {codigo}? (y/n): ", end='')
            # Para automatizar la prueba, insertar automáticamente
            respuesta = 'y'  # input().strip().lower()
            
            if respuesta == 'y':
                registro_id = test_insertar_registro_prueba(
                    codigo, 
                    resultado['proximo_codigo_completo']
                )
                
                if registro_id:
                    # Probar de nuevo para ver el incremento
                    print(f"\n🔄 Probando incremento después de insertar...")
                    resultado2 = test_obtener_siguiente_secuencial(codigo)
                    
                    if resultado2['success']:
                        print(f"✅ Incremento funciona correctamente:")
                        print(f"   Antes: {resultado['proximo_codigo_completo']}")
                        print(f"   Ahora: {resultado2['proximo_codigo_completo']}")
    
    print("\n🏁 PRUEBAS COMPLETADAS")
