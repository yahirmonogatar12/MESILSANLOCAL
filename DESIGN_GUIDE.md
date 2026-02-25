# 🎨 Guía de Diseño - ILSAN Landing Page

## 📋 Índice
1. [Paleta de Colores](#paleta-de-colores)
2. [Tipografía](#tipografía)
3. [Componentes](#componentes)
4. [Espaciado](#espaciado)
5. [Cómo Modificar Estilos](#cómo-modificar-estilos)

---

## 🎨 Paleta de Colores

### Colores Principales
```css
--landing-primary: #32323E      /* Fondo oscuro principal */
--landing-secondary: #40424F    /* Fondo oscuro secundario (navbar) */
--landing-accent: #3498db        /* Azul ILSAN - botones activos */
--landing-border: #e1e8ed        /* Bordes sutiles */
```

### Colores de Texto
```css
--landing-text-dark: #2c3e50    /* Texto oscuro en fondos claros */
--landing-text-light: #ecf0f1   /* Texto claro en fondos oscuros */
--landing-text-muted: #7f8c8d   /* Texto secundario/subtítulos */
```

### Colores Funcionales
- **Success:** `#27ae60` (verde)
- **Danger:** `#e74c3c` (rojo - logout, alerts)
- **Warning:** `#f39c12` (naranja)
- **Info:** `#3498db` (azul)

---

## 🔤 Tipografía

### Fuente Principal
- **Font Family:** `'Segoe UI', Tahoma, Geneva, Verdana, sans-serif`
- **Alternativa:** `'LG regular'` (si está disponible)

### Jerarquía de Tamaños
```css
/* Títulos */
.navbar-title: 1.3rem (20.8px)
.hero-title: 2.5rem (40px)
.section-title h2: 2.2rem (35.2px)

/* Subtítulos */
.navbar-subtitle: 0.75rem (12px)
.hero-subtitle: 1.1rem (17.6px)
.section-title p: 1.1rem (17.6px)

/* Texto Normal */
.user-name: 0.9rem (14.4px)
.user-greeting: 0.75rem (12px)
.navbar-menu a: 0.9rem (14.4px)
```

### Pesos de Fuente
- **Regular:** 400 (texto normal, subtítulos)
- **Medium:** 500 (links de navegación)
- **Semi-bold:** 600 (nombres de usuario, labels)
- **Bold:** 700 (títulos principales, logo)

---

## 🧩 Componentes

### 1. Navbar (Navegación Superior)

**Ubicación:** `app/static/css/landing-components.css` líneas 37-92

**Estructura:**
```html
<nav class="top-navbar">
    <div class="navbar-brand-section">
        <div class="navbar-logo">I</div>
        <div>
            <h1 class="navbar-title">ILSAN Electronics</h1>
            <small class="navbar-subtitle">Sistema Integrado de Gestión</small>
        </div>
    </div>
    <ul class="navbar-menu">
        <li><a href="/inicio" class="active">Inicio</a></li>
        ...
    </ul>
</nav>
```

**Cómo Modificar:**
- **Cambiar color del logo:** Modificar gradient en `.navbar-logo` (línea 46)
- **Cambiar texto del subtítulo:** Editar en `landing.html` línea 664
- **Agregar nuevo item al menú:** Duplicar `<li>` en `landing.html` línea 667-671
- **Cambiar color hover:** Modificar `.navbar-menu li a:hover` (línea 87)

---

### 2. User Info Bar (Barra de Usuario)

**Ubicación:** `app/static/css/landing-components.css` líneas 94-162

**Estructura:**
```html
<div class="user-info-bar">
    <div class="user-welcome">
        <div class="user-avatar-circle">J</div>
        <div class="user-text">
            <span class="user-greeting">Sesión activa</span>
            <span class="user-name">Jesus Gamez</span>
        </div>
    </div>
    <a href="/logout" class="logout-button">
        <i class="fas fa-sign-out-alt"></i>
        <span>Salir</span>
    </a>
</div>
```

**Cómo Modificar:**
- **Cambiar color del avatar:** Modificar gradient en `.user-avatar-circle` (línea 110)
- **Cambiar texto "Sesión activa":** Editar en `landing.html` línea 691
- **Cambiar estilo del botón logout:** Modificar `.logout-button` (línea 132)
- **Ocultar/mostrar greeting en desktop:** Modificar `.user-greeting` (línea 125)

---

### 3. Hero Banner

**Ubicación:** `app/templates/landing.html` líneas 90-110

**Cómo Modificar:**
- **Cambiar altura:** Modificar `.hero-banner height` (línea 82)
- **Cambiar gradiente de fondo:** Modificar `background` en `.hero-banner` (línea 84)
- **Cambiar textos:** Editar en HTML líneas 685-689
- **Agregar imagen de fondo:** Descomentar `url(...)` en línea 84

---

### 4. Application Cards

**Ubicación:** `app/templates/landing.html` líneas 264-331

**Colores por Tipo:**
```css
.mes-header: linear-gradient(135deg, #3498db 0%, #2980b9 100%) /* Azul */
.defect-header: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%) /* Rojo */
.tickets-header: linear-gradient(135deg, #f39c12 0%, #e67e22 100%) /* Naranja */
.admin-header: linear-gradient(135deg, #27ae60 0%, #229954 100%) /* Verde */
```

**Cómo Agregar Nueva Card:**
1. Copiar bloque `<div class="app-card">...</div>`
2. Cambiar clase del header (ej: `.new-app-header`)
3. Definir nuevo gradient en CSS
4. Actualizar ícono, título y descripción

---

## 📏 Espaciado

### Variables CSS
```css
--spacing-xs: 0.25rem  (4px)   /* Espacios muy pequeños */
--spacing-sm: 0.5rem   (8px)   /* Espacios pequeños */
--spacing-md: 1rem     (16px)  /* Espacios medianos (base) */
--spacing-lg: 1.5rem   (24px)  /* Espacios grandes */
--spacing-xl: 2rem     (32px)  /* Espacios extra grandes */
```

### Uso Recomendado
- **Padding interno de cards:** `var(--spacing-lg)` o `1.5rem`
- **Gap entre elementos:** `var(--spacing-md)` o `1rem`
- **Padding de navbar:** `var(--spacing-md) var(--spacing-xl)`
- **Margin entre secciones:** `var(--spacing-xl)` o `2rem`

---

## 🛠️ Cómo Modificar Estilos

### Archivos Clave
1. **`app/static/css/ilsan-theme.css`** - Tema global (colores, variables generales)
2. **`app/static/css/landing-components.css`** - Componentes específicos de landing
3. **`app/templates/landing.html`** - Estructura HTML + estilos inline específicos

### Flujo de Trabajo Recomendado

#### Para Cambios Pequeños (colores, tamaños)
1. Modificar variables CSS en `:root` (landing-components.css línea 1-25)
2. Guardar y refrescar navegador

#### Para Cambios Medianos (ajustar componente existente)
1. Identificar componente en landing-components.css
2. Modificar propiedades específicas
3. Verificar responsive en `@media (max-width: 768px)`

#### Para Cambios Grandes (nuevo componente)
1. Crear HTML en landing.html
2. Agregar estilos en landing-components.css
3. Agregar versión responsive
4. Documentar en esta guía

### Prioridad de Estilos
```
1. Inline styles en HTML (evitar si es posible)
2. landing.html <style> block (solo para estilos muy específicos de la página)
3. landing-components.css (componentes de landing)
4. ilsan-theme.css (tema global)
5. Bootstrap (base framework)
```

---

## 📱 Responsive Breakpoints

```css
/* Desktop First Approach */
Default: > 1200px    (Pantallas grandes)
@media (max-width: 1200px)  (Tablets grandes)
@media (max-width: 768px)   (Tablets / Móviles)
@media (max-width: 480px)   (Móviles pequeños)
```

### Cambios por Breakpoint

**768px (Tablet/Mobile):**
- Navbar menu vertical
- User greeting oculto
- Botón logout solo ícono
- Grid de apps a 1 columna

**480px (Mobile pequeño):**
- Hero banner más pequeño
- Textos más compactos
- Padding reducido

---

## 🔄 Actualizar Componentes Existentes

### Navbar Logo
**Archivo:** `landing.html` línea 662
```html
<!-- Actual: Logo con letra "I" -->
<div class="navbar-logo">I</div>

<!-- Para usar imagen: -->
<img src="..." class="navbar-logo-img" alt="ILSAN">
```

### User Avatar
**Archivo:** `landing.html` línea 688
```html
<!-- Actual: Iniciales -->
{{ nombre_usuario[0].upper() }}

<!-- Para usar foto de perfil: -->
<img src="{{ url_for('static', filename='avatars/' + usuario_id + '.jpg') }}" 
     onerror="this.outerHTML='{{ nombre_usuario[0].upper() }}'">
```

### Logout Button
**Archivo:** `landing-components.css` línea 132-150
```css
/* Cambiar a botón relleno rojo: */
.logout-button {
    background-color: #e74c3c;
    color: white;
    border: 1px solid #e74c3c;
}
```

---

## 🎯 Tips y Mejores Prácticas

###  DO (Hacer)
- Usar variables CSS para colores y espaciados
- Mantener consistencia con el theme ILSAN
- Documentar cambios significativos en esta guía
- Probar en mobile después de cada cambio
- Usar clases semánticas (`.user-info-bar` no `.blue-bar`)

###  DON'T (No Hacer)
- Usar `!important` (salvo excepciones críticas)
- Estilos inline directos en HTML (usar clases)
- Colores hardcoded (usar variables CSS)
- Cambiar estructura de Bootstrap sin probar responsive
- Duplicar estilos entre archivos CSS

---

## 📚 Recursos Adicionales

- **Bootstrap 5.3 Docs:** https://getbootstrap.com/docs/5.3
- **Font Awesome Icons:** https://fontawesome.com/icons
- **CSS Gradients Generator:** https://cssgradient.io
- **Color Palette Tool:** https://coolors.co

---

## 📝 Historial de Cambios

### v1.1 - 2025-10-16
-  Rediseño de navbar con logo cuadrado
-  Cambio de "Supplier Portal" a "Sistema Integrado de Gestión"
-  User avatar más discreto (36px → border sutil)
-  Botón logout outline style (menos llamativo)
-  Mejoras responsive para mobile
-  Separación de componentes en `landing-components.css`
-  Creación de esta guía de diseño

### v1.0 - 2025-10-15
-  Landing page inicial con hero banner
-  Sistema de navegación horizontal
-  Cards de aplicaciones con permisos
-  Footer corporativo

---

**Última actualización:** 2025-10-16  
**Mantenido por:** Departamento de TI - ILSAN Electronics
