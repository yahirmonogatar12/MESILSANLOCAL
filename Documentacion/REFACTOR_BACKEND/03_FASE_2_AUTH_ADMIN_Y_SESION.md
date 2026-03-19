# Fase 2 - Auth, Admin y Sesion

## Objetivo de la fase

Consolidar autenticacion, autorizacion, sesion y administracion de usuarios en fronteras claras para que permisos y estado de usuario no dependan de queries repetidas ni de logica duplicada en rutas.

## Estado actual observado

- `app/auth_system.py` tiene `1142` lineas y `50` usos de `cursor.execute(...)`.
- `app/user_admin.py` tiene `1859` lineas y `78` usos de `cursor.execute(...)`.
- `app/routes.py` sigue conteniendo parte de login, sesion, filtros de permisos y helpers asociados.
- Ya existe mejora reciente en cacheo de roles/permisos y throttling de actualizacion de sesion.
- La llave canonica de sesion apunta a `session['usuario']`, pero el proyecto historicamente ha tenido inconsistencia con `username`.
- El dominio admin sigue mezclando CRUD de usuarios, roles, permisos, auditoria y validaciones en un solo modulo.

## Archivos y modulos involucrados

- `app/auth_system.py`
- `app/user_admin.py`
- `app/routes.py`
- `app/admin_api.py`
- `app_factory.py`

## Problemas que resuelve

- Evita consultas repetidas de roles y permisos por request.
- Reduce duplicacion entre auth, admin y rutas generales.
- Facilita aplicar decoradores y politicas de acceso consistentes.
- Permite mover admin y auth a blueprints/servicios con limites claros.

## Entregables concretos

- Definicion de blueprint auth y blueprint admin.
- Helper canonico de usuario actual.
- Fuente unica para roles, permisos y botones permitidos.
- Mapa de rutas/decoradores que migran primero y de rutas que quedan temporalmente.

## Checklist ejecutable

- [ ] Documentar la frontera entre login/sesion y administracion de usuarios.
- [ ] Declarar `session['usuario']` como llave canonica y registrar la deuda legacy restante.
- [ ] Definir helper unico para usuario actual y rol principal.
- [ ] Definir servicio canonico para roles, permisos y permisos de botones.
- [ ] Separar conceptualmente CRUD admin de los decoradores de auth.
- [ ] Listar endpoints que requieren revalidacion estricta por seguridad durante el refactor.

## Criterios de salida

- Existe una estructura objetivo clara para auth y admin.
- La llave de sesion canonica queda documentada sin ambiguedad.
- Los permisos y roles tienen una sola fuente de verdad definida.
- Estan identificadas las rutas sensibles que no pueden migrarse sin pruebas.

## Riesgos y bloqueos

- Cambios en auth pueden romper todo el acceso al sistema.
- La mezcla de permisos de modulo y permisos de boton complica la separacion.
- Persisten queries directas ligadas a auditoria y CRUD admin.
- Hay dependencias con templates y filtros Jinja que usan el estado de sesion actual.

## Validacion requerida

- Confirmar que el diseño objetivo cubra login, logout, permisos de vista y permisos de boton.
- Confirmar que no queden dos fuentes distintas para rol principal.
- Confirmar que admin quede separado sin duplicar helpers de auth.

## Progreso de la fase

- Estado: `En progreso`
- Avance: `25`
- Ultima actualizacion: `2026-03-11`
- Siguiente accion: documentar el target de blueprint auth/admin y el helper canonico de usuario actual.

## Notas de continuidad

- Esta fase ya tiene adelantos reales en cacheo y sesion; no parte de cero.
- No mover mas piezas de seguridad sin que Fase 0 deje una validacion minima ejecutable.
