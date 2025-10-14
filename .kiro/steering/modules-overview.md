# Módulos del Sistema - Overview

## Resumen de Módulos Documentados

Este documento proporciona un índice rápido de todos los módulos del sistema ISEMM MES con enlaces a su documentación detallada.

## Módulos Principales

### 1. PO/WO (Purchase Orders & Work Orders)
**Archivo:** [modules-po-wo.md](modules-po-wo.md)

**Propósito:** Gestión de órdenes de compra y órdenes de trabajo para planificación de producción.

**Tablas:**
- `embarques` - Purchase Orders
- `work_orders` - Work Orders

**APIs Principales:**
- `POST /api/work_orders` - Crear WO
- `GET /api/work_orders` - Listar WOs
- `GET /api/po/listar` - Listar POs
- `POST /api/po/crear` - Crear PO

**Características Clave:**
- Generación automática de códigos (PO-YYMMDD-####, WO-YYMMDD-####)
- Estados de WO: CREADA, PLANIFICADA, EN_PRODUCCION, CERRADA
- Integración con tabla `raw` para nombres de modelos
- Relación 1:N entre PO y WO

---

### 2. AOI (Automated Optical Inspection)
**Archivo:** [modules-aoi.md](modules-aoi.md)

**Propósito:** Monitoreo y reporte de inspección óptica automatizada para líneas SMT.

**Tablas:**
- `aoi_file_log` - Registros de archivos AOI procesados

**APIs Principales:**
- `GET /api/shift-now` - Información del turno actual
- `GET /api/realtime` - Datos en tiempo real del turno
- `GET /api/day` - Datos completos de un día

**Características Clave:**
- Clasificación automática por turnos (DIA, TIEMPO_EXTRA, NOCHE)
- Manejo de turno nocturno que cruza medianoche
- Mapeo de líneas (1→A, 2→B, 3→C)
- Agregación por línea, modelo y lado de tarjeta
- Zona horaria México (GMT-6)

---

### 3. SMD Inventory (Inventario de Rollos SMD)
**Archivo:** [modules-smd-inventory.md](modules-smd-inventory.md)

**Propósito:** Sistema automático de inventario para rollos SMD con trazabilidad completa.

**Tablas:**
- `InventarioRollosSMD` - Inventario actual de rollos
- `HistorialMovimientosRollosSMD` - Historial de movimientos

**APIs Principales:**
- `GET /api/smd/inventario/rollos` - Listar rollos con filtros
- `GET /api/smd/inventario/rollo/<id>` - Detalle de rollo
- `POST /api/smd/inventario/rollo/<id>/marcar_agotado` - Marcar agotado
- `POST /api/smd/inventario/rollo/<id>/asignar_mounter` - Asignar a mounter
- `GET /api/smd/inventario/stats` - Estadísticas
- `POST /api/smd/inventario/sincronizar` - Sincronizar con almacén

**Características Clave:**
- Triggers automáticos desde almacén y mounters
- Estados: ACTIVO, EN_USO, AGOTADO, RETIRADO
- Trazabilidad completa desde almacén hasta mounter
- Generación automática de códigos de barras
- Integración con `movimientosimd_smd` y `historial_cambio_material_smt`

---

## Módulos Adicionales (No Documentados en Detalle)

### 4. Material Management
**Archivos:** `app/routes.py`, `app/db_mysql.py`

**Propósito:** Gestión de materiales, inventario y movimientos.

**Tablas:**
- `materiales` - Catálogo de materiales
- `inventario` - Niveles de inventario
- `movimientos_inventario` - Historial de movimientos
- `bom` - Bill of Materials

**Funcionalidades:**
- CRUD de materiales
- Control de entradas y salidas
- Gestión de BOM por modelo
- Importación/exportación Excel

---

### 5. SMT Monitoring
**Archivos:** `app/smt_routes_*.py`

**Propósito:** Monitoreo de operaciones SMT y cambios de material.

**Tablas:**
- `historial_cambio_material_smt` - Cambios de material en mounters
- Varias tablas de monitoreo SMT

**Funcionalidades:**
- Registro de cambios de material
- Monitoreo de líneas SMT
- Reportes de producción SMT

---

### 6. User Administration
**Archivos:** `app/auth_system.py`, `app/user_admin.py`, `app/admin_api.py`

**Propósito:** Gestión de usuarios, roles y permisos.

**Documentación:** Ver [auth.md](auth.md)

**Tablas:**
- `usuarios_sistema` - Usuarios
- `roles` - Roles del sistema
- `permisos_botones` - Permisos granulares
- `usuario_roles` - Asignación de roles
- `rol_permisos_botones` - Permisos por rol
- `auditoria` - Log de auditoría

---

### 7. Production Planning (Plan Main)
**Archivos:** `app/routes.py`, `app/static/js/plan.js`

**Propósito:** Planificación de producción assembly.

**Tablas:**
- `plan_main` - Planes de producción

**Funcionalidades:**
- Creación de planes de producción
- Asignación a líneas
- Control de turnos (DIA, TIEMPO_EXTRA, NOCHE)
- Generación de lot numbers
- Integración con WO

---

## Matriz de Integración

### Flujo de Datos Entre Módulos

```
Almacén (Material Management)
    ↓ (movimientos SALIDA)
SMD Inventory
    ↓ (asignación a mounter)
SMT Monitoring
    ↓ (cambios de material)
SMD Inventory (actualización estado)

PO (Purchase Orders)
    ↓ (genera)
WO (Work Orders)
    ↓ (planifica)
Plan Main
    ↓ (ejecuta)
SMT Monitoring / AOI
```

### Tablas Compartidas

#### `raw`
Tabla central de referencia de modelos.

**Usada por:**
- PO/WO - Para obtener nombres de proyectos
- Material Management - Para validar part numbers
- Plan Main - Para información de modelos

**Campos clave:**
- `part_no` - Número de parte
- `project` - Nombre del proyecto
- `ct` - Cycle time
- `uph` - Units per hour

---

## Patrones Comunes

### 1. Generación de Códigos
Todos los módulos que generan códigos siguen el patrón:
```
{TIPO}-{YYMMDD}-{SECUENCIA:04d}
```

Ejemplos:
- `PO-241015-0001`
- `WO-241015-0001`
- `ASSYLINE-241015-001`

### 2. Estados y Transiciones
Todos los módulos con estados siguen máquinas de estado claras:

**WO:** CREADA → PLANIFICADA → EN_PRODUCCION → CERRADA

**Rollo SMD:** ACTIVO → EN_USO → AGOTADO → RETIRADO

**Plan Main:** PLAN → EN_PROCESO → COMPLETADO

### 3. Auditoría
Todos los módulos registran:
- Usuario que realiza la acción
- Timestamp de la acción
- Estado anterior y nuevo
- Descripción de la acción

### 4. Timezone
Todos los módulos usan zona horaria de México (GMT-6):
```python
from app.auth_system import AuthSystem
mexico_time = AuthSystem.get_mexico_time()
```

### 5. Turnos
Clasificación estándar de turnos:
- **DIA:** 07:40 - 17:39
- **TIEMPO_EXTRA:** 17:40 - 22:49
- **NOCHE:** 22:50 - 07:30 (cruza medianoche)

---

## APIs por Categoría

### Consulta de Datos
- `GET /api/work_orders` - Listar WOs
- `GET /api/po/listar` - Listar POs
- `GET /api/smd/inventario/rollos` - Listar rollos SMD
- `GET /api/realtime` - Datos AOI en tiempo real
- `GET /api/day` - Datos AOI por día

### Creación de Recursos
- `POST /api/work_orders` - Crear WO
- `POST /api/po/crear` - Crear PO
- `POST /api/plan` - Crear plan de producción

### Actualización de Estado
- `PUT /api/wo/{codigo}/estado` - Actualizar estado WO
- `POST /api/smd/inventario/rollo/<id>/marcar_agotado` - Marcar rollo agotado
- `POST /api/plan/update` - Actualizar plan

### Estadísticas y Reportes
- `GET /api/smd/inventario/stats` - Estadísticas SMD
- `GET /api/shift-now` - Turno actual

### Sincronización
- `POST /api/smd/inventario/sincronizar` - Sincronizar inventario SMD

---

## Guías de Desarrollo

### Para Agregar un Nuevo Módulo
1. Leer [GUIA_DESARROLLO_MODULOS_MES.md](../../GUIA_DESARROLLO_MODULOS_MES.md)
2. Seguir patrones de [frontend.md](frontend.md)
3. Implementar APIs según [api-conventions.md](api-conventions.md)
4. Agregar permisos según [auth.md](auth.md)
5. Documentar en nuevo archivo `modules-{nombre}.md`

### Para Modificar un Módulo Existente
1. Consultar documentación específica del módulo
2. Verificar integraciones con otros módulos
3. Actualizar documentación después de cambios
4. Probar integraciones afectadas

### Para Debugging
1. Consultar sección Troubleshooting del módulo específico
2. Revisar logs con emojis para rastreo
3. Verificar permisos si hay errores 403
4. Comprobar formato de datos según documentación API

---

## Roadmap de Documentación

### Completado ✅
- [x] Estructura general del proyecto
- [x] Stack tecnológico
- [x] Patrones de frontend
- [x] Patrones de base de datos
- [x] Sistema de autenticación
- [x] Convenciones de API
- [x] Estándares de código
- [x] Deployment
- [x] Módulo PO/WO
- [x] Módulo AOI
- [x] Módulo SMD Inventory

### Pendiente 📋
- [ ] Módulo Material Management (detallado)
- [ ] Módulo SMT Monitoring (detallado)
- [ ] Módulo Plan Main (detallado)
- [ ] Módulo BOM Management
- [ ] Sistema de impresión de etiquetas
- [ ] Integración con Zebra printers
- [ ] Sistema de trazabilidad completo
- [ ] Reportes y exportación

---

## Contacto y Contribuciones

Para agregar o actualizar documentación de módulos:
1. Crear archivo `modules-{nombre}.md` en `.kiro/steering/`
2. Seguir estructura de módulos existentes
3. Incluir: Descripción, Arquitectura, APIs, Ejemplos, Troubleshooting
4. Actualizar este archivo de overview
5. Actualizar README.md si es necesario

---

**Última actualización:** Octubre 2024  
**Versión:** 1.0  
**Sistema:** ISEMM MES - ILSAN Electronics
