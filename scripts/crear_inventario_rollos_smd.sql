-- Script para crear sistema de inventario automático de rollos SMD
-- Tabla principal para el inventario de rollos en área SMD

-- 1. Crear tabla InventarioRollosSMD
CREATE TABLE IF NOT EXISTS InventarioRollosSMD (
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- Identificación del rollo
    numero_parte VARCHAR(100) NOT NULL,
    codigo_barras VARCHAR(100),
    lote VARCHAR(50),
    
    -- Información del área SMD
    area_smd VARCHAR(50) DEFAULT 'SMD_PRODUCTION',
    fecha_entrada DATETIME DEFAULT CURRENT_TIMESTAMP,
    origen_almacen VARCHAR(100) DEFAULT 'ALMACEN_GENERAL',
    
    -- Estado del rollo
    estado ENUM('ACTIVO', 'EN_USO', 'AGOTADO', 'RETIRADO') DEFAULT 'ACTIVO',
    cantidad_inicial DECIMAL(10,3) DEFAULT 0,
    cantidad_actual DECIMAL(10,3) DEFAULT 0,
    
    -- Información de mounter asignada
    linea_asignada VARCHAR(50),
    maquina_asignada VARCHAR(50),
    slot_asignado VARCHAR(20),
    fecha_asignacion DATETIME NULL,
    
    -- Trazabilidad
    movimiento_origen_id INT,
    usuario_responsable VARCHAR(100) DEFAULT 'SISTEMA_AUTO',
    
    -- Fechas de control
    fecha_ultimo_uso DATETIME NULL,
    fecha_agotamiento DATETIME NULL,
    fecha_retiro DATETIME NULL,
    
    -- Metadatos
    observaciones TEXT,
    creado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
    actualizado_en DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Índices
    INDEX idx_numero_parte (numero_parte),
    INDEX idx_codigo_barras (codigo_barras),
    INDEX idx_lote (lote),
    INDEX idx_estado (estado),
    INDEX idx_fecha_entrada (fecha_entrada),
    INDEX idx_linea_maquina (linea_asignada, maquina_asignada),
    INDEX idx_movimiento_origen (movimiento_origen_id)
);

-- 2. Tabla de historial de movimientos de rollos SMD
CREATE TABLE IF NOT EXISTS HistorialMovimientosRollosSMD (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rollo_id INT NOT NULL,
    
    -- Tipo de movimiento
    tipo_movimiento ENUM('ENTRADA', 'ASIGNACION', 'USO', 'AGOTAMIENTO', 'RETIRO') NOT NULL,
    
    -- Detalles del movimiento
    descripcion VARCHAR(255),
    cantidad_antes DECIMAL(10,3),
    cantidad_despues DECIMAL(10,3),
    
    -- Información de mounter (si aplica)
    linea VARCHAR(50),
    maquina VARCHAR(50),
    slot VARCHAR(20),
    
    -- Trazabilidad
    scan_date VARCHAR(20),
    scan_time VARCHAR(20),
    resultado_scan VARCHAR(10),
    
    -- Control
    usuario VARCHAR(100) DEFAULT 'SISTEMA_AUTO',
    fecha_movimiento DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (rollo_id) REFERENCES InventarioRollosSMD(id) ON DELETE CASCADE,
    INDEX idx_rollo_id (rollo_id),
    INDEX idx_tipo_movimiento (tipo_movimiento),
    INDEX idx_fecha_movimiento (fecha_movimiento)
);

-- 3. Trigger para registro automático desde salidas de almacén
DELIMITER //

CREATE TRIGGER trigger_registro_rollo_smd_salida
AFTER INSERT ON movimientosimd_smd
FOR EACH ROW
BEGIN
    DECLARE existe_rollo INT DEFAULT 0;
    
    -- Solo procesar salidas hacia área SMD
    IF NEW.tipo = 'SALIDA' AND NEW.ubicacion LIKE '%SMD%' THEN
        
        -- Verificar si ya existe el rollo para este número de parte y lote
        SELECT COUNT(*) INTO existe_rollo 
        FROM InventarioRollosSMD 
        WHERE numero_parte = NEW.nparte 
        AND estado = 'ACTIVO';
        
        -- Si no existe, crear nuevo registro
        IF existe_rollo = 0 THEN
            INSERT INTO InventarioRollosSMD (
                numero_parte,
                codigo_barras,
                cantidad_inicial,
                cantidad_actual,
                area_smd,
                origen_almacen,
                movimiento_origen_id,
                observaciones
            ) VALUES (
                NEW.nparte,
                CONCAT('SMD_', NEW.nparte, '_', DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s')),
                NEW.cantidad,
                NEW.cantidad,
                'SMD_PRODUCTION',
                NEW.ubicacion,
                NEW.id,
                CONCAT('Rollo registrado automáticamente desde salida de almacén. Carro: ', COALESCE(NEW.carro, 'N/A'))
            );
            
            -- Registrar en historial
            INSERT INTO HistorialMovimientosRollosSMD (
                rollo_id,
                tipo_movimiento,
                descripcion,
                cantidad_antes,
                cantidad_despues,
                usuario
            ) VALUES (
                LAST_INSERT_ID(),
                'ENTRADA',
                CONCAT('Entrada automática desde almacén: ', NEW.ubicacion),
                0,
                NEW.cantidad,
                'TRIGGER_AUTO'
            );
        END IF;
    END IF;
END//

DELIMITER ;

-- 4. Trigger para actualización automática desde cambios en mounters
DELIMITER //

CREATE TRIGGER trigger_actualizar_rollo_smd_mounter
AFTER INSERT ON historial_cambio_material_smt
FOR EACH ROW
BEGIN
    DECLARE rollo_id_encontrado INT DEFAULT 0;
    DECLARE cantidad_actual_rollo DECIMAL(10,3) DEFAULT 0;
    
    -- Buscar rollo activo correspondiente al PartName
    SELECT id, cantidad_actual INTO rollo_id_encontrado, cantidad_actual_rollo
    FROM InventarioRollosSMD 
    WHERE numero_parte = NEW.PartName 
    AND estado IN ('ACTIVO', 'EN_USO')
    ORDER BY fecha_entrada DESC 
    LIMIT 1;
    
    -- Si encontramos el rollo, actualizarlo
    IF rollo_id_encontrado > 0 THEN
        
        -- Actualizar información de asignación en mounter
        UPDATE InventarioRollosSMD 
        SET 
            linea_asignada = NEW.linea,
            maquina_asignada = NEW.maquina,
            slot_asignado = NEW.SlotNo,
            fecha_asignacion = STR_TO_DATE(CONCAT(NEW.ScanDate, ' ', NEW.ScanTime), '%Y%m%d %H:%i:%s'),
            fecha_ultimo_uso = STR_TO_DATE(CONCAT(NEW.ScanDate, ' ', NEW.ScanTime), '%Y%m%d %H:%i:%s'),
            estado = CASE 
                WHEN NEW.Result = 'OK' THEN 'EN_USO'
                WHEN NEW.Result = 'NG' THEN 'ACTIVO'
                ELSE estado
            END,
            actualizado_en = CURRENT_TIMESTAMP
        WHERE id = rollo_id_encontrado;
        
        -- Registrar movimiento en historial
        INSERT INTO HistorialMovimientosRollosSMD (
            rollo_id,
            tipo_movimiento,
            descripcion,
            cantidad_antes,
            cantidad_despues,
            linea,
            maquina,
            slot,
            scan_date,
            scan_time,
            resultado_scan,
            usuario
        ) VALUES (
            rollo_id_encontrado,
            CASE 
                WHEN NEW.Result = 'OK' THEN 'ASIGNACION'
                WHEN NEW.Result = 'NG' THEN 'USO'
                ELSE 'USO'
            END,
            CONCAT('Cambio detectado en mounter. Resultado: ', NEW.Result, '. Barcode: ', COALESCE(NEW.Barcode, 'N/A')),
            cantidad_actual_rollo,
            cantidad_actual_rollo, -- Mantener cantidad hasta implementar sistema de consumo
            NEW.linea,
            NEW.maquina,
            NEW.SlotNo,
            NEW.ScanDate,
            NEW.ScanTime,
            NEW.Result,
            'TRIGGER_MOUNTER'
        );
        
    END IF;
END//

DELIMITER ;

-- 5. Procedimiento para marcar rollos como agotados
DELIMITER //

CREATE PROCEDURE sp_marcar_rollo_agotado(
    IN p_rollo_id INT,
    IN p_observaciones TEXT
)
BEGIN
    UPDATE InventarioRollosSMD 
    SET 
        estado = 'AGOTADO',
        cantidad_actual = 0,
        fecha_agotamiento = CURRENT_TIMESTAMP,
        observaciones = CONCAT(COALESCE(observaciones, ''), ' | AGOTADO: ', p_observaciones),
        actualizado_en = CURRENT_TIMESTAMP
    WHERE id = p_rollo_id;
    
    -- Registrar en historial
    INSERT INTO HistorialMovimientosRollosSMD (
        rollo_id,
        tipo_movimiento,
        descripcion,
        cantidad_antes,
        cantidad_despues,
        usuario
    ) VALUES (
        p_rollo_id,
        'AGOTAMIENTO',
        p_observaciones,
        (SELECT cantidad_actual FROM InventarioRollosSMD WHERE id = p_rollo_id),
        0,
        'PROCEDIMIENTO_MANUAL'
    );
END//

DELIMITER ;

-- 6. Vista para consulta rápida de estado de rollos
CREATE VIEW vista_estado_rollos_smd AS
SELECT 
    r.id,
    r.numero_parte,
    r.codigo_barras,
    r.lote,
    r.estado,
    r.cantidad_inicial,
    r.cantidad_actual,
    r.linea_asignada,
    r.maquina_asignada,
    r.slot_asignado,
    r.fecha_entrada,
    r.fecha_ultimo_uso,
    -- Información del último movimiento
    h.tipo_movimiento as ultimo_movimiento,
    h.fecha_movimiento as fecha_ultimo_movimiento,
    h.descripcion as descripcion_ultimo_movimiento,
    -- Tiempo en área SMD
    TIMESTAMPDIFF(HOUR, r.fecha_entrada, COALESCE(r.fecha_ultimo_uso, NOW())) as horas_en_smd,
    -- Estado de utilización
    CASE 
        WHEN r.cantidad_actual = 0 THEN 'AGOTADO'
        WHEN r.linea_asignada IS NOT NULL THEN 'ASIGNADO'
        WHEN r.estado = 'ACTIVO' THEN 'DISPONIBLE'
        ELSE r.estado
    END as estado_detallado
FROM InventarioRollosSMD r
LEFT JOIN (
    SELECT 
        rollo_id,
        tipo_movimiento,
        fecha_movimiento,
        descripcion,
        ROW_NUMBER() OVER (PARTITION BY rollo_id ORDER BY fecha_movimiento DESC) as rn
    FROM HistorialMovimientosRollosSMD
) h ON r.id = h.rollo_id AND h.rn = 1
ORDER BY r.fecha_entrada DESC;

-- 7. Crear índices adicionales para optimización
CREATE INDEX idx_estado_fecha ON InventarioRollosSMD(estado, fecha_entrada);
CREATE INDEX idx_linea_maquina_slot ON InventarioRollosSMD(linea_asignada, maquina_asignada, slot_asignado);
CREATE INDEX idx_fecha_ultimo_uso ON InventarioRollosSMD(fecha_ultimo_uso);

-- Comentarios del sistema
INSERT INTO InventarioRollosSMD (numero_parte, observaciones, estado) 
VALUES ('SISTEMA_INIT', 'Tabla de inventario de rollos SMD inicializada correctamente', 'RETIRADO');
