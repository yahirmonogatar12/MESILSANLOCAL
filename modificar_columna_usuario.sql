-- Script para modificar la columna Usuario generada
-- Ejecutar este script en MySQL para que use el usuario actual

USE tu_base_de_datos;  -- Reemplaza con el nombre real de tu base de datos

-- Deshabilitar safe update mode temporalmente
SET SQL_SAFE_UPDATES = 0;

-- Ver la definición actual de la columna Usuario
SHOW CREATE TABLE raw;

-- Opción 1: Eliminar la columna generada y crear una columna normal
-- ADVERTENCIA: Esto eliminará todos los valores actuales de Usuario
ALTER TABLE raw DROP COLUMN Usuario;
ALTER TABLE raw ADD COLUMN Usuario varchar(100) NOT NULL DEFAULT 'Sistema' AFTER output;

-- Ahora que la columna es normal, actualizar los registros existentes
-- Opción A: Asignar todos los registros existentes a 'Yahir'
UPDATE raw SET Usuario = 'Yahir' WHERE id > 0;

-- Opción B: Si quieres asignar diferentes usuarios según algún criterio
-- UPDATE raw SET Usuario = 'Sr. Kim' WHERE fecha >= '2024-01-01';
-- UPDATE raw SET Usuario = 'Yahir' WHERE fecha < '2024-01-01';

-- Opción C: Si quieres asignar según el usuario que creó cada registro
-- (esto requeriría tener información adicional sobre quién creó cada registro)

-- Rehabilitar safe update mode
SET SQL_SAFE_UPDATES = 1;

-- Opción 2: Si quieres mantener los datos existentes, primero haz backup
-- CREATE TABLE raw_backup AS SELECT * FROM raw;

-- Opción 3: Si quieres mantener la columna generada pero cambiar su definición
-- Primero necesitamos ver cómo está definida actualmente
-- La consulta SHOW CREATE TABLE raw te mostrará algo como:
-- `Usuario` varchar(100) GENERATED ALWAYS AS ('Yahir') STORED

-- Para cambiar la definición de la columna generada:
-- ALTER TABLE raw MODIFY COLUMN Usuario varchar(100) GENERATED ALWAYS AS (USER()) STORED;

-- Verificar el cambio
DESCRIBE raw;
SELECT id, part_no, Usuario FROM raw LIMIT 5;
