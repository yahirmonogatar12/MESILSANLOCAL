-- Script corregido para crear inventarios automáticos por tipo de material
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
-- DATOS DE PRUEBA
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
