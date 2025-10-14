# Módulo SMD Inventory (Inventario de Rollos SMD)

## Descripción

Sistema automático de inventario para rollos de componentes SMD que se mueven desde el almacén general hacia el área de producción SMD, con trazabilidad completa hasta las máquinas mounters.

## Arquitectura

### Tablas de Base de Datos

#### `InventarioRollosSMD`
Tabla principal que mantiene el inventario actual de rollos en el área SMD.

**Campos principales:**
- `id` - Identificador único del rollo (AUTO_INCREMENT)
- `numero_parte` - Número de parte del componente
- `codigo_barras` - Código de barras generado automáticamente
- `lote` - Lote del material
- `cantidad_inicial` - Cantidad inicial del rollo
- `cantidad_actual` - Cantidad actual disponible
- `estado` - Estado del rollo (ACTIVO, EN_USO, AGOTADO, RETIRADO)
- `area_smd` - Área SMD donde se encuentra
- `linea_asignada` - Línea de producción asignada
- `maquina_asignada` - Máquina mounter asignada
- `slot_asignado` - Slot en la mounter
- `fecha_entrada` - Timestamp de entrada al área SMD
- `fecha_asignacion` - Timestamp de asignación a mounter
- `fecha_ultimo_uso` - Timestamp de último uso registrado
- `fecha_agotamiento` - Timestamp cuando se agotó
- `origen_almacen` - Ubicación de origen en almacén
- `movimiento_origen_id` - FK a `movimientosimd_smd`
- `observaciones` - Notas adicionales
- `creado_en` - Timestamp de creación
- `actualizado_en` - Timestamp de última actualización

#### `HistorialMovimientosRollosSMD`
Historial completo de todos los movimientos de cada rollo.

**Campos principales:**
- `id` - Identificador único
- `rollo_id` - FK a `InventarioRollosSMD`
- `tipo_movimiento` - Tipo (ENTRADA, ASIGNACION, USO, AGOTAMIENTO, RETIRO)
- `descripcion` - Descripción del movimiento
- `cantidad_antes` - Cantidad antes del movimiento
- `cantidad_despues` - Cantidad después del movimiento
- `linea` - Línea involucrada
- `maquina` - Máquina involucrada
- `slot` - Slot involucrado
- `resultado_scaneo` - Resultado del scaneo (OK, NG)
- `usuario` - Usuario que realizó el movimiento
- `fecha_movimiento` - Timestamp del movimiento

### Estados del Rollo

| Estado | Descripción | Transiciones Posibles |
|--------|-------------|----------------------|
| `ACTIVO` | Rollo disponible en área SMD | → EN_USO, AGOTADO, RETIRADO |
| `EN_USO` | Rollo asignado y funcionando en mounter | → ACTIVO, AGOTADO |
| `AGOTADO` | Rollo sin material restante | → RETIRADO |
| `RETIRADO` | Rollo removido del área SMD | - |

### Tipos de Movimientos

- `ENTRADA` - Rollo llega al área SMD desde almacén
- `ASIGNACION` - Rollo asignado a una mounter específica
- `USO` - Registro de uso en la mounter
- `AGOTAMIENTO` - Rollo se agota
- `RETIRO` - Rollo retirado del área

## Triggers Automáticos

### `trigger_registro_rollo_smd_salida`
**Activación:** Después de INSERT en `movimientosimd_smd`

**Condición:** 
- `tipo = 'SALIDA'`
- `ubicacion LIKE '%SMD%'`

**Función:**
- Crea automáticamente un nuevo rollo en `InventarioRollosSMD`
- Genera código de barras único
- Registra movimiento ENTRADA en historial
- Prevención: No duplica si ya existe rollo activo para la misma parte

### `trigger_actualizar_rollo_smd_mounter`
**Activación:** Después de INSERT en `historial_cambio_material_smt`

**Función:**
- Busca rollo correspondiente por `PartName`
- Actualiza línea, máquina, slot
- Actualiza fechas de asignación y último uso
- Cambia estado según resultado:
  - `OK` → `EN_USO`
  - `NG` → `ACTIVO`
- Registra movimiento en historial

## Procedimientos Almacenados

### `sp_marcar_rollo_agotado(rollo_id, observaciones)`
Marca un rollo como agotado.

**Parámetros:**
- `rollo_id` (INT) - ID del rollo
- `observaciones` (TEXT) - Observaciones adicionales

**Acciones:**
- Actualiza estado a `AGOTADO`
- Establece cantidad_actual a 0
- Registra fecha_agotamiento
- Inserta registro en historial

## API Endpoints

### GET `/smd/inventario`
Página HTML para visualizar el inventario de rollos SMD.

**Response:** HTML template

### GET `/api/smd/inventario/rollos`
Obtener inventario actual de rollos con filtros.

**Query Parameters:**
- `estado` - Filtrar por estado (ACTIVO, EN_USO, AGOTADO, RETIRADO)
- `numero_parte` - Buscar por número de parte (LIKE)
- `linea` - Filtrar por línea asignada
- `maquina` - Filtrar por máquina asignada
- `fecha_desde` - Fecha inicio (YYYY-MM-DD)
- `fecha_hasta` - Fecha fin (YYYY-MM-DD)

**Response:**
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "numero_parte": "R1234",
            "codigo_barras": "SMD_R1234_20241015_103045",
            "cantidad_inicial": 5000,
            "cantidad_actual": 3500,
            "estado": "EN_USO",
            "linea_asignada": "LINE_A",
            "maquina_asignada": "MOUNTER_01",
            "slot_asignado": "SLOT_12",
            "fecha_entrada": "2024-10-15 10:30:45",
            "fecha_asignacion": "2024-10-15 11:00:00",
            "fecha_ultimo_uso": "2024-10-15 14:30:00",
            "horas_en_smd": 4,
            "estado_detallado": "ASIGNADO"
        }
    ],
    "stats": {
        "total_rollos": 150,
        "activos": 50,
        "en_uso": 80,
        "agotados": 15,
        "asignados": 80,
        "cantidad_total_disponible": 250000
    },
    "total": 1
}
```

### GET `/api/smd/inventario/rollo/<rollo_id>`
Obtener detalle completo de un rollo específico con su historial.

**Response:**
```json
{
    "success": true,
    "rollo": {
        "id": 1,
        "numero_parte": "R1234",
        "codigo_barras": "SMD_R1234_20241015_103045",
        "cantidad_inicial": 5000,
        "cantidad_actual": 3500,
        "estado": "EN_USO",
        "linea_asignada": "LINE_A",
        "maquina_asignada": "MOUNTER_01",
        "slot_asignado": "SLOT_12",
        "horas_en_smd": 4
    },
    "historial": [
        {
            "id": 1,
            "tipo_movimiento": "ENTRADA",
            "descripcion": "Entrada desde almacén",
            "cantidad_antes": 0,
            "cantidad_despues": 5000,
            "fecha_movimiento": "2024-10-15 10:30:45"
        },
        {
            "id": 2,
            "tipo_movimiento": "ASIGNACION",
            "descripcion": "Asignado a LINE_A/MOUNTER_01",
            "linea": "LINE_A",
            "maquina": "MOUNTER_01",
            "slot": "SLOT_12",
            "fecha_movimiento": "2024-10-15 11:00:00"
        }
    ]
}
```

### POST `/api/smd/inventario/rollo/<rollo_id>/marcar_agotado`
Marcar un rollo como agotado manualmente.

**Request Body:**
```json
{
    "observaciones": "Rollo agotado durante producción",
    "usuario": "Juan Pérez"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Rollo marcado como agotado correctamente"
}
```

### POST `/api/smd/inventario/rollo/<rollo_id>/asignar_mounter`
Asignar un rollo manualmente a una mounter específica.

**Request Body:**
```json
{
    "linea": "LINE_A",
    "maquina": "MOUNTER_01",
    "slot": "SLOT_12",
    "usuario": "Juan Pérez"
}
```

**Validaciones:**
- Línea, máquina y slot son requeridos
- Rollo debe estar en estado ACTIVO o EN_USO
- Rollo debe existir

**Response:**
```json
{
    "success": true,
    "message": "Rollo asignado a LINE_A/MOUNTER_01 slot SLOT_12 correctamente"
}
```

### GET `/api/smd/inventario/stats`
Obtener estadísticas generales del inventario SMD.

**Response:**
```json
{
    "success": true,
    "stats": {
        "principales": {
            "total_rollos": 150,
            "activos": 50,
            "en_uso": 80,
            "agotados": 15,
            "asignados": 80,
            "cantidad_total_disponible": 250000,
            "partes_unicas": 45
        },
        "top_partes": [
            {
                "numero_parte": "R1234",
                "cantidad_rollos": 10,
                "cantidad_total": 50000,
                "promedio_por_rollo": 5000
            }
        ],
        "actividad_24h": {
            "movimientos_24h": 25,
            "entradas_24h": 5,
            "asignaciones_24h": 15,
            "agotamientos_24h": 5
        },
        "por_ubicacion": [
            {
                "ubicacion": "LINE_A / MOUNTER_01",
                "cantidad_rollos": 8
            }
        ]
    }
}
```

### POST `/api/smd/inventario/sincronizar`
Sincronizar inventario SMD con movimientos recientes del almacén.

**Request Body:**
```json
{
    "horas_atras": 24  // Opcional, default: 24
}
```

**Función:**
- Busca movimientos de salida hacia SMD en las últimas X horas
- Crea rollos para movimientos no registrados
- Evita duplicados

**Response:**
```json
{
    "success": true,
    "message": "Sincronización completada: 5 rollos creados",
    "rollos_creados": 5,
    "movimientos_procesados": 5
}
```

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
Genera código de barras único
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

## Integración con Frontend

### Carga de Módulo
```javascript
window.mostrarInventarioSMD = function() {
    window.cargarContenidoDinamico('smd-inventory-container', '/smd/inventario', () => {
        if (typeof window.initializeSMDInventoryEventListeners === 'function') {
            window.initializeSMDInventoryEventListeners();
        }
        if (typeof window.loadSMDInventoryData === 'function') {
            window.loadSMDInventoryData();
        }
    });
};
```

### Ejemplo de Uso
```javascript
// Cargar inventario con filtros
async function loadInventario() {
    try {
        const response = await axios.get('/api/smd/inventario/rollos', {
            params: {
                estado: 'EN_USO',
                linea: 'LINE_A',
                fecha_desde: '2024-10-01'
            }
        });
        
        if (response.data.success) {
            renderInventarioTable(response.data.data);
            updateStats(response.data.stats);
        }
    } catch (error) {
        console.error('❌ Error cargando inventario:', error);
    }
}

// Marcar rollo como agotado
async function marcarAgotado(rolloId) {
    try {
        const response = await axios.post(
            `/api/smd/inventario/rollo/${rolloId}/marcar_agotado`,
            {
                observaciones: 'Agotado durante producción',
                usuario: sessionStorage.getItem('usuario')
            }
        );
        
        if (response.data.success) {
            showNotification('Rollo marcado como agotado', 'success');
            loadInventario();
        }
    } catch (error) {
        showNotification('Error: ' + error.response.data.error, 'error');
    }
}
```

## Integración con Sistemas Existentes

### Con Sistema de Almacén
- Detecta automáticamente salidas hacia SMD
- Se integra con tabla `movimientosimd_smd`
- Mantiene referencia al movimiento origen

### Con Sistema SMT/Mounter
- Monitorea tabla `historial_cambio_material_smt`
- Actualiza estado según resultados de scaneo
- Mantiene trazabilidad completa

## Consultas Útiles

### Rollos activos por línea
```sql
SELECT linea_asignada, COUNT(*) as cantidad
FROM InventarioRollosSMD 
WHERE estado = 'EN_USO'
GROUP BY linea_asignada;
```

### Actividad reciente
```sql
SELECT tipo_movimiento, COUNT(*) as cantidad
FROM HistorialMovimientosRollosSMD
WHERE fecha_movimiento >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
GROUP BY tipo_movimiento;
```

### Rollos sin asignar hace más de X días
```sql
SELECT *
FROM InventarioRollosSMD
WHERE estado = 'ACTIVO'
AND linea_asignada IS NULL
AND fecha_entrada < DATE_SUB(NOW(), INTERVAL 3 DAY);
```

## Mantenimiento

### Limpieza de rollos antiguos agotados
```sql
UPDATE InventarioRollosSMD 
SET estado = 'RETIRADO'
WHERE estado = 'AGOTADO'
AND fecha_agotamiento < DATE_SUB(NOW(), INTERVAL 30 DAY);
```

### Sincronización manual
Ejecutar endpoint `/api/smd/inventario/sincronizar` periódicamente para capturar movimientos perdidos.

## Troubleshooting

### Rollos no se crean automáticamente
- Verificar que los triggers estén instalados
- Comprobar que los movimientos tengan `ubicacion LIKE '%SMD%'`
- Revisar logs de errores en triggers

### Estados no se actualizan desde mounters
- Verificar estructura de tabla `historial_cambio_material_smt`
- Comprobar coincidencia de `PartName` con `numero_parte`
- Revisar formato de fechas en triggers

### Performance lenta
- Verificar índices en tablas principales
- Considerar archivado de historial antiguo
- Optimizar consultas con muchos filtros

## Mejores Prácticas

1. **Sincronización regular:** Ejecutar sincronización cada hora para mantener datos actualizados
2. **Limpieza periódica:** Archivar o eliminar rollos retirados antiguos
3. **Monitoreo de estados:** Revisar rollos en estado ACTIVO sin asignar por más de 3 días
4. **Auditoría:** Siempre especificar usuario en operaciones manuales
5. **Validación:** Verificar que part numbers existan antes de crear rollos manualmente
