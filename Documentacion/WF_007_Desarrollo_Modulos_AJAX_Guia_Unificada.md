# WF_007 - Desarrollo de Modulos AJAX: Guia Unificada

> **Estado:** Documento homologado
> **Origen:** Consolida `GUIA_DESARROLLO_MODULOS_MES.md`, `INSTRUCCIONES-IMPLEMENTACION-AJAX.md` e `Implementar AJAX.md`
> **Relacionado:** `WF_001`, `WF_002`, `WF_003`, `WF_004`, `WF_005`

---

## Resumen

Esta guia concentra el flujo practico para crear o modificar modulos AJAX dentro del MES. Complementa los documentos `WF_001` a `WF_005`; no los reemplaza en detalle, sino que actua como checklist operativo unificado.

Usar este documento cuando se necesite implementar un modulo completo desde cero o migrar una implementacion legacy al patron actual.

## Principio Base

Cada modulo AJAX debe tener:

1. Un template HTML cargable como fragmento.
2. IDs unicos con prefijo o sufijo propio.
3. CSS persistente o cargado de forma segura.
4. JS inicializable despues de cada carga AJAX.
5. Ruta Flask bajo blueprint, no en `routes.py` para desarrollos nuevos.
6. Permiso sincronizable desde LISTAS y BD.
7. Manejo robusto de errores de red, sesion y permisos.

## Flujo Recomendado

### 1. Definir Identidad del Modulo

| Dato | Ejemplo |
|---|---|
| Seccion | `control_proceso` |
| Nombre funcional | `Control BOM` |
| Prefijo de IDs | `bom` |
| Contenedor | `bom-unique-container` |
| Template | `control_bom_ajax.html` |
| Funcion de navegacion | `mostrarControlBOM()` |
| Blueprint | `app/api/control_proceso/control_bom.py` |

Regla: no reutilizar IDs genericos como `tabla`, `modal`, `btnGuardar` o `filtroFecha`. Usar IDs especificos: `bom-tabla`, `bom-modal`, `bom-btn-guardar`, `bom-filtro-fecha`.

### 2. Crear Template HTML

El template debe ser un fragmento, no una pagina completa:

```html
<section id="bom-root" class="bom-module">
  <header class="bom-toolbar">
    <h2>Control BOM</h2>
  </header>

  <div class="bom-content">
    <!-- filtros, tabla y acciones -->
  </div>
</section>
```

Evitar:

- `<html>`, `<head>` y `<body>` dentro del fragmento.
- Scripts inline innecesarios.
- Modales estaticos dentro del contenedor si se van a reutilizar despues de navegacion AJAX. Ver `WF_008`.

### 3. Crear CSS

Preferir archivo CSS propio cuando el modulo crece:

```text
app/static/css/<modulo>.css
```

El CSS debe cargarse de forma persistente desde el layout principal o mediante el patron documentado en `WF_004`.

Reglas:

- No depender de que el `<style>` del fragmento AJAX sobreviva a navegaciones.
- Evitar selectores globales que afecten otros modulos.
- Prefijar clases del modulo.

### 4. Crear JS del Modulo

El JS debe exponer un inicializador global idempotente:

```javascript
window.initializeControlBom = function initializeControlBom() {
  const root = document.getElementById("bom-root");
  if (!root || root.dataset.initialized === "true") return;

  root.dataset.initialized = "true";
  root.addEventListener("click", (event) => {
    const target = event.target;
    if (target.matches("[data-bom-action='consultar']")) {
      window.loadControlBomData?.();
    }
  });
};
```

Reglas:

- Usar event delegation cuando el contenido se recrea por AJAX.
- No depender solo de `DOMContentLoaded`; el modulo puede cargarse despues.
- Exponer funciones requeridas por `scriptMain.js` en `window`.
- Evitar inicializar dos veces el mismo contenedor.

### 5. Crear Ruta Flask en Blueprint

Para desarrollos nuevos, no agregar rutas de modulo a `app/routes.py`.

```python
from flask import Blueprint, render_template
from app.api.shared import login_requerido

bp = Blueprint("control_bom", __name__, url_prefix="/control-proceso")


@bp.route("/control-bom")
@login_requerido
def control_bom_view():
    return render_template("Control de proceso/control_bom_ajax.html")
```

Registrar el blueprint en `app/api/__init__.py` siguiendo el patron existente.

### 6. Crear Funcion `mostrar*`

Patron actual:

```javascript
window.mostrarControlBOM = function mostrarControlBOM() {
  window.prepararPanelSeccion("proceso");

  const container = document.getElementById("bom-unique-container");
  if (container) {
    container.style.display = "block";
  }

  cargarContenidoDinamico("bom-unique-container", "/control-proceso/control-bom", () => {
    if (typeof window.initializeControlBom === "function") {
      window.initializeControlBom();
    }
  });
};
```

Para Informacion Basica usar `prepararPanelInformacionBasica()`.

### 7. Agregar Boton al Sidebar

En el archivo `LISTA_*.html` correspondiente:

```html
<li
  data-permiso-modulo="Control de proceso"
  data-permiso-vista="Control BOM"
  onclick="mostrarControlBOM()"
>
  Control BOM
</li>
```

Despues sincronizar permisos y asignarlos al rol correspondiente.

### 8. Manejo de Errores

Todo fetch de datos debe contemplar:

- `401` o redireccion a login.
- `403` permiso denegado.
- `404` ruta no registrada.
- `500` error de backend.
- Respuesta JSON invalida.
- Estado vacio de tabla.

### 9. Verificacion Manual

| Prueba | Resultado esperado |
|---|---|
| Click en navbar | Se carga la LISTA correcta. |
| Click en item del sidebar | Se abre tab/contenedor correcto. |
| Recargar pagina con tab abierto | Se restaura sin romper layout. |
| Navegar a otra seccion y volver | El modulo se reinicializa correctamente. |
| Usuario sin permiso | No ve el boton o recibe denegacion controlada. |
| Consola navegador | Sin errores JS. |
| Backend | Sin traceback en Flask. |

## Relacion con WF Existentes

| Documento | Cuando usarlo |
|---|---|
| `WF_001` | Cuando se agrega boton, LISTA o seccion al sidebar. |
| `WF_002` | Cuando se crea template HTML/CSS/JS completo. |
| `WF_003` | Cuando se integra API JSON, query SQL y exportacion Excel. |
| `WF_004` | Cuando hay problemas de estilos en modulos AJAX. |
| `WF_005` | Cuando los permisos de dropdown fallan por caracteres especiales. |
| `WF_008` | Cuando el modulo usa modales. |

## Documentos Legacy Cubiertos

- `GUIA_DESARROLLO_MODULOS_MES.md`
- `INSTRUCCIONES-IMPLEMENTACION-AJAX.md`
- `Implementar AJAX.md`

Los documentos legacy se mantienen como referencia historica, pero para nuevos desarrollos se debe seguir esta guia y los `WF_001` a `WF_005`.
