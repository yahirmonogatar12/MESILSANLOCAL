# 📘 Guía de Desarrollo de Módulos para Sistema MES

## 🎯 Objetivo
Este documento define los estándares y patrones para desarrollar módulos nuevos que sean compatibles con el sistema MES y su arquitectura de carga dinámica vía MaterialTemplate.

---

## 🏗️ Arquitectura del Sistema

### Sistema de Carga Dinámica
El sistema MES utiliza una arquitectura de **carga dinámica de contenido** que permite:
- Cargar módulos vía AJAX sin recargar la página
- Mantener el estado de la aplicación
- Gestionar múltiples módulos simultáneamente
- Navegación fluida entre secciones

### Componentes Principales

```
MaterialTemplate.html (Contenedor principal)
    ↓
scriptMain.js (Orquestador de navegación)
    ↓
cargarContenidoDinamico() (Función de carga AJAX)
    ↓
[Tu Módulo HTML] + [Tu Módulo JS] + [Tu Módulo CSS]
```

---

## 📋 Checklist de Desarrollo

### ✅ Requisitos Obligatorios

- [ ] Usar **Event Delegation** en lugar de event listeners directos
- [ ] Exponer funciones críticas en `window` para acceso global
- [ ] Implementar función de inicialización reutilizable
- [ ] Incluir logs de debugging con emojis para rastreo
- [ ] Evitar conflictos de nombres con otros módulos
- [ ] Usar contenedores únicos con ID específico
- [ ] Implementar manejo de errores robusto
- [ ] Agregar estados de loading/feedback visual

---

## 🛠️ Patrón de Desarrollo Estándar

### 1. Estructura de Archivos

```
app/
├── templates/
│   └── [categoria]/
│       └── tu_modulo.html          # Template HTML
├── static/
│   ├── js/
│   │   └── tu-modulo.js            # Lógica JavaScript
│   └── css/
│       └── tu-modulo.css           # Estilos específicos
└── routes.py                        # Endpoint AJAX
```

### 2. Template HTML

**Archivo:** `app/templates/[categoria]/tu_modulo.html`

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Tu Módulo</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/styles.css') }}">
  <link rel="stylesheet" href="{{ url_for('static', filename='css/tu-modulo.css') }}">
  <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
  <script src="{{ url_for('static', filename='js/tu-modulo.js') }}" defer></script>
</head>
<body id="tu-modulo-container">

  <!-- Toolbar / Controles -->
  <div id="tu-modulo-toolbar">
    <button id="tu-modulo-btn-accion1" class="btn">Acción 1</button>
    <button id="tu-modulo-btn-accion2" class="btn">Acción 2</button>
    <button id="tu-modulo-btn-export" class="btn">Exportar</button>
  </div>

  <!-- Contenido Principal -->
  <div id="tu-modulo-content">
    <!-- Tu contenido aquí -->
  </div>

  <!-- Script inline para inicialización -->
  <script>
    (function() {
      console.log('📝 Script inline de tu_modulo ejecutándose...');
      
      function tryInitialize() {
        if (typeof window.initializeTuModuloEventListeners === 'function') {
          console.log('✅ Inicializando listeners de tu_modulo');
          window.initializeTuModuloEventListeners();
        } else {
          console.log('⏳ Esperando inicialización de tu_modulo...');
          setTimeout(tryInitialize, 100);
        }
      }
      
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', tryInitialize);
      } else {
        tryInitialize();
      }
    })();
  </script>

</body>
</html>
```

### 3. JavaScript del Módulo

**Archivo:** `app/static/js/tu-modulo.js`

```javascript
// ====== Variables Globales del Módulo ======
let tuModuloData = [];
let tuModuloConfig = {
  // Tu configuración aquí
};

// ====== Funciones Principales ======

/**
 * Cargar datos del módulo
 */
async function loadTuModuloData() {
  console.log('📦 Cargando datos de tu_modulo...');
  try {
    const response = await axios.get('/api/tu-modulo/data');
    tuModuloData = response.data;
    renderTuModulo(tuModuloData);
  } catch (error) {
    console.error('❌ Error al cargar datos:', error);
    showNotification('Error al cargar datos', 'error');
  }
}

/**
 * Renderizar contenido del módulo
 */
function renderTuModulo(data) {
  console.log('🎨 Renderizando tu_modulo...');
  const container = document.getElementById('tu-modulo-content');
  if (!container) return;
  
  // Tu lógica de renderizado aquí
  container.innerHTML = '...';
}

/**
 * Acción 1 - Ejemplo de función expuesta
 */
async function tuModuloAccion1() {
  console.log('🚀 Ejecutando acción 1 de tu_modulo...');
  
  const btn = document.getElementById('tu-modulo-btn-accion1');
  if (!btn) return;
  
  const originalText = btn.textContent;
  btn.textContent = 'Procesando...';
  btn.disabled = true;
  
  try {
    // Tu lógica aquí
    const response = await axios.post('/api/tu-modulo/accion1', { /* data */ });
    
    // Feedback exitoso
    btn.textContent = '✅ Completado';
    btn.style.backgroundColor = '#27ae60';
    showNotification('Acción completada exitosamente', 'success');
    
    setTimeout(() => {
      btn.textContent = originalText;
      btn.style.backgroundColor = '';
      btn.disabled = false;
    }, 2000);
    
  } catch (error) {
    console.error('❌ Error en acción 1:', error);
    btn.textContent = '❌ Error';
    btn.style.backgroundColor = '#e74c3c';
    showNotification('Error al ejecutar acción', 'error');
    
    setTimeout(() => {
      btn.textContent = originalText;
      btn.style.backgroundColor = '';
      btn.disabled = false;
    }, 3000);
  }
}

/**
 * Exportar datos del módulo
 */
async function tuModuloExportar() {
  console.log('📊 Exportando datos de tu_modulo...');
  // Tu lógica de exportación aquí
}

// ====== Event Delegation (CRÍTICO PARA CARGA DINÁMICA) ======

/**
 * Función de inicialización usando Event Delegation
 * IMPORTANTE: Esta función debe poder llamarse múltiples veces sin causar problemas
 */
function initializeTuModuloEventListeners() {
  console.log('🔧 Inicializando event listeners de tu_modulo con event delegation...');
  
  // Protección contra inicialización múltiple
  if (!document.body.dataset.tuModuloListenersAttached) {
    
    // Event delegation para clicks
    document.body.addEventListener('click', function(e) {
      const target = e.target;
      
      // Acción 1
      if (target.id === 'tu-modulo-btn-accion1' || target.closest('#tu-modulo-btn-accion1')) {
        e.preventDefault();
        console.log('🎯 Click en btn-accion1 detectado');
        tuModuloAccion1();
        return;
      }
      
      // Acción 2
      if (target.id === 'tu-modulo-btn-accion2' || target.closest('#tu-modulo-btn-accion2')) {
        e.preventDefault();
        console.log('🎯 Click en btn-accion2 detectado');
        tuModuloAccion2();
        return;
      }
      
      // Exportar
      if (target.id === 'tu-modulo-btn-export' || target.closest('#tu-modulo-btn-export')) {
        e.preventDefault();
        console.log('🎯 Click en btn-export detectado');
        tuModuloExportar();
        return;
      }
    });
    
    // Event delegation para cambios (selects, inputs, etc.)
    document.body.addEventListener('change', function(e) {
      if (e.target.id === 'tu-modulo-select-filtro') {
        console.log('🎯 Cambio en filtro detectado');
        loadTuModuloData();
      }
    });
    
    document.body.dataset.tuModuloListenersAttached = 'true';
    console.log('✅ Event delegation configurado para tu_modulo');
  }
  
  console.log('✅ Inicialización de event listeners de tu_modulo completada');
}

// ====== Exponer Funciones Globalmente (CRÍTICO) ======

// Exponer función de inicialización
window.initializeTuModuloEventListeners = initializeTuModuloEventListeners;

// Exponer funciones principales
window.tuModuloAccion1 = tuModuloAccion1;
window.tuModuloAccion2 = tuModuloAccion2;
window.tuModuloExportar = tuModuloExportar;
window.loadTuModuloData = loadTuModuloData;

// ====== Auto-inicialización ======

// Ejecutar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', initializeTuModuloEventListeners);

// También ejecutar inmediatamente si el DOM ya está listo (para scripts defer)
if (document.readyState === 'interactive' || document.readyState === 'complete') {
  console.log('📦 DOM ya está listo, ejecutando initializeTuModuloEventListeners inmediatamente');
  initializeTuModuloEventListeners();
}

// ====== Funciones Auxiliares ======

/**
 * Mostrar notificaciones al usuario
 */
function showNotification(message, type = 'info') {
  const existingNotification = document.querySelector('.notification');
  if (existingNotification) existingNotification.remove();
  
  const notification = document.createElement('div');
  notification.className = 'notification';
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 15px 20px;
    border-radius: 5px;
    color: white;
    font-weight: bold;
    z-index: 10000;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    animation: slideIn 0.3s ease;
  `;
  
  if (type === 'success') notification.style.backgroundColor = '#27ae60';
  else if (type === 'error') notification.style.backgroundColor = '#e74c3c';
  else notification.style.backgroundColor = '#3498db';
  
  notification.textContent = message;
  document.body.appendChild(notification);
  
  setTimeout(() => {
    if (notification.parentNode) notification.remove();
  }, 4000);
}
```

### 4. Endpoint Backend

**Archivo:** `app/routes.py`

```python
@app.route('/tu-modulo-ajax')
def tu_modulo_ajax():
    """Ruta AJAX para cargar el template del módulo"""
    try:
        return render_template('categoria/tu_modulo.html')
    except Exception as e:
        logger.error(f"Error en tu_modulo_ajax: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tu-modulo/data', methods=['GET'])
def api_tu_modulo_data():
    """API para obtener datos del módulo"""
    try:
        # Tu lógica aquí
        data = []
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error en api_tu_modulo_data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tu-modulo/accion1', methods=['POST'])
def api_tu_modulo_accion1():
    """API para ejecutar acción 1"""
    try:
        data = request.get_json()
        # Tu lógica aquí
        return jsonify({"success": True, "message": "Acción ejecutada"})
    except Exception as e:
        logger.error(f"Error en api_tu_modulo_accion1: {e}")
        return jsonify({"error": str(e)}), 500
```

### 5. Integración en scriptMain.js

**Archivo:** `app/static/js/scriptMain.js`

```javascript
// Agregar función para mostrar tu módulo
window.mostrarTuModulo = function() {
    try {
        console.log('📦 Cargando Tu Módulo...');
        
        // Activar botón de navegación
        const navButton = document.getElementById('tu-categoria');
        if (navButton) {
            navButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'tu-categoria') btn.classList.remove('active');
            });
        }
        
        // Ocultar otros contenedores
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }
        
        // Mostrar contenedores necesarios
        const materialContainer = document.getElementById('material-container');
        const tuCategoriaContent = document.getElementById('tu-categoria-content');
        
        if (materialContainer) materialContainer.style.display = 'block';
        if (tuCategoriaContent) tuCategoriaContent.style.display = 'block';
        
        // Obtener contenedor único
        const containerId = 'tu-modulo-unique-container';
        const container = document.getElementById(containerId);
        
        if (!container) {
            console.error('❌ Contenedor no existe:', containerId);
            return;
        }
        
        container.style.display = 'block';
        container.style.opacity = '1';
        
        // Cargar contenido dinámico
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico(containerId, '/tu-modulo-ajax', () => {
                // Inicializar event listeners después de cargar
                console.log('📦 Contenido de Tu Módulo cargado, inicializando listeners...');
                
                if (typeof window.initializeTuModuloEventListeners === 'function') {
                    window.initializeTuModuloEventListeners();
                } else {
                    console.warn('⚠️ initializeTuModuloEventListeners no disponible');
                }
                
                // Cargar datos iniciales
                if (typeof window.loadTuModuloData === 'function') {
                    window.loadTuModuloData();
                }
            });
        }
        
    } catch (e) {
        console.error('❌ Error en mostrarTuModulo:', e);
    }
};
```

---

## 🚨 Errores Comunes a Evitar

### ❌ MAL - Event Listeners Directos
```javascript
// NO HACER ESTO - No funciona con carga dinámica
document.getElementById('mi-boton').addEventListener('click', miFuncion);
```

### ✅ BIEN - Event Delegation
```javascript
// HACER ESTO - Funciona siempre
document.body.addEventListener('click', function(e) {
  if (e.target.id === 'mi-boton' || e.target.closest('#mi-boton')) {
    e.preventDefault();
    miFuncion();
  }
});
```

### ❌ MAL - Funciones No Expuestas
```javascript
// NO HACER ESTO - No accesible desde fuera
function miFuncion() {
  console.log('Hola');
}
```

### ✅ BIEN - Funciones Expuestas Globalmente
```javascript
// HACER ESTO - Accesible globalmente
function miFuncion() {
  console.log('Hola');
}
window.miFuncion = miFuncion;
```

### ❌ MAL - Inicialización Solo en DOMContentLoaded
```javascript
// NO HACER ESTO - No funciona si el DOM ya está listo
document.addEventListener('DOMContentLoaded', inicializar);
```

### ✅ BIEN - Inicialización Flexible
```javascript
// HACER ESTO - Funciona siempre
document.addEventListener('DOMContentLoaded', inicializar);

if (document.readyState === 'interactive' || document.readyState === 'complete') {
  inicializar();
}
```

---

## 🎨 Convenciones de Nombres

### IDs de Elementos HTML
```
[modulo]-[elemento]-[accion]

Ejemplos:
- tu-modulo-btn-guardar
- tu-modulo-table-datos
- tu-modulo-modal-editar
- tu-modulo-input-fecha
```

### Funciones JavaScript
```
[modulo][Accion]

Ejemplos:
- tuModuloGuardar()
- tuModuloExportar()
- tuModuloCargarDatos()
- initializeTuModuloEventListeners()
```

### Variables Globales
```
[modulo][Descripcion]

Ejemplos:
- tuModuloData
- tuModuloConfig
- tuModuloState
```

### Endpoints API
```
/api/[modulo]/[accion]

Ejemplos:
- /api/tu-modulo/data
- /api/tu-modulo/guardar
- /api/tu-modulo/exportar
```

---

## 🔍 Testing y Debugging

### 1. Verificar Funciones Expuestas
Ejecuta en la consola del navegador:
```javascript
console.log('Funciones expuestas:', {
  inicializar: typeof window.initializeTuModuloEventListeners,
  accion1: typeof window.tuModuloAccion1,
  cargarDatos: typeof window.loadTuModuloData
});
```

### 2. Verificar Event Listeners
```javascript
console.log('Listeners:', document.body.dataset.tuModuloListenersAttached);
```

### 3. Test Manual de Botones
```javascript
// Simular click
if (typeof window.tuModuloAccion1 === 'function') {
  window.tuModuloAccion1();
} else {
  console.error('Función no disponible');
}
```

---

## 📊 Logs de Debugging Estándar

Usa emojis para facilitar la identificación en la consola:

```javascript
console.log('📦 Cargando...');      // Carga de datos
console.log('🚀 Ejecutando...');    // Ejecución de función
console.log('✅ Completado');        // Éxito
console.log('❌ Error:');            // Error
console.log('⚠️ Advertencia:');     // Advertencia
console.log('🎯 Click detectado');   // Evento detectado
console.log('🔧 Configurando...');   // Configuración
console.log('🎨 Renderizando...');   // Renderizado visual
console.log('💾 Guardando...');      // Guardado de datos
console.log('📊 Exportando...');     // Exportación
console.log('⏳ Esperando...');      // Espera/retry
```

---

## 🎯 Ejemplo Completo de Integración

Ver archivo de referencia: `app/static/js/plan.js` líneas 2167-2233

Este archivo contiene un ejemplo completo de:
- Event delegation correctamente implementado
- Funciones expuestas globalmente
- Inicialización flexible
- Manejo de errores robusto
- Feedback visual al usuario

---

## 📚 Referencias y Archivos Clave

### Archivos a Estudiar
1. `app/templates/MaterialTemplate.html` - Contenedor principal y función `cargarContenidoDinamico`
2. `app/static/js/scriptMain.js` - Orquestador de navegación
3. `app/static/js/plan.js` - Ejemplo de módulo bien implementado
4. `app/templates/Control de proceso/Control_produccion_assy.html` - Template de referencia

### Funciones Críticas del Sistema
- `window.cargarContenidoDinamico(containerId, templatePath, callback)` - Carga contenido vía AJAX
- `window.hideAllMaterialContainers()` - Oculta todos los contenedores
- `window.hideAllInformacionBasicaContainers()` - Oculta contenedores de info básica

---

## ✨ Checklist Final Antes de Integrar

- [ ] ✅ Event delegation implementado correctamente
- [ ] ✅ Todas las funciones críticas expuestas en `window`
- [ ] ✅ Función de inicialización puede llamarse múltiples veces sin problemas
- [ ] ✅ Logs de debugging con emojis agregados
- [ ] ✅ IDs únicos siguiendo convención de nombres
- [ ] ✅ Script inline de inicialización en el HTML
- [ ] ✅ Endpoint AJAX creado en routes.py
- [ ] ✅ Función de navegación agregada en scriptMain.js
- [ ] ✅ Contenedor único creado en MaterialTemplate.html
- [ ] ✅ Manejo de errores implementado
- [ ] ✅ Feedback visual al usuario implementado
- [ ] ✅ Testing manual completado en consola del navegador

---

## 🚀 Próximos Pasos Después de Crear tu Módulo

1. Crear contenedor en MaterialTemplate.html
2. Agregar función de navegación en scriptMain.js
3. Agregar botón/enlace en el menú de navegación
4. Implementar endpoints backend
5. Testing exhaustivo en consola del navegador
6. Verificar que funcione con carga dinámica
7. Documentar APIs y funciones específicas del módulo

---

**Última actualización:** Octubre 2025  
**Versión del documento:** 1.0  
**Basado en:** Sistema MES ILSAN LOCAL - Plan Main Module
