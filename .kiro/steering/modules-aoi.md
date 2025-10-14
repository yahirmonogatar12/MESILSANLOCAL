# Módulo AOI (Automated Optical Inspection)

## Descripción

Sistema de monitoreo y reporte de inspección óptica automatizada (AOI) para líneas de producción SMT. Procesa datos de archivos AOI y proporciona reportes en tiempo real por turno y día.

## Arquitectura

### Tabla de Base de Datos

#### `aoi_file_log`
Almacena registros procesados de archivos AOI.

**Campos principales:**
- `id` - Identificador único
- `line_no` - Número de línea (1=A, 2=B, 3=C)
- `model` - Modelo del producto
- `board_side` - Lado de la tarjeta (TOP, BOT, 1 SIDE)
- `piece_w` - Cantidad de piezas
- `shift` - Turno (DIA, TIEMPO_EXTRA, NOCHE)
- `shift_date` - Fecha del turno (date lógico)
- `file_timestamp` - Timestamp del archivo original
- `processed_at` - Timestamp de procesamiento

### Reglas de Turno

El sistema clasifica automáticamente los registros en turnos según la hora:

| Turno | Horario | Minutos |
|-------|---------|---------|
| DÍA | 07:40 - 17:39 | 460 - 1059 |
| TIEMPO EXTRA | 17:40 - 22:49 | 1060 - 1369 |
| NOCHE | 22:50 - 07:30 | 1370+ o 0-450 |

**Nota importante:** El turno NOCHE que cruza medianoche se asigna al día anterior.

### Cálculo de Fecha de Turno

```python
def compute_shift_date(dt: datetime, shift: str) -> date:
    # Si es turno NOCHE y la hora es <= 07:30, pertenece al día anterior
    if shift == "NOCHE" and (dt.hour*60 + dt.minute) <= 7*60+30:
        return (dt - timedelta(days=1)).date()
    return dt.date()
```

## API Endpoints

### GET `/api/shift-now`
Obtener información del turno actual.

**Response:**
```json
{
    "now": "2024-10-15T14:30:00",
    "shift": "DIA",
    "shift_date": "2024-10-15"
}
```

**Uso:** Banner de turno actual en la interfaz.

### GET `/api/realtime`
Obtener datos de producción del turno actual en tiempo real.

**Response:**
```json
{
    "shift_date": "2024-10-15",
    "shift": "DIA",
    "rows": [
        {
            "linea": "A",
            "modelo": "MODEL_XYZ",
            "lado": "TOP",
            "cantidad": 1500
        },
        {
            "linea": "A",
            "modelo": "MODEL_XYZ",
            "lado": "BOT",
            "cantidad": 1500
        },
        {
            "linea": "B",
            "modelo": "MODEL_ABC",
            "lado": "1 SIDE",
            "cantidad": 2000
        }
    ]
}
```

**Características:**
- Datos agregados por línea, modelo y lado
- Solo muestra datos del turno actual
- Actualización en tiempo real
- Ordenado por línea (A, B, C), modelo, lado (TOP, BOT, 1 SIDE)

### GET `/api/day`
Obtener datos de producción de un día completo (todos los turnos).

**Query Parameters:**
- `date` (requerido) - Fecha en formato YYYY-MM-DD

**Response:**
```json
{
    "rows": [
        {
            "fecha": "2024-10-15",
            "turno": "DIA",
            "linea": "A",
            "modelo": "MODEL_XYZ",
            "lado": "TOP",
            "cantidad": 1500
        },
        {
            "fecha": "2024-10-15",
            "turno": "TIEMPO_EXTRA",
            "linea": "A",
            "modelo": "MODEL_XYZ",
            "lado": "TOP",
            "cantidad": 800
        },
        {
            "fecha": "2024-10-15",
            "turno": "NOCHE",
            "linea": "A",
            "modelo": "MODEL_XYZ",
            "lado": "TOP",
            "cantidad": 600
        }
    ]
}
```

**Características:**
- Datos agregados por fecha, turno, línea, modelo y lado
- Muestra todos los turnos del día especificado
- Ordenado por turno (DIA, TIEMPO_EXTRA, NOCHE), línea, modelo, lado

## Mapeo de Líneas

El sistema mapea números de línea a letras:

```python
CASE line_no 
    WHEN 1 THEN 'A' 
    WHEN 2 THEN 'B' 
    WHEN 3 THEN 'C' 
    ELSE CONCAT('L', line_no) 
END
```

## Mapeo de Lados

Normaliza los valores de lado de tarjeta:

```python
CASE WHEN board_side IN ('TOP','BOT') 
    THEN board_side 
    ELSE '1 SIDE' 
END
```

Valores posibles:
- `TOP` - Lado superior
- `BOT` - Lado inferior
- `1 SIDE` - Un solo lado (o valor no estándar)

## Integración con Frontend

### Carga de Módulo
```javascript
window.mostrarAOI = function() {
    window.cargarContenidoDinamico('aoi-container', '/aoi-ajax', () => {
        if (typeof window.initializeAOIEventListeners === 'function') {
            window.initializeAOIEventListeners();
        }
        if (typeof window.loadAOIData === 'function') {
            window.loadAOIData();
        }
    });
};
```

### Ejemplo de Uso - Turno Actual
```javascript
// Cargar datos del turno actual
async function loadTurnoActual() {
    try {
        // Obtener info del turno
        const shiftInfo = await axios.get('/api/shift-now');
        updateShiftBanner(shiftInfo.data);
        
        // Cargar datos en tiempo real
        const response = await axios.get('/api/realtime');
        
        if (response.data.rows) {
            renderAOITable(response.data.rows);
            updateTotals(response.data.rows);
        }
    } catch (error) {
        console.error('❌ Error cargando datos AOI:', error);
    }
}

// Actualizar cada 30 segundos
setInterval(loadTurnoActual, 30000);
```

### Ejemplo de Uso - Día Completo
```javascript
// Cargar datos de un día específico
async function loadDiaCompleto(fecha) {
    try {
        const response = await axios.get('/api/day', {
            params: { date: fecha }
        });
        
        if (response.data.rows) {
            renderDayTable(response.data.rows);
            
            // Agrupar por turno para resumen
            const porTurno = agruparPorTurno(response.data.rows);
            renderTurnoSummary(porTurno);
        }
    } catch (error) {
        console.error('❌ Error cargando día:', error);
    }
}

// Función auxiliar para agrupar
function agruparPorTurno(rows) {
    const grupos = {
        'DIA': [],
        'TIEMPO_EXTRA': [],
        'NOCHE': []
    };
    
    rows.forEach(row => {
        if (grupos[row.turno]) {
            grupos[row.turno].push(row);
        }
    });
    
    return grupos;
}
```

### Renderizado de Tabla
```javascript
function renderAOITable(rows) {
    const tbody = document.getElementById('aoi-table-body');
    if (!tbody) return;
    
    tbody.innerHTML = rows.map(row => `
        <tr>
            <td>${row.linea}</td>
            <td>${row.modelo}</td>
            <td>${row.lado}</td>
            <td class="text-right">${row.cantidad.toLocaleString()}</td>
        </tr>
    `).join('');
    
    // Calcular totales
    const total = rows.reduce((sum, row) => sum + row.cantidad, 0);
    document.getElementById('total-piezas').textContent = total.toLocaleString();
}
```

## Procesamiento de Archivos AOI

### Loader de Archivos
El sistema incluye un loader que procesa archivos AOI automáticamente:

**Características:**
- Monitorea carpeta de archivos AOI
- Procesa archivos nuevos automáticamente
- Clasifica por turno según timestamp
- Calcula fecha de turno correcta
- Inserta en `aoi_file_log`

**Formato esperado de archivos:**
- Contienen información de línea, modelo, lado, cantidad
- Timestamp en nombre de archivo o contenido
- Formato específico del sistema AOI

## Consultas Útiles

### Producción por línea en turno actual
```sql
SELECT 
    CASE line_no WHEN 1 THEN 'A' WHEN 2 THEN 'B' WHEN 3 THEN 'C' END AS linea,
    SUM(piece_w) AS total
FROM aoi_file_log
WHERE shift_date = CURDATE() 
AND shift = 'DIA'
GROUP BY line_no;
```

### Producción total del día
```sql
SELECT 
    shift,
    SUM(piece_w) AS total_piezas
FROM aoi_file_log
WHERE shift_date = '2024-10-15'
GROUP BY shift
ORDER BY FIELD(shift, 'DIA', 'TIEMPO_EXTRA', 'NOCHE');
```

### Top modelos del mes
```sql
SELECT 
    model,
    SUM(piece_w) AS total_piezas,
    COUNT(DISTINCT shift_date) AS dias_producidos
FROM aoi_file_log
WHERE shift_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY model
ORDER BY total_piezas DESC
LIMIT 10;
```

## Timezone y Horarios

### Zona Horaria
El sistema usa la zona horaria de México (GMT-6):

```python
from app.auth_system import AuthSystem

now = AuthSystem.get_mexico_time()
```

### Consideraciones de Turno Nocturno
- El turno NOCHE cruza medianoche (22:50 - 07:30)
- Registros después de medianoche se asignan al día anterior
- Ejemplo: 2024-10-16 02:00 → shift_date = 2024-10-15

## Mejores Prácticas

### Actualización en Tiempo Real
1. Actualizar cada 30-60 segundos para datos en tiempo real
2. Usar polling en lugar de websockets (más simple)
3. Mostrar timestamp de última actualización

### Visualización
1. Usar colores diferentes por línea
2. Destacar línea con mayor producción
3. Mostrar gráficos de tendencia por turno
4. Incluir comparativa con turnos anteriores

### Performance
1. Agregar índices en `shift_date` y `shift`
2. Limitar consultas históricas a rangos razonables
3. Cachear datos de turnos completados

## Troubleshooting

### Datos no aparecen en tiempo real
- Verificar que archivos AOI se estén procesando
- Revisar clasificación de turno
- Verificar zona horaria del servidor

### Turno nocturno mal asignado
- Verificar lógica de `compute_shift_date`
- Confirmar que timestamps estén en zona horaria correcta
- Revisar registros con hora entre 00:00 y 07:30

### Líneas no se muestran correctamente
- Verificar mapeo de `line_no` a letra
- Confirmar que valores en BD sean 1, 2, 3
- Revisar ordenamiento en query

## Extensiones Futuras

1. **Dashboard en tiempo real:** Visualización gráfica de producción
2. **Alertas:** Notificaciones cuando producción baja de umbral
3. **Comparativas:** Comparar turnos y días
4. **Exportación:** Reportes en Excel/PDF
5. **Integración con MES:** Vincular con órdenes de trabajo
6. **Análisis de calidad:** Integrar datos de defectos AOI
