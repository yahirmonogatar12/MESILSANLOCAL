# WF_004 — Persistencia de Estilos CSS en Módulos AJAX del Portal

> **Versión:** 1.0  
> **Fecha:** 2026-04-10  
> **Prerequisitos:** [WF_001](./WF_001_Nuevos_Modulos_AJAX_Templates.md), [WF_002](./WF_002_Crear_Template_Completo.md), [WF_003](./WF_003_Integracion_API_JS_Template.md)  
> **Caso real:** Módulo **Almacén de Embarques** en `Control de proceso`

---

## Resumen

Este documento describe un problema real detectado al implementar los módulos AJAX de **Entradas almacén embarques**, **Salidas almacén embarques** y **Retorno almacén embarques** dentro del portal corporativo de `MESILSANLOCAL`.

El síntoma fue que los estilos personalizados inspirados en `ict-Pass-Fail.css`:

- se aplicaban correctamente una sola vez,
- o solo cargaban en uno de los módulos,
- mientras que otros módulos regresaban a una apariencia genérica o parcialmente sin estilo.

La causa raíz no estaba únicamente en el CSS, sino en la forma en que el portal carga **templates HTML por AJAX** dentro de un layout persistente.

---

## Problema Observado

### Síntomas

Durante la implementación de `Almacén de Embarques` se detectó que:

1. `Retorno almacén embarques` mostraba el estilo correcto.
2. `Entradas almacén embarques` y `Salidas almacén embarques` podían aparecer con estilos genéricos.
3. En algunos casos los estilos se veían bien solo en la primera carga y después desaparecían al navegar entre módulos.
4. Un hard refresh temporalmente corregía el problema, pero no de forma consistente.

### Impacto

- La interfaz quedaba visualmente inconsistente.
- Parecía que el CSS nuevo “no estaba cargando”, cuando en realidad había una mezcla entre caché, orden de carga y contenido AJAX.
- El problema podía confundirse con un error de HTML o con reglas CSS faltantes.

---

## Contexto Técnico

El portal usa esta arquitectura:

1. `MaterialTemplate.html` funciona como layout principal.
2. El contenido de cada módulo se inyecta dinámicamente vía AJAX.
3. Los módulos `Entradas`, `Salidas` y `Retorno` comparten:
   - `app/static/css/almacen_embarques_history.css`
   - `app/static/js/almacen_embarques_history.js`

Esto introduce una diferencia importante frente a una página tradicional:

- el layout principal **permanece vivo**,
- pero los fragments HTML cambian,
- y cualquier `<link rel="stylesheet">` dentro del fragment AJAX **no debe considerarse confiable como única estrategia de carga**.

---

## Causa Raíz

La incidencia fue causada por la combinación de estos factores:

### 1. CSS dependiente del fragment AJAX

Si el stylesheet solo vive dentro del template AJAX cargado dinámicamente, su aplicación puede ser inconsistente entre navegaciones.

### 2. Caché del navegador / servidor

El archivo `almacen_embarques_history.css` cambió varias veces durante la iteración visual. Sin un cambio de versión en la URL, el navegador podía seguir usando una versión anterior.

### 3. Layout persistente + módulos intercambiables

Aunque `MaterialTemplate.html` sigue visible todo el tiempo, los módulos AJAX pueden inicializarse en distinto orden. Eso hacía posible que un módulo renderizara antes de que el stylesheet correcto estuviera garantizado en `head`.

---

## Solución Aplicada

La solución final se implementó en **dos capas**.

### Capa 1 — Carga persistente del CSS desde el layout principal

Se agregó la hoja compartida al `<head>` de `MaterialTemplate.html`:

**Archivo:**
`app/templates/MaterialTemplate.html`

**Implementación:**

```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/almacen_embarques_history.css', v='20260410c') }}">
```

Esto asegura que el CSS exista en el layout base y no dependa únicamente del fragment HTML cargado por AJAX.

### Capa 2 — Seguro adicional desde el JS del módulo

En el JS compartido del módulo se agregó una rutina que verifica que el stylesheet exista en `document.head` y, si no existe o tiene versión vieja, lo inserta/actualiza.

**Archivo:**
`app/static/js/almacen_embarques_history.js`

**Implementación:**

```javascript
const STYLESHEET_ID = "almacen-embarques-history-css";
const STYLESHEET_HREF = "/static/css/almacen_embarques_history.css?v=20260410c";

function ensureModuleStyles() {
  const currentLink = document.getElementById(STYLESHEET_ID);
  if (currentLink) {
    if (!currentLink.getAttribute("href")?.includes("20260410c")) {
      currentLink.setAttribute("href", STYLESHEET_HREF);
    }
    return;
  }

  const link = document.createElement("link");
  link.id = STYLESHEET_ID;
  link.rel = "stylesheet";
  link.href = STYLESHEET_HREF;
  document.head.appendChild(link);
}
```

Y esa función se ejecuta al inicializar cada módulo:

```javascript
function initializeModule(config) {
  ensureModuleStyles();
  ...
}
```

---

## Archivos Involucrados

| Archivo | Rol |
|--------|-----|
| `app/templates/MaterialTemplate.html` | Layout persistente; carga global del stylesheet |
| `app/static/js/almacen_embarques_history.js` | Garantiza la presencia y versión del CSS en `head` |
| `app/static/css/almacen_embarques_history.css` | Hoja compartida de Entradas/Salidas/Retorno |
| `app/templates/Control de proceso/almacen_embarques_entradas_ajax.html` | Template AJAX del historial de entradas |
| `app/templates/Control de proceso/almacen_embarques_salidas_ajax.html` | Template AJAX del historial de salidas |
| `app/templates/Control de proceso/almacen_embarques_retorno_ajax.html` | Template AJAX del historial de retorno |

---

## Regla de Implementación para Nuevos Módulos AJAX

Cuando se cree un nuevo módulo con CSS propio dentro del portal:

1. **No depender solo del `<link>` dentro del fragment AJAX.**
2. Registrar el stylesheet en el layout principal si será reutilizado por varios templates.
3. Agregar **cache-busting** (`?v=...`) cada vez que cambie el CSS.
4. Si el módulo es crítico o compartido, agregar una función JS tipo `ensureModuleStyles()` que inserte el `<link>` en `head`.
5. Evitar mezclar múltiples versiones del mismo stylesheet bajo URLs distintas.

---

## Checklist de Diagnóstico

Si un módulo AJAX “pierde” estilos o solo uno de varios módulos se ve correcto, revisar en este orden:

1. Confirmar que el CSS esté cargado en `head`.
2. Confirmar que el `href` del stylesheet tenga la versión nueva.
3. Confirmar que el HTML del módulo use las clases nuevas esperadas por el CSS.
4. Revisar si el browser está usando una versión vieja del archivo estático.
5. Hacer hard refresh.
6. Reiniciar el servicio del portal si usa caché de templates/estáticos.

---

## Lecciones Aprendidas

- En `MESILSANLOCAL`, los módulos AJAX deben tratarse como **fragments de una SPA ligera**, no como páginas aisladas.
- El CSS compartido de módulos dinámicos debe manejarse como **recurso persistente del layout**, no como asset local de cada fragment.
- Cuando hay cambios visuales iterativos, el **cache-busting es obligatorio**.
- Si un problema visual aparece “solo en un módulo”, la causa puede ser el **ciclo de vida del layout y no el CSS del módulo en sí**.

---

## Resultado Esperado Después de la Corrección

Después de aplicar esta estrategia:

- `Entradas almacén embarques`
- `Salidas almacén embarques`
- `Retorno almacén embarques`

deben compartir la misma apariencia visual basada en `ict-Pass-Fail.css`, de forma consistente entre navegaciones internas.

---

## Nota Operativa

Después de modificar CSS, templates o carga de assets en el portal:

1. actualizar el parámetro `v=...` del stylesheet,
2. hacer recarga forzada del navegador,
3. y, si es necesario, reiniciar el servicio de `MESILSANLOCAL`.

Sin esos pasos, puede parecer que el cambio “no se aplicó”, aunque el código ya esté correcto.
