# Módulo PO/WO (Purchase Orders & Work Orders)

## Descripción

Sistema de gestión de órdenes de compra (PO) y órdenes de trabajo (WO) para planificación y seguimiento de producción.

## Arquitectura

### Tablas de Base de Datos

#### `embarques` (Purchase Orders)
Almacena información de órdenes de compra/embarques.

**Campos principales:**
- `codigo_po` - Código único formato `PO-YYMMDD-####`
- `nombre_po` - Nombre descriptivo de la PO
- `fecha_registro` - Fecha de registro
- `modelo` - Part number del modelo
- `cliente` - Cliente destino
- `proveedor` - Proveedor
- `total_cantidad_entregada` - Cantidad total a entregar
- `cantidad_entregada` - Cantidad ya entregada
- `estado` - Estado actual (PLAN, EN_PROCESO, COMPLETADO)
- `fecha_entrega` - Fecha programada de entrega
- `codigo_entrega` - Código de entrega
- `usuario_creacion` - Usuario que creó la PO
- `modificado` - Timestamp de última modificación

#### `work_orders` (Work Orders)
Almacena órdenes de trabajo para producción.

**Campos principales:**
- `codigo_wo` - Código único formato `WO-YYMMDD-####`
- `codigo_po` - Referencia a PO (puede ser 'SIN-PO')
- `modelo` - Part number del modelo
- `codigo_modelo` - Part number (persistente)
- `nombre_modelo` - Nombre del proyecto (persistente, desde tabla `raw`)
- `cantidad_planeada` - Cantidad a producir
- `fecha_operacion` - Fecha programada de operación
- `estado` - Estado actual (CREADA, PLANIFICADA, EN_PRODUCCION, CERRADA)
- `fecha_modificacion` - Timestamp de última modificación
- `modificador` - Usuario que modificó

### Integración con Tabla RAW

El sistema obtiene automáticamente el nombre del modelo desde la tabla `raw`:
```sql
SELECT project FROM raw 
WHERE TRIM(part_no) = TRIM(modelo) 
ORDER BY id DESC LIMIT 1
```

Esto permite mostrar nombres descriptivos en lugar de solo códigos de parte.

## API Endpoints

### Work Orders

#### POST `/api/work_orders`
Crear nueva Work Order.

**Request Body:**
```json
{
    "codigo_wo": "WO-241015-0001",  // Opcional, se genera automáticamente
    "modelo": "ABC123",              // Requerido
    "codigo_po": "PO-241015-0001",  // Opcional
    "cantidad_planeada": 1000,       // Requerido
    "fecha_operacion": "2024-10-15", // Opcional
    "usuario_creador": "Juan Pérez"  // Opcional
}
```

**Response:**
```json
{
    "ok": true,
    "codigo_wo": "WO-241015-0001",
    "message": "Work Order creada exitosamente"
}
```

**Validaciones:**
- Código WO debe seguir formato `WO-YYMMDD-####`
- Modelo es requerido
- Cantidad debe ser entero positivo
- Fecha debe ser formato `YYYY-MM-DD`
- No puede duplicar código WO existente

#### GET `/api/work_orders`
Listar Work Orders con filtros.

**Query Parameters:**
- `estado` - Filtrar por estado
- `codigo_wo` - Buscar WO específica
- `modelo` - Buscar por modelo (LIKE)
- `fecha_desde` - Fecha inicio
- `fecha_hasta` - Fecha fin
- `incluir_planificadas` - `true` para incluir WO planificadas (default: `false`)

**Comportamiento por defecto:**
- Solo muestra WO con estado `CREADA`
- Excluye WO con estado `PLANIFICADA` (a menos que se especifique `incluir_planificadas=true`)
- Ordena por fecha de modificación descendente

**Response:**
```json
{
    "ok": true,
    "work_orders": [
        {
            "codigo_wo": "WO-241015-0001",
            "codigo_po": "PO-241015-0001",
            "modelo": "ABC123",
            "codigo_modelo": "ABC123",
            "nombre_modelo": "Proyecto XYZ",
            "cantidad_planeada": 1000,
            "fecha_operacion": "2024-10-15",
            "estado": "CREADA",
            "fecha_modificacion": "2024-10-15 10:30:00",
            "modificador": "Juan Pérez"
        }
    ]
}
```

#### GET `/api/wo/listar`
Ruta alternativa para compatibilidad con frontend.

Mismos parámetros y comportamiento que `/api/work_orders`.

**Response:**
```json
{
    "success": true,
    "data": [ /* array de WOs */ ]
}
```

#### PUT `/api/wo/{codigo}/estado`
Actualizar estado de una Work Order.

**Request Body:**
```json
{
    "estado": "EN_PRODUCCION",
    "modificador": "Juan Pérez"
}
```

**Estados válidos:**
- `CREADA` - WO creada, lista para planificar
- `PLANIFICADA` - WO planificada en sistema
- `EN_PRODUCCION` - WO en proceso de producción
- `CERRADA` - WO completada

**Response:**
```json
{
    "ok": true,
    "message": "Estado de WO WO-241015-0001 actualizado a EN_PRODUCCION",
    "estado_anterior": "CREADA",
    "estado_nuevo": "EN_PRODUCCION"
}
```

#### POST `/api/wo/actualizar-po`
Actualizar código PO de una Work Order.

**Request Body:**
```json
{
    "codigo_wo": "WO-241015-0001",
    "codigo_po": "PO-241015-0002"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Código PO actualizado exitosamente",
    "codigo_wo": "WO-241015-0001",
    "codigo_po_anterior": "SIN-PO",
    "codigo_po_nuevo": "PO-241015-0002"
}
```

#### POST `/api/wo/actualizar`
Actualizar Work Order completa.

**Request Body:**
```json
{
    "codigo_wo": "WO-241015-0001",
    "modelo": "ABC123",
    "cantidad_planeada": 1500,
    "codigo_po": "PO-241015-0001"
}
```

**Actualiza:**
- Modelo y códigos relacionados
- Cantidad planeada
- Código PO
- Nombre del modelo (desde tabla `raw`)

#### DELETE `/api/wo/eliminar`
Eliminar Work Order.

**Request Body:**
```json
{
    "codigo_wo": "WO-241015-0001"
}
```

#### GET `/api/generar_codigo_wo`
Generar código WO automático.

**Response:**
```json
{
    "ok": true,
    "codigo_wo": "WO-241015-0005"
}
```

### Purchase Orders

#### GET `/api/po/listar`
Listar Purchase Orders.

**Query Parameters:**
- `estado` - Filtrar por estado
- `fecha_desde` - Fecha inicio
- `fecha_hasta` - Fecha fin

**Response:**
```json
{
    "success": true,
    "data": [
        {
            "codigo_po": "PO-241015-0001",
            "nombre_po": "Embarque Cliente XYZ",
            "fecha_registro": "2024-10-15",
            "modelo": "ABC123",
            "nombre_modelo": "Proyecto XYZ",
            "cliente": "Cliente ABC",
            "proveedor": "Proveedor DEF",
            "total_cantidad_entregada": 5000,
            "cantidad_entregada": 2000,
            "estado": "EN_PROCESO",
            "fecha_entrega": "2024-10-30"
        }
    ],
    "total": 1
}
```

#### POST `/api/po/crear`
Crear nueva Purchase Order.

**Request Body:**
```json
{
    "nombre_po": "Embarque Cliente XYZ",
    "fecha_registro": "2024-10-15",
    "modelo": "ABC123",
    "cliente": "Cliente ABC",
    "proveedor": "Proveedor DEF",
    "total_cantidad_entregada": 5000,
    "fecha_entrega": "2024-10-30",
    "estado": "PLAN"
}
```

**Genera automáticamente:**
- `codigo_po` en formato `PO-YYMMDD-####`
- Secuencia incremental por día

## Validaciones

### Formato de Códigos

#### Código PO
- Patrón: `PO-YYMMDD-####`
- Ejemplo: `PO-241015-0001`
- Validación: `^PO-\d{6}-\d{4}$`

#### Código WO
- Patrón: `WO-YYMMDD-####`
- Ejemplo: `WO-241015-0001`
- Validación: `^WO-\d{6}-\d{4}$`

### Generación Automática

Ambos códigos se generan automáticamente:
1. Obtener fecha actual en formato `YYMMDD`
2. Buscar último código del día
3. Incrementar secuencia
4. Formato: `{TIPO}-{FECHA}-{SECUENCIA:04d}`

## Manejo de Errores

### Códigos de Error

- `VALIDATION_ERROR` - Error de validación de datos
- `DUPLICATE_WO` - Código WO duplicado
- `NOT_FOUND` - Recurso no encontrado
- `INTERNAL_ERROR` - Error interno del servidor

### Respuestas de Error

```json
{
    "ok": false,
    "code": "VALIDATION_ERROR",
    "field": "cantidad_planeada",
    "message": "Cantidad planeada debe ser un número entero positivo"
}
```

## Integración con Frontend

### Carga de Módulo

```javascript
// En scriptMain.js
window.mostrarPOWO = function() {
    window.cargarContenidoDinamico('po-wo-container', '/po-wo-ajax', () => {
        if (typeof window.initializePOWOEventListeners === 'function') {
            window.initializePOWOEventListeners();
        }
        if (typeof window.loadPOWOData === 'function') {
            window.loadPOWOData();
        }
    });
};
```

### Ejemplo de Uso

```javascript
// Crear WO
async function crearWO(data) {
    try {
        const response = await axios.post('/api/work_orders', {
            modelo: data.modelo,
            cantidad_planeada: data.cantidad,
            fecha_operacion: data.fecha,
            usuario_creador: session.usuario
        });
        
        if (response.data.ok) {
            showNotification('WO creada: ' + response.data.codigo_wo, 'success');
            loadWOList();
        }
    } catch (error) {
        showNotification('Error: ' + error.response.data.message, 'error');
    }
}

// Listar WOs
async function loadWOList() {
    try {
        const response = await axios.get('/api/wo/listar', {
            params: {
                fecha_desde: '2024-10-01',
                fecha_hasta: '2024-10-31',
                incluir_planificadas: false
            }
        });
        
        if (response.data.success) {
            renderWOTable(response.data.data);
        }
    } catch (error) {
        console.error('Error cargando WOs:', error);
    }
}
```

## Flujo de Trabajo

### Ciclo de Vida de una WO

```
1. CREADA
   ↓ (Usuario planifica en sistema)
2. PLANIFICADA
   ↓ (Inicia producción)
3. EN_PRODUCCION
   ↓ (Completa producción)
4. CERRADA
```

### Relación PO → WO

```
Purchase Order (PO)
    ├── Work Order 1 (WO)
    ├── Work Order 2 (WO)
    └── Work Order 3 (WO)
```

- Una PO puede tener múltiples WOs
- Una WO puede existir sin PO (`codigo_po = 'SIN-PO'`)
- WOs se pueden reasignar a diferentes POs

## Mejores Prácticas

### Al Crear WOs
1. Siempre especificar `usuario_creador` para auditoría
2. Validar que el modelo existe en tabla `raw`
3. Verificar disponibilidad de materiales antes de crear
4. Usar generación automática de códigos

### Al Actualizar Estados
1. Registrar `modificador` en cada cambio
2. Validar transiciones de estado permitidas
3. Actualizar sistemas relacionados (plan_main, etc.)

### Al Consultar
1. Usar filtros de fecha para limitar resultados
2. Por defecto excluir WO planificadas para evitar confusión
3. Incluir `nombre_modelo` para mejor legibilidad

## Troubleshooting

### WO no aparece en listado
- Verificar que estado sea `CREADA` (no `PLANIFICADA`)
- Usar parámetro `incluir_planificadas=true` si es necesario
- Verificar filtros de fecha

### Nombre de modelo no se muestra
- Verificar que el part number existe en tabla `raw`
- Verificar que campo `project` en `raw` no esté vacío
- Ejecutar actualización manual si es necesario

### Error al crear WO
- Verificar formato de código WO
- Verificar que no exista código duplicado
- Validar que cantidad sea entero positivo
- Verificar formato de fecha
