# WF_002 — Flujo Completo para Crear un Nuevo Template (HTML + CSS + JS)

> **Versión:** 1.0  
> **Fecha:** 2026-03-23  
> **Prerequisito:** [WF_001 — Flujo para Agregar Nuevos Templates y Botones al Sidebar](./WF_001_Nuevos_Modulos_AJAX_Templates.md)
> **Ejemplo de referencia:** Módulo "Historial ICT % Pass/Fail"

---

## Resumen

Este documento detalla el flujo completo para crear un **nuevo módulo con template HTML, CSS propio y JS propio**, asegurando que no colisione con módulos existentes. Usa como ejemplo real el módulo **ICT % Pass/Fail** que agregamos sobre el ya existente **ICT**.

---

## Archivos que se Crean / Modifican

| Acción | Archivo | Descripción |
|--------|---------|-------------|
| ✨ CREAR | `app/templates/<Carpeta>/<nombre>.html` | Template HTML del módulo |
| ✨ CREAR | `app/static/css/<nombre>.css` | Estilos propios del módulo |
| ✨ CREAR | `app/static/js/<nombre>.js` | Lógica JS propia del módulo |
| ✨ CREAR / MODIFICAR | `app/api/<seccion>/<modulo>.py` | Blueprint con ruta Flask para servir el template |
| ✏️ MODIFICAR | `app/templates/LISTAS/LISTA_<SECCION>.html` | Botón `<li>` en el sidebar |
| ✏️ MODIFICAR | `app/static/js/scriptMain.js` | Función `mostrar*()` + contenedor en lista de ocultar |
| ✏️ MODIFICAR | `app/templates/MainTemplate.html` | Div contenedor para carga dinámica |
| ✏️ MODIFICAR | `app/static/permisos_dropdowns.js` | Registro del permiso del nuevo botón |

---

## Paso 1 — Elegir Prefijo Único para IDs

> **⚠️ CRÍTICO:** Si el módulo comparte estructura visual con otro módulo existente (ej: mismas tablas, filtros, modales), **TODOS los IDs deben ser únicos**. Caso contrario el JS tomará el primer elemento que encuentre en el DOM.

**Convención:** elegir un prefijo corto de 2-3 letras.

| Ejemplo | Prefijo | ID original → ID nuevo |
|---------|---------|------------------------|
| ICT Pass/Fail | `pf-` | `ict-table` → `pf-ict-table` |
| MCU Historial | `mcu-` | `filter-fecha` → `mcu-filter-fecha` |
| AOI Nuevo | `aoi2-` | `btn-consultar` → `aoi2-btn-consultar` |

---

## Paso 2 — Crear el Template HTML

**Ubicación:** `app/templates/<Carpeta del módulo>/<nombre>.html`

**Ejemplo real:** `app/templates/Control de resultados/history_ict_Pass_Fail.html`

### Estructura base:

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mi Módulo - ILSAN</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/ilsan-theme.css') }}">
  <link rel="stylesheet" href="{{ url_for('static', filename='css/mi-modulo.css') }}">
  <script defer src="{{ url_for('static', filename='js/mi-modulo.js') }}"></script>
</head>
<body id="mi-modulo-unique-container">
  <div class="ict-page">
    <!-- Contenido del módulo con IDs prefijados -->
    <div id="xx-filtros">...</div>
    <table id="xx-tabla">...</table>
  </div>
</body>
</html>
```

### Reglas:
1. **Todos los IDs** llevan el prefijo elegido (`xx-`)
2. **CSS y JS** propios, no compartidos con otro módulo
3. **`ilsan-theme.css`** sí se comparte (es el tema global)
4. El **`id` del `<body>`** debe coincidir con el nombre del contenedor en `MainTemplate.html`
5. Usar `{{ url_for('static', ...) }}` para assets

---

## Paso 3 — Crear el CSS

**Ubicación:** `app/static/css/<nombre>.css`

**Ejemplo real:** `app/static/css/Pass-Fail-ict.css`

### Qué cambiar respecto al CSS base:
- Todos los selectores con ID: `#ict-table` → `#pf-ict-table`
- Selectores responsive: `#ict-container` → `#mi-modulo-unique-container`
- Selectores de modal: `#modal-barcode` → `#xx-modal-barcode`

### Qué NO cambiar:
- Selectores por clase (`.filters-card`, `.btn-primary`, `.ict-page`, etc.) — estos son compartidos y genéricos

---

## Paso 4 — Crear el JS

**Ubicación:** `app/static/js/<nombre>.js`

**Ejemplo real:** `app/static/js/Pass-Fail-ict.js`

### Checklist de adaptación:

| Qué | Cómo |
|-----|------|
| Variables globales | Prefijar: `ictModuleData` → `pfIctModuleData` |
| Funciones | Prefijar: `loadIctData()` → `pfLoadIctData()` |
| `getElementById()` | Usar IDs prefijados: `"filter-fecha"` → `"pf-filter-fecha"` |
| Event delegation IDs | `target.id === "btn-consultar"` → `target.id === "pf-btn-consultar"` |
| Flag anti-duplicado | `dataset.ictListenersAttached` → `dataset.pfIctListenersAttached` |
| Scope de clicks en filas | `target.closest("#mi-modulo-unique-container")` |
| `window.*` exports | Nombres únicos: `window.initializeIctPassFailEventListeners` |
| Cleanup function | Nueva: `window.limpiarHistorialICTPassFail` |

### Funciones globales a exponer (para `scriptMain.js`):

```javascript
// Estas son las que llama scriptMain.js en el callback de cargarContenidoDinamico
window.initializeMiModuloEventListeners = initializeMiModuloEventListeners;
window.loadMiModuloData = pfLoadData;
```

---

## Paso 5 — Agregar el Contenedor en MainTemplate.html

**Archivo:** `app/templates/MainTemplate.html`

Buscar la zona de contenedores (cerca de línea ~574) y agregar:

```html
<!-- Contenedor específico para Mi Módulo -->
<div id="mi-modulo-unique-container" style="display: none;">
    <!-- El contenido se cargará dinámicamente con AJAX -->
</div>
```

> **Nota:** El `id` debe coincidir con el `id` del `<body>` del template HTML.

---

## Paso 6 — Agregar la Ruta Flask al Blueprint

**Archivo:** `app/api/<seccion>/<modulo>.py`

```python
from flask import Blueprint, render_template

from app.api.shared import login_requerido


bp = Blueprint("mi_modulo", __name__)


@bp.route("/mi-modulo")
@login_requerido
def mi_modulo():
    """Servir la página de Mi Módulo"""
    try:
        return render_template("Carpeta/mi_modulo.html")
    except Exception as e:
        print(f"Error al cargar Mi Módulo: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500
```

### Importante:
- **El nombre del archivo en `render_template`** debe coincidir EXACTAMENTE con el archivo real (case sensitive en Linux)
- **No necesitas ruta `-ajax`** separada si usas la misma ruta para carga directa y dinámica
- Decorar con `@login_requerido`
- Registrar el Blueprint en `app/api/__init__.py`
- El backend propio del módulo debe quedar en ese paquete Blueprint; si crece, crear módulos hermanos como `<modulo>_data.py` según [WF_003](./WF_003_Integracion_API_JS_Template.md)

---

## Paso 7 — Crear la Función mostrar*() en scriptMain.js

**Archivo:** `app/static/js/scriptMain.js` (o `MainTemplate.html` para módulos de Información Básica)

> **⚠️ ACTUALIZACIÓN 2026-05-21:** El bloque manual de "ocultar otras secciones + mostrar padres" se reemplazó por **helpers reutilizables** definidos en `MainTemplate.html`. Ya NO copies ese bloque en cada `mostrar*()`. Usa el helper correspondiente. Ver sección [7c — Helpers de preparación de panel](#7c--helpers-de-preparación-de-panel).

### 7a. Agregar el contenedor a la lista de "ocultar" del grupo

Buscar el array de contenedores de la sección correspondiente y agregar tu nuevo ID:

```javascript
const controlResultadosContainers = [
  "control-resultados-info-container",
  "historial-aoi-unique-container",
  "historial-ict-unique-container",
  "historial-cambios-parametros-ict-unique-container",
  "historial-maquina-ict-pass-fail-unique-container",  // ← AGREGAR
];
```

> Hay **DOS** lugares donde aparece esta lista: una en la definición principal (~línea 245) y otra dentro de la función `mostrar*()` (~línea 4482). **Agregar en ambas.**

### 7b. Crear la función `mostrar*()` (patrón actual)

Con los helpers de panel disponibles, la función queda mucho más corta:

```javascript
window.mostrarMiModulo = function () {
  try {
    // 1. Activar botón de nav (opcional, si el modulo se invoca desde sidebar)
    const navButton = document.getElementById("Control de resultados");
    if (navButton) {
      navButton.classList.add("active");
      document.querySelectorAll(".nav-button").forEach((btn) => {
        if (btn.id !== "Control de resultados") btn.classList.remove("active");
      });
    }

    // 2. Preparar el panel de la sección (oculta otras secciones,
    //    muestra el sidebar y content-area propios, limpia contenedores).
    //    Esto reemplaza ~30 líneas de código repetitivo.
    window.prepararPanelSeccion("resultados");

    // 3. Ocultar contenedores hermanos de mi sección
    controlResultadosContainers.forEach((id) => {
      const c = document.getElementById(id);
      if (c) c.style.display = "none";
    });

    // 4. Mostrar mi contenedor específico
    const miContainer = document.getElementById("mi-modulo-unique-container");
    if (miContainer) {
      miContainer.style.display = "block";
      miContainer.style.width = "100%";
    }

    // 5. Cargar contenido dinámico
    if (typeof window.cargarContenidoDinamico === "function") {
      window.cargarContenidoDinamico(
        "mi-modulo-unique-container",
        "/mi-modulo",
        () => {
          if (typeof window.initializeMiModuloEventListeners === "function") {
            window.initializeMiModuloEventListeners();
          }
          if (typeof window.loadMiModuloData === "function") {
            window.loadMiModuloData();
          }
        }
      );
    }
  } catch (error) {
    console.error("Error en mostrarMiModulo:", error);
  }
};
```

### 7c — Helpers de preparación de panel

**Ubicación:** `MainTemplate.html` (línea ~2316 aprox.)

El sistema expone tres helpers globales que encapsulan toda la lógica de "ocultar otras secciones / mostrar la mía":

#### `window.prepararPanelSeccion(seccion)`

Helper genérico. Recibe el nombre corto de la sección. Realiza:

1. Oculta los **content-areas** de TODAS las demás secciones (limpia `style.cssText` antes para borrar inline styles agresivos).
2. Oculta los **sidebars** de TODAS las demás secciones.
3. Llama a `hideAllMaterialContainers()` (limpia módulos específicos como BOM, almacén, etc.).
4. Muestra el `#material-container` padre.
5. Muestra el sidebar (`*-content`) de la sección activa.
6. Muestra el content-area (`*-content-area`) de la sección activa con `width: 100%`.

**Secciones válidas** (definidas en los mapas `SECCIONES_AREAS` y `SECCIONES_SIDEBARS`):

| Sección | Sidebar (`*-content`) | Content-area (`*-content-area`) |
|---|---|---|
| `informacion-basica` | `informacion-basica-content` | `informacion-basica-content-area` |
| `material` | `control-material-content` | `material-content-area` |
| `produccion` | `control-produccion-content` | `produccion-content-area` |
| `proceso` | `control-proceso-content` | `control-proceso-content-area` |
| `calidad` | `control-calidad-content` | `calidad-content-area` |
| `resultados` | `control-resultados-content` | `control-resultados-content-area` |
| `reporte` | `control-reporte-content` | *(no aplica, usa material-content-area)* |
| `configuracion` | `configuracion-programa-content` | *(no aplica)* |

#### `window.prepararPanelInformacionBasica()`

Especialización para Información Básica. Equivale a `prepararPanelSeccion('informacion-basica')` + `hideAllInformacionBasicaContainers()` para limpiar los muchos contenedores hijos de esta sección.

**Usar al inicio de cada `mostrarXxxInfo()` de Información Básica:**

```javascript
window.mostrarMiNuevoModuloInfo = function() {
    prepararPanelInformacionBasica();
    const container = document.getElementById('mi-nuevo-info-container');
    if (container) container.style.display = 'block';
};
```

#### `window.ocultarOtrasSecciones(seccion)`

Helper de bajo nivel. Solo oculta otras secciones SIN mostrar la activa. Útil si necesitas control fino del orden de operaciones (por ejemplo, `mostrarControlBOMInfo` lo usa combinado con limpiezas específicas adicionales).

#### Por qué importa

Antes del refactor, cada `mostrar*()` repetía ~20-30 líneas para ocultar las demás secciones. Esto provocaba:

- **Bug observado:** un `mostrarXxxInfo` olvidaba ocultar `material-content-area` → al navegar de Control de Material a Información Básica, el panel viejo quedaba superpuesto.
- **Bug observado:** cada función ocultaba un subconjunto distinto de sidebars → comportamientos inconsistentes entre secciones.
- **Bug futuro:** al agregar una nueva sección (ej. "Control de mantenimiento"), había que editar las 20+ funciones para que también la ocultaran.

Con los helpers:

- Una sola fuente de verdad: `SECCIONES_AREAS` y `SECCIONES_SIDEBARS`.
- Agregar una nueva sección = añadir UNA línea a cada mapa.
- Imposible olvidarse de ocultar un area.

#### Cómo agregar una nueva sección al sistema

1. Añadir entrada en `SECCIONES_AREAS`:
   ```javascript
   'mi-seccion': 'mi-seccion-content-area'
   ```
2. Añadir entrada en `SECCIONES_SIDEBARS`:
   ```javascript
   'mi-seccion': 'mi-seccion-content'
   ```
3. Tus `mostrar*()` ya pueden llamar `prepararPanelSeccion('mi-seccion')`.
4. Las demás secciones automáticamente la ocultarán al activarse.

---

## Paso 8 — Agregar el Botón en el Sidebar (LISTA)

**Archivo:** `app/templates/LISTAS/LISTA_<SECCION>.html`

```html
<li class="sidebar-link" tabindex="0"
    data-permiso-pagina="LISTA_DE_CONTROL_DE_RESULTADOS"
    data-permiso-seccion="Mi Sección"
    data-permiso-boton="Mi Módulo"
    onclick="window.parent.mostrarMiModulo ? window.parent.mostrarMiModulo() : (window.parent.cargarContenidoDinamico ? window.parent.cargarContenidoDinamico('mi-modulo-unique-container', '/mi-modulo') : window.location.href='/mi-modulo')">
    Mi Módulo
</li>
```

### Anatomía del `onclick` (patrón de fallback triple):
1. **Intento 1:** `window.parent.mostrarMiModulo()` — función completa con estilos
2. **Intento 2:** `window.parent.cargarContenidoDinamico(...)` — carga directa sin estilos extra
3. **Intento 3:** `window.location.href=...` — navegación directa como último recurso

---

## Paso 9 — Registrar el Permiso en permisos_dropdowns.js

**Archivo:** `app/static/permisos_dropdowns.js`

Agregar una entrada al array de permisos:

```javascript
{
    "pagina": "LISTA_DE_CONTROL_DE_RESULTADOS",
    "seccion": "Mi Sección",
    "boton": "Mi Módulo"
},
```

> Los valores deben coincidir EXACTAMENTE con los `data-permiso-*` del `<li>` del paso anterior.

---

## Paso 10 — Sincronizar Permisos

Desde la interfaz de administración, ejecutar la sincronización de permisos para que el sistema detecte el nuevo botón y lo registre en la tabla `permisos_botones`.

Luego, asignar el permiso del nuevo botón a los roles correspondientes.

---

## Checklist Final

```
[ ] Prefijo único elegido
[ ] HTML creado con IDs prefijados
[ ] CSS creado con selectores prefijados
[ ] JS creado con variables/funciones/IDs prefijados
[ ] Contenedor div agregado en MainTemplate.html
[ ] Ruta Flask agregada en el Blueprint del módulo
[ ] Función mostrar*() en scriptMain.js
[ ] mostrar*() usa prepararPanelSeccion() (NO copia bloque manual de ocultar)
[ ] Contenedor agregado en AMBAS listas de ocultar en scriptMain.js
[ ] Botón <li> agregado en LISTA_*.html con data-permiso-*
[ ] Permiso registrado en permisos_dropdowns.js
[ ] Permisos sincronizados y asignados a roles
[ ] Probado: el botón aparece en el sidebar
[ ] Probado: el template carga correctamente
[ ] Probado: JS funciona (filtros, tablas, modales)
[ ] Probado: no hay colisión de IDs con otros módulos
[ ] Probado: navegar a otra sección y volver NO deja paneles superpuestos
```

---

## Diagrama de Dependencias entre Archivos

```
MainTemplate.html
  │
  ├── HELPERS GLOBALES (definidos 1 sola vez)
  │     ├── prepararPanelSeccion(seccion)         ← úsalo en mostrar*()
  │     ├── prepararPanelInformacionBasica()      ← úsalo en mostrarXxxInfo()
  │     ├── ocultarOtrasSecciones(seccion)        ← bajo nivel
  │     ├── hideAllMaterialContainers()
  │     └── hideAllInformacionBasicaContainers()
  │
  ├── MAPAS DE SECCIONES (fuente de verdad)
  │     ├── SECCIONES_AREAS    { seccion → id del *-content-area }
  │     └── SECCIONES_SIDEBARS { seccion → id del *-content }
  │
  ├── scriptMain.js ──── mostrarMiModulo()
  │     │                    │
  │     │                    ├──▶ prepararPanelSeccion('mi-grupo')   ◀── 1 línea
  │     │                    │
  │     │                    ▼
  │     │              cargarContenidoDinamico()
  │     │                    │
  │     │                    ▼
  │     │              Blueprint app/api/<seccion>/<modulo>.py ──── /mi-modulo
  │     │                    │
  │     │                    ▼
  │     │              mi_modulo.html
  │     │                ├── mi-modulo.css
  │     │                └── mi-modulo.js
  │     │                      ├── initializeMiModuloEventListeners()
  │     │                      └── loadMiModuloData()
  │     │
  │     └── hideAllMaterialContainers()
  │
  ├── LISTA_*.html
  │     └── <li onclick="mostrarMiModulo()">
  │           └── data-permiso-pagina / seccion / boton
  │
  └── permisos_dropdowns.js
        └── { pagina, seccion, boton }
```

---

## Changelog

### 2026-05-21 — Refactor de helpers de panel
- Eliminado el bloque manual repetido de "ocultar otras secciones + mostrar padres" que aparecía en ~25 funciones `mostrar*()`.
- Introducidos los helpers globales `prepararPanelSeccion(seccion)`, `prepararPanelInformacionBasica()` y `ocultarOtrasSecciones(seccion)` en `MainTemplate.html`.
- Introducidos los mapas `SECCIONES_AREAS` y `SECCIONES_SIDEBARS` como fuente única de verdad sobre qué IDs pertenecen a cada sección.
- Refactorizadas:
  - `mostrarControlMaterial`, `mostrarControlProduccion`, `mostrarControlProceso`, `mostrarControlResultados`, `mostrarInformacionBasica` (funciones padre de navbar).
  - Los 23 handlers `mostrarXxxInfo` de Información Básica.
  - Los handlers inline de navbar para Calidad, Reporte y Configuración de programa.
- Bug previo resuelto: al navegar entre pestañas y volver, panes viejos quedaban superpuestos porque cada función ocultaba un subconjunto distinto de areas/sidebars. Ahora todas pasan por la misma lógica.
- Ver Paso 7c para uso detallado.
