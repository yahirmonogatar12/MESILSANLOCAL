#!/usr/bin/env python3
"""
Script para inicializar el inventario general con datos existentes
Ejecutar una sola vez después de implementar el nuevo sistema
"""

from app.db import recalcular_inventario_general, obtener_inventario_general

def main():
    print("🚀 Inicializando inventario general...")
    print("=" * 50)
    
    # Recalcular inventario desde cero
    resultado = recalcular_inventario_general()
    
    if resultado:
        print("✅ Inventario general inicializado correctamente")
        
        # Mostrar resumen
        inventario = obtener_inventario_general()
        print(f"\n📊 RESUMEN DEL INVENTARIO GENERAL:")
        print(f"   Total de números de parte: {len(inventario)}")
        
        if inventario:
            print(f"\n📋 PRIMEROS 10 REGISTROS:")
            for i, item in enumerate(inventario[:10]):
                print(f"   {i+1:2d}. {item['numero_parte']:<20} | "
                      f"Entradas: {item['cantidad_entradas']:>8.1f} | "
                      f"Salidas: {item['cantidad_salidas']:>8.1f} | "
                      f"Total: {item['cantidad_total']:>8.1f}")
            
            if len(inventario) > 10:
                print(f"   ... y {len(inventario) - 10} registros más")
        
        print(f"\n✅ Inventario general listo para usar")
        print(f"💡 Ahora el sistema mantendrá automáticamente:")
        print(f"   - Historial completo de ENTRADAS (control_material_almacen)")
        print(f"   - Historial completo de SALIDAS (control_material_salida)")  
        print(f"   - Inventario unificado por número de parte (inventario_general)")
        
    else:
        print("❌ Error al inicializar inventario general")
        return False

if __name__ == "__main__":
    main()
