-- Script para vistas consolidadas de inventarios
-- Ejecutar después de crear_inventarios_base.sql y crear_triggers_distribucion.sql

-- ========================================
-- VISTA CONSOLIDADA DE TODOS LOS INVENTARIOS
-- ========================================

-- Vista principal que unifica todos los inventarios
DROP VIEW IF EXISTS vista_inventario_consolidado;

CREATE VIEW vista_inventario_consolidado AS
-- Inventario SMD (si existe)
SELECT 
    id,
    'SMD' as tipo_inventario,
    numero_parte,
    codigo_barras,
    lote,
    estado,
    cantidad_inicial,
    cantidad_actual,
    'SMT_PRODUCTION' as area_produccion,
    linea_asignada,
    maquina_asignada as equipo_asignado,
    posicion_asignada as ubicacion_asignada,
    fecha_entrada,
    fecha_asignacion,
    fecha_ultimo_uso,
    usuario_responsable,
    observaciones,
    creado_en,
    actualizado_en
FROM InventarioRollosSMD
WHERE 1=1

UNION ALL

-- Inventario IMD
SELECT 
    id,
    'IMD' as tipo_inventario,
    numero_parte,
    codigo_barras,
    lote,
    estado,
    cantidad_inicial,
    cantidad_actual,
    area_imd as area_produccion,
    linea_asignada,
    maquina_asignada as equipo_asignado,
    posicion_asignada as ubicacion_asignada,
    fecha_entrada,
    fecha_asignacion,
    fecha_ultimo_uso,
    usuario_responsable,
    observaciones,
    creado_en,
    actualizado_en
FROM InventarioRollosIMD

UNION ALL

-- Inventario MAIN
SELECT 
    id,
    'MAIN' as tipo_inventario,
    numero_parte,
    codigo_barras,
    lote,
    estado,
    cantidad_inicial,
    cantidad_actual,
    area_main as area_produccion,
    linea_asignada,
    estacion_asignada as equipo_asignado,
    ubicacion_asignada,
    fecha_entrada,
    fecha_asignacion,
    fecha_ultimo_uso,
    usuario_responsable,
    observaciones,
    creado_en,
    actualizado_en
FROM InventarioRollosMAIN;

-- ========================================
-- VISTA DE RESUMEN POR TIPO
-- ========================================

DROP VIEW IF EXISTS vista_resumen_inventarios;

CREATE VIEW vista_resumen_inventarios AS
SELECT 
    tipo_inventario,
    COUNT(*) as total_rollos,
    COUNT(CASE WHEN estado = 'ACTIVO' THEN 1 END) as rollos_activos,
    COUNT(CASE WHEN estado = 'EN_USO' THEN 1 END) as rollos_en_uso,
    COUNT(CASE WHEN estado = 'AGOTADO' THEN 1 END) as rollos_agotados,
    COUNT(CASE WHEN estado = 'RETIRADO' THEN 1 END) as rollos_retirados,
    SUM(cantidad_inicial) as cantidad_total_inicial,
    SUM(cantidad_actual) as cantidad_total_actual,
    ROUND(SUM(cantidad_actual) / NULLIF(SUM(cantidad_inicial), 0) * 100, 2) as porcentaje_disponible,
    MIN(fecha_entrada) as primera_entrada,
    MAX(fecha_entrada) as ultima_entrada
FROM vista_inventario_consolidado
GROUP BY tipo_inventario;

-- ========================================
-- VISTA DE ACTIVIDAD RECIENTE
-- ========================================

DROP VIEW IF EXISTS vista_actividad_reciente;

CREATE VIEW vista_actividad_reciente AS
-- Actividad SMD (si existe la tabla)
SELECT 
    h.id,
    'SMD' as tipo_inventario,
    r.numero_parte,
    r.codigo_barras,
    h.tipo_movimiento,
    h.descripcion,
    h.usuario,
    h.fecha_movimiento,
    h.cantidad_anterior,
    h.cantidad_nueva,
    h.estado_anterior,
    h.estado_nuevo
FROM HistorialMovimientosRollosSMD h
JOIN InventarioRollosSMD r ON h.rollo_id = r.id
WHERE 1=0  -- Deshabilitado hasta que exista la tabla SMD

UNION ALL

-- Actividad IMD
SELECT 
    h.id,
    'IMD' as tipo_inventario,
    r.numero_parte,
    r.codigo_barras,
    h.tipo_movimiento,
    h.descripcion,
    h.usuario,
    h.fecha_movimiento,
    CAST(NULL AS DECIMAL(10,3)) as cantidad_anterior,
    h.cantidad_nueva,
    h.estado_anterior,
    h.estado_nuevo
FROM HistorialMovimientosRollosIMD h
JOIN InventarioRollosIMD r ON h.rollo_id = r.id

UNION ALL

-- Actividad MAIN
SELECT 
    h.id,
    'MAIN' as tipo_inventario,
    r.numero_parte,
    r.codigo_barras,
    h.tipo_movimiento,
    h.descripcion,
    h.usuario,
    h.fecha_movimiento,
    CAST(NULL AS DECIMAL(10,3)) as cantidad_anterior,
    h.cantidad_nueva,
    h.estado_anterior,
    h.estado_nuevo
FROM HistorialMovimientosRollosMAIN h
JOIN InventarioRollosMAIN r ON h.rollo_id = r.id

ORDER BY fecha_movimiento DESC;

-- ========================================
-- VISTA DE ALERTAS Y NOTIFICACIONES
-- ========================================

DROP VIEW IF EXISTS vista_alertas_inventario;

CREATE VIEW vista_alertas_inventario AS
SELECT 
    tipo_inventario,
    numero_parte,
    codigo_barras,
    lote,
    estado,
    cantidad_actual,
    cantidad_inicial,
    CASE 
        WHEN estado = 'AGOTADO' THEN 'CRITICO'
        WHEN cantidad_actual <= (cantidad_inicial * 0.1) THEN 'BAJO'
        WHEN cantidad_actual <= (cantidad_inicial * 0.2) THEN 'MODERADO'
        ELSE 'NORMAL'
    END as nivel_alerta,
    CASE 
        WHEN estado = 'AGOTADO' THEN 'Rollo agotado - Requiere reposición inmediata'
        WHEN cantidad_actual <= (cantidad_inicial * 0.1) THEN 'Stock crítico - Menos del 10% disponible'
        WHEN cantidad_actual <= (cantidad_inicial * 0.2) THEN 'Stock bajo - Menos del 20% disponible'
        ELSE 'Stock normal'
    END as mensaje_alerta,
    fecha_entrada,
    fecha_ultimo_uso,
    linea_asignada,
    equipo_asignado,
    usuario_responsable
FROM vista_inventario_consolidado
WHERE estado IN ('AGOTADO') 
   OR cantidad_actual <= (cantidad_inicial * 0.2)
ORDER BY 
    CASE nivel_alerta
        WHEN 'CRITICO' THEN 1
        WHEN 'BAJO' THEN 2
        WHEN 'MODERADO' THEN 3
        ELSE 4
    END,
    cantidad_actual ASC;
