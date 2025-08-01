#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear la tabla sesiones_activas en MySQL
"""

import pymysql

def crear_tabla_sesiones():
    """Crear tabla sesiones_activas"""
    try:
        connection = pymysql.connect(
            host='100.111.108.116',
            port=3306,
            user='ILSANMES',
            password='ISEMM2025',
            database='isemm2025',
            charset='utf8mb4',
            autocommit=True
        )
        
        cursor = connection.cursor()
        
        # Crear tabla sesiones_activas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sesiones_activas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario_id INT NOT NULL,
                token VARCHAR(255) UNIQUE NOT NULL,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_expiracion TIMESTAMP NOT NULL,
                ip_address VARCHAR(45),
                user_agent TEXT,
                activa BOOLEAN DEFAULT TRUE,
                INDEX idx_token (token),
                INDEX idx_usuario (usuario_id),
                INDEX idx_expiracion (fecha_expiracion)
            )
        """)
        
        print("✅ Tabla sesiones_activas creada exitosamente")
        
        # Verificar que la tabla existe
        cursor.execute("SHOW TABLES LIKE 'sesiones_activas'")
        result = cursor.fetchone()
        
        if result:
            print("✅ Tabla verificada en la base de datos")
        else:
            print("❌ Error: Tabla no encontrada después de la creación")
        
        cursor.close()
        connection.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando tabla sesiones_activas: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Creando tabla sesiones_activas...")
    if crear_tabla_sesiones():
        print("🎉 Tabla creada exitosamente")
    else:
        print("❌ Error en la creación")