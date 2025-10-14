# Frontend Patterns

## Architecture

### Single Page Application (SPA)
- Main container: `MaterialTemplate.html`
- Dynamic content loading via AJAX
- No full page reloads after initial load
- State managed in JavaScript

### Navigation Flow
```
User clicks menu item
    ↓
scriptMain.js calls window.mostrar[Module]()
    ↓
Hide all other containers
    ↓
Show target container
    ↓
cargarContenidoDinamico(containerId, '/module-ajax', callback)
    ↓
Load HTML via AJAX
    ↓
Execute inline initialization script
    ↓
Initialize event listeners via event delegation
    ↓
Load initial data
```

## Key JavaScript Files

### scriptMain.js
- Navigation orchestrator
- Container visibility management
- Module loading functions
- Global utility functions

### Module-Specific JS
- One file per module (e.g., `plan.js`, `smt.js`)
- Self-contained functionality
- Exposed functions via `window` object
- Event delegation for dynamic content

## Dynamic Content Loading

### cargarContenidoDinamico Function
```javascript
window.cargarContenidoDinamico = function(containerId, templatePath, callback) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    fetch(templatePath)
        .then(response => response.text())
        .then(html => {
            container.innerHTML = html;
            if (callback) callback();
        })
        .catch(error => console.error('Error:', error));
};
```

### Usage Pattern
```javascript
window.mostrarMiModulo = function() {
    // Hide other containers
    window.hideAllMaterialContainers();
    
    // Show target container
    const container = document.getElementById('mi-modulo-container');
    container.style.display = 'block';
    
    // Load content
    window.cargarContenidoDinamico('mi-modulo-container', '/mi-modulo-ajax', () => {
        // Initialize after load
        if (typeof window.initializeMiModuloEventListeners === 'function') {
            window.initializeMiModuloEventListeners();
        }
        
        // Load initial data
        if (typeof window.loadMiModuloData === 'function') {
            window.loadMiModuloData();
        }
    });
};
```

## Event Delegation Pattern

### Why Event Delegation
- Works with dynamically loaded content
- Prevents duplicate event listeners
- More efficient than individual listeners
- Survives content reloads

### Implementation
```javascript
function initializeEventListeners() {
    // Prevent duplicate initialization
    if (document.body.dataset.miModuloListenersAttached) {
        return;
    }
    
    // Delegate to document.body
    document.body.addEventListener('click', function(e) {
        const target = e.target;
        
        // Check for specific button
        if (target.id === 'mi-boton' || target.closest('#mi-boton')) {
            e.preventDefault();
            handleMiBoton();
            return;
        }
        
        // Check for class-based selector
        if (target.classList.contains('mi-clase')) {
            e.preventDefault();
            handleMiClase(target);
            return;
        }
    });
    
    // Mark as initialized
    document.body.dataset.miModuloListenersAttached = 'true';
}

// Expose globally
window.initializeEventListeners = initializeEventListeners;
```

## Module Structure

### HTML Template
```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Mi Módulo</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/mi-modulo.css') }}">
    <script src="{{ url_for('static', filename='js/mi-modulo.js') }}" defer></script>
</head>
<body id="mi-modulo-container">
    <!-- Content -->
    
    <script>
    (function() {
        function tryInitialize() {
            if (typeof window.initializeMiModuloEventListeners === 'function') {
                window.initializeMiModuloEventListeners();
            } else {
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

### JavaScript Module
```javascript
// Global state
let miModuloData = [];
let miModuloConfig = {};

// Main functions
async function loadData() {
    try {
        const response = await axios.get('/api/mi-modulo/data');
        miModuloData = response.data;
        renderData();
    } catch (error) {
        console.error('❌ Error:', error);
        showNotification('Error cargando datos', 'error');
    }
}

function renderData() {
    const container = document.getElementById('mi-modulo-content');
    if (!container) return;
    
    container.innerHTML = miModuloData.map(item => `
        <div class="item" data-id="${item.id}">
            ${item.name}
        </div>
    `).join('');
}

// Event delegation
function initializeEventListeners() {
    if (document.body.dataset.miModuloListenersAttached) return;
    
    document.body.addEventListener('click', function(e) {
        if (e.target.closest('.item')) {
            handleItemClick(e.target.closest('.item'));
        }
    });
    
    document.body.dataset.miModuloListenersAttached = 'true';
}

// Expose globally
window.initializeMiModuloEventListeners = initializeEventListeners;
window.loadMiModuloData = loadData;
window.miModuloAction = someAction;

// Auto-initialize
document.addEventListener('DOMContentLoaded', initializeEventListeners);
if (document.readyState !== 'loading') {
    initializeEventListeners();
}
```

## HTTP Requests

### Using Axios
```javascript
// GET request
const response = await axios.get('/api/endpoint', {
    params: { filter: 'value' }
});

// POST request
const response = await axios.post('/api/endpoint', {
    data: 'value'
});

// Error handling
try {
    const response = await axios.get('/api/endpoint');
    // Success
} catch (error) {
    if (error.response) {
        // Server responded with error
        console.error('Server error:', error.response.data);
    } else if (error.request) {
        // No response received
        console.error('Network error');
    } else {
        // Request setup error
        console.error('Error:', error.message);
    }
}
```

## UI Feedback

### Loading States
```javascript
async function performAction() {
    const btn = document.getElementById('action-btn');
    const originalText = btn.textContent;
    
    btn.textContent = 'Procesando...';
    btn.disabled = true;
    
    try {
        await axios.post('/api/action');
        btn.textContent = '✅ Completado';
        btn.style.backgroundColor = '#27ae60';
        
        setTimeout(() => {
            btn.textContent = originalText;
            btn.style.backgroundColor = '';
            btn.disabled = false;
        }, 2000);
    } catch (error) {
        btn.textContent = '❌ Error';
        btn.style.backgroundColor = '#e74c3c';
        
        setTimeout(() => {
            btn.textContent = originalText;
            btn.style.backgroundColor = '';
            btn.disabled = false;
        }, 3000);
    }
}
```

### Notifications
```javascript
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 5px;
        color: white;
        z-index: 10000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;
    
    if (type === 'success') notification.style.backgroundColor = '#27ae60';
    else if (type === 'error') notification.style.backgroundColor = '#e74c3c';
    else notification.style.backgroundColor = '#3498db';
    
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => notification.remove(), 4000);
}
```

## Naming Conventions

### HTML IDs
Format: `[module]-[element]-[action]`
- `plan-btn-guardar`
- `smt-table-datos`
- `material-modal-editar`

### JavaScript Functions
Format: `[module][Action]` (camelCase)
- `planGuardar()`
- `smtCargarDatos()`
- `materialExportar()`

### CSS Classes
Format: `[module]-[element]` (kebab-case)
- `.plan-container`
- `.smt-row`
- `.material-card`

## Debugging

### Console Logs with Emojis
```javascript
console.log('📦 Cargando datos...');
console.log('🚀 Ejecutando acción...');
console.log('✅ Completado exitosamente');
console.log('❌ Error:', error);
console.log('⚠️ Advertencia:', warning);
console.log('🎯 Evento detectado');
console.log('🔧 Configurando...');
console.log('🎨 Renderizando...');
```

### Testing in Console
```javascript
// Check if functions are exposed
console.log('Functions:', {
    initialize: typeof window.initializeMiModuloEventListeners,
    loadData: typeof window.loadMiModuloData,
    action: typeof window.miModuloAction
});

// Check event listeners
console.log('Listeners attached:', document.body.dataset.miModuloListenersAttached);

// Manually trigger function
if (typeof window.miModuloAction === 'function') {
    window.miModuloAction();
}
```

## Common Pitfalls

### ❌ Don't: Direct Event Listeners
```javascript
// This breaks with dynamic content
document.getElementById('btn').addEventListener('click', handler);
```

### ✅ Do: Event Delegation
```javascript
// This works with dynamic content
document.body.addEventListener('click', function(e) {
    if (e.target.id === 'btn') handler();
});
```

### ❌ Don't: Functions Not Exposed
```javascript
// Not accessible from outside
function myFunction() { }
```

### ✅ Do: Expose Globally
```javascript
// Accessible everywhere
function myFunction() { }
window.myFunction = myFunction;
```

### ❌ Don't: Only DOMContentLoaded
```javascript
// Doesn't work if DOM already loaded
document.addEventListener('DOMContentLoaded', init);
```

### ✅ Do: Check readyState
```javascript
// Works in all cases
document.addEventListener('DOMContentLoaded', init);
if (document.readyState !== 'loading') init();
```
