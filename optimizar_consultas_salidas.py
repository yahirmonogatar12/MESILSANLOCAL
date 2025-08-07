#!/usr/bin/env python3
"""
Script para agregar índices optimizados a la base de datos MySQL
para acelerar las consultas de historial de salidas
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import get_db_connection

def agregar_indices_optimizados():
    """Agregar índices para optimizar consultas de historial de salidas"""
    conn = None
    cursor = None
    try:
        print("🚀 Agregando índices optimizados para consultas de salidas...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Lista de índices a crear
        indices = [
            # Índice principal para fecha_salida (consultas más comunes)
            {
                'tabla': 'control_material_salida',
                'nombre': 'idx_fecha_salida',
                'columnas': 'fecha_salida DESC',
                'descripcion': 'Índice para ordenar por fecha de salida'
            },
            # Índice compuesto para búsquedas por código y fecha
            {
                'tabla': 'control_material_salida',
                'nombre': 'idx_codigo_fecha',
                'columnas': 'codigo_material_recibido, fecha_salida DESC',
                'descripcion': 'Índice compuesto para búsquedas por código y fecha'
            },
            # Índice para número de lote
            {
                'tabla': 'control_material_salida',
                'nombre': 'idx_numero_lote',
                'columnas': 'numero_lote',
                'descripcion': 'Índice para búsquedas por número de lote'
            },
            # Índice para control_material_almacen
            {
                'tabla': 'control_material_almacen',
                'nombre': 'idx_codigo_recibido',
                'columnas': 'codigo_material_recibido',
                'descripcion': 'Índice para JOINs rápidos'
            },
            # Índice para código_material_original
            {
                'tabla': 'control_material_almacen',
                'nombre': 'idx_codigo_original',
                'columnas': 'codigo_material_original',
                'descripcion': 'Índice para búsquedas por código original'
            }
        ]
        
        indices_creados = 0
        
        for indice in indices:
            try:
                # Verificar si el índice ya existe
                cursor.execute(f"""
                    SELECT COUNT(*) as count
                    FROM information_schema.statistics 
                    WHERE table_schema = DATABASE() 
                    AND table_name = '{indice['tabla']}' 
                    AND index_name = '{indice['nombre']}'
                """)
                
                existe = cursor.fetchone()[0] > 0
                
                if existe:
                    print(f"✅ Índice {indice['nombre']} ya existe en {indice['tabla']}")
                else:
                    # Crear el índice
                    sql = f"ALTER TABLE {indice['tabla']} ADD INDEX {indice['nombre']} ({indice['columnas']})"
                    cursor.execute(sql)
                    print(f"✅ Índice {indice['nombre']} creado en {indice['tabla']}: {indice['descripcion']}")
                    indices_creados += 1
                    
            except Exception as e:
                if "Duplicate key name" in str(e):
                    print(f"ℹ️ Índice {indice['nombre']} ya existe")
                else:
                    print(f"❌ Error creando índice {indice['nombre']}: {e}")
        
        # Optimizar tablas
        try:
            cursor.execute("OPTIMIZE TABLE control_material_salida")
            print("✅ Tabla control_material_salida optimizada")
        except Exception as e:
            print(f"⚠️ No se pudo optimizar control_material_salida: {e}")
            
        try:
            cursor.execute("OPTIMIZE TABLE control_material_almacen")
            print("✅ Tabla control_material_almacen optimizada")
        except Exception as e:
            print(f"⚠️ No se pudo optimizar control_material_almacen: {e}")
        
        conn.commit()
        print(f"🎉 Optimización completada. {indices_creados} nuevos índices agregados.")
        
        # Mostrar estadísticas
        cursor.execute("SELECT COUNT(*) FROM control_material_salida")
        salidas_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM control_material_almacen")
        almacen_count = cursor.fetchone()[0]
        
        print(f"📊 Estadísticas:")
        print(f"   - Registros en control_material_salida: {salidas_count}")
        print(f"   - Registros en control_material_almacen: {almacen_count}")
        print(f"✅ Las consultas deberían ser significativamente más rápidas ahora.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error general en agregar_indices_optimizados: {e}")
        return False
        
    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass

if __name__ == "__main__":
    agregar_indices_optimizados()
