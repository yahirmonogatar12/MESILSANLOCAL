"""
Script para integrar SMT Monitor con la aplicación Flask principal
Ejecutar DESPUÉS de instalar y configurar el monitor
"""

import os
import sys

def update_main_app():
    """Actualiza la aplicación principal para incluir las rutas SMT"""
    
    # Buscar archivo principal de Flask
    possible_files = ['run.py', 'app.py', 'main.py']
    main_file = None
    
    for file in possible_files:
        if os.path.exists(file):
            main_file = file
            break
    
    if not main_file:
        print("❌ No se encontró archivo principal de Flask")
        print("Agrega manualmente las siguientes líneas a tu archivo principal:")
        print_manual_instructions()
        return
    
    # Leer archivo actual
    with open(main_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar si ya está integrado
    if 'smt_routes' in content:
        print("✅ Las rutas SMT ya están integradas")
        return
    
    # Agregar importación
    import_line = "from app.smt_routes import register_smt_routes\n"
    
    # Encontrar línea de imports
    lines = content.split('\n')
    import_index = -1
    
    for i, line in enumerate(lines):
        if line.startswith('from flask') or line.startswith('from app'):
            import_index = i
    
    if import_index >= 0:
        lines.insert(import_index + 1, import_line)
    else:
        lines.insert(0, import_line)
    
    # Agregar registro de rutas
    register_line = "register_smt_routes(app)"
    
    # Encontrar donde registrar
    for i, line in enumerate(lines):
        if 'app.run(' in line or 'if __name__' in line:
            lines.insert(i, register_line)
            lines.insert(i, "")
            break
    else:
        lines.append("")
        lines.append(register_line)
    
    # Escribir archivo actualizado
    new_content = '\n'.join(lines)
    
    # Hacer backup
    backup_file = f"{main_file}.backup"
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Escribir nuevo contenido
    with open(main_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ {main_file} actualizado correctamente")
    print(f"📁 Backup guardado como: {backup_file}")

def print_manual_instructions():
    """Muestra instrucciones manuales"""
    print("\n" + "="*50)
    print("INSTRUCCIONES MANUALES")
    print("="*50)
    print("\n1. En tu archivo principal de Flask, agrega:")
    print("\n   from app.smt_routes import register_smt_routes")
    print("\n2. Después de crear la app, agrega:")
    print("\n   register_smt_routes(app)")
    print("\n3. Ejemplo completo:")
    print("""
from flask import Flask
from app.smt_routes import register_smt_routes

app = Flask(__name__)

# ... tus otras configuraciones ...

# Registrar rutas SMT
register_smt_routes(app)

if __name__ == '__main__':
    app.run(debug=True)
""")

def update_requirements():
    """Actualiza requirements.txt principal"""
    req_file = 'requirements.txt'
    
    new_requirements = [
        'mysql-connector-python==8.0.33',
        'watchdog==3.0.0'
    ]
    
    if os.path.exists(req_file):
        with open(req_file, 'r') as f:
            existing = f.read()
        
        # Verificar si ya están
        missing = []
        for req in new_requirements:
            if req.split('==')[0] not in existing:
                missing.append(req)
        
        if missing:
            with open(req_file, 'a') as f:
                f.write('\n# SMT Monitor dependencies\n')
                for req in missing:
                    f.write(f'{req}\n')
            print(f"✅ Requirements actualizados: {missing}")
        else:
            print("✅ Requirements ya están actualizados")
    else:
        with open(req_file, 'w') as f:
            f.write('# SMT Monitor dependencies\n')
            for req in new_requirements:
                f.write(f'{req}\n')
        print("✅ Requirements.txt creado")

def create_database_init():
    """Crea script para inicializar la base de datos"""
    sql_script = """
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
"""
    
    with open('init_smt_database.sql', 'w', encoding='utf-8') as f:
        f.write(sql_script)
    
    print("✅ Script SQL creado: init_smt_database.sql")
    print("   Ejecuta en MySQL para crear las tablas")

def main():
    """Función principal de integración"""
    print("🔧 Integrador SMT Monitor con Flask")
    print("="*40)
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists('app'):
        print("❌ No se encontró directorio 'app'")
        print("   Ejecuta este script desde la raíz del proyecto")
        return
    
    # Verificar que los archivos SMT existen
    required_files = [
        'app/smt_routes.py',
        'app/smt_csv_handler.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Archivos faltantes: {missing_files}")
        print("   Ejecuta primero el instalador SMT")
        return
    
    print("✅ Archivos SMT encontrados")
    
    # Integrar con aplicación principal
    update_main_app()
    
    # Actualizar requirements
    update_requirements()
    
    # Crear script de base de datos
    create_database_init()
    
    print("\n🎉 Integración completada!")
    print("\nPasos siguientes:")
    print("1. Ejecuta: mysql -u root -p < init_smt_database.sql")
    print("2. Configura: scripts/config.py con tus rutas y credenciales")
    print("3. Instala monitor: python scripts/setup.py")
    print("4. Inicia monitor: python scripts/smt_csv_monitor.py")
    print("5. Reinicia tu aplicación Flask")
    
    input("\nPresiona Enter para continuar...")

if __name__ == "__main__":
    main()
