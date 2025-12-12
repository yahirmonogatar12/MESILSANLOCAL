# Documentación: Modularización de Routes V2

**Fecha:** 12 de Diciembre, 2025  
**Versión:** 2.0  
**Estado:** ✅ Completado con correcciones de templates

---

## Resumen Ejecutivo

Se realizó una refactorización completa del archivo monolítico `routes.py` (12,065 líneas) dividiéndolo en **11 módulos organizados por área funcional** usando Flask Blueprints. Esta versión incluye **correcciones críticas de nombres de templates** que causaban errores en el sidebar.

---

## Problema Resuelto en V2

### Error Original
```
Error al cargar el contenido. Por favor, intente nuevamente.
```

### Causa
Los nombres de templates en `vistas_routes.py` **no coincidían** con los archivos reales en el sistema de archivos.

### Solución
Actualización de todos los nombres de templates para que coincidan exactamente con los archivos existentes.

---

## Estructura del Proyecto

### Antes (Monolítico)
```
app/
├── routes.py          # 12,065 líneas - MONOLÍTICO
├── __init__.py        # Vacío
└── ...
```

### Después (Modular)
```
app/
├── __init__.py              # Factory de aplicación (create_app)
├── routes_legacy.py         # Backup del routes.py original
├── routes/                  # NUEVO - Módulos organizados
│   ├── __init__.py          # Registro de blueprints
│   ├── utils.py             # Funciones compartidas
│   ├── auth_routes.py       # Autenticación
│   ├── vistas_routes.py     # Templates/Vistas HTML (CORREGIDO V2)
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

---

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

---

## 🔧 Correcciones V2: Templates de Listas

### Mapeo Corregido de Templates LISTAS

| Ruta | ❌ Template Original | ✅ Template Corregido |
|------|---------------------|----------------------|
| `/listas/informacion_basica` | `LISTAS/informacion_basica.html` | `LISTAS/LISTA_INFORMACIONBASICA.html` |
| `/listas/control_material` | `LISTAS/control_material.html` | `LISTAS/LISTA_DE_MATERIALES.html` |
| `/listas/control_produccion` | `LISTAS/control_produccion.html` | `LISTAS/LISTA_CONTROLDEPRODUCCION.html` |
| `/listas/control_proceso` | `LISTAS/control_proceso.html` | `LISTAS/LISTA_CONTROL_DE_PROCESO.html` |
| `/listas/control_calidad` | `LISTAS/control_calidad.html` | `LISTAS/LISTA_CONTROL_DE_CALIDAD.html` |
| `/listas/control_resultados` | `LISTAS/control_resultados.html` | `LISTAS/LISTA_DE_CONTROL_DE_RESULTADOS.html` |
| `/listas/control_reporte` | `LISTAS/control_reporte.html` | `LISTAS/LISTA_DE_CONTROL_DE_REPORTE.html` |
| `/listas/configuracion_programa` | `LISTAS/configuracion_programa.html` | `LISTAS/LISTA_DE_CONFIGPG.html` |

---

## 🔧 Correcciones V2: Templates de Material

### Mapeo Corregido de Templates MATERIAL

| Ruta | ❌ Template Original | ✅ Template Corregido |
|------|---------------------|----------------------|
| `/material/info` | `Control de material/Material info.html` | `info.html` |
| `/material/control_almacen` | `Control de material/Control de almacen.html` | `Control de material/Control de material de almacen.html` |
| `/material/historial_inventario` | `Control de material/Historial inventario.html` | `Control de material/Historial de inventario real.html` |
| `/material/registro_material` | `Control de material/Registro de material.html` | `Control de material/Registro de material real.html` |
| `/material/control_retorno` | `Control de material/Control de retorno.html` | `Control de material/Control de material de retorno.html` |
| `/material/recibo_pago` | `Control de material/Recibo de pago.html` | `Control de material/Recibo y pago del material.html` |
| `/material/longterm_inventory` | `Control de material/Longterm inventory.html` | `Control de material/Control de Long-Term Inventory.html` |
| `/material/ajuste_numero` | `Control de material/Ajuste numero de parte.html` | `Control de material/Ajuste de número de parte.html` |

---

## 🔧 Correcciones V2: Templates de Información Básica

| Ruta | ❌ Template Original | ✅ Template Corregido |
|------|---------------------|----------------------|
| `/informacion_basica/control_de_material` | `INFORMACION BASICA/Control de material.html` | `INFORMACION BASICA/CONTROL_DE_MATERIAL.html` |
| `/informacion_basica/control_de_bom` | `INFORMACION BASICA/Control de bom.html` | `INFORMACION BASICA/CONTROL_DE_BOM.html` |

---

## Archivos de Templates Reales

### Carpeta: `app/templates/LISTAS/`
```
LISTA_CONTROLDEPRODUCCION.html
LISTA_CONTROL_DE_CALIDAD.html
LISTA_CONTROL_DE_PROCESO.html
LISTA_DE_CONFIGPG.html
LISTA_DE_CONTROL_DE_REPORTE.html
LISTA_DE_CONTROL_DE_RESULTADOS.html
LISTA_DE_MATERIALES.html
LISTA_INFORMACIONBASICA.html
menu_sidebar.html
```

### Carpeta: `app/templates/Control de material/`
```
Control de material de almacen.html
Control de material de retorno.html
Control de salida.html
Estatus de material.html
Historial de inventario real.html
Registro de material real.html
... (y más archivos _ajax.html)
```

### Carpeta: `app/templates/INFORMACION BASICA/`
```
CONTROL_DE_BOM.html
CONTROL_DE_MATERIAL.html
Control_modelos_SMT.html
MODELOS.html
... (y más archivos _ajax.html)
```

---

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

---

## Cambios en Templates (url_for)

Al usar Blueprints, las referencias `url_for()` en templates deben incluir el prefijo del blueprint:

| Antes (routes.py) | Después (Blueprints) |
|-------------------|---------------------|
| `url_for('login')` | `url_for('auth.login')` |
| `url_for('logout')` | `url_for('auth.logout')` |
| `url_for('index')` | `url_for('vistas.index')` |
| `url_for('dashboard')` | `url_for('vistas.dashboard')` |

### Templates Actualizados
- `app/templates/landing.html` - Actualizado `url_for('login')` → `url_for('auth.login')`

---

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
📋 Total de módulos de rutas: 11
```

---

## Notas Técnicas Importantes

1. **Imports de db_mysql.py**: Usar `get_connection()` (no `get_mysql_connection()`)
2. **Blueprint SMT**: Renombrado a `smt_modular` para evitar conflicto con `smt_routes_date_fixed`
3. **Funciones en db.py**: 
   - `agregar_control_material_almacen`
   - `obtener_control_material_almacen`
4. **Funciones en db_mysql.py**:
   - `insertar_bom_desde_dataframe`
   - `listar_bom_por_modelo`

---

## Verificación Post-Migración V2

✅ **Checklist completado:**
- [x] App importa correctamente con 16 blueprints
- [x] Servidor Flask inicia sin errores
- [x] Conexión a MySQL Seenode funciona
- [x] Tablas de base de datos creadas/verificadas
- [x] Endpoint `/login` responde correctamente
- [x] Templates renderizados sin errores de `url_for`
- [x] Archivo `routes_legacy.py` guardado como respaldo
- [x] **Templates de LISTAS corregidos** (V2)
- [x] **Templates de MATERIAL corregidos** (V2)
- [x] **Templates de INFORMACIÓN BÁSICA corregidos** (V2)
- [x] **Sidebar carga correctamente** (V2)

---

## Archivos de Respaldo

- `app/routes_legacy.py` - Copia completa del routes.py original (12,065 líneas)
  - Mantener como referencia hasta validar que todo funciona
  - Puede eliminarse después de pruebas exhaustivas

---

## Beneficios de la Modularización

1. **Mantenibilidad**: Código organizado por funcionalidad
2. **Escalabilidad**: Fácil agregar nuevos módulos
3. **Colaboración**: Múltiples desarrolladores pueden trabajar en paralelo
4. **Testing**: Más fácil probar módulos individuales
5. **Depuración**: Errores más fáciles de localizar
6. **Rendimiento**: Imports más eficientes

---

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

## Historial de Versiones

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 12/12/2025 | Modularización inicial de routes.py |
| 2.0 | 12/12/2025 | Corrección de nombres de templates (LISTAS, MATERIAL, INFO BÁSICA) |

---

**Autor:** Sistema MES ILSAN  
**Última actualización:** 12/12/2025 - V2.0
