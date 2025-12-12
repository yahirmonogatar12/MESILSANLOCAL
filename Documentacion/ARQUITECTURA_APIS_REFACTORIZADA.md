# Arquitectura de APIs Refactorizada - Sistema MES

## Resumen de la Refactorización

Este documento describe la nueva arquitectura modular implementada para el sistema MES de ILSAN Electronics.

## Estructura de Directorios

```
app/
├── __init__.py              # Inicialización de la app Flask
├── routes.py                # Rutas legacy (se mantiene por compatibilidad)
│
├── api/                     # APIs modulares v2
│   ├── __init__.py
│   ├── register_blueprints.py  # Registro centralizado de blueprints
│   ├── plan_api.py         # API de planes de producción
│   ├── material_api.py     # API de materiales
│   ├── bom_api.py          # API de BOM (Bill of Materials)
│   ├── inventario_api.py   # API de inventario consolidado ⭐ NUEVO
│   └── work_orders_api.py  # API de órdenes de trabajo ⭐ NUEVO
│
├── services/               # Capa de lógica de negocio
│   ├── __init__.py
│   ├── plan_service.py     # Servicio de planes
│   ├── material_service.py # Servicio de materiales
│   ├── bom_service.py      # Servicio de BOM
│   ├── inventario_service.py   # Servicio de inventario ⭐ NUEVO
│   └── work_orders_service.py  # Servicio de work orders ⭐ NUEVO
│
├── utils/                  # Utilidades compartidas
│   ├── __init__.py
│   ├── responses.py        # Respuestas JSON estandarizadas
│   ├── timezone.py         # Manejo de zona horaria México
│   └── validators.py       # Validaciones de entrada
│
├── admin_api.py            # API de administración (legacy)
├── aoi_api.py              # API de AOI (legacy)
├── api_po_wo.py            # API de PO/WO (legacy)
├── api_raw_modelos.py      # API de modelos RAW (legacy)
├── smd_inventory_api.py    # API de inventario SMD (legacy)
├── smt_routes*.py          # Rutas SMT (legacy)
└── user_admin.py           # API de usuarios (legacy)
```

## Respuestas JSON Estandarizadas

### Formato de Respuesta Exitosa
```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "Operación exitosa",
  "data": { ... },
  "meta": {
    "timestamp": "2024-01-15T10:30:00-06:00"
  }
}
```

### Formato de Respuesta de Error
```json
{
  "success": false,
  "code": "ERROR",
  "message": "Descripción del error",
  "errors": ["Detalle 1", "Detalle 2"],
  "meta": {
    "timestamp": "2024-01-15T10:30:00-06:00"
  }
}
```

## APIs v2 (Nuevas)

### Plan API (`/api/v2/plan`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v2/plan` | Listar planes |
| POST | `/api/v2/plan` | Crear plan |
| GET | `/api/v2/plan/<lot_no>` | Obtener plan |
| PUT/PATCH | `/api/v2/plan/<lot_no>` | Actualizar plan |
| DELETE | `/api/v2/plan/<lot_no>` | Eliminar plan |
| POST | `/api/v2/plan/<lot_no>/status` | Cambiar estado |
| GET | `/api/v2/plan/lines-summary` | Resumen por línea |
| GET | `/api/v2/raw/search` | Buscar en RAW |

### Material API (`/api/v2/materials`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v2/materials` | Listar materiales |
| POST | `/api/v2/materials` | Crear material |
| GET | `/api/v2/materials/<codigo>` | Obtener material |
| PUT/PATCH | `/api/v2/materials/<codigo>` | Actualizar material |
| POST | `/api/v2/materials/<codigo>/stock` | Actualizar stock |
| GET | `/api/v2/materials/summary` | Resumen inventario |
| GET | `/api/v2/materials/low-stock` | Stock bajo |
| GET | `/api/v2/materials/movements` | Historial movimientos |

### BOM API (`/api/v2/bom`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v2/bom/models` | Listar modelos |
| GET | `/api/v2/bom/<model_code>` | Obtener BOM |
| POST | `/api/v2/bom/<model_code>/items` | Agregar item |
| PUT/PATCH | `/api/v2/bom/items/<id>` | Actualizar item |
| DELETE | `/api/v2/bom/items/<id>` | Eliminar item |
| POST | `/api/v2/bom/<model_code>/import` | Importar BOM |
| GET | `/api/v2/bom/<model_code>/requirements` | Calcular requerimientos |
| GET | `/api/v2/bom/search` | Buscar componente |

### Inventario API (`/api/v2/inventario`) ⭐ NUEVO

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v2/inventario/health` | Health check |
| POST | `/api/v2/inventario/consultar` | Consultar inventario con filtros |
| GET | `/api/v2/inventario/detalle/<np>` | Detalle por número de parte |
| GET | `/api/v2/inventario/historial` | Historial de movimientos |
| POST | `/api/v2/inventario/ajuste` | Registrar ajuste de inventario |
| GET | `/api/v2/inventario/resumen` | Resumen general |
| GET | `/api/v2/inventario/buscar?q=` | Búsqueda rápida |

### Work Orders API (`/api/v2/work-orders`) ⭐ NUEVO

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v2/work-orders/health` | Health check |
| GET | `/api/v2/work-orders` | Listar work orders |
| GET | `/api/v2/work-orders/<wo>` | Detalle de work order |
| POST | `/api/v2/work-orders` | Crear work order |
| PUT | `/api/v2/work-orders/<wo>/estado` | Actualizar estado |
| POST | `/api/v2/work-orders/<wo>/importar` | Importar a plan |
| GET | `/api/v2/work-orders/estadisticas` | Estadísticas generales |
| GET | `/api/v2/work-orders/buscar?q=` | Búsqueda rápida |
| GET | `/api/v2/work-orders/pendientes` | Listar pendientes |
| GET | `/api/v2/work-orders/no-importados` | Listar no importados |

## Capa de Servicios

Los servicios encapsulan la lógica de negocio, separándola de los endpoints:

### PlanService

```python
from app.services import PlanService

# Crear plan
success, result = PlanService.create_plan({
    'working_date': '2024-01-15',
    'part_no': 'ABC123',
    'line': 'L1',
    'plan_count': 100
})

# Listar planes
plans, error = PlanService.list_plans(
    start_date='2024-01-01',
    end_date='2024-01-31',
    line='L1'
)

# Cambiar estado
success, result = PlanService.change_status('LOT-001', 'EN PROGRESO')
```

### MaterialService

```python
from app.services import MaterialService

# Obtener materiales
materials, total, error = MaterialService.get_materials(
    search='resistor',
    category='SMD'
)

# Actualizar stock
success, result = MaterialService.update_stock(
    codigo='RES-001',
    cantidad=100,
    tipo='ENTRADA',
    usuario='admin'
)
```

### BomService

```python
from app.services import BomService

# Obtener BOM
items, error = BomService.get_bom_by_model('MODEL-001')

# Calcular requerimientos
requirements, error = BomService.calculate_material_requirements(
    'MODEL-001', 
    quantity=1000
)
```

## Validaciones

Usando la clase `Validator`:

```python
from app.utils import Validator

data = request.get_json()

validator = Validator(data)
validator.required('part_no', 'quantity')
validator.positive_int('quantity', required=True)
validator.date('working_date', required=True)

if not validator.is_valid():
    return ApiResponse.validation_error(
        validator.get_first_error(),
        errors=validator.get_errors()
    )
```

## Zona Horaria

```python
from app.utils import get_mexico_time, classify_shift

# Obtener hora de México
now = get_mexico_time()

# Clasificar turno
turno = classify_shift(now)  # 'DIA', 'NOCHE', o 'TIEMPO EXTRA'
```

## Migración de APIs Legacy

Las APIs legacy (`/api/plan`, `/api/bom/*`) siguen funcionando.
Las nuevas APIs v2 (`/api/v2/*`) ofrecen:

- Respuestas JSON estandarizadas
- Mejor manejo de errores
- Validación de entrada mejorada
- Separación de lógica de negocio

### Ejemplo de Migración

**Antes (legacy):**
```javascript
fetch('/api/plan', {
    method: 'POST',
    body: JSON.stringify(data)
})
.then(r => r.json())
.then(data => {
    if (data.error) { /* error */ }
    else { /* success */ }
});
```

**Después (v2):**
```javascript
fetch('/api/v2/plan', {
    method: 'POST',
    body: JSON.stringify(data)
})
.then(r => r.json())
.then(response => {
    if (response.success) {
        // response.data contiene los datos
        // response.message contiene mensaje
    } else {
        // response.message contiene error
        // response.errors contiene detalles
    }
});
```

## Registro de Blueprints

Para registrar todas las APIs en la aplicación:

```python
from app.register_blueprints import register_all

app = Flask(__name__)
register_all(app)
```

O registro selectivo:

```python
from app.register_blueprints import register_api_blueprints

register_api_blueprints(app)
```

## Próximos Pasos

1. ✅ Crear estructura de utils (responses, timezone, validators)
2. ✅ Crear capa de servicios (plan, material, bom)
3. ✅ Crear APIs modulares v2 (plan, material, bom)
4. ✅ Agregar API de inventario v2
5. ✅ Agregar API de work orders v2
6. ⏳ Crear API de autenticación v2
7. ⏳ Migrar gradualmente rutas legacy a v2
8. ⏳ Actualizar frontend para usar v2
9. ⏳ Documentar con OpenAPI/Swagger

## Resumen de APIs v2 Disponibles

| API | URL Base | Estado |
|-----|----------|--------|
| Plan | `/api/v2/plan` | ✅ Activa |
| Materials | `/api/v2/materials` | ✅ Activa |
| BOM | `/api/v2/bom` | ✅ Activa |
| Inventario | `/api/v2/inventario` | ✅ Activa |
| Work Orders | `/api/v2/work-orders` | ✅ Activa |
| Auth | `/api/v2/auth` | ⏳ Pendiente |
