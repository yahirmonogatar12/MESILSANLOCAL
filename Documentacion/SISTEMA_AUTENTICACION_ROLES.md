# Documentación Técnica: Sistema de Autenticación y Autorización Basado en Roles (RBAC)

Este documento detalla el funcionamiento lógico, el modelo de datos y los flujos de control del sistema de autenticación y seguridad por roles implementado en **ILSAN MES**.

El sistema utiliza un enfoque de **Control de Acceso Basado en Roles (RBAC - Role-Based Access Control)** con la particularidad de evaluar permisos granulares al nivel de páginas, secciones y botones específicos (Dropdowns/Sidebars) para proveer una experiencia fluida e inyección dinámica de módulos (AJAX).

---

## 1. Arquitectura y Modelo de Datos (DB Schema)

El motor de persistencia del sistema de autenticación corre sobre **MySQL**. A continuación se muestra la estructura y relaciones de las tablas involucradas en el proceso de autenticación, asignación de roles, permisos de interfaz y auditoría:

```mermaid
erDiagram
    usuarios_sistema {
        int id PK "Autoincremental"
        string username UK "Nombre de usuario único"
        string password_hash "Hash SHA-256 de la contraseña"
        string email "Correo electrónico"
        string nombre_completo "Nombre del empleado"
        string departamento "Departamento asignado"
        string cargo "Cargo del puesto"
        int activo "Estatus de cuenta (1: Activo, 0: Inactivo)"
        timestamp fecha_creacion "Fecha de alta"
        timestamp ultimo_acceso "Fecha de último login"
        int intentos_fallidos "Contador de intentos de login fallidos"
        timestamp bloqueado_hasta "Tiempo de desbloqueo"
        string creado_por "Usuario creador"
        string modificado_por "Último usuario modificador"
        timestamp fecha_modificacion "Fecha de modificación"
    }

    roles {
        int id PK "Autoincremental"
        string nombre UK "Nombre único del rol"
        string descripcion "Propósito del rol"
        int nivel "Nivel jerárquico (1 a 10)"
        int activo "Estatus (1: Activo, 0: Inactivo)"
        timestamp fecha_creacion "Fecha de creación"
    }

    usuario_roles {
        int usuario_id PK, FK "Referencia a usuarios_sistema"
        int rol_id PK, FK "Referencia a roles"
        timestamp fecha_asignacion "Fecha de asignación del rol"
        string asignado_por "Usuario que asignó el rol"
    }

    permisos_botones {
        int id PK "Autoincremental"
        string pagina "Identificador de página (ej. LISTA_DE_MATERIALES)"
        string seccion "Sección o grupo (ej. Control de material)"
        string boton "Nombre del botón o acción (ej. Inventario actual)"
        string descripcion "Propósito de la acción"
        int activo "Estatus del permiso"
    }

    rol_permisos_botones {
        int rol_id PK, FK "Referencia a roles"
        int permiso_boton_id PK, FK "Referencia a permisos_botones"
        timestamp fecha_asignacion "Fecha de asignación"
    }

    sesiones_activas {
        int id PK "Autoincremental"
        int usuario_id FK "Referencia a usuarios_sistema"
        string token UK "Token de sesión en hexadecimal (SHA-256)"
        string ip_address "IP del cliente"
        string user_agent "Navegador o dispositivo utilizado"
        timestamp fecha_inicio "Inicio de sesión"
        timestamp fecha_ultima_actividad "Última interacción registrada"
        timestamp fecha_expiracion "Límite de validez de la sesión"
        int activa "Estatus (1: Activa, 0: Cerrada/Expirada)"
    }

    auditoria {
        int id PK "Autoincremental"
        string usuario "Nombre del usuario que ejecutó la acción"
        string modulo "Módulo del sistema afectado"
        string accion "Acción realizada (ej. Crear, Editar)"
        string descripcion "Detalle textual de la operación"
        string datos_antes "JSON de estado inicial del registro"
        string datos_despues "JSON de estado final tras mutación"
        string ip_address "IP desde donde se originó"
        string user_agent "Dispositivo/Cliente origen"
        string resultado "Resultado (EXITOSO, DENEGADO, ERROR)"
        int duracion_ms "Tiempo de respuesta del servidor en ms"
        string endpoint "Ruta Flask invocada"
        string metodo_http "Método HTTP (POST, GET, etc.)"
        timestamp fecha_hora "Fecha y hora local de México"
    }

    usuarios_sistema ||--o{ usuario_roles : "tiene"
    roles ||--o{ usuario_roles : "asignado_a"
    roles ||--o{ rol_permisos_botones : "tiene"
    permisos_botones ||--o{ rol_permisos_botones : "asignado_a"
    usuarios_sistema ||--o{ sesiones_activas : "inicia"
```

### Niveles Jerárquicos de Roles Predeterminados

El sistema inicializa automáticamente los siguientes roles y niveles jerárquicos a través de la función `_crear_roles_default` en [app/auth_system.py](file:///c:/Users/yahir/OneDrive/Escritorio/MES/MES/MESILSANLOCAL/app/auth_system.py#L258-L277):

| Rol | Nivel | Descripción |
| :--- | :---: | :--- |
| **superadmin** | `10` | Super Administrador con acceso total (bypassa el chequeo de permisos de botones). |
| **admin** | `9` | Administrador del sistema (acceso casi completo excepto configuraciones críticas). |
| **supervisor_almacen** | `8` | Supervisor del almacén general y almacén de materias primas. |
| **supervisor_produccion** | `7` | Supervisor de líneas de ensamble SMT, ASSY, IMT. |
| **operador_almacen** | `5` | Operador para registrar entradas, salidas e impresiones de etiquetas. |
| **operador_produccion** | `4` | Operador en planta con permisos de registro básico de producción. |
| **calidad** | `3` | Personal de control de calidad (inspecciones IQC, OQC y liberaciones LQC). |
| **consulta** | `2` | Usuario con permisos de visualización general en módulos del MES. |
| **invitado** | `1` | Usuario externo o temporal con privilegios mínimos. |

---

## 2. Flujo de Autenticación (Login & Bloqueo)

Este flujo detalla cómo se procesa una solicitud de inicio de sesión, incluyendo la protección contra ataques de fuerza bruta (bloqueo temporal tras 5 intentos fallidos) y la gestión de sesiones activas.

```mermaid
sequenceDiagram
    autonumber
    actor User as Usuario (Cliente)
    participant App as Interfaz Web / PDA
    participant Auth as AuthSystem (auth_system.py)
    participant DB as Base de Datos (MySQL)

    User->>App: Ingresa usuario y contraseña
    App->>Auth: verificar_usuario(username, password)
    Auth->>DB: Consultar usuario (username, activo, intentos_fallidos, bloqueado_hasta, etc.)
    DB-->>Auth: Retorna datos de usuario

    alt Usuario no existe
        Auth-->>App: Retorna (False, "Usuario no encontrado")
        App-->>User: Muestra error en interfaz
    end

    alt Usuario bloqueado y tiempo de bloqueo no ha expirado (ahora < bloqueado_hasta)
        Auth-->>App: Retorna (False, "Usuario bloqueado hasta HH:MM:SS")
        App-->>User: Muestra alerta de bloqueo temporal
    else Usuario bloqueado pero tiempo ya expiró (ahora >= bloqueado_hasta)
        Auth->>DB: Desbloquear usuario (bloqueado_hasta = NULL, intentos_fallidos = 0)
        Note over Auth, DB: Continúa con la verificación de contraseña
    end

    alt Usuario inactivo (activo != 1)
        Auth-->>App: Retorna (False, "Usuario inactivo")
        App-->>User: Muestra error "Usuario inactivo"
    end

    Auth->>Auth: Comparar hash: hash_password(password) == password_hash

    alt Contraseña correcta
        Auth->>DB: Actualizar ultimo_acceso, resetear intentos_fallidos y limpiar bloqueo
        Auth->>DB: Registrar nueva sesión en sesiones_activas (token, ip, user_agent, exp: +24 hrs)
        DB-->>Auth: Confirmación de transacción
        Auth-->>App: Retorna (True, "Login exitoso")
        App->>User: Redirige a dashboard y establece Flask session['usuario']
    else Contraseña incorrecta
        Auth->>Auth: Incrementar intentos_fallidos (intentos = intentos + 1)
        alt intentos >= 5
            Auth->>DB: Establecer bloqueado_hasta = (ahora + 30 minutos) e intentos_fallidos
            Auth-->>App: Retorna (False, "Usuario bloqueado por 30 minutos")
        else intentos < 5
            Auth->>DB: Actualizar intentos_fallidos en base de datos
            Auth-->>App: Retorna (False, "Contraseña incorrecta. Intentos restantes: X")
        end
        App-->>User: Muestra error de credenciales e intentos restantes
    end
```

---

## 3. Flujo de Autorización y Chequeo de Permisos de Botón

La autorización en el MES está optimizada mediante una fachada centralizada y un decorador que intercepta peticiones AJAX y navegación directa. Además, cuenta con un sistema de caché TTL en memoria del servidor Flask para no sobrecargar a la base de datos MySQL con peticiones repetidas.

```mermaid
sequenceDiagram
    autonumber
    actor User as Usuario
    participant View as Componente UI (Frontend)
    participant Route as Endpoint Flask (Decorator requiere_permiso_dropdown)
    participant PermFacade as Fachada Permisos (app/api/shared/permisos.py)
    participant Auth as AuthSystem (app/auth_system.py)
    participant Cache as Caché de Permisos (_BUTTON_PERMISSIONS_CACHE)
    participant DB as Base de Datos (MySQL)

    User->>View: Hace clic en botón de acción (ej. "Aprobar ECO")
    View->>Route: Petición HTTP (ej. POST /api/eco/approve)
    Note over Route: El decorador intercepta la petición: @requiere_permiso_dropdown(pagina, seccion, boton)

    alt Sesión inactiva (no hay 'usuario' en session)
        Route-->>View: Retorna 401 JSON con redirect a /login
        View-->>User: Redirige al login
    end

    Route->>Auth: obtener_rol_principal_usuario(username)
    Note over Auth: Lee de session['rol_principal']. Si es nulo, consulta DB y lo cachea en Flask session.
    Auth-->>Route: Retorna rol principal (ej. "calidad")

    alt Rol es "superadmin"
        Note over Route: Bypass automático de permisos
        Route->>Route: Ejecuta controlador original
        Route-->>View: Retorna 200 OK / Fragmento HTML
        View-->>User: Renderiza resultado en interfaz
    end

    Route->>Auth: verificar_permiso_boton(username, pagina, seccion, boton)
    Auth->>Auth: obtener_permisos_botones_usuario(username, pagina)
    Auth->>Cache: Buscar permisos en memoria para el usuario
    
    alt Caché Miss o Caché Expirada (TTL 300s)
        Cache-->>Auth: No encontrado o expirado
        Auth->>DB: SELECT DISTINCT pb.pagina, pb.seccion, pb.boton de los roles asignados al usuario
        DB-->>Auth: Lista de permisos de botones
        Auth->>Cache: Guardar lista de permisos con fecha de expiración
    else Caché Hit
        Cache-->>Auth: Retorna lista de permisos en memoria (rápido)
    end

    Auth->>Auth: Validar si existe el botón solicitado en la estructura del usuario

    alt Permiso Concedido
        Auth-->>Route: Retorna True
        Route->>Route: Ejecuta controlador de la ruta
        Route-->>View: Retorna 200 OK / Datos JSON / Template HTML
        View-->>User: Renderiza pantalla / ejecuta acción exitosa
    else Permiso Denegado
        Auth-->>Route: Retorna False
        Route->>Auth: registrar_auditoria(usuario, modulo, accion, ..., resultado='DENEGADO')
        Auth->>DB: INSERT INTO auditoria (resultado = 'DENEGADO')
        
        alt Petición es JSON / AJAX (Content-Type: application/json)
            Route-->>View: Retorna 403 JSON (error de permisos)
        else Carga de Fragmento HTML (Navegación Sidebar)
            Route-->>View: Retorna 403 HTML con diseño de candado (Acceso Denegado)
        end
        View-->>User: Muestra interfaz de bloqueo o alerta visual
    end
```

---

## 4. Sistema de Auditoría y Bitácora de Acciones

El sistema registra de forma obligatoria toda mutación de estado relevante (rutas POST/PUT/DELETE) así como los intentos de acceso no autorizados.

```mermaid
graph TD
    Trigger["Evento de Seguridad / Escritura en BD<br>(Mutación de datos, Error de backend o Intento denegado)"] --> Call["Invocación a auth_system.registrar_auditoria(...)"]
    
    subgraph Captura["Captura Automática de Metadatos de Red (Flask request)"]
        IP["ip_address = request.remote_addr"]
        UA["user_agent = request.headers['User-Agent']"]
        Endpoint["endpoint = request.endpoint"]
        Method["metodo_http = request.method"]
    end
    
    subgraph Serializacion["Tratamiento de Parámetros"]
        Antes["Serializar datos_antes a JSON string"]
        Despues["Serializar datos_despues a JSON string"]
    end

    Call --> Captura
    Call --> Serializacion
    
    Captura & Serializacion --> DBWrite["Ejecutar INSERT INTO auditoria en MySQL"]
    DBWrite --> DB[("Tabla auditoria (MySQL)")]
```

> [!NOTE]
> **Gestión de Fechas**: Las fechas y marcas de tiempo del sistema de auditoría y base de datos son forzadas a la zona horaria de México (GMT-6) mediante métodos estáticos en `AuthSystem` (`get_mexico_time()`, `get_mexico_time_mysql()`), garantizando la homogeneidad horaria incluso si el servidor físico se encuentra en otra zona horaria.

---

## 5. Implementación en Código y Uso de Decoradores

El sistema de seguridad está implementado y centralizado principalmente en dos componentes clave:
1.  **Lógica Central**: [app/auth_system.py](file:///c:/Users/yahir/OneDrive/Escritorio/MES/MES/MESILSANLOCAL/app/auth_system.py), responsable del backend, cifrado, consultas CRUD a base de datos y la caché TTL en memoria.
2.  **Fachada de Permisos (Dropdowns)**: [app/api/shared/permisos.py](file:///c:/Users/yahir/OneDrive/Escritorio/MES/MES/MESILSANLOCAL/app/api/shared/permisos.py), responsable de centralizar el decorador `@requiere_permiso_dropdown` utilizado en los diferentes blueprints del sistema.

### Ejemplo de Integración en Vistas del Servidor

Para proteger cualquier endpoint del sistema, se debe importar y añadir el decorador `@requiere_permiso_dropdown` especificando la **página**, la **sección** y el **botón** configurado en la base de datos:

```python
from flask import Blueprint, jsonify, render_template
# Importar el decorador unificado desde la fachada central de permisos
from app.api.shared import requiere_permiso_dropdown

bp = Blueprint('mi_modulo', __name__)

@bp.route('/mi-ruta-de-accion', methods=['POST'])
@requiere_permiso_dropdown('LISTA_DE_MATERIALES', 'Control de material', 'Historial de entradas')
def mi_controlador():
    # Esta función solo se ejecutará si el usuario:
    # 1. Tiene sesión activa.
    # 2. Es "superadmin" u ostenta un rol que contiene el permiso específico.
    return jsonify({"success": True, "message": "Operación autorizada"})
```

> [!IMPORTANT]
> **Bypass para Superadmin**: Si un usuario tiene asignado el rol `superadmin`, el decorador de permisos ignorará cualquier restricción de botón devolviendo directamente `True` (acceso absoluto). Esto permite realizar labores de soporte de forma ágil sin registrar permisos redundantes para dicho rol.
