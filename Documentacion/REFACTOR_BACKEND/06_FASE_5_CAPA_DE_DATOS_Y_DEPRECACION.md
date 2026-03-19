# Fase 5 - Capa de Datos y Deprecacion

## Objetivo de la fase

Unificar el patron de acceso a datos del backend, consolidar uso de pool/conexiones y definir el retiro controlado de modulos y patrones legacy que hoy siguen mezclados con rutas y logica de negocio.

## Estado actual observado

- `app/db_mysql.py` tiene `2171` lineas y `72` usos de `execute_query(...)`.
- `app/db.py` sigue reflejando mezcla historica entre SQLite y MySQL.
- `app/config_mysql.py` ya tuvo mejoras recientes para reutilizar conexiones a traves del pool.
- `app/routes.py`, `app/auth_system.py` y `app/user_admin.py` todavia hacen queries directas.
- El backend todavia no opera con una capa de repositorio unica ni con ownership claro por dominio.
- Existen carpetas `app/database` y `app/services`, pero aun no materializan una estrategia consolidada.

## Archivos y modulos involucrados

- `app/config_mysql.py`
- `app/db_mysql.py`
- `app/db.py`
- `app/routes.py`
- `app/auth_system.py`
- `app/user_admin.py`
- `app/database`
- `app/services`

## Problemas que resuelve

- Reduce reconexiones y uso inconsistente de la base de datos.
- Evita SQL directo disperso en capas altas.
- Facilita observabilidad y control de timeouts o errores de DB.
- Permite retirar piezas legacy sin romper dependencias ocultas.

## Entregables concretos

- Patron unico documentado para repositorio/servicio/consulta.
- Regla de uso de pool, cierre de conexion y timeout.
- Mapa de migracion desde SQL directo en rutas hacia repositorios.
- Lista de modulos legacy candidatos a deprecacion y retiro.

## Checklist ejecutable

- [ ] Declarar el patron canonico de acceso a datos que deben usar las rutas nuevas.
- [ ] Definir cuando se permite `execute_query(...)` directo y cuando ya no.
- [ ] Definir estrategia de migracion para queries existentes por dominio.
- [ ] Registrar politica de pool, cierre de conexion y errores transitorios.
- [ ] Listar piezas legacy que deben congelarse antes de retirarlas.
- [ ] Documentar compatibilidades temporales necesarias mientras convivan patrones viejos y nuevos.

## Criterios de salida

- Existe un patron unico de acceso a datos definido y aceptado.
- Hay una politica documentada de pool y manejo de conexion.
- Esta trazado el camino para sacar SQL directo de rutas y auth/admin.
- Los modulos legacy candidatos a retiro estan inventariados y clasificados.

## Riesgos y bloqueos

- Hay mucho SQL incrustado en rutas operativas.
- Persisten patrones heredados de SQLite junto con MySQL.
- Cambios en la capa de datos pueden impactar performance y transaccionalidad.
- Sin pruebas por dominio es facil romper escritura o reportes.

## Validacion requerida

- Confirmar que el patron documentado sea compatible con el pool actual y con el despliegue existente.
- Confirmar que las reglas de migracion no obliguen a una reescritura total.
- Confirmar que la lista de legacy priorice primero piezas peligrosas y despues piezas solo incomodas.

## Progreso de la fase

- Estado: `En progreso`
- Avance: `15`
- Ultima actualizacion: `2026-03-11`
- Siguiente accion: documentar el patron canonico de acceso a datos y clasificar los puntos actuales de SQL directo por dominio.

## Notas de continuidad

- Esta fase ya tiene un adelanto real por la mejora reciente de reutilizacion de conexiones.
- No debe intentarse retirar legacy sin que las fases de dominio hayan definido ownership de rutas y servicios.
