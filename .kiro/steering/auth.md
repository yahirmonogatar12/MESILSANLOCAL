# Authentication & Authorization

## Authentication System

### Session-Based Authentication
- Flask sessions with secret key
- Session data stored server-side
- Login required decorator: `@login_requerido`
- Advanced login decorator: `@auth_system.login_requerido_avanzado`

### User Management
- User table: `usuarios_sistema`
- Password hashing via `auth_system.hash_password()`
- Account lockout after failed attempts
- Session tracking in `sesiones_activas` table

### Login Flow
1. User submits credentials via `/login`
2. System checks `usuarios_sistema` table
3. On success: Create session, load permissions, redirect based on role
4. On failure: Increment failed attempts, lock account if threshold reached
5. Fallback to legacy `usuarios.json` if database auth fails

## Authorization System

### Role-Based Access Control (RBAC)
- Roles stored in `roles` table with hierarchy levels
- User-role mapping in `usuario_roles` table
- Multiple roles per user supported

### Default Roles (by level)
- `superadmin` (10) - Full system access
- `admin` (9) - System administration
- `supervisor_almacen` (8) - Warehouse supervisor
- `supervisor_produccion` (7) - Production supervisor
- `operador_almacen` (5) - Warehouse operator
- `operador_produccion` (4) - Production operator
- `calidad` (3) - Quality control
- `consulta` (2) - Read-only access
- `invitado` (1) - Guest access

### Permission Types

#### Module Permissions (Legacy)
- Stored in `permisos` table
- Format: `(modulo, accion)` e.g., `('material', 'crear')`
- Mapped to roles via `rol_permisos` table
- Decorator: `@auth_system.requiere_permiso(modulo, accion)`

#### Button/Dropdown Permissions (Current)
- Stored in `permisos_botones` table
- Format: `(pagina, seccion, boton)` e.g., `('LISTA_DE_MATERIALES', 'Control de material', 'Control de material de almacén')`
- Mapped to roles via `rol_permisos_botones` table
- Decorator: `@requiere_permiso_dropdown(pagina, seccion, boton)`

### Permission Checking

#### Backend
```python
# Module permission
@auth_system.requiere_permiso('material', 'crear')
def crear_material():
    pass

# Dropdown permission
@requiere_permiso_dropdown('LISTA_DE_MATERIALES', 'Control de material', 'Inventario de rollos SMD')
def inventario_rollos():
    pass
```

#### Frontend (Jinja2)
```html
<!-- Check button permission -->
{% if usuario|tiene_permiso_boton('Control de material de almacén') %}
  <button>Acceder</button>
{% endif %}

<!-- Get all permissions for page -->
{% set permisos = usuario|permisos_botones_pagina('LISTA_DE_MATERIALES') %}
```

## Session Management

### Session Data
- `usuario` - Username
- `nombre_completo` - Full name
- `email` - Email address
- `departamento` - Department
- `permisos` - Permission dictionary

### Session Lifecycle
- Created on successful login
- Updated on each request (activity tracking)
- Cleared on logout or timeout
- Tracked in `sesiones_activas` table

## Audit System

### Audit Logging
All security-relevant actions logged to `auditoria` table:
- User actions (login, logout, failed attempts)
- Data modifications (create, update, delete)
- Permission changes
- Configuration changes

### Audit Fields
- `usuario` - Who performed the action
- `modulo` - Which module/area
- `accion` - What action
- `descripcion` - Human-readable description
- `datos_antes` - State before change (JSON)
- `datos_despues` - State after change (JSON)
- `ip_address` - Client IP
- `user_agent` - Browser/client info
- `resultado` - EXITOSO, ERROR, DENEGADO
- `fecha_hora` - Timestamp (Mexico timezone)

### Registering Audit Events
```python
auth_system.registrar_auditoria(
    usuario=session.get('usuario'),
    modulo='material',
    accion='crear_material',
    descripcion='Material XYZ creado',
    datos_antes=None,
    datos_despues={'numero_parte': 'XYZ123'},
    resultado='EXITOSO'
)
```

## Protected Users

### Admin User Protection
The `admin` user has special protections:
- Cannot be deleted
- Cannot be deactivated
- Cannot have password changed by other users
- All modification attempts are logged and blocked

## Security Best Practices

### When Adding New Features
1. Always use `@login_requerido` or `@login_requerido_avanzado` on routes
2. Add specific permission checks with `@requiere_permiso_dropdown`
3. Register audit events for sensitive operations
4. Never expose raw SQL errors to users
5. Validate all user input before database operations
6. Use parameterized queries (already handled by `execute_query`)

### Permission Naming Convention
- Page: `LISTA_[CATEGORY]` (e.g., `LISTA_DE_MATERIALES`)
- Section: Descriptive name (e.g., `Control de material`)
- Button: Specific action (e.g., `Control de material de almacén`)

### Testing Permissions
1. Create test user with specific role
2. Login as test user
3. Verify access to permitted features
4. Verify denial of non-permitted features
5. Check audit log for permission denials
