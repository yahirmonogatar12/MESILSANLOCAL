# WF_010 - Refactor de Arquitectura Backend y UI

> **Estado:** Documento homologado
> **Origen:** Consolida `PLAN_REFACTORIZAR_ROUTES.md` y `PLAN_REFACTOR_CONTENEDOR_UNICO.md`
> **Uso:** Seguimiento de refactors estructurales del backend y del shell visual.

---

## Resumen

El proyecto tiene dos lineas principales de refactor:

1. Reducir `app/routes.py` y mover ownership de modulos a blueprints bajo `app/api/`.
2. Simplificar la arquitectura de contenedores UI hacia un contenedor universal.

La primera linea ya aparece avanzada/completada por fases en la documentacion original. La segunda esta documentada como plan pendiente o futuro.

## Objetivo General

Reducir acoplamiento entre modulos, simplificar el alta de nuevas pantallas AJAX y evitar bugs visuales por contenedores anidados, placeholders y duplicacion de funciones `mostrar*`.

## Refactor Backend: `routes.py` a Blueprints

### Principio Rector

`app/routes.py` debe quedarse como nucleo transversal y compatibilidad legacy. Los modulos nuevos deben vivir en:

```text
app/api/<seccion>/<modulo>.py
```

Registrados desde:

```text
app/api/__init__.py
```

### Debe Quedarse en `routes.py`

- Configuracion transversal de app si aplica.
- Helpers compartidos legacy aun no migrados.
- Health checks.
- Rutas centrales antiguas que todavia no tienen blueprint.
- Rutas LISTAS actuales mientras no exista ownership nuevo.

### No Debe Agregarse a `routes.py`

- Rutas nuevas de templates AJAX.
- APIs JSON de modulos nuevos.
- Exportaciones Excel nuevas.
- Logica de negocio especifica de un dominio.

## Fases Backend Homologadas

| Fase | Objetivo | Estado segun legacy |
|---|---|---|
| 0 | Snapshot inicial | Referencia |
| 1 | Borrar rutas huerfanas | Completada 2026-05-28 |
| 2 | Limpiar reexports zombies | Completada 2026-05-28 |
| 3 | Mover renders cortos a blueprints | Completada 2026-05-28 |
| 4 | Mover rutas grandes a blueprints | Completada 2026-05-28 |
| 5 | Borrar helpers huerfanos e imports muertos | Completada 2026-05-28 |
| 6 | Extraer auth/sesion a blueprint propio | Completada 2026-05-28 |

## Refactor UI: Contenedor Universal

### Problema Actual

El shell historico tiene multiples `*-content-area` y muchos contenedores hijos. Esto provoca:

- Placeholders visibles junto al contenido real.
- Containers viejos que quedan visibles al cambiar de tab/seccion.
- CSS especifico dificil de mantener.
- Necesidad de actualizar mapas/listas por cada modulo nuevo.
- Bugs al restaurar tabs o medir anchos en contenedores ocultos.

### Diseno Propuesto

```html
<header class="app-header">...</header>
<div id="global-tabs-bar"></div>

<div class="main-wrapper-universal">
  <aside id="universal-sidebar"></aside>
  <main id="universal-content"></main>
</div>
```

Regla: todos los modulos cargan como hijos directos de `#universal-content`. El sidebar de la seccion activa se inyecta en `#universal-sidebar`.

### Helpers Propuestos

```javascript
function getUniversalContent() {
  return document.getElementById("universal-content");
}

function ensureUniversalContainer(id) {
  const host = getUniversalContent();
  let container = document.getElementById(id);
  if (!container) {
    container = document.createElement("div");
    container.id = id;
    container.style.display = "none";
    host.appendChild(container);
  }
  return container;
}
```

## Estrategia de Migracion UI

| Fase | Accion |
|---|---|
| 1 | Crear `#universal-content`, `#universal-sidebar` y helpers sin cambiar comportamiento visible. |
| 2 | Migrar funciones `mostrar*()` por seccion. |
| 3 | Mover contenedores hijos al universal. |
| 4 | Adaptar `sidebar-tabs.js` para operar sobre un unico host. |
| 5 | Eliminar placeholders y `*-content-area` obsoletos. |
| 6 | Mantener compatibilidad de `localStorage` o migrarla explicitamente. |

## Smoke Test Entre Fases

- Login correcto.
- Navbar carga LISTA esperada.
- Sidebar muestra botones segun permisos.
- Abrir modulo existente.
- Abrir dos o mas tabs.
- Cambiar entre tabs sin superposiciones.
- Recargar con F5 y validar restauracion.
- Navegar entre secciones y volver.
- Revisar consola del navegador.
- Revisar logs Flask.

## Riesgos y Mitigacion

| Riesgo | Mitigacion |
|---|---|
| Romper tabs persistidos | Migracion o fallback de claves `localStorage`. |
| Modulos con selectores dependientes del padre | Revisar CSS y JS por modulo migrado. |
| Inicializadores duplicados | Usar patron idempotente de `WF_007`. |
| Modales dentro de contenedores | Migrar con `WF_008`. |
| Tablas calculadas cuando estan ocultas | Usar leccion de `WF_013`. |

## Documentos Legacy Cubiertos

- `PLAN_REFACTORIZAR_ROUTES.md`
- `PLAN_REFACTOR_CONTENEDOR_UNICO.md`
