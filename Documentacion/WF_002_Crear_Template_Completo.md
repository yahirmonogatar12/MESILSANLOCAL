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
| ✏️ MODIFICAR | `app/routes.py` | Ruta Flask para servir el template |
| ✏️ MODIFICAR | `app/templates/LISTAS/LISTA_<SECCION>.html` | Botón `<li>` en el sidebar |
| ✏️ MODIFICAR | `app/static/js/scriptMain.js` | Función `mostrar*()` + contenedor en lista de ocultar |
| ✏️ MODIFICAR | `app/templates/MaterialTemplate.html` | Div contenedor para carga dinámica |
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
4. El **`id` del `<body>`** debe coincidir con el nombre del contenedor en `MaterialTemplate.html`
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

## Paso 5 — Agregar el Contenedor en MaterialTemplate.html

**Archivo:** `app/templates/MaterialTemplate.html`

Buscar la zona de contenedores (cerca de línea ~574) y agregar:

```html
<!-- Contenedor específico para Mi Módulo -->
<div id="mi-modulo-unique-container" style="display: none;">
    <!-- El contenido se cargará dinámicamente con AJAX -->
</div>
```

> **Nota:** El `id` debe coincidir con el `id` del `<body>` del template HTML.

---

## Paso 6 — Agregar la Ruta Flask

**Archivo:** `app/routes.py`

```python
@app.route("/mi-modulo")
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

---

## Paso 7 — Crear la Función mostrar*() en scriptMain.js

**Archivo:** `app/static/js/scriptMain.js`

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

### 7b. Crear la función `mostrar*()`

Copiar el patrón de una función existente del mismo grupo y adaptar:

```javascript
window.mostrarMiModulo = function () {
  try {
    // 1. Activar botón de nav
    const navButton = document.getElementById("Control de resultados");
    if (navButton) {
      navButton.classList.add("active");
      document.querySelectorAll(".nav-button").forEach((btn) => {
        if (btn.id !== "Control de resultados") btn.classList.remove("active");
      });
    }

    // 2. Ocultar otros contenedores
    if (typeof window.hideAllMaterialContainers === "function") {
      window.hideAllMaterialContainers();
    }
    controlResultadosContainers.forEach((id) => {
      const c = document.getElementById(id);
      if (c) c.style.display = "none";
    });

    // 3. Mostrar contenedores padres
    const materialContainer = document.getElementById("material-container");
    if (materialContainer) materialContainer.style.display = "block";
    // ... (control-resultados-content, control-resultados-content-area)

    // 4. Mostrar mi contenedor
    const miContainer = document.getElementById("mi-modulo-unique-container");
    if (miContainer) {
      miContainer.style.display = "block";
      miContainer.style.width = "100%";
      // ... más estilos
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
[ ] Contenedor div agregado en MaterialTemplate.html
[ ] Ruta Flask agregada en routes.py
[ ] Función mostrar*() en scriptMain.js
[ ] Contenedor agregado en AMBAS listas de ocultar en scriptMain.js
[ ] Botón <li> agregado en LISTA_*.html con data-permiso-*
[ ] Permiso registrado en permisos_dropdowns.js
[ ] Permisos sincronizados y asignados a roles
[ ] Probado: el botón aparece en el sidebar
[ ] Probado: el template carga correctamente
[ ] Probado: JS funciona (filtros, tablas, modales)
[ ] Probado: no hay colisión de IDs con otros módulos
```

---

## Diagrama de Dependencias entre Archivos

```
MaterialTemplate.html
  │
  ├── scriptMain.js ──── mostrarMiModulo()
  │     │                    │
  │     │                    ▼
  │     │              cargarContenidoDinamico()
  │     │                    │
  │     │                    ▼
  │     │              routes.py ──── /mi-modulo
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
