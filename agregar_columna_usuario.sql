-- Script para agregar la columna Usuario a la tabla raw
-- Ejecutar este script en MySQL

USE tu_base_de_datos;  -- Reemplaza 'tu_base_de_datos' con el nombre real de tu base de datos

-- Agregar la columna Usuario después de la columna output
ALTER TABLE raw 
ADD COLUMN Usuario varchar(100) NOT NULL DEFAULT 'Sistema' 
AFTER output;

-- Opcional: Actualizar registros existentes para que tengan un usuario por defecto
UPDATE raw 
SET Usuario = 'Yahir' 
WHERE Usuario = 'Sistema';

-- Verificar que la columna se agregó correctamente
DESCRIBE raw;

-- Mostrar algunos registros para verificar
SELECT id, part_no, model, Usuario FROM raw LIMIT 5;
