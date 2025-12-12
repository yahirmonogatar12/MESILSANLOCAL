# Reorganización de Estructura de Carpetas V3

**Fecha:** 2025-12-12  
**Estado:** ✅ Completado

## Resumen de Cambios

Se reorganizó la estructura de carpetas del proyecto para mejorar la organización y mantenibilidad del código.

## Estructura Anterior vs Nueva

### Antes (Archivos dispersos en `app/`)
```
app/
├── __init__.py
├── auth_system.py          # Auth disperso
├── user_admin.py           # Admin disperso
├── db.py                   # DB dispersa
├── db_mysql.py             # DB dispersa
├── config_mysql.py         # Config disperso
├── smt_csv_handler.py      # Utils disperso
├── models_po_wo.py         # REDUNDANTE
├── po_wo_models.py         # REDUNDANTE
├── register_blueprints.py  # REDUNDANTE
├── config_mysql_hybrid.py  # REDUNDANTE
├── mysql_http_client.py    # REDUNDANTE
└── ...
```

### Después (Organizado por responsabilidad)
```
app/
├── __init__.py
├── core/                    # 🆕 Autenticación y administración
│   ├── __init__.py
│   ├── auth_system.py      # Sistema de autenticación
│   └── user_admin.py       # Administración de usuarios
├── database/               # 🔄 Módulos de base de datos
│   ├── __init__.py
│   ├── config_mysql.py     # Configuración MySQL
│   ├── db_mysql.py         # Funciones MySQL
│   ├── db.py               # Inicialización DB
│   └── ISEMM_MES.db        # SQLite legacy
├── api/                    # APIs centralizadas
│   ├── __init__.py
│   ├── admin_api.py
│   ├── aoi_api.py
│   ├── bom_api.py
│   ├── inventario_api.py
│   ├── material_api.py
│   ├── plan_api.py
│   ├── po_wo_api.py
│   ├── raw_modelos_api.py
│   ├── smd_inventory_api.py
│   └── work_orders_api.py
├── routes/                 # Rutas de vistas
│   ├── __init__.py
│   ├── auth_routes.py
│   ├── bom_routes.py
│   ├── calidad_routes.py
│   ├── ict_routes.py
│   ├── materiales_routes.py
│   ├── metal_mask_routes.py
│   ├── mysql_routes.py
│   ├── plan_smd_routes.py
│   ├── produccion_routes.py
│   ├── smt_routes.py
│   ├── smt_routes_clean.py
│   ├── smt_routes_date_fixed.py
│   ├── utils.py
│   └── vistas_routes.py
├── services/               # Servicios de negocio
│   ├── bom_service.py
│   ├── inventario_service.py
│   ├── material_service.py
│   ├── plan_service.py
│   └── work_orders_service.py
├── utils/                  # 🔄 Utilidades
│   ├── __init__.py
│   ├── responses.py
│   ├── smt_csv_handler.py  # Movido desde raíz
│   ├── timezone.py
│   └── validators.py
└── py/                     # Scripts Python especiales
    ├── control_modelos_smt.py
    ├── print_service.py
    └── settings.py
```

## Archivos Eliminados (Redundantes)

| Archivo | Motivo de eliminación |
|---------|----------------------|
| `models_po_wo.py` | Modelo SQLAlchemy nunca utilizado |
| `po_wo_models.py` | Archivo corrupto/duplicado |
| `register_blueprints.py` | Funcionalidad ya existe en `__init__.py` |
| `config_mysql_hybrid.py` | No importado en ningún archivo |
| `mysql_http_client.py` | Solo usado por config_mysql_hybrid eliminado |

## Archivos Movidos

| Origen | Destino |
|--------|---------|
| `app/auth_system.py` | `app/core/auth_system.py` |
| `app/user_admin.py` | `app/core/user_admin.py` |
| `app/db.py` | `app/database/db.py` |
| `app/db_mysql.py` | `app/database/db_mysql.py` |
| `app/config_mysql.py` | `app/database/config_mysql.py` |
| `app/smt_csv_handler.py` | `app/utils/smt_csv_handler.py` |

## Cambios en Imports

### Patrón de Importación Actualizado

```python
# ANTES (imports desde raíz de app/)
from .db_mysql import execute_query
from .auth_system import AuthSystem
from .db import init_db

# DESPUÉS (imports desde subcarpetas)
from .database.db_mysql import execute_query
from .core.auth_system import AuthSystem
from .database.db import init_db
```

### Archivos Actualizados con Nuevos Imports

| Archivo | Import Actualizado |
|---------|-------------------|
| `app/__init__.py` | `database.db`, `core.auth_system`, `core.user_admin` |
| `app/routes/*.py` | `..database.db_mysql`, `..core.auth_system` |
| `app/services/*.py` | `..database.db_mysql` |
| `app/api/*.py` | `..database.db_mysql`, `..core.auth_system` |
| `app/py/control_modelos_smt.py` | `..database.config_mysql` |

## Nuevos Archivos `__init__.py`

### `app/core/__init__.py`
```python
"""
Core Module - Sistema de autenticación y administración
"""
from .auth_system import AuthSystem
from .user_admin import user_admin_bp

__all__ = ['AuthSystem', 'user_admin_bp']
```

### `app/database/__init__.py`
```python
"""
Database Module - Conexiones y operaciones de base de datos
"""
from .db_mysql import (
    execute_query,
    get_mysql_connection,
    get_connection,
    MYSQL_AVAILABLE
)
from .config_mysql import test_connection
from .db import init_db, get_db_connection as get_sqlite_connection

__all__ = [
    'execute_query',
    'get_mysql_connection', 
    'get_connection',
    'MYSQL_AVAILABLE',
    'test_connection',
    'init_db',
    'get_sqlite_connection'
]
```

## Verificación

El servidor arranca correctamente con todos los módulos:

```
📦 Registrando blueprints core...
  ✅ Admin blueprints
  ✅ API RAW (part_no)
  ✅ SMD Inventory routes
  ✅ SMT Routes Simple

📦 Registrando rutas modulares...
  ✅ Autenticación
  ✅ Materiales/Inventario
  ✅ Producción/Plan
  ✅ BOM
  ✅ SMT
  ✅ Calidad
  ✅ Metal Mask
  ✅ Vistas/Templates
  ✅ MySQL/Utilidades
  ✅ Plan SMD/Runs
  ✅ ICT/Defectos
📋 Total de módulos de rutas: 11

✅ Aplicación MES iniciada correctamente
```

## Beneficios de la Reorganización

1. **Separación de responsabilidades**: Cada carpeta tiene un propósito claro
2. **Facilidad de navegación**: Es más fácil encontrar archivos relacionados
3. **Mejor mantenibilidad**: Los cambios en un área no afectan a otras
4. **Imports más claros**: El path del import indica la función del módulo
5. **Menos archivos en raíz**: La carpeta `app/` está más limpia
