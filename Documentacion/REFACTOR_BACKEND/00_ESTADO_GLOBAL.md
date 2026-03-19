# Estado Global del Refactor Backend

Punto de entrada diario del programa de refactor.

Fecha de corte: `2026-03-11`

| Fase | Estado | Avance % | Objetivo | Bloqueador actual | Siguiente accion | Ultima actualizacion |
| --- | --- | ---: | --- | --- | --- | --- |
| Fase 0 - Baseline y guardrails | En progreso | 20 | Cerrar baseline funcional, smoke tests y reglas de seguridad para refactor | No existe suite minima de pruebas ni linea base de rendimiento documentada | Documentar matriz inicial de endpoints criticos y comandos de smoke test | 2026-03-11 |
| Fase 1 - Bootstrap y composicion | En progreso | 15 | Consolidar `create_app`, entrypoints y registro de blueprints | `app/routes.py` sigue creando la app y registrando piezas; `api/index.py` aun compone directo | Definir composicion canonica y mapa de piezas que salen de `app/routes.py` | 2026-03-11 |
| Fase 2 - Auth, admin y sesion | En progreso | 25 | Consolidar auth, permisos, sesion y admin | La logica sigue repartida entre `app/auth_system.py`, `app/routes.py` y `app/user_admin.py` | Diseñar frontera entre blueprint auth, blueprint admin y servicio de permisos | 2026-03-11 |
| Fase 3 - Material, BOM e inventario | No iniciado | 5 | Separar el dominio de materiales del monolito | Endpoints, consultas y renderizado siguen mayormente en `app/routes.py` | Inventariar endpoints criticos y dependencias compartidas antes de extraer | 2026-03-11 |
| Fase 4 - Planificacion, produccion y SMT | No iniciado | 5 | Reagrupar planeacion y SMT por limites funcionales reales | Varias implementaciones SMT y rutas de planeacion compiten entre si | Elegir implementacion SMT canon y orden de extraccion por subdominio | 2026-03-11 |
| Fase 5 - Capa de datos y deprecacion | En progreso | 15 | Unificar acceso a datos y retiro controlado de legacy | Siguen existiendo SQL directo en rutas y mezcla de patrones de acceso | Definir patron unico de repositorio y reglas de migracion desde SQL directo | 2026-03-11 |

## Hechos base del repo al 2026-03-11

- `app/routes.py` tiene `14352` lineas.
- `app/routes.py` contiene `291` rutas con `@app.route`.
- `app/routes.py` contiene `87` usos de `cursor.execute(...)` y `186` usos de `execute_query(...)`.
- `app/auth_system.py` tiene `1142` lineas y `50` usos de `cursor.execute(...)`.
- `app/user_admin.py` tiene `1859` lineas y `78` usos de `cursor.execute(...)`.
- `app/db_mysql.py` tiene `2171` lineas y `72` usos de `execute_query(...)`.
- Existen cinco variantes SMT activas en el repo: `app/smt_routes.py`, `app/smt_routes_clean.py`, `app/smt_routes_date_fixed.py`, `app/smt_routes_fixed.py`, `app/smt_routes_simple.py`.
- Existen carpetas destino como `app/routes`, `app/services`, `app/core` y `app/database`, pero hoy no operan como estructura consolidada del backend.
- No se detecto una suite `tests/` o archivos `test_*.py` en el repo.

## Regla operativa

Cada sesion futura debe actualizar este archivo antes de tocar cualquier otro documento de la carpeta.
