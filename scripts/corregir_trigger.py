#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corregir el trigger de distribución automática
"""

import mysql.connector

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
    print("🔧 Corrigiendo trigger de distribución automática...")
    
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Eliminar trigger existente
        print("1. Eliminando trigger existente...")
        cursor.execute("DROP TRIGGER IF EXISTS tr_distribuir_salidas_por_tipo")
        
        # Crear trigger corregido
        print("2. Creando trigger corregido...")
        trigger_sql = """
CREATE TRIGGER tr_distribuir_salidas_por_tipo
    AFTER INSERT ON control_material_salida
    FOR EACH ROW
BEGIN
    -- Distribución directa para IMD basado en especificación
    IF NEW.especificacion_material LIKE '%IMD%' OR NEW.modelo LIKE '%IMD%' THEN
        INSERT INTO InventarioRollosIMD (
            numero_parte, codigo_barras, lote, cantidad_inicial, cantidad_actual,
            estado, movimiento_origen_id, usuario_responsable, observaciones
        ) VALUES (
            NEW.codigo_material_recibido,
            CONCAT('AUTO_IMD_', NEW.id, '_', DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s')),
            NEW.numero_lote,
            NEW.cantidad_salida,
            NEW.cantidad_salida,
            'ACTIVO',
            NEW.id,
            'SISTEMA_AUTO',
            CONCAT('Auto-distribución IMD desde salida ID: ', NEW.id, ' - Modelo: ', NEW.modelo)
        );
    END IF;
    
    -- Distribución directa para MAIN basado en especificación
    IF NEW.especificacion_material LIKE '%MAIN%' OR NEW.modelo LIKE '%MAIN%' THEN
        INSERT INTO InventarioRollosMAIN (
            numero_parte, codigo_barras, lote, cantidad_inicial, cantidad_actual,
            estado, movimiento_origen_id, usuario_responsable, observaciones
        ) VALUES (
            NEW.codigo_material_recibido,
            CONCAT('AUTO_MAIN_', NEW.id, '_', DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s')),
            NEW.numero_lote,
            NEW.cantidad_salida,
            NEW.cantidad_salida,
            'ACTIVO',
            NEW.id,
            'SISTEMA_AUTO',
            CONCAT('Auto-distribución MAIN desde salida ID: ', NEW.id, ' - Modelo: ', NEW.modelo)
        );
    END IF;
END
"""
        
        cursor.execute(trigger_sql)
        connection.commit()
        
        print("✅ Trigger corregido exitosamente")
        
        # Verificar que el trigger existe
        cursor.execute("SHOW TRIGGERS LIKE 'tr_distribuir_salidas_por_tipo'")
        if cursor.fetchone():
            print("✅ Trigger verificado - funcionando correctamente")
        else:
            print("❌ Trigger no encontrado después de la creación")
            
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
    input("Presione Enter para continuar...")
