#!/usr/bin/env python3
"""
Script simple para verificar la tabla work_orders
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

try:
    from config_mysql import execute_query
    
    # Verificar estructura de la tabla work_orders usando SHOW COLUMNS
    print("📋 Estructura de la tabla work_orders:")
    print("=" * 70)
    
    try:
        resultado = execute_query("SHOW COLUMNS FROM work_orders", fetch='all')
        if resultado and isinstance(resultado, list):
            print("Campo               | Tipo            | Nulo | Clave | Default | Extra")
            print("-" * 70)
            for col in resultado:
                if isinstance(col, dict):
                    field = col.get('Field', '')
                    type_col = col.get('Type', '')
                    null_col = col.get('Null', '')
                    key = col.get('Key', '')
                    default = col.get('Default', '')
                    extra = col.get('Extra', '')
                    
                    print(f"{field:<20} | {type_col:<15} | {null_col:<4} | {key:<5} | {str(default):<7} | {extra}")
        else:
            print(f"❌ Error: Resultado inesperado: {type(resultado)} - {resultado}")
    except Exception as e:
        print(f"❌ Error ejecutando SHOW COLUMNS: {e}")
    
    # Verificar si hay datos en la tabla
    print("\n📊 Contando registros en work_orders:")
    try:
        resultado = execute_query("SELECT COUNT(*) as total FROM work_orders", fetch='one')
        if resultado and isinstance(resultado, dict):
            total = resultado.get('total', 0)
            print(f"📈 Total de Work Orders: {total}")
        else:
            print(f"❌ Error contando: {type(resultado)} - {resultado}")
    except Exception as e:
        print(f"❌ Error contando registros: {e}")

except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
