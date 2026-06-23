# WF_006 — Mover un Módulo Existente Entre Secciones del Navbar

> **Versión:** 1.0
> **Fecha:** 2026-06-23
> **Prerequisitos:** [WF_001](./WF_001_Nuevos_Modulos_AJAX_Templates.md), [WF_002](./WF_002_Crear_Template_Completo.md), [WF_003](./WF_003_Integracion_API_JS_Template.md)
> **Caso real:** Mover **Trazabilidad de PCB** de `Control de resultados / Control de inventario` a `Control de reporte / Product Tracking`.

---

## Resumen

WF_001–WF_005 cubren **crear** un módulo nuevo. Este documento cubre **mover** un
módulo ya existente de una sección del navbar a otra (p.ej. de "Control de
resultados" a "Control de reporte").

Mover un módulo NO es solo cambiar el `<li>` de archivo LISTA. Hay estado
asociado a la sección vieja en **cuatro lugares distintos**, y si se omite
alguno el módulo "carga pero no se ve", o al hacer click te manda a la sección
vieja. Este WF documenta los cuatro y los bugs reales que aparecieron.

> **Regla de oro del diagnóstico:** si el módulo "no abre", NO adivines qué CSS
> lo tapa. Ejecuta el [snippet de diagnóstico de DOM](#a-snippet-de-diagnóstico-de-dom)
> en la consola. Te dice en una corrida qué elemento (container, área o ancestro)
> está oculto y si el HTML realmente se cargó. Ahorra horas.

---

## El modelo mental: container, área y sección no son lo mismo

Tres conceptos que es fácil confundir y que causaron todos los bugs de este caso:

| Concepto | Qué es | Ejemplo |
|---|---|---|
| **Container** | El `<div id="...-unique-container">` donde se inyecta el HTML del módulo | `trazabilidad-pcb-unique-container` |
| **Área (`*-content-area`)** | El contenedor padre que el sistema muestra/oculta por sección | `control-resultados-content-area` |
| **Sección navbar** | El botón del navbar y su sidebar (LISTA) | `Control de reporte` |

**Punto crítico:** el `<div>` del container vive físicamente dentro de UN área en
el DOM (`MainTemplate.html`). Esa área NO cambia solo porque muevas el botón del
menú a otra sección. Si mueves el botón a "Control de reporte" pero el `<div>`
sigue dentro de `control-resultados-content-area`, entonces al activar reporte el
sistema oculta el área de resultados (con `display:none` + clase
`mes-area-hidden !important`) y tu módulo queda invisible aunque su HTML esté
cargado y el container tenga `display:block`.

`Control de reporte` y `Configuración de programa` **no tienen área propia** en
`SECCIONES_AREAS`. Sus módulos viven dentro del área de otra sección. Esto hay
que manejarlo explícitamente (ver Paso 3 y 5).

---

## Los 4 lugares con estado por sección (checklist)

Al mover el módulo `X-unique-container` de la sección VIEJA a la NUEVA:

| # | Lugar | Qué hacer | Si lo omites… |
|---|---|---|---|
| 1 | `LISTAS/LISTA_<VIEJA>.html` y `LISTAS/LISTA_<NUEVA>.html` | Quitar el `<li>` de la vieja, agregarlo a la nueva con los `data-permiso-*` de la NUEVA página/sección | El botón aparece en el menú viejo / permisos no migran |
| 2 | `MainTemplate.html` → función `mostrar<Modulo>()` | Cambiar `prepararPanelSeccion('<vieja>')` por `prepararPanelSeccion('<nueva>')` **y** mostrar explícitamente el área donde vive el `<div>` | El módulo carga pero su área queda oculta → pantalla en gris |
| 3 | `scriptMain.js` → handler navbar de la sección NUEVA (`else if (this.id === "Control de ...")`) | Asegurar que muestre el área donde vive el `<div>` (no que la oculte) | Click en el botón navbar oculta el área → gris |
| 4 | `scriptMain.js` → hide-lists `control<Vieja>Containers` (varias copias) | Quitar el container de TODAS las copias de la lista de la sección vieja | Al hacer click en la pestaña te manda a la sección vieja |

Y dos cosas más:

| # | Lugar | Qué hacer |
|---|---|---|
| 5 | `sidebar-tabs.js` → `SECCIONES_AREAS_MAP` | Si la sección NUEVA no tiene área propia, mapearla al área donde vive el `<div>`; manejar el conflicto si ese área ya pertenece a otra sección (ver abajo) |
| 6 | `sidebar-tabs.js` → migración de localStorage `mes_tabs_v1` | Migrar la pestaña guardada de la sección vieja a la nueva (ver Paso 6). Sin esto, la pestaña queda "atrapada" en la sección vieja tras un reinicio |

---

## Paso a paso (con el caso real)

### Paso 1 — Mover el `<li>` entre archivos LISTA

Quitar de `LISTA_DE_CONTROL_DE_RESULTADOS.html`. Agregar a
`LISTA_DE_CONTROL_DE_REPORTE.html`, dentro del `<ul>` de la sección destino, con
los `data-permiso-*` de la NUEVA ubicación y el patrón de fallback triple
(WF_002 §8):

```html
<li class="sidebar-link" tabindex="0"
        data-permiso-pagina="LISTA_DE_CONTROL_DE_REPORTE"
        data-permiso-seccion="Product Tracking"
        data-permiso-boton="Trazabilidad de PCB"
        onclick="window.parent.mostrarTrazabilidadPcb ? window.parent.mostrarTrazabilidadPcb() : (window.parent.cargarContenidoDinamico ? window.parent.cargarContenidoDinamico('trazabilidad-pcb-unique-container', '/control_resultados/trazabilidad_pcb') : window.location.href='/control_resultados/trazabilidad_pcb')">Trazabilidad de PCB</li>
```

> La **ruta Flask y el blueprint NO se mueven**: solo cambia el menú. La ruta
> puede seguir siendo `/control_resultados/trazabilidad_pcb` aunque el botón viva
> ahora en reporte. Mover el archivo Python solo si además migras el módulo de
> verdad (raro).

### Paso 2 — Ajustar `mostrar<Modulo>()` en MainTemplate.html

Cambiar la sección y **mostrar el área donde vive el `<div>`** (no la de la
sección nueva si esta no tiene área propia):

```javascript
window.mostrarTrazabilidadPcb = function() {
    prepararPanelSeccion('reporte');
    // El <div> vive (en el DOM) dentro de control-resultados-content-area.
    // prepararPanelSeccion('reporte') la deja oculta -> mostrarla explicitamente.
    const area = document.getElementById('control-resultados-content-area');
    if (area) {
        area.classList.remove('mes-area-hidden');
        area.style.display = 'block';
        area.style.width = '100%';
    }
    const container = document.getElementById('trazabilidad-pcb-unique-container');
    if (container) container.style.display = 'block';
    cargarContenidoDinamico('trazabilidad-pcb-unique-container', '/control_resultados/trazabilidad_pcb', () => {
        if (typeof window.loadTrazabilidadPcbData === 'function') window.loadTrazabilidadPcbData();
    });
};
```

> **Cómo saber en qué área vive el `<div>`:** busca el `id` del container en
> `MainTemplate.html` y mira dentro de qué `*-content-area` cae. O usa el snippet
> de diagnóstico (`AREA:` te lo dice). NO asumas.

### Paso 3 — Handler navbar de la sección nueva (scriptMain.js)

El bloque `else if (this.id === "Control de reporte")` por defecto hace
`materialContentArea.style.display = "none"` y NO muestra el área del módulo.
Hay que mostrar el área correcta:

```javascript
} else if (this.id === "Control de reporte") {
    materialContainer.style.display = "block";
    if (controlReporteContent) controlReporteContent.style.display = "block";
    materialContentArea.style.display = "none";
    // Modulos de reporte cuyo <div> vive en control-resultados-content-area:
    if (controlResultadosContentArea)
        controlResultadosContentArea.style.display = "block";
}
```

### Paso 4 — Quitar el container de las hide-lists de la sección vieja

En `scriptMain.js`, el array `controlResultadosContainers` (u homólogo) aparece
**varias veces** (una por cada función `mostrar*` de la sección + la definición).
Quita el container de TODAS:

```javascript
// ANTES
"inventario-reparacion-smd-unique-container",
"trazabilidad-pcb-unique-container",   // <- quitar de las N copias
"inventario-reparacion-assy-unique-container",
```

Si no se quita, el sistema sigue tratando el container como "de resultados" y al
hacer click en su pestaña te lleva a esa sección.

### Paso 5 — `SECCIONES_AREAS_MAP` en sidebar-tabs.js (áreas compartidas)

Si la sección nueva no tiene área propia, mapéala al área donde vive el `<div>`:

```javascript
const SECCIONES_AREAS_MAP = {
    ...
    'Control de resultados': 'control-resultados-content-area',
    // Reporte comparte el area de resultados (ahi vive el <div> de Trazabilidad).
    'Control de reporte': 'control-resultados-content-area'
};
```

**Conflicto por área compartida:** `migrarTabsACorrectaSeccion()` invierte este
mapa (`areaId -> navTab`). Si dos secciones comparten un área, la inversión es
ambigua (gana la última). Por eso el módulo movido se resuelve por una
**migración explícita por container** (Paso 6), y se excluye del mapeo por área:

```javascript
// dentro de migrarTabsACorrectaSeccion(), al construir areaIdToNavTab:
if (areaId === 'control-resultados-content-area' && navTab === 'Control de reporte') return;
// y al filtrar tabs:
if (RESUELTOS_EXPLICITO.has(tab.container)) return true; // ya migrado explicito
```

### Paso 6 — Migrar la pestaña en localStorage (`mes_tabs_v1`)

El sistema de tabs persiste qué pestañas pertenecen a cada sección en
`localStorage['mes_tabs_v1']`. Una pestaña abierta ANTES del movimiento queda
guardada bajo la sección vieja; al reiniciar se restaura ahí y "atrapa" el
módulo. Cerrar/reabrir NO basta (al recargar se restaura de nuevo).

Solución: migración automática al iniciar `sidebar-tabs.js`. Se invoca desde
`migrarTabsACorrectaSeccion()` (que ya corre en el arranque):

```javascript
function migrarTabsMovidas() {
    const MOVIDAS = [
        { container: 'trazabilidad-pcb-unique-container',
          de: 'Control de resultados', a: 'Control de reporte' },
    ];
    const state = readState();
    let cambio = false;
    for (const m of MOVIDAS) {
        const orig = state[m.de];
        if (!orig || !Array.isArray(orig.tabs)) continue;
        const tab = orig.tabs.find(t => t.container === m.container);
        if (!tab) continue;
        orig.tabs = orig.tabs.filter(t => t.container !== m.container);
        if (orig.active === m.container)
            orig.active = orig.tabs.length ? orig.tabs[orig.tabs.length - 1].container : null;
        if (!state[m.a]) state[m.a] = { tabs: [], active: null };
        if (!state[m.a].tabs.find(t => t.container === m.container)) state[m.a].tabs.push(tab);
        cambio = true;
    }
    if (cambio) writeState(state);
}
```

> El array `MOVIDAS` es acumulativo: cada vez que muevas un módulo entre
> secciones, agrega una entrada. Es idempotente (si ya está migrado, no hace
> nada), así que puede quedarse en el código indefinidamente.

### Paso 7 — Cache-busting y reinicio

Subir el `?v=` de TODOS los assets tocados: `MainTemplate.html` (el `<script>`
de `scriptMain.js` y `sidebar-tabs.js`), el JS/CSS del módulo. Reiniciar el
server (waitress no recarga) y hacer **`Ctrl+Shift+R`** en el navegador (un F5
normal puede no recargar el JS cacheado).

### Paso 8 — Sincronizar y reasignar permisos

El botón cambió de `pagina`/`seccion`, así que su permiso viejo ya no aplica:

1. `POST /admin/sincronizar_permisos_dropdowns` (registra el permiso nuevo).
2. Asignar el permiso nuevo a los roles. (El superadmin lo ve sin esto.)

---

## Causa raíz de los 3 bugs reales (este caso)

Aparecieron en cascada; cada fix revelaba el siguiente:

1. **"Carga pero pantalla en gris".** El `<div>` vivía en
   `control-resultados-content-area`, que `prepararPanelSeccion('reporte')`
   ocultaba con `mes-area-hidden !important`. El container estaba `display:block`
   con su HTML cargado (7355 chars), pero su área padre estaba oculta. → Paso 2 y 3.
   - **El error de base fue asumir en qué área vivía el `<div>`.** El snippet de
     diagnóstico lo habría dicho en el primer intento (`AREA: ... display:none`).

2. **"Click en la pestaña me manda a Control de resultados".** El container seguía
   en las hide-lists `controlResultadosContainers` y en `mes_tabs_v1` bajo
   resultados. → Paso 4 y 6.

3. **`sidebarAge` gigante / "navegación interna".** En la restauración, el
   interceptor ejecuta el `onclick` guardado sin un click real, así que
   `__ultimoSidebarLinkAt` queda viejo y `sidebarAge = Date.now() - 0` da un
   número enorme → se trata como navegación interna y no se registra el tab. Se
   resuelve al migrar correctamente la pestaña (Paso 6): tras la migración, el
   click real del usuario sí pasa por el listener y `sidebarAge ≈ 0`.

---

## Apéndices

### A. Snippet de diagnóstico de DOM

Con la pestaña del módulo activa (aunque se vea en gris), pegar en F12 → Console:

```javascript
(() => {
  const c = document.getElementById('trazabilidad-pcb-unique-container'); // <- tu container
  const a = c?.closest('[id$="-content-area"]');
  const r = (el) => el ? {id:el.id, display:getComputedStyle(el).display, vis:getComputedStyle(el).visibility, cls:el.className, inlineDisplay:el.style.display} : 'NULL';
  console.log('CONTAINER:', r(c));
  console.log('AREA:', r(a));
  console.log('material-container:', r(document.getElementById('material-container')));
  console.log('contenido container (chars):', c ? c.innerHTML.length : 0);
  let p = c?.parentElement, chain=[];
  while (p && p !== document.body) { const s=getComputedStyle(p); if(s.display==='none'||s.visibility==='hidden') chain.push({id:p.id||p.className, display:s.display, vis:s.visibility}); p=p.parentElement; }
  console.log('ANCESTROS OCULTOS:', chain.length ? chain : 'ninguno');
})();
```

Interpretación:
- `contenido container (chars) > 100` → el HTML SÍ se cargó; el problema es de visibilidad, no de carga.
- `AREA: display:none` o clase `mes-area-hidden` → el área padre está oculta (Paso 2/3).
- `CONTAINER: display:none` → el container está oculto (markActive no lo activó, o el onclick no corrió).
- `ANCESTROS OCULTOS` no vacío → ese ancestro es el culpable.

### B. Logs útiles del sistema de tabs

En la consola, al hacer click, deben aparecer (en `sidebar-tabs.js`):

- `[TABS-INTERCEPT] <container> sidebarAge= 0 ms` → click real capturado (bien).
  - `sidebarAge` gigante (~1.7e12) → el listener de click no se disparó; viene de
    restauración programática, no de un click (ver bug 3).
- `[TABS-INITCB] <container> ejecutando initCallback? function` → el JS del módulo se inicializó.
- `[TABS-MIGRATE] <container> <vieja> -> <nueva>` → migración de sección aplicada.
- `[TABS-RESTORE] ...` → restauración de pestañas al cargar la sección.

---

## Checklist final

```
[ ] <li> quitado de LISTA vieja, agregado a LISTA nueva con data-permiso-* nuevos
[ ] mostrar<Modulo>() usa prepararPanelSeccion('<nueva>')
[ ] mostrar<Modulo>() muestra explicitamente el área donde vive el <div>
[ ] handler navbar de la sección nueva (scriptMain) muestra esa área
[ ] container quitado de TODAS las copias de la hide-list de la sección vieja
[ ] SECCIONES_AREAS_MAP (sidebar-tabs) mapea la sección nueva al área correcta
[ ] conflicto de área compartida manejado (exclusión + RESUELTOS_EXPLICITO)
[ ] migrarTabsMovidas() tiene la entrada {container, de, a}
[ ] ?v= subido en MainTemplate para scriptMain.js, sidebar-tabs.js, y JS/CSS del módulo
[ ] server reiniciado + Ctrl+Shift+R
[ ] permisos sincronizados y reasignados al rol
[ ] PROBADO: click en el botón carga y se ve (no gris)
[ ] PROBADO: navegar a otra sección y volver, el módulo sigue bien
[ ] PROBADO: reiniciar con la pestaña abierta -> se restaura en la sección nueva
```

---

## Changelog

### 2026-06-23 — v1.0
- Documento inicial. Caso real: Trazabilidad de PCB de Control de resultados a
  Control de reporte / Product Tracking.
- Documenta los 4 lugares con estado por sección + migración de localStorage +
  manejo de áreas compartidas (secciones sin área propia).
- Agrega snippet de diagnóstico de DOM y guía de logs del sistema de tabs.
