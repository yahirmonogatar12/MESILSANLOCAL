import os
from app.config_mysql import get_mysql_connection_string
import pymysql

print('=== Configurando triggers para salidas ===')

try:
    config = get_mysql_connection_string()
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    
    # Extraer número de parte del código material recibido
    def extract_numero_parte(codigo_material_recibido):
        """Extrae el número de parte del código material recibido"""
        if ',' in codigo_material_recibido:
            return codigo_material_recibido.split(',')[0]
        return codigo_material_recibido
    
    print('🔄 Creando triggers para control_material_salida...')
    
    # Trigger AFTER INSERT para salidas
    trigger_insert_salida = '''
    CREATE TRIGGER tr_salida_insert 
    AFTER INSERT ON control_material_salida
    FOR EACH ROW
    BEGIN
        DECLARE numero_parte_extraido VARCHAR(255);
        
        -- Extraer número de parte del código material recibido
        SET numero_parte_extraido = SUBSTRING_INDEX(NEW.codigo_material_recibido, ',', 1);
        
        -- Actualizar o insertar en inventario_consolidado
        INSERT INTO inventario_consolidado (
            numero_parte,
            codigo_material,
            especificacion,
            cantidad_entradas,
            cantidad_salidas,
            cantidad_actual,
            total_lotes,
            fecha_ultima_entrada,
            fecha_ultima_salida,
            fecha_actualizacion
        ) VALUES (
            numero_parte_extraido,
            NEW.codigo_material_recibido,
            NEW.especificacion_material,
            0,
            NEW.cantidad_salida,
            -NEW.cantidad_salida,
            0,
            NULL,
            NEW.fecha_salida,
            NOW()
        ) ON DUPLICATE KEY UPDATE
            cantidad_salidas = cantidad_salidas + NEW.cantidad_salida,
            cantidad_actual = cantidad_entradas - cantidad_salidas,
            fecha_ultima_salida = GREATEST(COALESCE(fecha_ultima_salida, '1900-01-01'), NEW.fecha_salida),
            fecha_actualizacion = NOW();
    END
    '''
    
    # Trigger AFTER UPDATE para salidas
    trigger_update_salida = '''
    CREATE TRIGGER tr_salida_update 
    AFTER UPDATE ON control_material_salida
    FOR EACH ROW
    BEGIN
        DECLARE numero_parte_extraido_old VARCHAR(255);
        DECLARE numero_parte_extraido_new VARCHAR(255);
        
        -- Extraer números de parte
        SET numero_parte_extraido_old = SUBSTRING_INDEX(OLD.codigo_material_recibido, ',', 1);
        SET numero_parte_extraido_new = SUBSTRING_INDEX(NEW.codigo_material_recibido, ',', 1);
        
        -- Revertir la salida anterior
        UPDATE inventario_consolidado 
        SET 
            cantidad_salidas = cantidad_salidas - OLD.cantidad_salida,
            cantidad_actual = cantidad_entradas - cantidad_salidas,
            fecha_actualizacion = NOW()
        WHERE numero_parte = numero_parte_extraido_old;
        
        -- Aplicar la nueva salida
        INSERT INTO inventario_consolidado (
            numero_parte,
            codigo_material,
            especificacion,
            cantidad_entradas,
            cantidad_salidas,
            cantidad_actual,
            total_lotes,
            fecha_ultima_entrada,
            fecha_ultima_salida,
            fecha_actualizacion
        ) VALUES (
            numero_parte_extraido_new,
            NEW.codigo_material_recibido,
            NEW.especificacion_material,
            0,
            NEW.cantidad_salida,
            -NEW.cantidad_salida,
            0,
            NULL,
            NEW.fecha_salida,
            NOW()
        ) ON DUPLICATE KEY UPDATE
            cantidad_salidas = cantidad_salidas + NEW.cantidad_salida,
            cantidad_actual = cantidad_entradas - cantidad_salidas,
            fecha_ultima_salida = GREATEST(COALESCE(fecha_ultima_salida, '1900-01-01'), NEW.fecha_salida),
            fecha_actualizacion = NOW();
    END
    '''
    
    # Trigger AFTER DELETE para salidas
    trigger_delete_salida = '''
    CREATE TRIGGER tr_salida_delete 
    AFTER DELETE ON control_material_salida
    FOR EACH ROW
    BEGIN
        DECLARE numero_parte_extraido VARCHAR(255);
        
        -- Extraer número de parte
        SET numero_parte_extraido = SUBSTRING_INDEX(OLD.codigo_material_recibido, ',', 1);
        
        -- Revertir la salida
        UPDATE inventario_consolidado 
        SET 
            cantidad_salidas = cantidad_salidas - OLD.cantidad_salida,
            cantidad_actual = cantidad_entradas - cantidad_salidas,
            fecha_actualizacion = NOW()
        WHERE numero_parte = numero_parte_extraido;
    END
    '''
    
    # Eliminar triggers existentes si existen
    triggers_to_drop = [
        'tr_salida_insert',
        'tr_salida_update', 
        'tr_salida_delete'
    ]
    
    for trigger_name in triggers_to_drop:
        try:
            cursor.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")
            print(f"✅ Trigger {trigger_name} eliminado (si existía)")
        except Exception as e:
            print(f"⚠️ Error eliminando trigger {trigger_name}: {e}")
    
    # Crear nuevos triggers
    triggers = [
        ('tr_salida_insert', trigger_insert_salida),
        ('tr_salida_update', trigger_update_salida),
        ('tr_salida_delete', trigger_delete_salida)
    ]
    
    for trigger_name, trigger_sql in triggers:
        try:
            cursor.execute(trigger_sql)
            print(f"✅ Trigger {trigger_name} creado exitosamente")
        except Exception as e:
            print(f"❌ Error creando trigger {trigger_name}: {e}")
    
    # Poblar datos iniciales de salidas
    print('\n🔄 Poblando datos iniciales de salidas...')
    
    cursor.execute('''
        SELECT 
            SUBSTRING_INDEX(codigo_material_recibido, ',', 1) as numero_parte,
            SUM(cantidad_salida) as total_salidas,
            MAX(fecha_salida) as fecha_ultima_salida
        FROM control_material_salida
        GROUP BY SUBSTRING_INDEX(codigo_material_recibido, ',', 1)
    ''')
    
    salidas = cursor.fetchall()
    
    for salida in salidas:
        numero_parte = salida[0]
        total_salidas = float(salida[1]) if salida[1] else 0.0
        fecha_ultima_salida = salida[2]
        
        # Actualizar inventario consolidado con salidas
        cursor.execute('''
            UPDATE inventario_consolidado 
            SET 
                cantidad_salidas = %s,
                cantidad_actual = cantidad_entradas - %s,
                fecha_ultima_salida = %s,
                fecha_actualizacion = NOW()
            WHERE numero_parte = %s
        ''', (total_salidas, total_salidas, fecha_ultima_salida, numero_parte))
        
        print(f"  ✅ {numero_parte}: {total_salidas} salidas")
    
    # Verificar el resultado final
    print('\n=== Verificando inventario consolidado final ===')
    cursor.execute('''
        SELECT 
            numero_parte,
            cantidad_entradas,
            cantidad_salidas,
            cantidad_actual,
            total_lotes
        FROM inventario_consolidado
        WHERE numero_parte LIKE '0RH5602C622%'
        LIMIT 3
    ''')
    
    resultados = cursor.fetchall()
    for row in resultados:
        print(f"  {row[0]}: Entradas={row[1]}, Salidas={row[2]}, Actual={row[3]}, Lotes={row[4]}")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print('\n✅ Triggers para salidas configurados exitosamente')
    
except Exception as e:
    print(f'❌ Error: {e}')
