# 🔐 Sistema de Usuarios y Auditoría - ILSAN MES

## ✅ IMPLEMENTACIÓN COMPLETADA

### 📁 Archivos Creados

1. **`app/auth_system.py`** - Sistema principal de autenticación
2. **`app/user_admin.py`** - Blueprint de administración de usuarios
3. **`app/templates/panel_usuarios.html`** - Panel de administración de usuarios
4. **`app/templates/auditoria.html`** - Panel de auditoría y logs
5. **`inicializar_usuarios.py`** - Script de inicialización

### 🚀 PASOS DE INTEGRACIÓN

#### 1. **Verificar Integración en `app/routes.py`**
```python
# ✅ Ya agregado automáticamente:
from .auth_system import AuthSystem
from .user_admin import user_admin_bp

app.register_blueprint(user_admin_bp, url_prefix='/admin')
auth_system = AuthSystem()
auth_system.init_database()
```

#### 2. **Inicializar Base de Datos de Usuarios**
```bash
# Ejecutar desde la carpeta raíz del proyecto
python inicializar_usuarios.py
```

#### 3. **Actualizar rutas existentes con permisos**
Para proteger tus rutas actuales, agregar decoradores:

```python
# Ejemplo: Proteger ruta de materiales
@app.route('/material')
@auth_system.login_requerido_avanzado  # Login requerido
@auth_system.requiere_permiso('material', 'ver')  # Permiso específico
def material():
    # Registrar actividad en auditoría
    auth_system.registrar_auditoria(
        session.get('usuario'), 
        'material', 
        'acceso', 
        'Acceso al módulo de materiales'
    )
    # Tu código existente...
```

#### 4. **Agregar enlaces de administración al menú**
En tus templates principales, agregar:

```html
<!-- En el menú principal -->
{% if session.usuario == 'admin' or 'super_admin' in session.roles %}
<a href="/admin/panel" class="admin-link">
    <i class="fas fa-users-cog"></i> Admin Usuarios
</a>
<a href="/admin/auditoria" class="admin-link">
    <i class="fas fa-history"></i> Auditoría
</a>
{% endif %}
```

### 🎯 FUNCIONALIDADES IMPLEMENTADAS

#### **Sistema de Autenticación**
- ✅ Login con verificación SHA256
- ✅ Sistema de roles jerárquico
- ✅ Permisos granulares por módulo.acción
- ✅ Bloqueo de cuenta tras intentos fallidos
- ✅ Registro de sesiones activas

#### **Panel de Administración**
- ✅ CRUD completo de usuarios
- ✅ Gestión de roles y permisos
- ✅ Activación/desactivación de usuarios
- ✅ Estadísticas en tiempo real
- ✅ Interfaz responsive con Bootstrap 5

#### **Sistema de Auditoría**
- ✅ Registro automático de todas las acciones
- ✅ Búsqueda avanzada por filtros
- ✅ Exportación a Excel
- ✅ Actividad de usuarios en tiempo real
- ✅ Detalles técnicos (IP, User-Agent, duración)

### 👤 USUARIOS POR DEFECTO

```
👑 Administrador
Usuario: admin
Contraseña: admin123

🔗 URLs de Administración:
📋 Panel Admin: http://localhost:5000/admin/panel
📊 Auditoría: http://localhost:5000/admin/auditoria
```

### 🛡️ ROLES Y PERMISOS

#### **Roles Predefinidos:**
1. **super_admin** - Acceso total al sistema
2. **admin_usuario** - Gestión de usuarios únicamente  
3. **supervisor_produccion** - Supervisión de producción
4. **operador_materiales** - Operaciones de materiales
5. **operador_calidad** - Operaciones de calidad
6. **operador_almacen** - Operaciones de almacén
7. **solo_lectura** - Solo visualización

#### **Módulos de Permisos:**
- **sistema** (usuarios, configuracion, auditoria)
- **material** (ver, crear, editar, eliminar, exportar)
- **almacen** (ver, crear, editar, eliminar, exportar)
- **produccion** (ver, crear, editar, eliminar, exportar)
- **calidad** (ver, crear, editar, eliminar, exportar)
- **bom** (ver, crear, editar, eliminar, exportar)

### 📊 CARACTERÍSTICAS AVANZADAS

#### **Seguridad**
- Hashing SHA256 para contraseñas
- Bloqueo automático tras 5 intentos fallidos
- Registro de IP y User-Agent
- Limpieza automática de sesiones expiradas

#### **Auditoría Completa**
- Registro de datos antes/después de cambios
- Duración de operaciones en milisegundos
- Filtros avanzados por fecha, usuario, módulo
- Estadísticas en tiempo real

#### **Interfaz Moderna**
- Bootstrap 5 con tema oscuro
- Responsive design para móviles
- Iconos Font Awesome
- Actualización automática de datos

### 🔧 CONFIGURACIÓN ADICIONAL

#### **Personalizar Roles**
Editar directamente en `auth_system.py` la función `_crear_roles_default()`

#### **Agregar Nuevos Permisos**
Editar la función `_crear_permisos_default()` en `auth_system.py`

#### **Configurar Base de Datos**
El sistema usa SQLite por defecto. Las tablas se crean automáticamente:
- `usuarios_sistema`
- `roles`
- `permisos`
- `usuario_roles`
- `rol_permisos`
- `auditoria`
- `sesiones_activas`

### ⚠️ IMPORTANTE - SEGURIDAD

1. **Cambiar contraseña de admin** inmediatamente en producción
2. **Configurar HTTPS** para proteger credenciales
3. **Revisar permisos** antes de desplegar
4. **Backup regular** de la base de datos de usuarios

### 🐛 TROUBLESHOOTING

#### **Error de Import**
Si hay errores de importación, verificar que todos los archivos estén en `app/`:
- `app/auth_system.py`
- `app/user_admin.py`

#### **Error de Base de Datos**
```python
# Ejecutar para recrear tablas
auth_system.init_database()
```

#### **Panel no aparece**
Verificar que el Blueprint esté registrado en `routes.py`:
```python
app.register_blueprint(user_admin_bp, url_prefix='/admin')
```

### 🎉 ¡SISTEMA LISTO!

El sistema de usuarios está completamente implementado y listo para usar.

**Próximos pasos recomendados:**
1. Ejecutar `python inicializar_usuarios.py`
2. Probar login con admin/admin123
3. Acceder a `/admin/panel`
4. Crear usuarios para tu equipo
5. Proteger rutas existentes con decoradores
6. Personalizar permisos según necesidades

---
**Creado para ILSAN MES - Sistema de Manufactura**  
*Implementación modular que mantiene routes.py limpio* ✨
