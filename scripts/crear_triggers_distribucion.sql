-- Script para triggers automáticos de distribución por tipo de material
-- Ejecutar después de crear_inventarios_base.sql

-- ========================================
-- TRIGGER DE DISTRIBUCIÓN AUTOMÁTICA
-- ========================================

-- Trigger para distribución automática después de salidas
DROP TRIGGER IF EXISTS tr_distribuir_salidas_por_tipo;

CREATE TRIGGER tr_distribuir_salidas_por_tipo
    AFTER INSERT ON control_material_salida
    FOR EACH ROW
BEGIN
    DECLARE v_propiedad_material VARCHAR(50);
    DECLARE v_cantidad_total DECIMAL(10,3);
    DECLARE v_exit_handler_called BOOLEAN DEFAULT FALSE;
    
    -- Manejador de errores
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SET v_exit_handler_called = TRUE;
        INSERT INTO sistema_logs (tabla, accion, descripcion, fecha_evento)
        VALUES ('control_material_salida', 'ERROR_TRIGGER', 
               CONCAT('Error en trigger distribución: ID=', NEW.id), NOW());
    END;
    
    -- Obtener la propiedad del material desde el almacén
    SELECT propiedad_material, cantidad 
    INTO v_propiedad_material, v_cantidad_total
    FROM control_material_almacen 
    WHERE id = NEW.id_material_almacen
    LIMIT 1;
    
    -- Solo procesar si encontramos la propiedad
    IF v_propiedad_material IS NOT NULL AND NOT v_exit_handler_called THEN
        
        -- Distribución para SMD
        IF v_propiedad_material = 'SMD' OR v_propiedad_material LIKE 'SMD%' THEN
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
            
        -- Distribución para IMD
        ELSEIF v_propiedad_material = 'IMD' OR v_propiedad_material LIKE 'IMD%' THEN
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
            
        -- Distribución para MAIN
        ELSEIF v_propiedad_material = 'MAIN' OR v_propiedad_material LIKE 'MAIN%' THEN
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
        
        -- Log del evento si fue exitoso
        IF NOT v_exit_handler_called THEN
            INSERT INTO sistema_logs (tabla, accion, descripcion, fecha_evento)
            VALUES ('control_material_salida', 'AUTO_DISTRIBUCION', 
                   CONCAT('Material distribuido: ', v_propiedad_material, ' ID=', NEW.id), NOW());
        END IF;
        
    END IF;
    
END;

-- ========================================
-- TRIGGERS DE HISTORIAL AUTOMÁTICO
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
