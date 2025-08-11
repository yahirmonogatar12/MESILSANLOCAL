#!/usr/bin/env python3
"""
Script para verificar la estructura de la tabla work_orders
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

try:
    from config_mysql import execute_query, test_connection
    
    # Probar la conexión
    print("🔍 Probando conexión a MySQL...")
    if not test_connection():
        print("❌ Error: No se pudo conectar a MySQL")
        sys.exit(1)
    
    print("✅ Conexión exitosa a MySQL")
    
    # Verificar estructura de la tabla work_orders
    print("\n📋 Estructura de la tabla work_orders:")
    print("=" * 70)
    
    try:
        resultado = execute_query("DESCRIBE work_orders")
        if resultado and isinstance(resultado, list):
            for col in resultado:
                if isinstance(col, (list, tuple)) and len(col) >= 4:
                    field = col[0]
                    type_col = col[1]
                    null_col = col[2]
                    key = col[3]
                    default = col[4] if len(col) > 4 else ''
                    extra = col[5] if len(col) > 5 else ''
                    
                    print(f"{field:<20} | {type_col:<20} | {null_col:<5} | {key:<5} | {str(default):<10} | {extra}")
        else:
            print("❌ Error: Resultado inesperado de DESCRIBE")
            print(f"Tipo de resultado: {type(resultado)}")
            print(f"Contenido: {resultado}")
    except Exception as e:
        print(f"❌ Error ejecutando DESCRIBE: {e}")
    
    # Verificar si hay datos en la tabla
    print("\n📊 Contando registros en work_orders:")
    try:
        resultado = execute_query("SELECT COUNT(*) as total FROM work_orders")
        if resultado and isinstance(resultado, list) and len(resultado) > 0:
            total = resultado[0][0]
            print(f"📈 Total de Work Orders: {total}")
            
            # Si hay datos, mostrar algunos ejemplos
            if total > 0:
                print("\n📝 Primeros 3 registros:")
                registros = execute_query("SELECT id, codigo_wo, po_origen, modelo, cantidad, estado, orden_proceso FROM work_orders LIMIT 3")
                if registros and isinstance(registros, list):
                    print("ID | Código WO | PO Origen | Modelo | Cantidad | Estado | Orden Proceso")
                    print("-" * 80)
                    for reg in registros:
                        if isinstance(reg, (list, tuple)) and len(reg) >= 6:
                            orden_proceso = reg[6] if len(reg) > 6 else 'N/A'
                            print(f"{reg[0]} | {reg[1]} | {reg[2]} | {reg[3]} | {reg[4]} | {reg[5]} | {orden_proceso}")
        else:
            print("❌ Error contando registros")
    except Exception as e:
        print(f"❌ Error contando registros: {e}")

except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("💡 Asegúrate de que estás en el directorio correcto")
except Exception as e:
    print(f"❌ Error: {e}")
