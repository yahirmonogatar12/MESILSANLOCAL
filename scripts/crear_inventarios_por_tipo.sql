-- Script para crear inventarios automáticos por tipo de material
-- IMD, MAIN y completar la integración automática

-- ========================================
-- INVENTARIO IMD (Insert Mount Device)
-- ========================================

-- Tabla principal para inventario IMD
CREATE TABLE IF NOT EXISTS InventarioRollosIMD (
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- Identificación del rollo
    numero_parte VARCHAR(100) NOT NULL,
    codigo_barras VARCHAR(100),
    lote VARCHAR(50),
    
    -- Información del área IMD
    area_imd VARCHAR(50) DEFAULT 'IMD_PRODUCTION',
    fecha_entrada DATETIME DEFAULT CURRENT_TIMESTAMP,
    origen_almacen VARCHAR(100) DEFAULT 'ALMACEN_GENERAL',
    
    -- Estado del rollo
    estado ENUM('ACTIVO', 'EN_USO', 'AGOTADO', 'RETIRADO') DEFAULT 'ACTIVO',
    cantidad_inicial DECIMAL(10,3) DEFAULT 0,
    cantidad_actual DECIMAL(10,3) DEFAULT 0,
    
    -- Información de máquina asignada
    linea_asignada VARCHAR(50),
    maquina_asignada VARCHAR(50),
    posicion_asignada VARCHAR(20),
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Historial de movimientos IMD
CREATE TABLE IF NOT EXISTS HistorialMovimientosRollosIMD (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rollo_id INT NOT NULL,
    
    -- Tipo de movimiento
    tipo_movimiento ENUM('ENTRADA', 'ASIGNACION', 'USO', 'AGOTAMIENTO', 'RETIRO', 'TRANSFERENCIA') NOT NULL,
    descripcion TEXT,
    
    -- Información antes del movimiento
    estado_anterior ENUM('ACTIVO', 'EN_USO', 'AGOTADO', 'RETIRADO'),
    cantidad_anterior DECIMAL(10,3),
    linea_anterior VARCHAR(50),
    maquina_anterior VARCHAR(50),
    
    -- Información después del movimiento
    estado_nuevo ENUM('ACTIVO', 'EN_USO', 'AGOTADO', 'RETIRADO'),
    cantidad_nueva DECIMAL(10,3),
    linea_nueva VARCHAR(50),
    maquina_nueva VARCHAR(50),
    
    -- Metadatos
    usuario VARCHAR(100) DEFAULT 'SISTEMA_AUTO',
    fecha_movimiento DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    
    -- Relaciones
    FOREIGN KEY (rollo_id) REFERENCES InventarioRollosIMD(id) ON DELETE CASCADE,
    INDEX idx_rollo_id (rollo_id),
    INDEX idx_tipo_movimiento (tipo_movimiento),
    INDEX idx_fecha_movimiento (fecha_movimiento)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ========================================
-- INVENTARIO MAIN (Componentes principales/Through-hole)
-- ========================================

-- Tabla principal para inventario MAIN
CREATE TABLE IF NOT EXISTS InventarioRollosMAIN (
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- Identificación del rollo/componente
    numero_parte VARCHAR(100) NOT NULL,
    codigo_barras VARCHAR(100),
    lote VARCHAR(50),
    
    -- Información del área MAIN
    area_main VARCHAR(50) DEFAULT 'MAIN_PRODUCTION',
    fecha_entrada DATETIME DEFAULT CURRENT_TIMESTAMP,
    origen_almacen VARCHAR(100) DEFAULT 'ALMACEN_GENERAL',
    
    -- Estado del componente
    estado ENUM('ACTIVO', 'EN_USO', 'AGOTADO', 'RETIRADO') DEFAULT 'ACTIVO',
    cantidad_inicial DECIMAL(10,3) DEFAULT 0,
    cantidad_actual DECIMAL(10,3) DEFAULT 0,
    
    -- Información de estación asignada
    linea_asignada VARCHAR(50),
    estacion_asignada VARCHAR(50),
    ubicacion_asignada VARCHAR(20),
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
    INDEX idx_linea_estacion (linea_asignada, estacion_asignada),
    INDEX idx_movimiento_origen (movimiento_origen_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Historial de movimientos MAIN
CREATE TABLE IF NOT EXISTS HistorialMovimientosRollosMAIN (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rollo_id INT NOT NULL,
    
    -- Tipo de movimiento
    tipo_movimiento ENUM('ENTRADA', 'ASIGNACION', 'USO', 'AGOTAMIENTO', 'RETIRO', 'TRANSFERENCIA') NOT NULL,
    descripcion TEXT,
    
    -- Información antes del movimiento
    estado_anterior ENUM('ACTIVO', 'EN_USO', 'AGOTADO', 'RETIRADO'),
    cantidad_anterior DECIMAL(10,3),
    linea_anterior VARCHAR(50),
    estacion_anterior VARCHAR(50),
    
    -- Información después del movimiento
    estado_nuevo ENUM('ACTIVO', 'EN_USO', 'AGOTADO', 'RETIRADO'),
    cantidad_nueva DECIMAL(10,3),
    linea_nueva VARCHAR(50),
    estacion_nueva VARCHAR(50),
    
    -- Metadatos
    usuario VARCHAR(100) DEFAULT 'SISTEMA_AUTO',
    fecha_movimiento DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    
    -- Relaciones
    FOREIGN KEY (rollo_id) REFERENCES InventarioRollosMAIN(id) ON DELETE CASCADE,
    INDEX idx_rollo_id (rollo_id),
    INDEX idx_tipo_movimiento (tipo_movimiento),
    INDEX idx_fecha_movimiento (fecha_movimiento)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ========================================
-- TRIGGERS AUTOMÁTICOS PARA DISTRIBUCIÓN
-- ========================================

DELIMITER //

-- Trigger para distribuir automáticamente las salidas por tipo de material
CREATE TRIGGER IF NOT EXISTS tr_distribuir_salidas_por_tipo
AFTER INSERT ON control_material_salida
FOR EACH ROW
BEGIN
    DECLARE material_propiedad VARCHAR(512);
    DECLARE material_numero_parte VARCHAR(100);
    DECLARE material_lote VARCHAR(50);
    
    -- Obtener información del material del almacén
    SELECT cma.propiedad_material, cma.numero_parte, cma.numero_lote_material
    INTO material_propiedad, material_numero_parte, material_lote
    FROM control_material_almacen cma
    WHERE cma.codigo_material_recibido = NEW.codigo_material_recibido
    LIMIT 1;
    
    -- Distribución automática por tipo de material
    IF material_propiedad = 'SMD' THEN
        -- Insertar en inventario SMD
        INSERT INTO InventarioRollosSMD (
            numero_parte, 
            codigo_barras, 
            lote,
            cantidad_inicial, 
            cantidad_actual,
            area_smd,
            movimiento_origen_id,
            observaciones
        ) VALUES (
            COALESCE(material_numero_parte, NEW.codigo_material_recibido),
            NEW.codigo_material_recibido,
            COALESCE(material_lote, NEW.numero_lote),
            NEW.cantidad_salida,
            NEW.cantidad_salida,
            CONCAT('SMD_', NEW.depto_salida),
            NEW.id,
            CONCAT('Auto-registrado desde salida ID: ', NEW.id, ' - ', NEW.proceso_salida)
        );
        
    ELSEIF material_propiedad = 'IMD' THEN
        -- Insertar en inventario IMD
        INSERT INTO InventarioRollosIMD (
            numero_parte, 
            codigo_barras, 
            lote,
            cantidad_inicial, 
            cantidad_actual,
            area_imd,
            movimiento_origen_id,
            observaciones
        ) VALUES (
            COALESCE(material_numero_parte, NEW.codigo_material_recibido),
            NEW.codigo_material_recibido,
            COALESCE(material_lote, NEW.numero_lote),
            NEW.cantidad_salida,
            NEW.cantidad_salida,
            CONCAT('IMD_', NEW.depto_salida),
            NEW.id,
            CONCAT('Auto-registrado desde salida ID: ', NEW.id, ' - ', NEW.proceso_salida)
        );
        
    ELSEIF material_propiedad = 'MAIN' THEN
        -- Insertar en inventario MAIN
        INSERT INTO InventarioRollosMAIN (
            numero_parte, 
            codigo_barras, 
            lote,
            cantidad_inicial, 
            cantidad_actual,
            area_main,
            movimiento_origen_id,
            observaciones
        ) VALUES (
            COALESCE(material_numero_parte, NEW.codigo_material_recibido),
            NEW.codigo_material_recibido,
            COALESCE(material_lote, NEW.numero_lote),
            NEW.cantidad_salida,
            NEW.cantidad_salida,
            CONCAT('MAIN_', NEW.depto_salida),
            NEW.id,
            CONCAT('Auto-registrado desde salida ID: ', NEW.id, ' - ', NEW.proceso_salida)
        );
    END IF;
END//

DELIMITER ;

-- ========================================
-- VISTAS UNIFICADAS
-- ========================================

-- Vista consolidada de todos los inventarios
CREATE OR REPLACE VIEW vista_inventarios_consolidados AS
SELECT 
    'SMD' as tipo_inventario,
    id,
    numero_parte,
    codigo_barras,
    lote,
    estado,
    cantidad_inicial,
    cantidad_actual,
    COALESCE(area_smd, 'SMD') as area_asignada,
    COALESCE(linea_asignada, '') as linea,
    COALESCE(maquina_asignada, '') as equipo,
    COALESCE(slot_asignado, '') as posicion,
    fecha_entrada,
    fecha_asignacion,
    fecha_ultimo_uso,
    observaciones
FROM InventarioRollosSMD

UNION ALL

SELECT 
    'IMD' as tipo_inventario,
    id,
    numero_parte,
    codigo_barras,
    lote,
    estado,
    cantidad_inicial,
    cantidad_actual,
    COALESCE(area_imd, 'IMD') as area_asignada,
    COALESCE(linea_asignada, '') as linea,
    COALESCE(maquina_asignada, '') as equipo,
    COALESCE(posicion_asignada, '') as posicion,
    fecha_entrada,
    fecha_asignacion,
    fecha_ultimo_uso,
    observaciones
FROM InventarioRollosIMD

UNION ALL

SELECT 
    'MAIN' as tipo_inventario,
    id,
    numero_parte,
    codigo_barras,
    lote,
    estado,
    cantidad_inicial,
    cantidad_actual,
    COALESCE(area_main, 'MAIN') as area_asignada,
    COALESCE(linea_asignada, '') as linea,
    COALESCE(estacion_asignada, '') as equipo,
    COALESCE(ubicacion_asignada, '') as posicion,
    fecha_entrada,
    fecha_asignacion,
    fecha_ultimo_uso,
    observaciones
FROM InventarioRollosMAIN;

-- Vista de estadísticas por tipo de inventario
CREATE OR REPLACE VIEW vista_estadisticas_inventarios AS
SELECT 
    tipo_inventario,
    COUNT(*) as total_rollos,
    SUM(CASE WHEN estado = 'ACTIVO' THEN 1 ELSE 0 END) as rollos_activos,
    SUM(CASE WHEN estado = 'EN_USO' THEN 1 ELSE 0 END) as rollos_en_uso,
    SUM(CASE WHEN estado = 'AGOTADO' THEN 1 ELSE 0 END) as rollos_agotados,
    SUM(cantidad_actual) as cantidad_total_disponible,
    AVG(cantidad_actual) as promedio_cantidad_por_rollo
FROM vista_inventarios_consolidados
GROUP BY tipo_inventario;

-- ========================================
-- PROCEDIMIENTOS ALMACENADOS
-- ========================================

DELIMITER //

-- Procedimiento para marcar rollo como agotado (genérico)
CREATE PROCEDURE IF NOT EXISTS sp_marcar_rollo_agotado_generico(
    IN p_tipo_inventario VARCHAR(10),
    IN p_rollo_id INT,
    IN p_usuario VARCHAR(100)
)
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE table_name VARCHAR(50);
    DECLARE history_table VARCHAR(50);
    
    -- Determinar las tablas según el tipo
    CASE p_tipo_inventario
        WHEN 'SMD' THEN 
            SET table_name = 'InventarioRollosSMD';
            SET history_table = 'HistorialMovimientosRollosSMD';
        WHEN 'IMD' THEN 
            SET table_name = 'InventarioRollosIMD';
            SET history_table = 'HistorialMovimientosRollosIMD';
        WHEN 'MAIN' THEN 
            SET table_name = 'InventarioRollosMAIN';
            SET history_table = 'HistorialMovimientosRollosMAIN';
        ELSE
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Tipo de inventario no válido';
    END CASE;
    
    -- Actualizar el rollo (usando SQL dinámico sería ideal, pero por simplicidad...)
    IF p_tipo_inventario = 'SMD' THEN
        UPDATE InventarioRollosSMD 
        SET estado = 'AGOTADO', 
            cantidad_actual = 0, 
            fecha_agotamiento = NOW()
        WHERE id = p_rollo_id;
        
        INSERT INTO HistorialMovimientosRollosSMD (rollo_id, tipo_movimiento, descripcion, usuario)
        VALUES (p_rollo_id, 'AGOTAMIENTO', 'Rollo marcado como agotado manualmente', p_usuario);
        
    ELSEIF p_tipo_inventario = 'IMD' THEN
        UPDATE InventarioRollosIMD 
        SET estado = 'AGOTADO', 
            cantidad_actual = 0, 
            fecha_agotamiento = NOW()
        WHERE id = p_rollo_id;
        
        INSERT INTO HistorialMovimientosRollosIMD (rollo_id, tipo_movimiento, descripcion, usuario)
        VALUES (p_rollo_id, 'AGOTAMIENTO', 'Rollo marcado como agotado manualmente', p_usuario);
        
    ELSEIF p_tipo_inventario = 'MAIN' THEN
        UPDATE InventarioRollosMAIN 
        SET estado = 'AGOTADO', 
            cantidad_actual = 0, 
            fecha_agotamiento = NOW()
        WHERE id = p_rollo_id;
        
        INSERT INTO HistorialMovimientosRollosMAIN (rollo_id, tipo_movimiento, descripcion, usuario)
        VALUES (p_rollo_id, 'AGOTAMIENTO', 'Rollo marcado como agotado manualmente', p_usuario);
    END IF;
END//

DELIMITER ;

-- ========================================
-- DATOS DE PRUEBA PARA VERIFICACIÓN
-- ========================================

-- Algunos datos de prueba para IMD
INSERT IGNORE INTO InventarioRollosIMD (numero_parte, codigo_barras, cantidad_inicial, cantidad_actual, estado, observaciones)
VALUES 
    ('INDUCTOR_1210_10UH', 'IMD_INDUCTOR_1210_10UH_20250813_001', 2000, 2000, 'ACTIVO', 'Datos de prueba IMD'),
    ('CONNECTOR_2MM_4PIN', 'IMD_CONNECTOR_2MM_4PIN_20250813_002', 1500, 1200, 'EN_USO', 'Datos de prueba IMD'),
    ('TRANSFORMER_EE16', 'IMD_TRANSFORMER_EE16_20250813_003', 800, 600, 'EN_USO', 'Datos de prueba IMD');

-- Algunos datos de prueba para MAIN
INSERT IGNORE INTO InventarioRollosMAIN (numero_parte, codigo_barras, cantidad_inicial, cantidad_actual, estado, observaciones)
VALUES 
    ('RESISTOR_TH_1K_1W', 'MAIN_RESISTOR_TH_1K_1W_20250813_001', 5000, 5000, 'ACTIVO', 'Datos de prueba MAIN'),
    ('CAPACITOR_ELEC_1000UF', 'MAIN_CAPACITOR_ELEC_1000UF_20250813_002', 300, 280, 'EN_USO', 'Datos de prueba MAIN'),
    ('IC_DIP8_MCU', 'MAIN_IC_DIP8_MCU_20250813_003', 100, 95, 'EN_USO', 'Datos de prueba MAIN');
