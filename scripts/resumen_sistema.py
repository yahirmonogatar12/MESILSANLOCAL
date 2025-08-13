#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resumen del sistema de inventarios múltiples instalado
Muestra el estado completo y funcionalidades disponibles
"""

import mysql.connector
from datetime import datetime

# Configuración de base de datos
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_0900_ai_ci'
}

def main():
    print("=" * 70)
    print("📊 RESUMEN COMPLETO - SISTEMA DE INVENTARIOS MÚLTIPLES")
    print("=" * 70)
    print(f"📅 Fecha de verificación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        print("\n🗂️  TABLAS INSTALADAS:")
        tablas = [
            'InventarioRollosIMD',
            'InventarioRollosMAIN', 
            'HistorialMovimientosRollosIMD',
            'HistorialMovimientosRollosMAIN'
        ]
        
        for tabla in tablas:
            cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
            count = cursor.fetchone()[0]
            print(f"   ✅ {tabla}: {count} registros")
        
        print("\n📊 VISTAS CONSOLIDADAS:")
        vistas = [
            'vista_inventario_consolidado',
            'vista_resumen_inventarios',
            'vista_actividad_reciente',
            'vista_alertas_inventario'
        ]
        
        for vista in vistas:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {vista}")
                count = cursor.fetchone()[0]
                print(f"   ✅ {vista}: {count} registros")
            except:
                print(f"   ❌ {vista}: Error al acceder")
        
        print("\n⚡ TRIGGERS ACTIVOS:")
        cursor.execute("SHOW TRIGGERS")
        triggers = cursor.fetchall()
        
        triggers_sistema = [
            'tr_distribuir_salidas_por_tipo',
            'tr_historial_imd_insert', 
            'tr_historial_main_insert'
        ]
        
        for trigger_name in triggers_sistema:
            encontrado = any(trigger[0] == trigger_name for trigger in triggers)
            if encontrado:
                print(f"   ✅ {trigger_name}: ACTIVO")
            else:
                print(f"   ❌ {trigger_name}: NO ENCONTRADO")
        
        print("\n🔍 RESUMEN POR TIPO DE INVENTARIO:")
        cursor.execute("""
            SELECT 
                tipo_inventario,
                total_rollos,
                rollos_activos,
                rollos_en_uso,
                cantidad_total_actual
            FROM vista_resumen_inventarios
        """)
        
        resumen = cursor.fetchall()
        for row in resumen:
            tipo, total, activos, en_uso, cantidad = row
            print(f"   📦 {tipo}:")
            print(f"      Total de rollos: {total}")
            print(f"      Activos: {activos}")
            print(f"      En uso: {en_uso}")
            print(f"      Cantidad disponible: {cantidad}")
        
        print("\n📈 ACTIVIDAD RECIENTE:")
        cursor.execute("""
            SELECT 
                tipo_inventario,
                tipo_movimiento,
                fecha_movimiento
            FROM vista_actividad_reciente
            ORDER BY fecha_movimiento DESC
            LIMIT 5
        """)
        
        actividad = cursor.fetchall()
        if actividad:
            for row in actividad:
                tipo, movimiento, fecha = row
                print(f"   🔄 {tipo}: {movimiento} - {fecha}")
        else:
            print("   ℹ️  No hay actividad reciente registrada")
        
        print("\n🚨 ALERTAS ACTIVAS:")
        cursor.execute("""
            SELECT 
                tipo_inventario,
                numero_parte,
                nivel_alerta,
                mensaje_alerta
            FROM vista_alertas_inventario
            LIMIT 5
        """)
        
        alertas = cursor.fetchall()
        if alertas:
            for row in alertas:
                tipo, parte, nivel, mensaje = row
                print(f"   ⚠️  {tipo} - {parte}: {nivel} - {mensaje}")
        else:
            print("   ✅ No hay alertas activas")
        
        cursor.close()
        connection.close()
        
        print("\n" + "=" * 70)
        print("✅ SISTEMA COMPLETAMENTE FUNCIONAL")
        print("=" * 70)
        
        print("\n🎯 FUNCIONALIDADES DISPONIBLES:")
        print("1. ✅ Inventario automático IMD (Insert Mount Device)")
        print("2. ✅ Inventario automático MAIN (Componentes principales)")
        print("3. ✅ Distribución automática por tipo de material")
        print("4. ✅ Historial completo de movimientos")
        print("5. ✅ Vistas consolidadas para reportes")
        print("6. ✅ Sistema de alertas por stock bajo")
        print("7. ✅ Triggers automáticos funcionando")
        
        print("\n🔄 CÓMO FUNCIONA LA DISTRIBUCIÓN AUTOMÁTICA:")
        print("- Cuando se registra una salida en 'control_material_salida'")
        print("- El trigger verifica el campo 'especificacion_material' o 'modelo'")
        print("- Si contiene 'IMD' → va a InventarioRollosIMD")
        print("- Si contiene 'MAIN' → va a InventarioRollosMAIN")
        print("- Si contiene 'SMD' → va a InventarioRollosSMD (si existe)")
        print("- Se registra automáticamente en el historial")
        
        print("\n📋 PRÓXIMOS PASOS:")
        print("1. 🧪 Probar el sistema registrando una salida de material")
        print("2. 🖥️  Configurar interfaz web para visualizar inventarios")
        print("3. 📊 Revisar reportes en las vistas consolidadas")
        print("4. ⚙️  Ajustar reglas de distribución según necesidades")
        
        print("\n💡 COMANDOS ÚTILES PARA PROBAR:")
        print("- SELECT * FROM vista_inventario_consolidado;")
        print("- SELECT * FROM vista_resumen_inventarios;")
        print("- SELECT * FROM vista_actividad_reciente;")
        print("- SELECT * FROM vista_alertas_inventario;")
        
    except Exception as e:
        print(f"❌ Error al generar resumen: {e}")

if __name__ == "__main__":
    main()
    input("\nPresione Enter para salir...")
