
-- Script para unificar collations
-- Ejecutar como administrador de base de datos

-- 1. Cambiar collation de la base de datos
ALTER DATABASE db_rrpq0erbdujn CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 2. Cambiar collation de tabla control_material_salida
ALTER TABLE control_material_salida CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 3. Cambiar collation de tabla movimientosimd_smd
ALTER TABLE movimientosimd_smd CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 4. Cambiar collation de tabla historial_cambio_material_smt
ALTER TABLE historial_cambio_material_smt CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 5. Verificar cambios
SELECT TABLE_NAME, TABLE_COLLATION 
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
AND TABLE_NAME IN ('control_material_salida', 'movimientosimd_smd', 'historial_cambio_material_smt');
