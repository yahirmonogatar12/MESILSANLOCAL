# WF_003 — Integración de API Backend + JS Frontend para Nuevos Templates

> **Versión:** 2.2
> **Fecha:** 2026-05-28 (v2.2 — refactor de `routes.py` + auth blueprint)
> **Prerequisitos:** [WF_001](./WF_001_Nuevos_Modulos_AJAX_Templates.md), [WF_002](./WF_002_Crear_Template_Completo.md)
> **Ejemplo de referencia:** Módulo "Historial ICT % Pass/Fail" con API `/api/ict/pass-fail`

---

## Resumen

Este documento cubre el proceso de crear los **endpoints de API en Flask** y la **lógica JS del frontend** que conectan un template HTML a la base de datos. Es el complemento de WF_002, que cubre la estructura visual (HTML/CSS) y el registro en la app.

> **Cambio v2.1 (2026-05-22):** El backend completo de cada módulo nuevo debe vivir bajo su paquete Blueprint en `app/api/`. No basta con mover los endpoints: también se quedan ahí sus rutas de template, permisos, serialización, exportación y lógica de datos propia. Ver sección [Arquitectura del paquete app/api/](#arquitectura-del-paquete-appapi).

> **Cambio v2.2 (2026-05-28):** `app/routes.py` quedó reducido a núcleo
> transversal tras las fases 1-6 del plan de refactorización. Auth/sesión vive
> en `app/api/auth/sesion.py`; los módulos migrados se registran desde
> `_MODULOS_REGISTRADOS`; `routes.py` no debe volver a crecer con backend de
> módulos.

---

## Arquitectura del paquete `app/api/`

Cada sección del navbar tiene su propia carpeta dentro de `app/api/`, y cada módulo es un archivo Python con su propio Flask **Blueprint**:

```
app/api/
├── __init__.py                 ← registrar_blueprints_api(app) [orquestador]
├── auth/
│   └── sesion.py               ← /, /inicio, /login, /logout, /api/mi-perfil
├── admin/                      ← permisos y usuarios
├── shared/
│   └── __init__.py             ← execute_query + re-exports lazy core
├── informacion_basica/         ← LISTA_INFORMACIONBASICA
│   ├── __init__.py
│   ├── raw_modelos.py
│   ├── po_wo.py
│   └── ...
├── control_material/           ← LISTA_DE_MATERIALES
│   ├── __init__.py
│   ├── material_admin.py
│   └── ...
├── control_produccion/         ← LISTA_CONTROLDEPRODUCCION
│   └── ...
├── control_proceso/            ← LISTA_CONTROL_DE_PROCESO
│   └── ...
├── control_calidad/            ← LISTA_CONTROL_DE_CALIDAD
│   ├── aoi.py
│   └── ...
├── control_resultados/         ← LISTA_DE_CONTROL_DE_RESULTADOS
│   └── ...
├── control_reporte/            ← LISTA_DE_CONTROL_DE_REPORTE
│   └── ...
├── configuracion/              ← LISTA_DE_CONFIGPG
│   └── ...
├── portal/                     ← tickets / integraciones portal
└── pda/                        ← APIs móviles PDA
```

**Reglas duras:**

1. **Cada archivo expone un atributo `bp`** (Flask Blueprint).
2. **El nombre del archivo coincide con el módulo** (snake_case del template, no del listing).
3. **Se importan helpers transversales desde `app.api.shared`**:
   ```python
   from app.api.shared import login_requerido, execute_query, auth_system
   ```
   `login_requerido` y `auth_system` se resuelven de forma lazy desde
   `app.routes` para evitar ciclos de import. `obtener_fecha_hora_mexico` vive
   en `app/api/shared/datetime_helpers.py` y también se expone desde
   `app.api.shared`. Helpers privados de otro módulo no se re-exportan aquí:
   impórtalos desde su dueño.
4. **Para registrar el blueprint**, se agrega su ruta a `_MODULOS_REGISTRADOS` en `app/api/__init__.py`:
   ```python
   _MODULOS_REGISTRADOS = [
       "auth.sesion",
       "control_material.material_admin",
       "control_calidad.aoi",
       "mi_seccion.mi_modulo",  # ← agregar aqui
   ]
   ```
   `app_factory.py` se encarga de llamar `registrar_blueprints_api(app)` y todo queda registrado.
5. **Todo backend propio del módulo vive en el paquete Blueprint** dentro de `app/api/<seccion>/`.
6. **`app/routes.py`, `app/db_mysql.py` y archivos `*_api.py` sueltos no son destino para backend nuevo de un módulo.** Solo permanecen como infraestructura compartida o legado pendiente de migrar. Tras la Fase 6, `routes.py` conserva el core transversal, LISTAS actuales, health, dashboard/material y pocos renders legacy.

### Frontera obligatoria del backend del módulo

Para módulos nuevos o para una migración que ya se está tocando, el backend debe quedar localizado por sección:

| Debe vivir junto al Blueprint | Ejemplos |
|---|---|
| Rutas HTML/AJAX del template | `@bp.route("/mi-modulo")` con `render_template(...)` |
| APIs JSON y exportaciones | `GET /api/...`, `POST /api/...`, `.xlsx` |
| Permisos y validaciones HTTP | decoradores, lectura de `session`, respuestas `403/400` |
| Serializadores y adaptadores de respuesta | fechas, shape legacy del frontend, metadatos |
| SQL/CRUD/lógica de negocio propia | helpers de consulta, servicios y publicación del módulo |

El archivo que expone `bp` es la puerta HTTP. Si la lógica crece, se divide en módulos hermanos dentro de la misma sección, por ejemplo:

```
app/api/informacion_basica/
├── control_bom.py          # Blueprint, rutas, permisos HTTP
└── control_bom_data.py     # consultas, ECO/KS, serialización de datos propia
```

No se debe dejar una ruta en el Blueprint y mover su SQL o CRUD a `db_mysql.py` solo para reducir el tamaño del archivo. `db_mysql.py` puede seguir exponiendo conexión, inicialización general o legado compartido mientras se migra, pero no debe recibir backend nuevo específico de un módulo.

**Por qué importa:**

- Cualquiera puede encontrar el código de un módulo siguiendo la misma estructura que ya conoce de `app/templates/`.
- No hay que tocar `routes.py` para agregar un endpoint nuevo; el archivo ya fue
  refactorizado y no debe volver a absorber backend de módulos.
- Cada módulo es un archivo aislado: si se rompe, solo se rompe ese.
- Blueprints permiten desregistrar y testear módulos individualmente.

---

## Archivos que se Crean / Modifican

| Acción | Archivo | Descripción |
|--------|---------|-------------|
| ✨ CREAR | `app/api/<seccion>/<modulo>.py` | Blueprint con endpoint(s) API (JSON / Excel) |
| ✨ CREAR opcional | `app/api/<seccion>/<modulo>_data.py` o `_<servicio>.py` | Lógica de datos propia si no cabe limpiamente en el archivo del Blueprint |
| ✏️ MODIFICAR | `app/api/__init__.py` | Agregar `"<seccion>.<modulo>"` a `_MODULOS_REGISTRADOS` |
| ✏️ MODIFICAR | `app/static/js/<nombre>.js` | Lógica de carga, render y exportación |
| — REFERENCIA | `app/api/shared/__init__.py` | Expone `execute_query` y re-exports lazy de helpers core |
| — REFERENCIA | `app/config_mysql.py` | Implementación real de `execute_query()` (pool de conexiones + fail-loud) |

---

## Paso 1 — Diseñar la Query SQL

Antes de escribir código, definir la query que alimentará la tabla.

### 1a. Identificar la tabla de origen y columnas relevantes

Ejemplo con `history_ict`:

```
┌─────────────────────────────────────────────────────────┐
│ history_ict                                             │
├──────────┬──────┬──────┬───────────┬──────────┬─────────┤
│ fecha    │ linea│ ict  │ no_parte  │ resultado│ barcode │
│ (date)   │ (str)│ (int)│ (str)     │ OK/NG    │ (str)   │
└──────────┴──────┴──────┴───────────┴──────────┴─────────┘
```

### 1b. Definir la agrupación y cálculos

Para conteo distintivo por no_parte:

```sql
SELECT fecha, linea, ict, no_parte,
       COUNT(DISTINCT CASE WHEN resultado='OK' THEN barcode END) AS ok_count,
       COUNT(DISTINCT CASE WHEN resultado='NG' THEN barcode END) AS ng_count,
       COUNT(DISTINCT barcode) AS total
FROM history_ict
WHERE 1=1         -- base para concatenar filtros dinámicos
GROUP BY fecha, linea, ict, no_parte
ORDER BY fecha DESC, linea, ict, no_parte
LIMIT 2000
```

### 1c. Mapear columnas SQL → columnas de la tabla HTML

| Columna SQL | Campo JSON | Columna HTML |
|-------------|------------|--------------|
| `fecha` | `fecha` | Fecha |
| `linea` | `linea` | Línea |
| `ict` | `ict` | ICT |
| `no_parte` | `no_parte` | No. Parte |
| `ok_count` | `ok_count` | OK |
| `ng_count` | `ng_count` | NG |
| *(calculado)* | `pct_ok` | %OK |
| *(calculado)* | `pct_ng` | %NG |
| `total` | `total` | Total |

---

## Paso 2 — Crear el Blueprint con el Endpoint API de Datos

**Archivo:** `app/api/<seccion>/<modulo>.py`

> **v2.1:** El backend nuevo NO va más a `routes.py` ni a `db_mysql.py` por conveniencia. Cada módulo queda bajo su Blueprint y sus módulos hermanos dentro de la sección que corresponde.

La ruta que renderiza el template AJAX también pertenece al mismo Blueprint:

```python
from flask import Blueprint, render_template

from app.api.shared import login_requerido


bp = Blueprint("mi_modulo", __name__)


@bp.route("/mi-modulo")
@login_requerido
def mi_modulo_template():
    return render_template("MI_SECCION/mi_modulo.html")
```

### Estructura base:

```python
"""Endpoints HTTP del modulo <Nombre>.

Rutas:
  GET /api/<modulo>/<accion>         -> JSON
  GET /api/<modulo>/<accion>/export  -> XLSX
"""

import logging
import traceback

from flask import Blueprint, jsonify, request

from app.api.shared import execute_query, login_requerido

logger = logging.getLogger(__name__)

bp = Blueprint("mi_modulo", __name__)


@bp.route("/api/<modulo>/<accion>")
@login_requerido
def mi_api():
    """Descripcion del endpoint."""
    try:
        # 1. Leer filtros desde query params
        fecha    = request.args.get("fecha", "").strip()
        linea    = request.args.get("linea", "").strip()
        no_parte = request.args.get("no_parte", "").strip()

        # 2. Construir query con filtros dinamicos
        sql = (
            "SELECT ... "
            "FROM <tabla> WHERE 1=1"
        )
        params = []

        if fecha:
            sql += " AND fecha=%s"
            params.append(fecha)
        if linea:
            sql += " AND linea=%s"
            params.append(linea)
        if no_parte:
            sql += " AND no_parte LIKE %s"
            params.append(f"%{no_parte}%")

        sql += " GROUP BY ... ORDER BY ... LIMIT 2000"

        # 3. Ejecutar query
        rows = execute_query(sql, tuple(params) if params else None, fetch="all") or []

        # 4. Formatear resultado como lista de dicts
        result = []
        for row in rows:
            total = row.get("total", 0) or 0
            ok = row.get("ok_count", 0) or 0
            pct_ok = round(ok / total * 100, 2) if total > 0 else 0

            result.append({
                "fecha": str(row.get("fecha", "")) if row.get("fecha") else "",
                "linea": row.get("linea", "") or "",
                "pct_ok": pct_ok,
                "total": total,
            })

        # 5. Retornar JSON
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500
```

### Registrar el blueprint

Despues de crear el archivo, **agregar su ruta** a `app/api/__init__.py`:

```python
_MODULOS_REGISTRADOS = [
    "control_material.material_admin",
    "control_calidad.aoi",
    "<seccion>.<modulo>",  # ← tu nuevo modulo
]
```

`app_factory.py` ya llama `registrar_blueprints_api(app)` al arrancar; el módulo nuevo queda registrado sin tocar nada más.

### Reglas importantes:

| Regla | Detalle |
|-------|---------|
| **Siempre usar `execute_query()`** | No crear conexiones manuales; usar la función centralizada (`config_mysql.py`, re-exportada por `app.api.shared`). Hace _fail-loud_: si la query falla re-lanza, no devuelve `[]` |
| **Filtros con `WHERE 1=1`** | Permite concatenar `AND` dinámicos sin lógica condicional extra |
| **Campos `date`/`datetime` → `str()`** | Los tipos `date` de Python no son serializables por `jsonify` |
| **Valores `None` → valor por defecto** | Usar `row.get("campo", "") or ""` para evitar `null` en JSON |
| **LIKE para búsqueda parcial** | `%s` con `f"%{valor}%"` para campos de texto como `no_parte` |
| **`=` para filtros exactos** | Para campos como `fecha`, `linea` que deben ser exactos |
| **`LIMIT`** | Siempre incluir un límite para evitar queries gigantes |

---

## Paso 3 — Crear el Endpoint de Exportación Excel

**Misma ubicación** que el endpoint de datos: dentro del mismo Blueprint (mismo archivo `app/api/<seccion>/<modulo>.py`), justo después del endpoint JSON.

### Estructura base:

```python
@bp.route("/api/<modulo>/<accion>/export")
@login_requerido
def mi_api_export():
    """Exportar datos a Excel."""
    try:
        # 1. Mismos filtros y query que el endpoint de datos
        #    (copiar la lógica de filtros)
        # ...
        sql += " LIMIT 5000"  # Límite mayor para exportación
        rows = execute_query(sql, tuple(params) if params else None, fetch="all") or []

        # 2. Crear workbook
        from io import BytesIO
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill

        wb = Workbook()
        ws = wb.active
        ws.title = "Nombre del Reporte"

        # 3. Encabezados con estilo ILSAN
        headers = ["Fecha", "Línea", "ICT", "No. Parte", "OK", "NG", "%OK", "%NG", "Total"]
        header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)

        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        # 4. Filas de datos
        for row_idx, row in enumerate(rows, 2):
            ws.cell(row=row_idx, column=1, value=str(row.get("fecha", "")))
            # ... más columnas

        # 5. Anchos de columna
        col_widths = [12, 8, 8, 20, 8, 8, 8, 8, 8]
        for col_idx, width in enumerate(col_widths, 1):
            ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = width

        # 6. Retornar como descarga
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        from flask import Response
        filename = f"reporte_{fecha or 'todos'}.xlsx"
        return Response(
            output.getvalue(),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        logger.exception("Error exportando: %s", e)
        return jsonify({"error": str(e)}), 500
```

### Estilo de encabezados Excel (estándar ILSAN):

| Propiedad | Valor |
|-----------|-------|
| Color fondo | `#1F4E79` (azul oscuro) |
| Color texto | `#FFFFFF` (blanco) |
| Fuente | Bold |
| Alineación | Centro |

---

## Paso 4 — Implementar la Lógica JS del Frontend

**Archivo:** `app/static/js/<nombre>.js` (creado vacío en WF_002)

### Estructura completa del JS:

```javascript
// ====== Módulo <Nombre> ======
// Prefijo "xx-" en todos los IDs

let xxModuleData = [];

// ── Control de carga ──
function xxShowLoading() {
  const loader = document.getElementById("xx-table-loading");
  const table  = document.getElementById("xx-table");
  if (loader && table) {
    const wrap  = table.closest(".xx-table-wrap");
    const thead = table.querySelector("thead");
    if (wrap && thead) wrap.style.setProperty("--thead-height", `${thead.offsetHeight}px`);
    loader.classList.add("active");
  }
}

function xxHideLoading() {
  const loader = document.getElementById("xx-table-loading");
  if (loader) loader.classList.remove("active");
}

// ── Notificaciones ──
function xxNotify(message, type = "info") {
  const old = document.querySelector(".xx-notification");
  if (old) old.remove();
  const el = document.createElement("div");
  el.className = "xx-notification";
  el.style.cssText = `
    position:fixed; top:20px; right:20px; padding:12px 20px;
    border-radius:6px; color:#fff; font-weight:600; font-size:0.9rem;
    z-index:10000; box-shadow:0 4px 12px rgba(0,0,0,.3);
  `;
  el.style.backgroundColor =
    type === "success" ? "#27ae60" :
    type === "error"   ? "#e74c3c" : "#3498db";
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => { if (el.parentNode) el.remove(); }, 4000);
}

// ── Carga de datos ──
async function xxLoadData() {
  xxShowLoading();
  try {
    const fecha    = document.getElementById("xx-filter-fecha")?.value || "";
    const linea    = document.getElementById("xx-filter-linea")?.value || "";
    const no_parte = document.getElementById("xx-filter-part")?.value  || "";

    const url = `/api/<modulo>/<accion>?fecha=${encodeURIComponent(fecha)}&linea=${encodeURIComponent(linea)}&no_parte=${encodeURIComponent(no_parte)}`;
    const res  = await fetch(url);
    const data = await res.json();

    if (data.error) { xxNotify("Error: " + data.error, "error"); return; }

    xxModuleData = data;

    // Actualizar contador
    const counter = document.getElementById("xx-record-count");
    if (counter) counter.textContent = `${data.length} registro${data.length !== 1 ? "s" : ""}`;

    xxRenderTable(data);
  } catch (err) {
    console.error(err);
    xxNotify("Error al cargar datos", "error");
  } finally {
    xxHideLoading();
  }
}

// ── Renderizado de tabla ──
function xxRenderTable(data) {
  const tbody = document.getElementById("xx-body");
  if (!tbody) return;
  tbody.innerHTML = "";

  data.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.campo1 ?? ""}</td>
      <td>${row.campo2 ?? ""}</td>
      <!-- ... más columnas ... -->
    `;
    tbody.appendChild(tr);
  });
}

// ── Exportar a Excel ──
async function xxExportExcel() {
  const fecha    = document.getElementById("xx-filter-fecha")?.value || "";
  const linea    = document.getElementById("xx-filter-linea")?.value || "";
  const no_parte = document.getElementById("xx-filter-part")?.value  || "";

  const url = `/api/<modulo>/<accion>/export?fecha=${encodeURIComponent(fecha)}&linea=${encodeURIComponent(linea)}&no_parte=${encodeURIComponent(no_parte)}`;

  try {
    const response = await fetch(url, { method: "GET", credentials: "same-origin" });
    if (!response.ok) throw new Error(`Status ${response.status}`);

    const blob = await response.blob();
    let filename = `reporte_${Date.now()}.xlsx`;

    const disposition = response.headers.get("content-disposition");
    if (disposition) {
      const match = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
      if (match && match[1]) filename = match[1].replace(/['"]/g, "");
    }

    const a = document.createElement("a");
    a.href = window.URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();

    xxNotify("Exportación completada", "success");
  } catch (err) {
    console.error(err);
    xxNotify("Error al exportar", "error");
  }
}

// ── Fecha por defecto ──
function xxSetDefaultDate() {
  const input = document.getElementById("xx-filter-fecha");
  if (input && !input.value) input.value = new Date().toISOString().split("T")[0];
}

// ── Cleanup (para cuando se navega a otro módulo) ──
function xxCleanup() {
  const loader = document.getElementById("xx-table-loading");
  if (loader) loader.classList.remove("active");
}
window.limpiarMiModulo = xxCleanup;

// ── Event Delegation ──
function xxInitListeners() {
  if (document.body.dataset.xxListenersAttached) return;

  document.body.addEventListener("click", function (e) {
    const target = e.target;

    if (target.id === "xx-btn-consultar" || target.closest("#xx-btn-consultar")) {
      e.preventDefault(); xxLoadData(); return;
    }
    if (target.id === "xx-btn-export-excel" || target.closest("#xx-btn-export-excel")) {
      e.preventDefault(); xxExportExcel(); return;
    }
  });

  document.body.dataset.xxListenersAttached = "true";
}

// ── Exponer globalmente ──
window.xxLoadData      = xxLoadData;
window.xxExportExcel   = xxExportExcel;
window.xxInitListeners = xxInitListeners;

// ── Auto-inicialización ──
document.addEventListener("DOMContentLoaded", function () {
  xxSetDefaultDate();
  xxInitListeners();
  xxLoadData();
});

if (document.readyState === "interactive" || document.readyState === "complete") {
  xxSetDefaultDate();
  xxInitListeners();
  setTimeout(() => xxLoadData(), 100);
}
```

### Componentes obligatorios del JS:

| Componente | Función | ¿Por qué? |
|------------|---------|------------|
| `xxShowLoading / xxHideLoading` | Spinner overlay | UX durante la carga de datos |
| `xxNotify` | Toast de éxito/error | Feedback al usuario |
| `xxLoadData` | Fetch → render | Función principal que conecta API con tabla |
| `xxRenderTable` | innerHTML builder | Genera las filas `<tr>` dinámicamente |
| `xxExportExcel` | Download blob | Descarga el .xlsx desde el endpoint de export |
| `xxSetDefaultDate` | Preset filtro | Evita tabla vacía al abrir el módulo |
| `xxCleanup` | Limpiar estado | Se llama al navegar fuera del módulo |
| `xxInitListeners` | Event delegation | Un solo listener en `body`, idempotente |
| Auto-init | `DOMContentLoaded` + fallback | Funciona tanto en carga directa como AJAX |

---

## Paso 5 — Conectar Filtros HTML con Params de API

### Mapeo de IDs de filtros → query params:

| Filtro HTML (ID) | Param de API | Tipo en SQL |
|------------------|--------------|-------------|
| `xx-filter-fecha` | `fecha` | `= %s` (exacto) |
| `xx-filter-linea` | `linea` | `= %s` (exacto) |
| `xx-filter-part` | `no_parte` | `LIKE %s` (parcial) |

### Formato de la URL de fetch:

```javascript
const url = `/api/modulo/accion?fecha=${encodeURIComponent(fecha)}&linea=${encodeURIComponent(linea)}&no_parte=${encodeURIComponent(no_parte)}`;
```

> **⚠️ Siempre usar `encodeURIComponent()`** — algunos part numbers contienen caracteres especiales.

---

## Paso 6 — Reiniciar el Servidor

El servidor usa **waitress** sin auto-reload. Después de agregar/modificar cualquier archivo en `app/api/` **siempre** reiniciar:

```powershell
# Detener
taskkill /F /IM python.exe

# Reiniciar
cd c:\Users\jesus\OneDrive\Documents\Desarrollo\MESILSANLOCAL
python run.py
```

> El servidor tarda ~12 segundos en iniciar (crea/verifica tablas).

---

## Paso 7 — Testing de la Integración

### 7a. Verificar que el API devuelve datos

**Desde el navegador** (después de iniciar sesión):

```
http://localhost:5000/api/<modulo>/<accion>?fecha=<fecha_con_datos>
```

**Resultado esperado:** JSON array con objetos. Si devuelve `[]`, verificar:
- ¿La fecha tiene datos en la tabla?
- ¿Los nombres de columna en la query coinciden con la tabla?
- ¿El servidor se reinició después de los cambios?

### 7b. Verificar la tabla en el template

1. Navegar a la ruta del template (ej: `/historial-maquina-ict-pass-fail`)
2. Cambiar la fecha a una que tenga datos
3. Hacer clic en "Consultar"
4. Verificar:

| Check | Qué verificar |
|-------|---------------|
| ✅ Spinner | Se muestra durante la carga y desaparece |
| ✅ Contador | Muestra "N registros" correcto |
| ✅ Filas | Las columnas coinciden con los encabezados |
| ✅ Porcentajes | Los % se calculan correctamente |
| ✅ Filtros | Línea y Part Number filtran los resultados |

### 7c. Verificar exportación Excel

1. Con datos en la tabla, hacer clic en "Exportar Excel"
2. Verificar que se descarga un archivo `.xlsx`
3. Abrir el Excel y confirmar:
   - Encabezados con estilo (azul oscuro + blanco + bold)
   - Datos coinciden con los de la tabla
   - Anchos de columna razonables

### 7d. Verificar consola del navegador

Abrir DevTools → Console (F12) y buscar:

```
❌ Errores 404: la URL del API no coincide con la ruta registrada por el Blueprint
❌ Errores CORS: no debería haber (mismo origen)
❌ TypeError: un ID del HTML no coincide con el ID en el JS
✅ Sin errores: todo correcto
```

### 7e. Verificar que no hay colisiones con otros módulos

1. Abrir el módulo nuevo
2. Navegar a otro módulo del mismo grupo (ej: Historial ICT)
3. Volver al módulo nuevo
4. Verificar que:
   - Los filtros no retienen valores del otro módulo
   - La tabla muestra datos propios, no del otro
   - El spinner no queda activo

---

## Checklist de Integración

```
[ ] Query SQL diseñada y probada en MySQL
[ ] Blueprint creado en app/api/<seccion>/<modulo>.py
[ ] Blueprint expone atributo `bp` y usa imports desde app.api.shared
[ ] Ruta HTML/AJAX del template creada dentro del Blueprint si el módulo la necesita
[ ] Endpoint de datos creado dentro del blueprint (retorna JSON)
[ ] Endpoint de exportación creado dentro del blueprint (retorna .xlsx)
[ ] SQL/CRUD/servicios propios viven en el paquete app/api/<seccion>/ del módulo
[ ] No se agregó backend nuevo del módulo a routes.py, db_mysql.py ni archivos *_api.py sueltos
[ ] Modulo agregado a _MODULOS_REGISTRADOS en app/api/__init__.py
[ ] JS implementado con todas las funciones (load, render, export, listeners)
[ ] IDs del HTML coinciden con los del JS
[ ] Filtros del HTML mapeados a params de la API
[ ] Servidor reiniciado
[ ] API probada: retorna 200 + JSON válido
[ ] Tabla renderiza datos correctos
[ ] Exportación descarga archivo .xlsx válido
[ ] Sin errores en consola del navegador
[ ] Sin colisiones con otros módulos
```

---

## Referencia Rápida — Ejemplo Completo (v2.0)

Para un módulo nuevo "Historial ICT % Pass/Fail" en la sección Control de resultados:

| Componente | Archivo | Ruta / ID |
|------------|---------|-----------|
| Template | `app/templates/Control de resultados/history_ict_Pass_Fail.html` | — |
| CSS | `app/static/css/ict-Pass-Fail.css` | — |
| JS | `app/static/js/ict-Pass-Fail.js` | — |
| Blueprint | `app/api/control_resultados/ict_pass_fail.py` | `bp = Blueprint("ict_pass_fail", ...)` |
| Registrado en | `app/api/__init__.py` | `_MODULOS_REGISTRADOS += ["control_resultados.ict_pass_fail"]` |
| Ruta página | `app/api/control_resultados/ict_pass_fail.py` | `/historial-maquina-ict-pass-fail` |
| API datos | `app/api/control_resultados/ict_pass_fail.py` | `GET /api/ict/pass-fail` |
| API export | `app/api/control_resultados/ict_pass_fail.py` | `GET /api/ict/pass-fail/export` |
| Tabla HTML | `#pf-ict-table` | tbody: `#pf-ict-body` |
| Filtro fecha | `#pf-filter-fecha` | param: `fecha` |
| Filtro línea | `#pf-filter-linea` | param: `linea` |
| Filtro parte | `#pf-filter-part-number` | param: `no_parte` |
| Btn consultar | `#pf-btn-consultar` | → `pfLoadData()` |
| Btn exportar | `#pf-btn-export-excel` | → `pfExportExcel()` |

---

## Módulos legacy

Tras la Fase 6 de la refactorización, `routes.py` ya no es un contenedor de
backend de módulos. Lo que queda ahí es core transversal: decoradores/helpers
compartidos, `before_request`, health, dashboard/material, LISTAS actuales,
`cargar_template` y pocos renders legacy consumidos por el layout.

| Estado | Ubicación | Ejemplo |
|---|---|---|
| ✅ Nuevo / migrado | `app/api/<seccion>/<modulo>.py` | `app/api/control_resultados/historial_ict_pass_fail.py` |
| ✅ Auth/sesión | `app/api/auth/sesion.py` | `/inicio`, `/login`, `/logout`, `/api/mi-perfil` |
| ⚠️ Core transversal | `app/routes.py` | `login_requerido`, LISTAS, `api_health`, `dashboard` |

**Para nuevos módulos: usar siempre v2.2.** Para módulos existentes, migrar
oportunisticamente cuando se tocan. Al migrar un módulo, mover una porción
coherente: ruta, API, permisos, datos propios, DDL local y exports deben quedar
bajo su Blueprint o un módulo hermano de la misma sección.

---

## Changelog

### 2026-05-28 — v2.2 (refactor de `routes.py` + auth blueprint)
- `routes.py` quedó reducido a core transversal/listas y deja de documentarse
  como backend legacy de módulos.
- Auth/sesión se movió a `app/api/auth/sesion.py`; usar endpoints
  `auth_sesion.inicio`, `auth_sesion.login` y `auth_sesion.logout` en
  `url_for()`.
- `app/api/shared` queda como proxy lazy de helpers core y `execute_query`; no
  debe re-exportar helpers privados de otros blueprints.
- `_MODULOS_REGISTRADOS` es la fuente de registro para auth, admin, módulos de
  secciones, servicios compartidos, portal y PDA.

### 2026-05-22 — v2.1 (ownership del backend por Blueprint)
- Regla dura: todo backend nuevo del módulo vive bajo `app/api/<seccion>/`.
- Las rutas HTML/AJAX del template se documentan dentro del mismo Blueprint.
- Si la lógica de datos crece, se separa en módulos hermanos del Blueprint y no se agrega a `db_mysql.py`.
- `routes.py`, `db_mysql.py` y `*_api.py` sueltos quedan solo para infraestructura compartida o legado pendiente de migrar.

### 2026-05-22 — v2.0 (refactor `app/api/`)
- Nueva regla: los endpoints nuevos van a `app/api/<seccion>/<modulo>.py` como Flask Blueprints.
- Nuevo paquete `app/api/shared` con re-exports (`execute_query`, `login_requerido`, `auth_system`).
- `app/api/__init__.py` define `_MODULOS_REGISTRADOS` y `registrar_blueprints_api(app)`.
- `app_factory.py` invoca el registro automático; ya NO se importan blueprints individualmente.
- Migración piloto: `app/Almacen_api.py` → `app/api/control_material/material_admin.py` (mismo blueprint name, rutas idénticas, frontend sin cambios).
- Migración subsecuente: `aoi_api.py`, `api_raw_modelos.py`, `api_po_wo.py` (planeadas).
- Pendiente en ese momento: extraer endpoints de `routes.py` por sección
  (completado parcialmente y documentado como core transversal en v2.2).

### 2026-03-24 — v1.0
- Documento inicial. Convención: endpoints en `routes.py` con `@app.route(...)`.
