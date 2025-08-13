-- Script simplificado para triggers de distribución automática
-- Sin DECLARE statements complejos

-- ========================================
-- TRIGGER SIMPLIFICADO DE DISTRIBUCIÓN AUTOMÁTICA
-- ========================================

-- Eliminar trigger existente
DROP TRIGGER IF EXISTS tr_distribuir_salidas_por_tipo;

-- Crear trigger simplificado
CREATE TRIGGER tr_distribuir_salidas_por_tipo
    AFTER INSERT ON control_material_salida
    FOR EACH ROW
BEGIN
    -- Distribución directa para SMD
    IF (SELECT propiedad_material FROM control_material_almacen WHERE id = NEW.id_material_almacen LIMIT 1) LIKE 'SMD%' THEN
        INSERT INTO InventarioRollosSMD (
            numero_parte, codigo_barras, lote, cantidad_inicial, cantidad_actual,
            estado, movimiento_origen_id, usuario_responsable, observaciones
        ) VALUES (
            NEW.numero_parte,
            CONCAT('AUTO_SMD_', NEW.id, '_', DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s')),
            NEW.lote,
            NEW.cantidad,
            NEW.cantidad,
            'ACTIVO',
            NEW.id,
            COALESCE(NEW.usuario, 'SISTEMA_AUTO'),
            CONCAT('Auto-distribución SMD desde salida ID: ', NEW.id)
        );
    END IF;
    
    -- Distribución directa para IMD
    IF (SELECT propiedad_material FROM control_material_almacen WHERE id = NEW.id_material_almacen LIMIT 1) LIKE 'IMD%' THEN
        INSERT INTO InventarioRollosIMD (
            numero_parte, codigo_barras, lote, cantidad_inicial, cantidad_actual,
            estado, movimiento_origen_id, usuario_responsable, observaciones
        ) VALUES (
            NEW.numero_parte,
            CONCAT('AUTO_IMD_', NEW.id, '_', DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s')),
            NEW.lote,
            NEW.cantidad,
            NEW.cantidad,
            'ACTIVO',
            NEW.id,
            COALESCE(NEW.usuario, 'SISTEMA_AUTO'),
            CONCAT('Auto-distribución IMD desde salida ID: ', NEW.id)
        );
    END IF;
    
    -- Distribución directa para MAIN
    IF (SELECT propiedad_material FROM control_material_almacen WHERE id = NEW.id_material_almacen LIMIT 1) LIKE 'MAIN%' THEN
        INSERT INTO InventarioRollosMAIN (
            numero_parte, codigo_barras, lote, cantidad_inicial, cantidad_actual,
            estado, movimiento_origen_id, usuario_responsable, observaciones
        ) VALUES (
            NEW.numero_parte,
            CONCAT('AUTO_MAIN_', NEW.id, '_', DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s')),
            NEW.lote,
            NEW.cantidad,
            NEW.cantidad,
            'ACTIVO',
            NEW.id,
            COALESCE(NEW.usuario, 'SISTEMA_AUTO'),
            CONCAT('Auto-distribución MAIN desde salida ID: ', NEW.id)
        );
    END IF;
END;

-- ========================================
-- TRIGGERS DE HISTORIAL SIMPLIFICADOS
-- ========================================

-- Trigger para historial IMD
DROP TRIGGER IF EXISTS tr_historial_imd_insert;

CREATE TRIGGER tr_historial_imd_insert
    AFTER INSERT ON InventarioRollosIMD
    FOR EACH ROW
BEGIN
    INSERT INTO HistorialMovimientosRollosIMD (
        rollo_id, tipo_movimiento, descripcion,
        estado_nuevo, cantidad_nueva, usuario, fecha_movimiento
    ) VALUES (
        NEW.id,
        'ENTRADA',
        CONCAT('Rollo agregado automáticamente: ', NEW.numero_parte),
        NEW.estado,
        NEW.cantidad_actual,
        NEW.usuario_responsable,
        NOW()
    );
END;

-- Trigger para historial MAIN
DROP TRIGGER IF EXISTS tr_historial_main_insert;

CREATE TRIGGER tr_historial_main_insert
    AFTER INSERT ON InventarioRollosMAIN
    FOR EACH ROW
BEGIN
    INSERT INTO HistorialMovimientosRollosMAIN (
        rollo_id, tipo_movimiento, descripcion,
        estado_nuevo, cantidad_nueva, usuario, fecha_movimiento
    ) VALUES (
        NEW.id,
        'ENTRADA',
        CONCAT('Componente agregado automáticamente: ', NEW.numero_parte),
        NEW.estado,
        NEW.cantidad_actual,
        NEW.usuario_responsable,
        NOW()
    );
END;
