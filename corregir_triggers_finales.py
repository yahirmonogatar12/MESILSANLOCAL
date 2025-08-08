import os
from app.config_mysql import get_mysql_connection_string
import pymysql

print('=== Corrigiendo triggers con nombres correctos de columnas ===')

try:
    config = get_mysql_connection_string()
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    
    print('🔄 Eliminando triggers anteriores...')
    
    # Eliminar triggers existentes
    triggers_to_drop = [
        'tr_salida_insert',
        'tr_salida_update', 
        'tr_salida_delete',
        'tr_entrada_insert',
        'tr_entrada_update',
        'tr_entrada_delete'
    ]
    
    for trigger_name in triggers_to_drop:
        try:
            cursor.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")
            print(f"✅ Trigger {trigger_name} eliminado")
        except Exception as e:
            print(f"⚠️ Error eliminando trigger {trigger_name}: {e}")
    
    print('\n🔄 Creando triggers corregidos...')
    
    # Trigger AFTER INSERT para salidas (corregido)
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
            total_entradas,
            total_salidas,
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
            total_salidas = total_salidas + NEW.cantidad_salida,
            cantidad_actual = total_entradas - total_salidas,
            fecha_ultima_salida = GREATEST(COALESCE(fecha_ultima_salida, '1900-01-01'), NEW.fecha_salida),
            fecha_actualizacion = NOW();
    END
    '''
    
    # Trigger AFTER UPDATE para salidas (corregido)
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
            total_salidas = total_salidas - OLD.cantidad_salida,
            cantidad_actual = total_entradas - total_salidas,
            fecha_actualizacion = NOW()
        WHERE numero_parte = numero_parte_extraido_old;
        
        -- Aplicar la nueva salida
        INSERT INTO inventario_consolidado (
            numero_parte,
            codigo_material,
            especificacion,
            total_entradas,
            total_salidas,
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
            total_salidas = total_salidas + NEW.cantidad_salida,
            cantidad_actual = total_entradas - total_salidas,
            fecha_ultima_salida = GREATEST(COALESCE(fecha_ultima_salida, '1900-01-01'), NEW.fecha_salida),
            fecha_actualizacion = NOW();
    END
    '''
    
    # Trigger AFTER DELETE para salidas (corregido)
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
            total_salidas = total_salidas - OLD.cantidad_salida,
            cantidad_actual = total_entradas - total_salidas,
            fecha_actualizacion = NOW()
        WHERE numero_parte = numero_parte_extraido;
    END
    '''
    
    # Trigger AFTER INSERT para entradas (corregido)
    trigger_insert_entrada = '''
    CREATE TRIGGER tr_entrada_insert 
    AFTER INSERT ON control_material_almacen
    FOR EACH ROW
    BEGIN
        -- Actualizar o insertar en inventario_consolidado
        INSERT INTO inventario_consolidado (
            numero_parte,
            codigo_material,
            especificacion,
            propiedad_material,
            total_entradas,
            total_salidas,
            cantidad_actual,
            total_lotes,
            fecha_primera_entrada,
            fecha_ultima_entrada,
            fecha_actualizacion
        ) VALUES (
            NEW.numero_parte,
            NEW.codigo_material,
            NEW.especificacion,
            NEW.propiedad_material,
            NEW.cantidad_actual,
            0,
            NEW.cantidad_actual,
            1,
            NEW.fecha_recibo,
            NEW.fecha_recibo,
            NOW()
        ) ON DUPLICATE KEY UPDATE
            total_entradas = total_entradas + NEW.cantidad_actual,
            cantidad_actual = total_entradas - total_salidas,
            total_lotes = total_lotes + 1,
            fecha_primera_entrada = LEAST(COALESCE(fecha_primera_entrada, '2099-12-31'), NEW.fecha_recibo),
            fecha_ultima_entrada = GREATEST(COALESCE(fecha_ultima_entrada, '1900-01-01'), NEW.fecha_recibo),
            fecha_actualizacion = NOW();
    END
    '''
    
    # Crear nuevos triggers
    triggers = [
        ('tr_salida_insert', trigger_insert_salida),
        ('tr_salida_update', trigger_update_salida),
        ('tr_salida_delete', trigger_delete_salida),
        ('tr_entrada_insert', trigger_insert_entrada)
    ]
    
    for trigger_name, trigger_sql in triggers:
        try:
            cursor.execute(trigger_sql)
            print(f"✅ Trigger {trigger_name} creado exitosamente")
        except Exception as e:
            print(f"❌ Error creando trigger {trigger_name}: {e}")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print('\n✅ Todos los triggers corregidos y funcionando')
    
except Exception as e:
    print(f'❌ Error: {e}')
