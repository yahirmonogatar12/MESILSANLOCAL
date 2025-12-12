# Documentación: Modularización de Routes

**Fecha:** 12 de Diciembre, 2025  
**Versión:** 1.0

## Resumen

Se realizó una refactorización completa del archivo monolítico `routes.py` (12,065 líneas) dividiéndolo en **11 módulos organizados por área funcional** usando Flask Blueprints.

## Estructura Anterior vs Nueva

### Antes
```
app/
├── routes.py          # 12,065 líneas - MONOLÍTICO
├── __init__.py        # Vacío
└── ...
```

### Después
```
app/
├── __init__.py              # Factory de aplicación (create_app)
├── routes_legacy.py         # Backup del routes.py original
├── routes/                  # NUEVO - Módulos organizados
│   ├── __init__.py          # Registro de blueprints
│   ├── utils.py             # Funciones compartidas
│   ├── auth_routes.py       # Autenticación
│   ├── vistas_routes.py     # Templates/Vistas HTML
│   ├── materiales_routes.py # Control de materiales
│   ├── bom_routes.py        # Bill of Materials
│   ├── produccion_routes.py # Plan de producción
│   ├── smt_routes.py        # Líneas SMT
│   ├── calidad_routes.py    # Control de calidad/AOI
│   ├── metal_mask_routes.py # Máscaras metálicas
│   ├── mysql_routes.py      # Visor MySQL
│   ├── plan_smd_routes.py   # Plan SMD y runs
│   └── ict_routes.py        # Historial ICT
└── ...
```

## Módulos Creados

| Archivo | Blueprint | Descripción | Rutas Principales |
|---------|-----------|-------------|-------------------|
| `auth_routes.py` | `auth_bp` | Autenticación y sesiones | `/login`, `/logout`, `/verificar_permiso_dropdown` |
| `vistas_routes.py` | `vistas_bp` | Templates HTML y vistas | `/`, `/inicio`, `/calendario`, `/dashboard`, `/listas/*` |
| `materiales_routes.py` | `materiales_bp` | Control de materiales e inventario | `/guardar_material`, `/listar_materiales`, `/importar_excel`, `/control_almacen` |
| `bom_routes.py` | `bom_bp` | Bill of Materials | `/importar_excel_bom`, `/listar_bom`, `/consultar_bom`, `/api/bom/update` |
| `produccion_routes.py` | `produccion_bp` | Plan de producción principal | `/api/plan`, `/api/plan/status`, `/api/raw/search` |
| `smt_routes.py` | `smt_modular` | Líneas SMT y CSV viewer | `/csv-viewer`, `/historial-cambio-material-smt`, `/api/csv_data` |
| `calidad_routes.py` | `calidad_bp` | Control de calidad y AOI | `/historial-aoi`, `/api/inventario_general`, `/api/aoi/historial` |
| `metal_mask_routes.py` | `metal_mask_bp` | Máscaras metálicas | `/control/metal-mask`, `/api/masks`, `/api/storage` |
| `mysql_routes.py` | `mysql_bp` | Visor MySQL | `/visor-mysql`, `/api/mysql/tables`, `/api/mysql/data` |
| `plan_smd_routes.py` | `plan_smd_bp` | Plan SMD y runs | `/api/plan-smd/list`, `/api/plan-run/start`, `/api/plan-run/end` |
| `ict_routes.py` | `ict_bp` | Historial ICT | `/historial-ict`, `/api/ict/data`, `/api/ict/defects` |

## Archivo utils.py

Contiene funciones compartidas por todos los módulos:

```python
# Decoradores
login_requerido(f)              # Verificar autenticación
requiere_permiso_dropdown(...)  # Verificar permisos específicos

# Utilidades
obtener_fecha_hora_mexico()     # Fecha/hora en zona México
tiene_permiso_boton(...)        # Verificar permiso de botón
cargar_usuarios()               # Cargar lista de usuarios
```

## Cambios en Archivos Existentes

### `app/__init__.py`
- Implementa patrón Factory con `create_app()`
- Inicializa base de datos y autenticación
- Registra todos los blueprints core y modulares
- Exporta `app` para compatibilidad con imports existentes

### `run.py`
- Ahora importa `app` desde `app/__init__.py`
- Registra blueprints adicionales (AOI, APIs v2, etc.)
- Mantiene compatibilidad con el flujo de inicio anterior

## Cómo Usar

### Importar la aplicación
```python
# Forma recomendada
from app import app

# O usando el factory
from app import create_app
app = create_app()
```

### Agregar nuevas rutas
1. Crear archivo en `app/routes/` (ej: `mi_modulo_routes.py`)
2. Definir el blueprint:
```python
from flask import Blueprint
mi_bp = Blueprint('mi_modulo', __name__)

@mi_bp.route('/mi-ruta')
def mi_ruta():
    return "OK"
```
3. Registrar en `app/routes/__init__.py`:
```python
from .mi_modulo_routes import mi_bp
# Agregar a blueprints list en register_all_routes()
```

## Archivos de Respaldo

- `app/routes_legacy.py` - Copia completa del routes.py original (12,065 líneas)
  - Mantener como referencia hasta validar que todo funciona
  - Puede eliminarse después de pruebas exhaustivas

## Beneficios de la Modularización

1. **Mantenibilidad**: Código organizado por funcionalidad
2. **Escalabilidad**: Fácil agregar nuevos módulos
3. **Colaboración**: Múltiples desarrolladores pueden trabajar en paralelo
4. **Testing**: Más fácil probar módulos individuales
5. **Depuración**: Errores más fáciles de localizar
6. **Rendimiento**: Imports más eficientes

## Blueprints Registrados (Total: 16)

Al iniciar la aplicación se registran:

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
```

## Cambios en Templates

Al usar Blueprints, las referencias `url_for()` en templates deben incluir el prefijo del blueprint:

| Antes (routes.py) | Después (Blueprints) |
|-------------------|---------------------|
| `url_for('login')` | `url_for('auth.login')` |
| `url_for('logout')` | `url_for('auth.logout')` |
| `url_for('index')` | `url_for('vistas.index')` |
| `url_for('dashboard')` | `url_for('vistas.dashboard')` |

### Templates Actualizados
- `app/templates/landing.html` - Actualizado `url_for('login')` → `url_for('auth.login')`

## Notas Técnicas

- Los imports de `db_mysql.py` usan `get_connection()` (no `get_mysql_connection()`)
- El blueprint SMT se renombró a `smt_modular` para evitar conflicto con `smt_routes_date_fixed`
- Las funciones `agregar_control_material_almacen` y `obtener_control_material_almacen` están en `db.py`, no en `db_mysql.py`
- Las funciones `insertar_bom_desde_dataframe` y `listar_bom_por_modelo` están en `db_mysql.py`

## Verificación Post-Migración

✅ **Checklist completado:**
- [x] App importa correctamente con 16 blueprints
- [x] Servidor Flask inicia sin errores
- [x] Conexión a MySQL Seenode funciona
- [x] Tablas de base de datos creadas/verificadas
- [x] Endpoint `/login` responde correctamente
- [x] Templates renderizados sin errores de `url_for`
- [x] Archivo `routes_legacy.py` guardado como respaldo

## Comandos Útiles

```powershell
# Verificar que la app carga correctamente
python -c "from app import app; print(f'Blueprints: {len(app.blueprints)}')"

# Iniciar servidor de desarrollo
python run.py

# Listar todas las rutas registradas
python -c "from app import app; print([r.rule for r in app.url_map.iter_rules()])"
```

---

**Autor:** Sistema MES ILSAN  
**Última actualización:** 12/12/2025
