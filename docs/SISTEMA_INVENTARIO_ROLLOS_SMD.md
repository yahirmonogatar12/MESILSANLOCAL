# Sistema de Inventario Automático de Rollos SMD

## Descripción General

Este sistema implementa un inventario automático para rollos de componentes SMD que se mueven desde el almacén general hacia el área de producción SMD, con trazabilidad completa hasta las máquinas mounters.

## Arquitectura del Sistema

### Tablas Principales

#### 1. `InventarioRollosSMD`
Tabla principal que mantiene el inventario actual de rollos en el área SMD.

**Campos principales:**
- `id` - Identificador único del rollo
- `numero_parte` - Número de parte del componente
- `codigo_barras` - Código de barras generado automáticamente
- `lote` - Lote del material
- `estado` - ACTIVO, EN_USO, AGOTADO, RETIRADO
- `cantidad_inicial/actual` - Control de cantidades
- `linea_asignada/maquina_asignada/slot_asignado` - Ubicación en mounter
- `fecha_entrada/asignacion/ultimo_uso` - Control temporal
- `movimiento_origen_id` - Referencia al movimiento de almacén que originó el registro

#### 2. `HistorialMovimientosRollosSMD`
Historial completo de todos los movimientos de cada rollo.

**Tipos de movimientos:**
- `ENTRADA` - Rollo llega al área SMD desde almacén
- `ASIGNACION` - Rollo asignado a una mounter específica
- `USO` - Registro de uso en la mounter
- `AGOTAMIENTO` - Rollo se agota
- `RETIRO` - Rollo retirado del área

### Triggers Automáticos

#### 1. `trigger_registro_rollo_smd_salida`
- **Activación:** Después de INSERT en `movimientosimd_smd`
- **Condición:** `tipo = 'SALIDA'` AND `ubicacion LIKE '%SMD%'`
- **Función:** Crea automáticamente un nuevo rollo en `InventarioRollosSMD`
- **Prevención:** No duplica si ya existe rollo activo para la misma parte

#### 2. `trigger_actualizar_rollo_smd_mounter`
- **Activación:** Después de INSERT en `historial_cambio_material_smt`
- **Función:** Actualiza información de asignación cuando se detecta cambio en mounter
- **Actualiza:** Línea, máquina, slot, fechas, estado según resultado (OK/NG)

### Procedimientos Almacenados

#### `sp_marcar_rollo_agotado(rollo_id, observaciones)`
- Marca un rollo como agotado
- Actualiza cantidad a 0
- Registra en historial
- Permite observaciones adicionales

### Vista de Consulta

#### `vista_estado_rollos_smd`
Vista optimizada que combina:
- Información básica del rollo
- Último movimiento registrado
- Estado detallado calculado
- Tiempo en área SMD
- Estado de utilización

## APIs REST

### Endpoints Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/smd/inventario` | Página web del inventario |
| GET | `/api/smd/inventario/rollos` | Lista rollos con filtros |
| GET | `/api/smd/inventario/rollo/<id>` | Detalle de rollo específico |
| POST | `/api/smd/inventario/rollo/<id>/marcar_agotado` | Marcar como agotado |
| POST | `/api/smd/inventario/rollo/<id>/asignar_mounter` | Asignar a mounter |
| GET | `/api/smd/inventario/stats` | Estadísticas generales |
| POST | `/api/smd/inventario/sincronizar` | Sincronizar con almacén |

### Filtros Disponibles
- `estado` - Por estado del rollo
- `numero_parte` - Por número de parte
- `linea` - Por línea asignada
- `maquina` - Por máquina asignada
- `fecha_desde/hasta` - Por rango de fechas

## Flujo de Trabajo Automático

### 1. Salida de Almacén → Registro SMD
```
Movimiento en almacén (SALIDA hacia SMD)
    ↓
Trigger detecta salida
    ↓
Verifica si ya existe rollo activo
    ↓
Crea nuevo registro en InventarioRollosSMD
    ↓
Registra movimiento ENTRADA en historial
```

### 2. Cambio en Mounter → Actualización Estado
```
Cambio de material en mounter
    ↓
Registro en historial_cambio_material_smt
    ↓
Trigger busca rollo correspondiente
    ↓
Actualiza línea/máquina/slot/fechas
    ↓
Cambia estado según resultado (OK→EN_USO, NG→ACTIVO)
    ↓
Registra movimiento en historial
```

### 3. Gestión Manual
```
Usuario web marca rollo como agotado
    ↓
Llamada a procedimiento sp_marcar_rollo_agotado
    ↓
Actualiza estado a AGOTADO
    ↓
Registra en historial con observaciones
```

## Estados del Rollo

| Estado | Descripción | Transiciones Posibles |
|--------|-------------|----------------------|
| `ACTIVO` | Rollo disponible en área SMD | → EN_USO, AGOTADO, RETIRADO |
| `EN_USO` | Rollo asignado y funcionando en mounter | → ACTIVO, AGOTADO |
| `AGOTADO` | Rollo sin material restante | → RETIRADO |
| `RETIRADO` | Rollo removido del área SMD | - |

## Instalación

### 1. Ejecutar Script SQL
```bash
python scripts/instalar_inventario_smd.py
```

### 2. Integrar con Aplicación Principal
```python
# En routes.py principal
from .smd_inventory_api import register_smd_inventory_routes

# En inicialización de app
register_smd_inventory_routes(app)
```

### 3. Agregar al Menú
```html
<a href="/smd/inventario" class="nav-link">
    <i class="fas fa-tape"></i>
    Inventario Rollos SMD
</a>
```

## Configuración

### Base de Datos
El sistema utiliza la misma configuración de MySQL que el sistema principal:
```python
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4'
}
```

## Monitoreo y Mantenimiento

### Consultas Útiles

#### Rollos activos por línea
```sql
SELECT linea_asignada, COUNT(*) as cantidad
FROM InventarioRollosSMD 
WHERE estado = 'EN_USO'
GROUP BY linea_asignada;
```

#### Actividad reciente
```sql
SELECT tipo_movimiento, COUNT(*) as cantidad
FROM HistorialMovimientosRollosSMD
WHERE fecha_movimiento >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
GROUP BY tipo_movimiento;
```

#### Rollos sin asignar hace más de X días
```sql
SELECT *
FROM InventarioRollosSMD
WHERE estado = 'ACTIVO'
AND linea_asignada IS NULL
AND fecha_entrada < DATE_SUB(NOW(), INTERVAL 3 DAY);
```

### Mantenimiento Periódico

1. **Limpieza de rollos antiguos agotados:**
   ```sql
   UPDATE InventarioRollosSMD 
   SET estado = 'RETIRADO'
   WHERE estado = 'AGOTADO'
   AND fecha_agotamiento < DATE_SUB(NOW(), INTERVAL 30 DAY);
   ```

2. **Sincronización manual:**
   - Usar endpoint `/api/smd/inventario/sincronizar`
   - Ejecutar periódicamente para capturar movimientos perdidos

## Integración con Sistemas Existentes

### Con Sistema de Almacén
- Detecta automáticamente salidas hacia SMD
- Se integra con tabla `movimientosimd_smd`
- Mantiene referencia al movimiento origen

### Con Sistema SMT/Mounter
- Monitorea tabla `historial_cambio_material_smt`
- Actualiza estado según resultados de scaneo
- Mantiene trazabilidad completa

### Con Sistema de Reportes
- Proporciona datos históricos detallados
- Estadísticas en tiempo real
- Integración vía APIs REST

## Troubleshooting

### Problema: Rollos no se crean automáticamente
- Verificar que los triggers estén instalados
- Comprobar que los movimientos tengan `ubicacion LIKE '%SMD%'`
- Revisar logs de errores en triggers

### Problema: Estados no se actualizan desde mounters
- Verificar estructura de tabla `historial_cambio_material_smt`
- Comprobar coincidencia de `PartName` con `numero_parte`
- Revisar formato de fechas en triggers

### Problema: Performance lenta
- Verificar índices en tablas principales
- Considerar archivado de historial antiguo
- Optimizar consultas con muchos filtros

## Logs y Auditoría

### Campos de Auditoría
- `creado_en` - Timestamp de creación
- `actualizado_en` - Timestamp de última actualización
- `usuario_responsable` - Usuario que realizó la acción
- `observaciones` - Notas adicionales

### Historial Completo
Todos los movimientos se registran en `HistorialMovimientosRollosSMD` con:
- Timestamp exacto
- Usuario responsable
- Descripción detallada
- Estados antes/después
- Información de mounter (si aplica)

## Extensiones Futuras

### Posibles Mejoras
1. **Control de consumo real:** Integrar con datos de producción para calcular consumo exacto
2. **Alertas automáticas:** Notificaciones cuando rollos están por agotarse
3. **Optimización de ubicación:** Sugerencias de asignación óptima de rollos
4. **Integración con ERP:** Sincronización bidireccional con sistema de planificación
5. **Dashboard en tiempo real:** Visualización avanzada del estado del inventario
6. **API móvil:** Aplicación móvil para gestión de inventario
7. **Predicción de demanda:** ML para predecir necesidades de reposición
