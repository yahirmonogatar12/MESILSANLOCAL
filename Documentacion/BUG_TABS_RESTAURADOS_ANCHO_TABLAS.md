# Bug: Tablas desplazadas al restaurar tabs de embarques tras F5

> **Fecha:** 2026-05-22
> **Estado:** Resuelto
> **Severidad:** Media (visual, no afecta datos)
> **Modulos afectados:** Almacen de embarques (entradas, salidas, retorno, movimientos, catalogo, inventario general)
> **Archivos modificados:**
> - `app/static/js/almacen_embarques_history.js`
> - `app/static/js/almacen_embarques_admin.js`
> - `app/static/js/sidebar-tabs.js`

---

## Sintoma

Con uno o mas tabs de Almacen de embarques abiertos, al recargar la pagina (F5):

1. El tab que estaba activo se restaura correctamente.
2. Los **tabs inactivos**, al hacerles click para verlos, aparecen con la tabla **desplazada hacia la derecha** (las columnas no encajan en el viewport, hay scroll horizontal innecesario o las cabeceras no se alinean con las celdas).
3. El bug se "arregla solo" al disparar un reflow del navegador:
   - Click en **Consultar** -> recarga datos y recalcula layout.
   - Abrir **DevTools (F12)** -> el cambio de viewport dispara `window.resize`.
   - Cualquier resize manual de la ventana.

## Causa raiz

Los modulos de embarques usan tablas con `table-layout: fixed` y columnas redimensionables (ver `almacen_embarques_history.css` y la funcion `bindColumnResizers`). Los anchos de cada columna se calculan en JS a partir de:

```js
function getAvailableTableWidth(tableShell) {
  const bodyWrap = tableShell.querySelector(".ae-table-body-wrap");
  return Math.max(1, Math.floor(bodyWrap?.clientWidth || tableShell.clientWidth || 0));
}
```

y se persisten en `localStorage` con clave `ae-column-widths:<moduleId>:<shellIndex>:<signature>`.

### Flujo del bug

1. **Usuario tiene N tabs de embarques abiertos** y recarga (F5).
2. `sidebar-tabs.js` -> `restaurarTabsDeSeccion()` lee el state de `localStorage` y, **para cada tab guardado**, ejecuta su `onclick` (la funcion `mostrar*` del modulo).
3. Cada modulo se inyecta dentro de su `*-unique-container`. Solo el tab marcado como `active` queda con `display: block`; los demas con `display: none`.
4. Cada modulo corre su inicializador (`inicializarAlmacenEmbarques*Ajax`), que llama a `bindColumnResizers` -> `getInitialColumnWidths` -> `getAvailableTableWidth`.
5. Para los **tabs ocultos**, `bodyWrap.clientWidth === 0` porque su contenedor padre tiene `display:none`. La funcion devuelve `1`.
6. `normalizeWidthsToAvailable(widths, labels, 1, {...})` escala todos los anchos a ~1px y los aplica como inline styles en cada `<col>`. El total del `<table>` queda en pocos pixeles.
7. El flag `tableShell.dataset.columnWidthsReady = "true"` se setea para evitar recalcular.
8. Cuando el usuario hace click en el tab, `switchTab` lo muestra (`display: block`), pero el codigo del modulo **no observa** ese cambio y los anchos diminutos persisten.
9. Cualquier evento que dispare un `window.resize` o un `loadModule()` (Consultar) llama a `bindColumnResizers` con `availableWidth` correcto y se arregla.

### Por que pasaba en algunos modulos y no otros

Inicialmente solo se aplico el fix con ResizeObserver a `almacen_embarques_history.js` (entries/exits/returns). Sin embargo:

- **Salidas/Retorno** funcionaron porque el ResizeObserver del `moduleRoot` detecto la transicion `width: 0 -> width real` al hacerse visible.
- **Entradas** seguia fallando porque su layout particular no disparaba el observer de forma fiable.
- **Inventario general** estaba implementado en `almacen_embarques_admin.js` (no en history.js), donde el fix aun no estaba aplicado.
- **Movimientos/Catalogo** tambien viven en admin.js.

## Solucion aplicada

### 1. ResizeObserver en ambos archivos (defensa en profundidad)

En `almacen_embarques_history.js` (`bindModuleResize`) y `almacen_embarques_admin.js` (`bindModule`, bloque inline tras `bindColumnResizers`):

```js
if (typeof ResizeObserver === "function" && !moduleRoot.__aeResizeObserver) {
  let lastWidth = Math.floor(moduleRoot.getBoundingClientRect().width || 0);
  const ro = new ResizeObserver((entries) => {
    for (const entry of entries) {
      const width = Math.floor(entry.contentRect?.width || 0);
      if (width <= 0) continue;
      if (Math.abs(width - lastWidth) < 1) continue;
      const transicionDesdeOculto = lastWidth === 0;
      lastWidth = width;
      if (transicionDesdeOculto) {
        // Invalidar caches de ancho de columna (pudieron haberse calculado
        // con width=0 durante restauracion de tabs en F5).
        moduleRoot.querySelectorAll(".ae-table-shell").forEach((shell) => {
          delete shell.dataset.columnWidthsReady;
        });
      }
      updateHeight();
    }
  });
  ro.observe(moduleRoot);
  moduleRoot.__aeResizeObserver = ro;
}
```

**Puntos clave:**
- Se guarda el observer en `moduleRoot.__aeResizeObserver` para no duplicar.
- Solo dispara cuando hay un cambio real de ancho (≥1px) y el ancho actual es > 0.
- Cuando detecta `lastWidth === 0` (transicion desde oculto), **borra el flag `columnWidthsReady`** de todos los `.ae-table-shell` para que `bindColumnResizers` reentre y recalcule desde cero con el ancho correcto.

### 2. Red de seguridad en `sidebar-tabs.js`

En la funcion `switchTab`, despues de `markActive(area, containerId)`:

```js
// Red de seguridad: algunos modulos (ej. embarques) calculan
// anchos de tabla a partir de clientWidth. Si se restauraron tras
// un F5 mientras estaban ocultos, midieron 0 y quedaron mal hasta
// que algo dispare reflow. Forzar 'resize' tras el switch los
// hace recalcular sin acoplar sidebar-tabs a cada modulo.
requestAnimationFrame(() => {
    try { window.dispatchEvent(new Event('resize')); } catch (e) {}
});
```

Esto resuelve el caso donde el `ResizeObserver` no dispara de forma fiable (entradas) y sirve como fallback universal para cualquier modulo futuro que dependa de mediciones de viewport.

## Verificacion

1. Abrir 4-5 tabs de embarques distintos (entradas, salidas, retorno, inventario general, movimientos).
2. Recargar la pagina (F5).
3. Hacer click en cada tab restaurado.
4. **Esperado:** cada tabla aparece con sus columnas alineadas y ocupando el ancho disponible.
5. **Anterior al fix:** las tablas aparecian apretadas a la izquierda con scroll horizontal y cabeceras desalineadas hasta hacer click en Consultar o abrir DevTools.

## Lecciones para nuevos modulos

Si desarrollas un modulo nuevo que calcula widths/heights a partir de `clientWidth`, `offsetWidth` o `getBoundingClientRect()`:

- **No confies** en que el container este visible en el momento del init. El sistema de tabs restaura modulos ocultos.
- **Agrega un `ResizeObserver`** sobre el moduleRoot que detecte la transicion 0 -> width real e invalide cualquier cache derivado.
- El `window.resize` que dispara `switchTab` ya es una red de seguridad — si tu modulo escucha `resize` y recalcula, te beneficias automaticamente.
- Considera persistir solo dimensiones que tengan sentido (`> minWidth * N`) para evitar guardar valores corruptos en `localStorage`.

## Relacionado

- [PLAN_REFACTOR_CONTENEDOR_UNICO.md](PLAN_REFACTOR_CONTENEDOR_UNICO.md) — cuando se implemente el refactor a contenedor unico, este patron seguira siendo necesario porque los containers inactivos seguiran ocultos durante restauracion.
- [GUIA_DESARROLLO_MODULOS_MES.md](GUIA_DESARROLLO_MODULOS_MES.md) — guia general de desarrollo de modulos.
- [WF_004_Estilos_Persistentes_Modulos_AJAX.md](WF_004_Estilos_Persistentes_Modulos_AJAX.md) — patrones relacionados con estilos al recargar via AJAX.
