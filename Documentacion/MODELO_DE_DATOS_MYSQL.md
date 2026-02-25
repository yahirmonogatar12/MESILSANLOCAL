# Modelo de Datos MySQL

Este documento resume tablas, relaciones y estrategia de evolucion de esquema observada en el codigo.

## 1. Fuentes de schema/migraciones

Archivos principales:

- `app/db_mysql.py`
- `app/auth_system.py`
- `app/po_wo_models.py`
- `app/routes.py`
- `app/db.py` (tablas legacy de compatibilidad)

## 2. Tablas base (materiales, inventario, BOM, usuarios)

## 2.1 Materiales e inventario (`app/db_mysql.py`)

Creacion en `create_tables()`:

- `materiales` (`app/db_mysql.py:219`)
  - Campos clave: `codigo_material`, `numero_parte` (unique), `classification`, `especificacion_material`, `usuario_registro`.
  - Indices: `idx_numero_parte`, `idx_codigo_material`, `idx_usuario_registro`.
- `inventario` (`app/db_mysql.py:270`)
  - `numero_parte` unique, `cantidad_actual`, `ultima_actualizacion`.
- `movimientos_inventario` (`app/db_mysql.py:278`)
  - Trazabilidad de movimientos por `numero_parte`.
- `bom` (`app/db_mysql.py:289`)
  - Base BOM por `modelo`, `numero_parte`, `side`.
  - Unique key compuesta `unique_bom (modelo, numero_parte, side)`.

Migraciones relevantes:

- `migrar_tabla_bom()` agrega `posicion_assy` (`app/db_mysql.py:1806`).
- `agregar_columna_usuario_registro()` asegura campo/indice en `materiales` (`app/db_mysql.py:2139`).

## 2.2 Sistema de autenticacion/permisos (`app/auth_system.py`)

Definidas en `init_database()`:

- `usuarios_sistema` (`app/auth_system.py:86`)
- `roles` (`app/auth_system.py:107`)
- `permisos` (`app/auth_system.py:119`)
- `usuario_roles` (`app/auth_system.py:131`)
- `rol_permisos` (`app/auth_system.py:144`)
- `auditoria` (`app/auth_system.py:156`)
- `sesiones_activas` (`app/auth_system.py:176`)
- `permisos_botones` (`app/auth_system.py:190`)
- `rol_permisos_botones` (`app/auth_system.py:203`)

Uso:

- autenticacion, autorizacion por rol/boton, auditoria de acciones y sesiones.

## 3. Planeacion y trazabilidad

## 3.1 Plan MAIN / IMD

- `plan_main` y `plan_imd` son usadas extensivamente por rutas, pero su definicion inicial no esta centralizada en un unico punto visible en este repo.
- Migracion concreta observada:
  - `migrar_tabla_plan_main()` agrega `wo_id` + indice (`app/po_wo_models.py:641`).

## 3.2 Plan SMT / SMD / Runs

- `plan_smt` (`app/routes.py:1851`)
  - creada en `crear_tabla_plan_smt_v2()` (ejecutada al importar `routes.py`).
- `plan_smd` (`app/routes.py:4365`)
  - creada en `crear_tabla_plan_smd()` (ejecutada al importar `routes.py`).
- `plan_smd_runs` (`app/routes.py:11700`)
  - creada en `crear_tabla_plan_smd_runs()`.
  - alter posteriores para estado `PAUSED` y columnas AOI baseline/final.
- `trazabilidad` (`app/routes.py:12240`)
  - estado por lote (`PLANEADO`, `INICIADO`, `PAUSA`, `FINALIZADO`).

## 4. PO/WO

Archivo: `app/po_wo_models.py`

- `embarques` (`app/po_wo_models.py:20`)
- `work_orders` (`app/po_wo_models.py:43`)

Migraciones:

- columnas nuevas en `embarques` (`migrar_tabla_embarques`).
- columnas nuevas en `work_orders` (`migrar_tabla_work_orders`): `orden_proceso`, `nombre_modelo`, `codigo_modelo`, `fecha_creacion`, `linea`.
- ajuste para independencia de WO vs PO (`migrar_work_orders_independientes`).

## 5. Modulos especificos (AOI, SMT historial, Metal Mask, SMD rolls)

## 5.1 AOI / SMT historial

Tablas usadas por consultas (asumidas existentes):

- `aoi_file_log` (AOI realtime/day y baseline runs).
- `historial_cambio_material_smt` (rutas SMT historial).
- `history_ict`, `history_ict_defects` (modulo ICT).

## 5.2 Metal Mask

Definicion en `app/routes.py`:

- `metal_mask_history` (`app/routes.py:10380`)
- `masks` (`app/routes.py:12273`)
- `storage_boxes` (`app/routes.py:12308`)

Incluye migracion soft de enum `disuse` en `masks`.

## 5.3 Inventario rollos SMD

Rutas en `app/smd_inventory_api.py` usan:

- `InventarioRollosSMD`
- `HistorialMovimientosRollosSMD`
- procedimiento `sp_marcar_rollo_agotado`

No se observa script de creacion en el repo analizado (asumido schema externo).

## 6. Tablas legacy de compatibilidad (`app/db.py`)

`create_legacy_tables()` crea:

- `entrada_aereo`
- `control_material_almacen`
- `control_material_produccion`
- `control_calidad`

Estas conviven con tablas de otros modulos y rutas historicas.

## 7. Estrategia de migracion observada

No existe framework formal tipo Alembic.

Patron actual:

1. Crear tabla con `CREATE TABLE IF NOT EXISTS`.
2. Intentar `ALTER TABLE` y capturar duplicados (`1060`, `1061`).
3. Ejecutar migraciones al importar modulos (side-effect de import).

Puntos tecnicos importantes:

- `app/routes.py` ejecuta creacion de varias tablas al import.
- `app/po_wo_models.py` ejecuta migraciones al import.
- `app/config_mysql.py::execute_query()` para DDL no siempre propaga todos los errores (puede ocultar fallos reales).

## 8. Relaciones logicas principales

Relaciones funcionales (no siempre con FK fisica activa):

- `materiales.numero_parte` <-> `inventario.numero_parte`
- `materiales.numero_parte` <-> `movimientos_inventario.numero_parte`
- `materiales.numero_parte` <-> `bom.numero_parte`
- `plan_smd.id` <-> `plan_smd_runs.plan_id`
- `plan_smd.lote` <-> `trazabilidad.lot_no`
- `usuarios_sistema.id` <-> `usuario_roles.usuario_id`
- `roles.id` <-> `usuario_roles.rol_id` y `rol_permisos*`

## 9. Inconsistencias detectadas en modelo/SQL

- Mezcla de SQL MySQL con sintaxis SQLite en rutas de import (`INSERT OR REPLACE`).
- Nombres de tabla no uniformes en material legacy (`control_almacen` vs `control_material_almacen`).
- Uso parcial de FKs (creacion/desactivacion/migracion no centralizada).

Riesgos y remediacion priorizada:

- [HALLAZGOS_TECNICOS_Y_RIESGOS.md](./HALLAZGOS_TECNICOS_Y_RIESGOS.md)

