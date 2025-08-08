"""
Script para crear tabla de inventario consolidado y triggers automáticos
Este enfoque mejora significativamente la eficiencia del sistema
"""

import os
from app.config_mysql import get_mysql_connection_string
import pymysql

def crear_inventario_consolidado():
    """Crear tabla de inventario consolidado con triggers automáticos"""
    
    config = get_mysql_connection_string()
    if not config:
        print("❌ No se pudo obtener configuración MySQL")
        return False
    
    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        
        print("🚀 Creando sistema de inventario consolidado...")
        
        # 1. Crear tabla de inventario consolidado
        tabla_inventario = """
        CREATE TABLE IF NOT EXISTS inventario_consolidado (
            id INT AUTO_INCREMENT PRIMARY KEY,
            numero_parte VARCHAR(100) NOT NULL UNIQUE,
            codigo_material VARCHAR(255),
            especificacion TEXT,
            propiedad_material VARCHAR(100) DEFAULT 'COMMON USE',
            total_entradas DECIMAL(15,3) DEFAULT 0,
            total_salidas DECIMAL(15,3) DEFAULT 0,
            cantidad_actual DECIMAL(15,3) DEFAULT 0,
            total_lotes INT DEFAULT 0,
            fecha_primera_entrada DATETIME NULL,
            fecha_ultima_entrada DATETIME NULL,
            fecha_ultima_salida DATETIME NULL,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            
            INDEX idx_numero_parte (numero_parte),
            INDEX idx_cantidad_actual (cantidad_actual),
            INDEX idx_fecha_actualizacion (fecha_actualizacion)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor.execute(tabla_inventario)
        print("✅ Tabla inventario_consolidado creada")
        
        # 2. Crear trigger para actualizaciones de entradas (control_material_almacen)
        trigger_entradas = """
        CREATE TRIGGER IF NOT EXISTS tr_actualizar_inventario_entrada
        AFTER INSERT ON control_material_almacen
        FOR EACH ROW
        BEGIN
            INSERT INTO inventario_consolidado (
                numero_parte, 
                codigo_material, 
                especificacion, 
                propiedad_material,
                total_entradas,
                cantidad_actual,
                total_lotes,
                fecha_primera_entrada,
                fecha_ultima_entrada
            ) VALUES (
                NEW.numero_parte,
                NEW.codigo_material,
                NEW.especificacion,
                NEW.propiedad_material,
                NEW.cantidad_actual,
                NEW.cantidad_actual,
                1,
                NEW.fecha_recibo,
                NEW.fecha_recibo
            )
            ON DUPLICATE KEY UPDATE
                codigo_material = COALESCE(NEW.codigo_material, codigo_material),
                especificacion = COALESCE(NEW.especificacion, especificacion),
                propiedad_material = COALESCE(NEW.propiedad_material, propiedad_material),
                total_entradas = total_entradas + NEW.cantidad_actual,
                cantidad_actual = total_entradas - total_salidas + NEW.cantidad_actual,
                total_lotes = (
                    SELECT COUNT(DISTINCT numero_lote_material) 
                    FROM control_material_almacen 
                    WHERE numero_parte = NEW.numero_parte AND cantidad_actual > 0
                ),
                fecha_primera_entrada = CASE 
                    WHEN fecha_primera_entrada IS NULL OR NEW.fecha_recibo < fecha_primera_entrada 
                    THEN NEW.fecha_recibo 
                    ELSE fecha_primera_entrada 
                END,
                fecha_ultima_entrada = CASE 
                    WHEN NEW.fecha_recibo > fecha_ultima_entrada 
                    THEN NEW.fecha_recibo 
                    ELSE fecha_ultima_entrada 
                END;
        END
        """
        
        cursor.execute("DROP TRIGGER IF EXISTS tr_actualizar_inventario_entrada")
        cursor.execute(trigger_entradas)
        print("✅ Trigger de entradas creado")
        
        # 3. Crear trigger para actualizaciones de salidas (control_material_salida)
        # Nota: En control_material_salida no hay numero_parte directo, se debe derivar del codigo_material_recibido
        trigger_salidas = """
        CREATE TRIGGER IF NOT EXISTS tr_actualizar_inventario_salida
        AFTER INSERT ON control_material_salida
        FOR EACH ROW
        BEGIN
            -- Extraer numero_parte del codigo_material_recibido (asumiendo formato: numero_parte!...)
            SET @numero_parte = SUBSTRING_INDEX(NEW.codigo_material_recibido, '!', 1);
            
            UPDATE inventario_consolidado 
            SET 
                total_salidas = total_salidas + NEW.cantidad_salida,
                cantidad_actual = total_entradas - (total_salidas + NEW.cantidad_salida),
                fecha_ultima_salida = NEW.fecha_salida
            WHERE numero_parte = @numero_parte;
            
            -- Si no existe el registro, crearlo (caso edge)
            IF ROW_COUNT() = 0 THEN
                INSERT INTO inventario_consolidado (
                    numero_parte,
                    total_salidas,
                    cantidad_actual,
                    fecha_ultima_salida
                ) VALUES (
                    @numero_parte,
                    NEW.cantidad_salida,
                    -NEW.cantidad_salida,
                    NEW.fecha_salida
                );
            END IF;
        END
        """
        
        cursor.execute("DROP TRIGGER IF EXISTS tr_actualizar_inventario_salida")
        cursor.execute(trigger_salidas)
        print("✅ Trigger de salidas creado")
        
        # 4. Crear trigger para actualizaciones en control_material_almacen
        trigger_update_entradas = """
        CREATE TRIGGER IF NOT EXISTS tr_actualizar_inventario_update
        AFTER UPDATE ON control_material_almacen
        FOR EACH ROW
        BEGIN
            IF OLD.cantidad_actual != NEW.cantidad_actual THEN
                UPDATE inventario_consolidado 
                SET 
                    total_entradas = total_entradas - OLD.cantidad_actual + NEW.cantidad_actual,
                    cantidad_actual = total_entradas - total_salidas - OLD.cantidad_actual + NEW.cantidad_actual,
                    total_lotes = (
                        SELECT COUNT(DISTINCT numero_lote_material) 
                        FROM control_material_almacen 
                        WHERE numero_parte = NEW.numero_parte AND cantidad_actual > 0
                    )
                WHERE numero_parte = NEW.numero_parte;
            END IF;
        END
        """
        
        cursor.execute("DROP TRIGGER IF EXISTS tr_actualizar_inventario_update")
        cursor.execute(trigger_update_entradas)
        print("✅ Trigger de actualización de entradas creado")
        
        conn.commit()
        print("🎉 Sistema de inventario consolidado creado exitosamente")
        
        # 5. Poblar tabla con datos existentes
        print("📊 Poblando inventario consolidado con datos existentes...")
        
        poblar_query = """
        INSERT INTO inventario_consolidado (
            numero_parte,
            codigo_material,
            especificacion,
            propiedad_material,
            total_entradas,
            total_salidas,
            cantidad_actual,
            total_lotes,
            fecha_primera_entrada,
            fecha_ultima_entrada,
            fecha_ultima_salida
        )
        SELECT 
            e.numero_parte,
            e.codigo_material,
            e.especificacion,
            e.propiedad_material,
            COALESCE(e.total_entradas, 0) as total_entradas,
            COALESCE(s.total_salidas, 0) as total_salidas,
            COALESCE(e.total_entradas, 0) - COALESCE(s.total_salidas, 0) as cantidad_actual,
            COALESCE(e.total_lotes, 0) as total_lotes,
            e.fecha_primera_entrada,
            e.fecha_ultima_entrada,
            s.fecha_ultima_salida
        FROM (
            SELECT 
                numero_parte,
                MAX(codigo_material) as codigo_material,
                MAX(especificacion) as especificacion,
                MAX(propiedad_material) as propiedad_material,
                SUM(cantidad_actual) as total_entradas,
                COUNT(DISTINCT numero_lote_material) as total_lotes,
                MIN(fecha_recibo) as fecha_primera_entrada,
                MAX(fecha_recibo) as fecha_ultima_entrada
            FROM control_material_almacen
            GROUP BY numero_parte
        ) e
        LEFT JOIN (
            SELECT 
                SUBSTRING_INDEX(codigo_material_recibido, '!', 1) as numero_parte,
                SUM(cantidad_salida) as total_salidas,
                MAX(fecha_salida) as fecha_ultima_salida
            FROM control_material_salida
            GROUP BY SUBSTRING_INDEX(codigo_material_recibido, '!', 1)
        ) s ON e.numero_parte = s.numero_parte
        ON DUPLICATE KEY UPDATE
            total_entradas = VALUES(total_entradas),
            total_salidas = VALUES(total_salidas),
            cantidad_actual = VALUES(cantidad_actual),
            total_lotes = VALUES(total_lotes),
            fecha_primera_entrada = VALUES(fecha_primera_entrada),
            fecha_ultima_entrada = VALUES(fecha_ultima_entrada),
            fecha_ultima_salida = VALUES(fecha_ultima_salida)
        """
        
        cursor.execute(poblar_query)
        filas_afectadas = cursor.rowcount
        conn.commit()
        
        print(f"✅ Inventario consolidado poblado con {filas_afectadas} registros")
        
        # 6. Verificar algunos registros
        cursor.execute("""
            SELECT numero_parte, total_entradas, total_salidas, cantidad_actual, total_lotes
            FROM inventario_consolidado 
            ORDER BY fecha_ultima_entrada DESC 
            LIMIT 5
        """)
        
        registros = cursor.fetchall()
        print("\n📋 Muestra de inventario consolidado:")
        for reg in registros:
            print(f"  {reg[0]}: Entradas={reg[1]}, Salidas={reg[2]}, Actual={reg[3]}, Lotes={reg[4]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando inventario consolidado: {e}")
        return False

if __name__ == "__main__":
    crear_inventario_consolidado()
