# ISEMM MES - Steering Documentation

Esta carpeta contiene documentación de steering para guiar el desarrollo en el sistema ISEMM MES.

## Documentos Disponibles

### 📦 [product.md](product.md)
Descripción general del producto ISEMM MES, sus capacidades principales y módulos clave.

**Contenido:**
- Descripción del sistema MES para manufactura electrónica
- Capacidades principales (gestión de materiales, planificación, SMT, BOM, trazabilidad)
- Lista de módulos principales

### 🛠️ [tech.md](tech.md)
Stack tecnológico, librerías y comandos comunes.

**Contenido:**
- Backend: Flask, Gunicorn, MySQL
- Frontend: AJAX SPA, Jinja2, Vanilla JS, Axios
- Librerías clave: pandas, openpyxl, beautifulsoup4
- Deployment: Vercel serverless
- Comandos de desarrollo y testing

### 🏗️ [structure.md](structure.md)
Organización del proyecto y estructura de carpetas.

**Contenido:**
- Estructura de directorios raíz y app/
- Patrones arquitectónicos (dynamic module loading, blueprints)
- Convenciones de nombres para archivos, IDs, funciones y endpoints
- Archivos de configuración

### 🔐 [auth.md](auth.md)
Sistema de autenticación y autorización.

**Contenido:**
- Autenticación basada en sesiones Flask
- Sistema RBAC (Role-Based Access Control)
- Roles predeterminados y jerarquía
- Tipos de permisos (módulos y botones/dropdowns)
- Sistema de auditoría
- Protección de usuarios especiales
- Mejores prácticas de seguridad

### 🎨 [frontend.md](frontend.md)
Patrones y convenciones del frontend.

**Contenido:**
- Arquitectura SPA con carga dinámica
- Flujo de navegación
- Patrón de event delegation
- Estructura de módulos (HTML, JS)
- Manejo de peticiones HTTP con Axios
- UI feedback y notificaciones
- Convenciones de nombres
- Debugging y testing
- Errores comunes a evitar

### 💾 [database.md](database.md)
Patrones de acceso a base de datos.

**Contenido:**
- Gestión de conexiones MySQL
- Patrón de ejecución de queries
- Tablas principales del sistema
- Patrones comunes (upsert, joins, agregaciones, transacciones)
- Tipos de datos y character set
- Manejo de timezone (México GMT-6)
- Foreign keys (deshabilitadas por diseño)
- Patrones de migración
- Consideraciones de performance

### 🌐 [api-conventions.md](api-conventions.md)
Convenciones para endpoints y APIs REST.

**Contenido:**
- Patrones de endpoints (AJAX, REST, Admin)
- Métodos HTTP (GET, POST, PUT, DELETE)
- Formatos de request/response
- Query parameters (filtros, paginación, fechas, ordenamiento)
- Autenticación y autorización en rutas
- Manejo de errores y códigos HTTP
- Validación de datos
- File uploads y downloads
- Blueprints
- CORS y rate limiting
- Testing de APIs

### 🚀 [deployment.md](deployment.md)
Configuración de deployment y entorno.

**Contenido:**
- Plataformas de hosting (Vercel, local)
- Variables de entorno
- Configuración de Vercel
- Entry points (producción y desarrollo)
- Archivos estáticos
- Conexión a base de datos
- Logging y auditoría
- Optimización de performance
- Consideraciones de seguridad
- Monitoreo y health checks
- Backup y recovery
- Troubleshooting
- Workflow de deployment
- Consideraciones de escalabilidad

### 📝 [coding-standards.md](coding-standards.md)
Estándares de código y mejores prácticas.

**Contenido:**
- Estilo de código Python (PEP 8, convenciones de nombres)
- Estilo de código JavaScript (ES6+, async/await, event delegation)
- Templates HTML/Jinja2
- Queries SQL (formateo, parametrización)
- Organización de archivos
- Orden de imports
- Mensajes de commit Git
- Checklist de code review
- Patrones comunes a seguir

## Guías de Referencia Adicionales

### 📘 [GUIA_DESARROLLO_MODULOS_MES.md](../../GUIA_DESARROLLO_MODULOS_MES.md)
Guía completa para desarrollar nuevos módulos compatibles con la arquitectura de carga dinámica.

**Incluye:**
- Checklist de requisitos obligatorios
- Patrón de desarrollo estándar
- Estructura de archivos (HTML, JS, Python)
- Event delegation detallado
- Integración en scriptMain.js
- Errores comunes a evitar
- Convenciones de nombres
- Testing y debugging
- Ejemplo completo de integración

### 📄 [docs/SISTEMA_INVENTARIO_ROLLOS_SMD.md](../../docs/SISTEMA_INVENTARIO_ROLLOS_SMD.md)
Documentación del sistema de inventario automático de rollos SMD.

**Incluye:**
- Arquitectura del sistema
- Tablas principales y triggers
- APIs REST
- Flujo de trabajo automático
- Estados del rollo
- Instalación y configuración
- Monitoreo y mantenimiento
- Integración con sistemas existentes

## Cómo Usar Esta Documentación

### Para Nuevos Desarrolladores
1. Empieza con **product.md** para entender qué es el sistema
2. Lee **tech.md** y **structure.md** para familiarizarte con la arquitectura
3. Revisa **coding-standards.md** antes de escribir código
4. Consulta **frontend.md** y **database.md** según necesites

### Para Desarrollar Nuevos Módulos
1. Lee **GUIA_DESARROLLO_MODULOS_MES.md** completa
2. Revisa **frontend.md** para patrones de event delegation
3. Consulta **api-conventions.md** para crear endpoints
4. Usa **auth.md** para agregar permisos

### Para Debugging
1. **frontend.md** - Problemas de JavaScript y carga dinámica
2. **database.md** - Problemas de queries y conexión
3. **deployment.md** - Problemas de entorno y deployment
4. **auth.md** - Problemas de permisos y sesiones

### Para Code Review
1. Verifica contra **coding-standards.md**
2. Confirma patrones de **frontend.md** (event delegation)
3. Valida seguridad con **auth.md**
4. Revisa convenciones de **api-conventions.md**

## Principios Fundamentales

### 🎯 Event Delegation
**Crítico para carga dinámica de contenido**
- Siempre usar event delegation en `document.body`
- Nunca usar event listeners directos en elementos dinámicos
- Ver frontend.md para detalles

### 🌐 Funciones Globales
**Necesario para módulos dinámicos**
- Exponer funciones críticas en `window`
- Permite acceso desde callbacks y otros módulos
- Ver frontend.md para patrón completo

### 🔒 Seguridad
**Protección en cada capa**
- Decoradores de autenticación en todas las rutas
- Permisos granulares por botón/dropdown
- Queries parametrizadas siempre
- Auditoría de acciones sensibles

### 📊 Base de Datos
**Sin ORM, SQL directo**
- Usar `execute_query()` para todas las operaciones
- Queries parametrizadas para prevenir SQL injection
- Foreign keys deshabilitadas por diseño
- Timezone México (GMT-6) para timestamps

### 🎨 Frontend SPA
**Carga dinámica sin recargas**
- `MaterialTemplate.html` como contenedor principal
- `cargarContenidoDinamico()` para cargar módulos
- Event delegation para sobrevivir recargas de contenido
- Estado en JavaScript, no en DOM

## Actualizaciones

Esta documentación debe actualizarse cuando:
- Se agreguen nuevos módulos importantes
- Cambien patrones arquitectónicos
- Se modifiquen convenciones de código
- Se descubran mejores prácticas
- Se implementen nuevas funcionalidades de seguridad

## Contacto y Soporte

Para preguntas sobre esta documentación o el sistema:
- Revisar código de referencia en `app/static/js/plan.js`
- Consultar ejemplos en `GUIA_DESARROLLO_MODULOS_MES.md`
- Verificar implementaciones existentes en el código base

---

**Última actualización:** Octubre 2024  
**Versión:** 1.0  
**Sistema:** ISEMM MES - ILSAN Electronics
