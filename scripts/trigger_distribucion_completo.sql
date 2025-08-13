-- Trigger mejorado para distribución automática con SMD incluido

-- Eliminar trigger existente
DROP TRIGGER IF EXISTS tr_distribuir_salidas_por_tipo;

-- Crear trigger mejorado
CREATE TRIGGER tr_distribuir_salidas_por_tipo
    AFTER INSERT ON control_material_salida
    FOR EACH ROW
BEGIN
    -- Distribución directa para SMD basado en especificación
    IF NEW.especificacion_material LIKE '%SMD%' OR NEW.modelo LIKE '%SMD%' THEN
        INSERT INTO InventarioRollosSMD (
            numero_parte, codigo_barras, lote, cantidad_inicial, cantidad_actual,
            estado, movimiento_origen_id, usuario_responsable, observaciones
        ) VALUES (
            NEW.codigo_material_recibido,
            CONCAT('AUTO_SMD_', NEW.id, '_', DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s')),
            NEW.numero_lote,
            NEW.cantidad_salida,
            NEW.cantidad_salida,
            'ACTIVO',
            NEW.id,
            'SISTEMA_AUTO',
            CONCAT('Auto-distribución SMD desde salida ID: ', NEW.id, ' - Modelo: ', NEW.modelo)
        );
    END IF;
    
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
END;