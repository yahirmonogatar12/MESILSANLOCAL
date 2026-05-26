# Plan: Refactor estructural a contenedor único universal

> **Fecha:** 2026-05-22
> **Estado:** Pendiente de implementación
> **Prerequisito:** Sistema de tabs globales ya implementado (`#global-tabs-bar`, `sidebar-tabs.js`)
> **Relacionado:** WF_001, WF_002, WF_003, WF_004, GUIA_DESARROLLO_MODULOS_MES.md

## Contexto

El sistema actual del MES tiene **6 `*-content-area`** (uno por sección navbar), cada uno con sus propios `*-unique-container` y `*-info-container` hijos. Esta arquitectura provoca bugs visuales recurrentes:

- Placeholders (`*-info-container`) que se mostraban junto al contenido real
- Reglas CSS específicas por módulo (ej. `:has(> #x[style*="display: block"])`) que sobrescriben el ocultado de áreas
- Containers viejos que quedan visibles al cambiar entre tabs/secciones
- Cada nuevo módulo requiere agregar entradas a `hideAllMaterialContainers`, `hideAllInformacionBasicaContainers`, mapas `SECCIONES_AREAS`, listas en `scriptMain.js`, etc.

La barra de tabs ya es **global** (un solo `#global-tabs-bar` fijo debajo del navbar). El siguiente paso lógico es: **un solo div universal** donde TODOS los módulos cargan su contenido, eliminando los content-areas intermedios. Esto:

- Elimina ~70 placeholders distintos
- Hace que cualquier módulo nuevo "funcione automáticamente" sin tocar listas/mapas
- Reduce CSS específico (ej. la regla `:has(> #x[display:block])` desaparece junto con el `*-content-area` padre)
- Acopla el sistema de tabs 1:1 con el contenedor (un tab = un slot de contenido en el universal)

Persistencia (`mes_tabs_v1`, `mes_nav_active_v1`, `mes_sidebar_item_v1`) se mantiene compatible.

## Diseño

### Estructura nueva en `MainTemplate.html`

```html
<header class="app-header">...</header>
<div id="global-tabs-bar"></div>  <!-- ya existe -->

<div class="main-wrapper-universal">
  <!-- Sidebars izquierdos (uno visible a la vez, segun pestaña navbar) -->
  <aside id="universal-sidebar">
    <!-- Aqui se inyectan dinamicamente los .app-sidebar de cada LISTA_*.html -->
  </aside>

  <!-- Area de contenido UNICA -->
  <main id="universal-content">
    <!-- Aqui van TODOS los containers de modulos.
         Cada modulo tiene su propio div hijo aqui (no en distintos *-content-area).
         Solo el container del tab activo tiene display:block; los demas display:none. -->
  </main>
</div>
```

### Migración de containers

- Todos los **`*-unique-container`** se mueven como hijos directos de `#universal-content` (vía script de migración o reescritura manual del HTML).
- Todos los **`*-info-container`** que son módulos reales (BOM, Material, Modelos, etc.) también se mueven a `#universal-content`.
- Los **placeholders de "info default"** (`info-basica-default-container`, `material-info-container`, `produccion-info-container`, `control-proceso-info-container`, `control-resultados-info-container`) se eliminan o reemplazan por un solo `#welcome-placeholder` global que se muestra cuando NO hay tabs abiertos.
- Los **`*-content-area`** (`material-content-area`, `produccion-content-area`, etc.) se **eliminan completamente**.

### Migración de funciones `mostrar*()`

Cada función `mostrar*` (hay ~50 distribuidas entre `MainTemplate.html` y `scriptMain.js`) se reescribe a la forma mínima:

```js
window.mostrarXxx = function() {
  ensureUniversalContainer('xxx-unique-container');
  cargarContenidoDinamico('xxx-unique-container', '/ruta/xxx', initCb);
};
```

Donde:
- `ensureUniversalContainer(id)` crea el div como hijo de `#universal-content` si no existe (eliminando la necesidad de declararlos pre-renderizados en `MainTemplate.html`).
- Las llamadas a `prepararPanelSeccion`, `hideAllMaterialContainers`, `hideAllInformacionBasicaContainers` **se eliminan** porque el sistema de tabs gestiona la visibilidad.

### Migración de `sidebar-tabs.js`

- `findAreaFor(containerId)` siempre devuelve `#universal-content`.
- `markActive` solo recorre hijos directos de `#universal-content`, sin lógica de placeholders (ya no existen).
- `ensureGlobalTabsBar` sigue igual.
- `containerToNavTab` y el flujo de cambio de navbar al click se mantienen sin cambios.

### Migración del sidebar izquierdo (LISTAS)

Las funciones `mostrarControlMaterial()`, `mostrarControlProduccion()`, etc. (las del navbar) hoy hacen `cargarSidebarDinamico('xxx-content', '/listas/xxx')`. Esto reemplaza el contenido de `#informacion-basica-content`, `#control-material-content`, etc.

Nueva versión: existe **un solo `#universal-sidebar`** que se recarga con la lista correspondiente al click del navbar. Los `*-content` (sidebar wrappers) se eliminan.

### Persistencia (sin cambios)

El localStorage actual (`mes_tabs_v1`) ya guarda `{ container, label, path, onclick, navTab }` por sección. La estructura es compatible — solo cambia que `container` apunta a un div hijo de `#universal-content` en lugar de a un div hijo de `*-content-area`. El campo `navTab` sigue indicando a qué sección navbar pertenece (para mostrar el sidebar correcto).

## Implementación por fases

### Fase 1: Preparación (sin cambios visibles)
1. Crear `#universal-content` y `#universal-sidebar` en `MainTemplate.html` (vacíos, `display: none` por defecto).
2. Crear funciones helper `ensureUniversalContainer(id)`, `getUniversalContent()`, `moveToUniversal(id)`.
3. Crear `#welcome-placeholder` con el mensaje "Seleccione una opción del menú".

### Fase 2: Migrar `mostrar*()` por sección
Por cada sección navbar (Información Básica, Material, Producción, Proceso, Calidad, Resultados, Reporte, Configuración):
1. Reescribir todas sus funciones `mostrar*` para usar `ensureUniversalContainer` + `cargarContenidoDinamico`.
2. Eliminar referencias a `prepararPanelSeccion`, `hideAll*Containers`, `*-content-area`.
3. Cambiar la función padre `mostrarControlXxx()` (navbar handler) para que solo cargue la LISTA en `#universal-sidebar`.
4. Probar la sección antes de pasar a la siguiente.

### Fase 3: Limpiar HTML estructural
1. Borrar los 6 `*-content-area` del `MainTemplate.html`.
2. Borrar los `*-content` sidebar wrappers (`informacion-basica-content`, etc.).
3. Borrar los ~30 `*-info-container` placeholders pre-renderizados.
4. Borrar los `*-unique-container` pre-declarados (ahora `ensureUniversalContainer` los crea on-demand).

### Fase 4: Limpiar JS
1. Borrar `hideAllMaterialContainers`, `hideAllInformacionBasicaContainers`, `ocultarOtrasSecciones`, `prepararPanelSeccion`, `prepararPanelInformacionBasica`, `SECCIONES_AREAS`, `SECCIONES_SIDEBARS`.
2. Borrar las listas duplicadas `controlResultadosContainers`, etc. en `scriptMain.js`.
3. Simplificar `findAreaFor` en `sidebar-tabs.js` para devolver siempre `#universal-content`.
4. Borrar `markActive` lógica de placeholders (líneas 116-124 de sidebar-tabs.js).

### Fase 5: Limpiar CSS
1. Borrar reglas de `*-content-area` en `style.css` (líneas 416-501 aprox).
2. Borrar `.mes-area-hidden`, reglas con `:has(> .section-tabs-bar)`.
3. Borrar reglas en módulos específicos como `almacen_embarques_history.css` líneas 13-47 que hacen `#control-proceso-content-area:has(...)`.
4. Reglas de `#universal-content` (height, overflow, padding).

### Fase 6: Migración de localStorage existente
Al cargar la app por primera vez post-refactor, leer `mes_tabs_v1` y para cada tab guardado: ejecutar su `onclick` para que `ensureUniversalContainer` lo cree con el nuevo flujo. El localStorage existente sigue siendo válido porque solo guarda IDs + onclick.

## Archivos a modificar

| Archivo | Cambio |
|---|---|
| `app/templates/MainTemplate.html` | Reescribir estructura HTML (líneas 348-845). Reescribir ~30 `window.mostrar*Info` (líneas 2400-2700) |
| `app/static/js/scriptMain.js` | Reescribir ~25 funciones `mostrar*` (líneas 750-3800). Eliminar variables locales de containers (líneas 1-300) |
| `app/static/js/sidebar-tabs.js` | Simplificar `findAreaFor`, `markActive`, eliminar lógica de placeholders |
| `app/static/css/sidebar-tabs.css` | Reescribir reglas de áreas. Añadir `#universal-content`, `#universal-sidebar` |
| `app/static/style.css` | Borrar reglas de `*-content-area`, `*-content` sidebars (~líneas 389-600) |
| `app/static/css/almacen_embarques_history.css` | Borrar reglas con `:has(> #x-unique-container[style*="display: block"])` líneas 13-47 |
| `app/static/css/control_material.css` | Verificar que selectores `#control-material-info-container` sigan funcionando |
| `app/templates/MainTemplate.html` (líneas 1230-1500) | Simplificar `loadCurrentSidebarContent`, `loadListContent`, mobile menu |

## Funciones existentes a reutilizar

- `window.cargarContenidoDinamico(containerId, path, initCallback)` — sigue siendo el loader AJAX principal (MainTemplate.html línea 1888)
- `window.cargarSidebarDinamico(containerId, path)` — para cargar el sidebar (MainTemplate.html línea 2068)
- `window.sidebarTabs.openTab/closeTab/switchTab` — API de tabs existente
- `ejecutarScriptsDinamicos(container)` — re-ejecuta scripts inline al inyectar HTML (MainTemplate.html línea 1823)
- `inicializarContenidoDinamico(container, initCallback)` — corre tooltips Bootstrap + initCallback (línea 1870)

## Verificación end-to-end

1. **Estructura limpia**: inspeccionar el DOM en DevTools, verificar que solo existen `#global-tabs-bar`, `#universal-sidebar`, `#universal-content` como contenedores principales. Los `*-content-area` deben estar ausentes.
2. **Carga de módulo**: ir a "Control de proceso" → "IMD-SMD TERMINADO" → debe aparecer como tab y el contenido cargar dentro de `#universal-content`. Click en "Consultar" debe funcionar.
3. **Tabs cross-section**: abrir un tab en "Control de proceso", cambiar a "Información Básica", abrir "Control de BOM". La barra global debe tener ambos tabs; click en cualquiera debe regresar a su sección navbar.
4. **Persistencia F5**: con varios tabs abiertos en distintas secciones, recargar. Todos deben restaurarse y abrir el último activo.
5. **No hay placeholders visibles**: nunca debe aparecer el `info-basica-default-container` ni `control-proceso-info-container` cuando hay un tab abierto. Inspeccionar DOM con DevTools.
6. **Permisos siguen funcionando**: los `data-permiso-*` en las LISTAS siguen aplicando (no se tocan).
7. **Sin errores en consola**: `F12` no debe mostrar `Cannot read property of null` ni errores de Bootstrap Collapse.
8. **Móvil**: probar el hamburger menu y verificar que sigue mostrando las listas correctamente.

## Riesgo y mitigación

- **Riesgo alto**: 1,384 referencias en 151 archivos a cambiar. Cualquier `mostrar*` que se olvide quedará roto.
- **Mitigación**:
  - Hacer el refactor en una rama git separada (`git checkout -b refactor-universal-container`).
  - Implementar **por sección navbar**: Información Básica primero (módulos más simples), luego Control de Proceso (la sección con más módulos). Probar cada sección antes de pasar a la siguiente.
  - En Fase 3 NO borrar los content-areas inmediatamente. Dejarlos con `display: none !important` durante 1-2 sesiones de uso para validar que ninguna `mostrar*` olvidada quedó apuntando a ellos. Después borrarlos.
  - Mantener los nombres de IDs originales de los `*-unique-container` para no romper el localStorage existente ni los `onclick` de las LISTAS.
