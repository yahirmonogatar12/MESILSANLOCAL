# Documentación: Problema y Solución de Modales en Carga AJAX

## 📋 Resumen Ejecutivo

**Problema:** Los modales (Nuevo Plan, Reprogramar, Importar WOs) no se visualizaban correctamente cuando se navegaba entre secciones del sistema MES, a pesar de que los logs indicaban que se estaban "abriendo".

**Causa Raíz:** Conflicto entre CSS externo y la arquitectura de carga dinámica AJAX que causaba que los modales tuvieran `opacity: 0` y `display: none` incluso después de establecer `display: flex`.

**Solución:** Crear modales dinámicamente en JavaScript con estilos inline forzados que sobrescriben cualquier CSS conflictivo.

---

## 🔍 Análisis del Problema

### Síntomas Observados

1. **Primera carga:** Los modales funcionaban correctamente
2. **Después de navegar:** Al ir a otra sección (ej: Información Básica) y regresar a Control de Producción ASSY, los modales no se veían
3. **Logs engañosos:** Los console.log mostraban "✅ Modal abierto" pero visualmente no aparecía nada
4. **Fondo transparente:** El modal de Work Orders mostraba fondo transparente en lugar del color oscuro esperado

### Diagnóstico Técnico

#### Problema 1: Modales Perdidos en el DOM
```
Usuario navega a "Información Básica"
    ↓
cargarContenidoDinamico() reemplaza innerHTML del contenedor
    ↓
Los modales que estaban dentro del contenedor se eliminan del DOM
    ↓
Usuario regresa a "Control de Producción ASSY"
    ↓
Los modales ya no existen → No se pueden abrir
```

#### Problema 2: CSS Conflictivo
Cuando se establecía `modal.style.display = 'flex'`, el CSS computed mostraba:
```javascript
{
  display: 'flex',           // ✅ Establecido correctamente
  computedDisplay: 'none',   // ❌ CSS externo sobrescribiendo
  opacity: '0',              // ❌ Modal invisible
  zIndex: '9999998'          // ❌ Valor incorrecto (debería ser 10000)
}
```

#### Problema 3: Modales en HTML Estático
Los modales estaban definidos en el HTML del template:
```html
<!-- ❌ PROBLEMA: Se pierden al recargar contenido AJAX -->
<div id="plan-modal" class="modal-overlay">
  <!-- contenido del modal -->
</div>
```

---

## ✅ Solución Implementada

### Arquitectura de la Solución

```
1. Crear modales dinámicamente en JavaScript
    ↓
2. Insertar directamente en document.body (no en contenedores)
    ↓
3. Aplicar estilos inline con !important
    ↓
4. Verificar existencia antes de abrir y recrear si es necesario
```

### Componentes de la Solución

#### 1. Función `createModalsInBody()`

**Ubicación:** `app/static/js/plan.js` (líneas ~2565-2768)

**Propósito:** Crear todos los modales dinámicamente en el `document.body` con estilos inline completos.

**Modales creados:**
- `plan-modal` - Nuevo Plan
- `plan-editModal` - Editar Plan
- `reschedule-modal` - Reprogramar Planes

**Características clave:**
```javascript
// Verificar si ya existe antes de crear
if (!document.getElementById('plan-modal')) {
  const modal = document.createElement('div');
  modal.id = 'plan-modal';
  modal.className = 'modal-overlay';
  
  // Estilos inline como fallback
  modal.style.cssText = `
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.6);
    justify-content: center;
    align-items: center;
    z-index: 10000;
  `;
  
  // Contenido con estilos inline
  modal.innerHTML = `...`;
  
  document.body.appendChild(modal);
}
```

#### 2. Función `createWorkOrdersModal()`

**Ubicación:** `app/static/js/plan.js` (líneas ~26796-29555)

**Propósito:** Crear el modal de Work Orders dinámicamente con estilos compactos.

**Diferencias con otros modales:**
- Inputs con anchos específicos (180px, 140px, 120px)
- Tabla con estilos de headers oscuros
- Botones con colores específicos (azul para Recargar, verde para Importar)

#### 3. Apertura de Modales con Estilos Forzados

**Ubicación:** `app/static/js/plan.js` - Event delegation en `initializePlanEventListeners()`

**Código de apertura:**
```javascript
// Verificar si el modal existe
if (!document.getElementById('reschedule-modal')) {
  createModalsInBody();
}

const modal = document.getElementById('reschedule-modal');
if (modal) {
  // FORZAR estilos inline para sobrescribir CSS conflictivo
  modal.style.cssText = `
    display: flex !important;
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100% !important;
    height: 100% !important;
    background: rgba(0,0,0,0.6) !important;
    justify-content: center !important;
    align-items: center !important;
    z-index: 10000 !important;
    opacity: 1 !important;
    visibility: visible !important;
  `;
}
```

#### 4. Eliminación de Modales del HTML

**Archivo:** `app/templates/Control de proceso/Control_produccion_assy.html`

**Cambio:**
```html
<!-- ANTES: Modales en HTML -->
<div id="plan-modal" class="modal-overlay">...</div>
<div id="plan-editModal" class="modal-overlay">...</div>
<div id="reschedule-modal" class="modal-overlay">...</div>

<!-- DESPUÉS: Solo comentario -->
<!-- Los modales se crean dinámicamente en JavaScript (ver plan.js - createModalsInBody()) -->
```

---

## 🎨 Estilos Aplicados

### Paleta de Colores

```css
/* Fondo del modal */
background: rgba(0,0,0,0.6);  /* Overlay semi-transparente */

/* Contenido del modal */
background: #34334E;  /* Fondo oscuro principal */

/* Inputs y selects */
background: #2B2D3E;  /* Fondo de inputs */
border: 1px solid #20688C;  /* Borde azul */
color: lightgray;  /* Texto claro */

/* Headers de tabla */
background: #1e1e2e;  /* Fondo más oscuro */
border-bottom: 2px solid #20688C;  /* Borde azul */

/* Botones */
Recargar: #2980b9 (azul)
Importar/Guardar: #27ae60 (verde)
Cancelar: #666 (gris)
Cancelar Plan: #e74c3c (rojo)
Reprogramar: #8e44ad (morado)
```

### Tamaños de Inputs

```css
/* Modal de Work Orders */
Buscar WO/PO: width: 180px;
Fechas: width: 140px;
Estado: width: 120px;
Padding: 6px 8px;
Font-size: 12px;

/* Modal de Reprogramar */
Similar a Work Orders
Padding: 6px;
Font-size: 11px (labels)
```

---

## 📁 Archivos Modificados

### 1. `app/static/js/plan.js`

**Cambios principales:**
- ✅ Agregada función `createModalsInBody()` (líneas ~2565-2768)
- ✅ Modificada función `createWorkOrdersModal()` con estilos inline
- ✅ Actualizada apertura de modales con `cssText` forzado
- ✅ Agregada verificación de existencia antes de abrir modales

**Líneas modificadas:**
- ~2565-2768: Función `createModalsInBody()`
- ~2740-2755: Apertura modal Nuevo Plan
- ~2769-2790: Apertura modal Work Orders
- ~2849-2882: Apertura modal Reprogramar
- ~26796-29555: Función `createWorkOrdersModal()`

### 2. `app/templates/Control de proceso/Control_produccion_assy.html`

**Cambios principales:**
- ✅ Eliminados todos los `<div>` de modales del HTML
- ✅ Agregado comentario explicativo
- ✅ Script inline actualizado para llamar a `createModalsInBody()`

**Líneas modificadas:**
- Eliminadas ~150 líneas de HTML de modales
- Agregado comentario en su lugar

### 3. `app/static/js/scriptMain.js`

**Cambios principales:**
- ✅ Función `mostrarPlanMainASSY()` actualizada con mejor manejo de carga
- ✅ Agregado retry logic para esperar a que scripts se carguen

**Líneas modificadas:**
- ~956-1000: Función `mostrarPlanMainASSY()`

### 4. `GUIA_DESARROLLO_MODULOS_MES.md`

**Cambios principales:**
- ✅ Agregada sección "Manejo de Modales en Carga AJAX"
- ✅ Ejemplos de código para crear modales dinámicamente
- ✅ Mejores prácticas documentadas

---

## 🧪 Testing y Verificación

### Escenarios de Prueba

#### ✅ Prueba 1: Primera Carga
```
1. Navegar a "Control de producción ASSY"
2. Hacer clic en "Nuevo Plan"
3. Resultado esperado: Modal se abre con fondo oscuro
4. Estado: PASS ✅
```

#### ✅ Prueba 2: Navegación Entre Secciones
```
1. Navegar a "Control de producción ASSY"
2. Hacer clic en "Reprogramar" (verificar que abre)
3. Cerrar modal
4. Navegar a "Información Básica"
5. Navegar de vuelta a "Control de producción ASSY"
6. Hacer clic en "Reprogramar" nuevamente
7. Resultado esperado: Modal se abre correctamente
8. Estado: PASS ✅
```

#### ✅ Prueba 3: Múltiples Navegaciones
```
1. Navegar entre varias secciones (Información Básica, Control de Material, etc.)
2. Regresar a "Control de producción ASSY"
3. Probar todos los modales (Nuevo Plan, Reprogramar, Importar WOs)
4. Resultado esperado: Todos los modales funcionan
5. Estado: PASS ✅
```

#### ✅ Prueba 4: Estilos Visuales
```
1. Abrir modal "Importar WOs"
2. Verificar:
   - Fondo oscuro (#34334E) ✅
   - Inputs compactos (no muy grandes) ✅
   - Tabla con headers oscuros ✅
   - Botones con colores correctos ✅
3. Estado: PASS ✅
```

### Comandos de Verificación en Consola

```javascript
// Verificar que los modales existen en el body
console.log('Modales en body:', {
  planModal: document.body.contains(document.getElementById('plan-modal')),
  editModal: document.body.contains(document.getElementById('plan-editModal')),
  rescheduleModal: document.body.contains(document.getElementById('reschedule-modal')),
  woModal: document.body.contains(document.getElementById('wo-modal'))
});

// Verificar z-index
console.log('Z-index:', {
  planModal: window.getComputedStyle(document.getElementById('plan-modal')).zIndex,
  rescheduleModal: window.getComputedStyle(document.getElementById('reschedule-modal')).zIndex
});

// Verificar funciones expuestas
console.log('Funciones disponibles:', {
  createModalsInBody: typeof window.createModalsInBody,
  createWorkOrdersModal: typeof window.createWorkOrdersModal,
  initializePlanEventListeners: typeof window.initializePlanEventListeners
});
```

---

## 🎓 Lecciones Aprendidas

### 1. Modales en HTML + AJAX = Problemas
**Problema:** Los modales definidos en HTML se pierden cuando se recarga contenido vía AJAX.

**Solución:** Crear modales dinámicamente en JavaScript y agregarlos directamente al `document.body`.

### 2. CSS Computed vs CSS Inline
**Problema:** Establecer `modal.style.display = 'flex'` no garantiza que el modal sea visible si hay CSS conflictivo.

**Solución:** Usar `cssText` con todos los estilos necesarios para sobrescribir cualquier CSS externo.

### 3. Event Delegation es Esencial
**Problema:** Event listeners directos no funcionan con contenido cargado dinámicamente.

**Solución:** Usar event delegation en `document.body` para capturar eventos de elementos que se crean después.

### 4. Verificar Antes de Usar
**Problema:** Intentar abrir un modal que no existe causa errores silenciosos.

**Solución:** Siempre verificar si el modal existe antes de abrirlo y recrearlo si es necesario.

### 5. Estilos Inline como Fallback
**Problema:** Los estilos CSS externos pueden no cargarse o ser sobrescritos.

**Solución:** Incluir estilos inline completos en los modales creados dinámicamente.

---

## 🔄 Flujo de Trabajo Final

```
Usuario hace clic en botón de modal
    ↓
Event delegation captura el click en document.body
    ↓
¿El modal existe en el DOM?
    ├─ NO → Llamar createModalsInBody() o createWorkOrdersModal()
    └─ SÍ → Continuar
    ↓
Aplicar estilos forzados con cssText
    ↓
modal.style.cssText = `display: flex !important; ...`
    ↓
Modal visible en pantalla ✅
```

---

## 📚 Referencias

### Archivos Clave
- `app/static/js/plan.js` - Lógica principal de modales
- `app/templates/Control de proceso/Control_produccion_assy.html` - Template HTML
- `app/static/js/scriptMain.js` - Orquestador de navegación
- `GUIA_DESARROLLO_MODULOS_MES.md` - Guía de desarrollo

### Funciones Críticas
- `createModalsInBody()` - Crear modales de Plan
- `createWorkOrdersModal()` - Crear modal de Work Orders
- `initializePlanEventListeners()` - Event delegation
- `mostrarPlanMainASSY()` - Carga del módulo

### Patrones Aplicados
- Event Delegation
- Dynamic DOM Manipulation
- Inline Styles Override
- Lazy Modal Creation
- Existence Verification

---

## 🚀 Aplicación a Otros Módulos

Este patrón puede aplicarse a cualquier módulo que use modales:

1. **Eliminar modales del HTML**
2. **Crear función `createModalsInBody()`** específica del módulo
3. **Usar estilos inline completos**
4. **Verificar existencia antes de abrir**
5. **Aplicar estilos forzados al abrir**

Ver `GUIA_DESARROLLO_MODULOS_MES.md` sección "Manejo de Modales en Carga AJAX" para más detalles.

---

**Fecha de Resolución:** Octubre 2025  
**Versión del Sistema:** MES ILSAN LOCAL v1.0  
**Módulo Afectado:** Control de Producción ASSY  
**Estado:** ✅ RESUELTO

