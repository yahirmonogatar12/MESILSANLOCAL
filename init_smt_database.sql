
-- Script de inicialización para SMT Monitor
-- Ejecutar en MySQL antes de usar el sistema

-- Crear base de datos si no existe
CREATE DATABASE IF NOT EXISTS isemm_mes CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE isemm_mes;

-- Tabla principal de datos SMT
CREATE TABLE IF NOT EXISTS historial_cambio_material_smt (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scan_date DATE NOT NULL,
    scan_time TIME NOT NULL,
    slot_no VARCHAR(50),
    result VARCHAR(10),
    part_name VARCHAR(100),
    quantity INT,
    vendor VARCHAR(100),
    lot_no VARCHAR(100),
    barcode VARCHAR(200),
    feeder_base VARCHAR(100),
    previous_barcode VARCHAR(200),
    source_file VARCHAR(255),
    line_number INT NOT NULL,
    mounter_number INT NOT NULL,
    file_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Índices para optimización
    INDEX idx_scan_date (scan_date),
    INDEX idx_part_name (part_name),
    INDEX idx_result (result),
    INDEX idx_line_mounter (line_number, mounter_number),
    INDEX idx_barcode (barcode),
    INDEX idx_file_hash (file_hash),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla de control de archivos procesados
CREATE TABLE IF NOT EXISTS smt_files_processed (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) UNIQUE NOT NULL,
    filepath VARCHAR(500),
    line_number INT NOT NULL,
    mounter_number INT NOT NULL,
    file_hash VARCHAR(64),
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    records_count INT DEFAULT 0,
    file_size BIGINT,
    
    INDEX idx_filename (filename),
    INDEX idx_file_hash (file_hash),
    INDEX idx_processed_at (processed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Datos de ejemplo (opcional)
-- INSERT INTO historial_cambio_material_smt 
-- (scan_date, scan_time, slot_no, result, part_name, quantity, vendor, lot_no, barcode, feeder_base, previous_barcode, source_file, line_number, mounter_number, file_hash)
-- VALUES 
-- ('2024-01-15', '10:30:25', '1', 'OK', 'R0603_100K', 1, 'VENDOR_A', 'LOT123', 'BAR456', 'FB01', 'PREV789', 'test.csv', 1, 1, 'testhash');

SHOW TABLES;
SELECT 'SMT Monitor database initialized successfully!' AS Status;
