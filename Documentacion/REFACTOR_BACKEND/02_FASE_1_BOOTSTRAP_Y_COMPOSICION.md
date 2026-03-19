# Fase 1 - Bootstrap y Composicion

## Objetivo de la fase

Definir una composicion unica de la aplicacion Flask, sacar side-effects de import del bootstrap y dejar claro cual es el entrypoint canonico para local y serverless.

## Estado actual observado

- `app_factory.py` ya existe y expone `create_app()`.
- `run.py` ya consume `create_app()`.
- `api/index.py` todavia importa `app.routes` directamente y vuelve a registrar piezas.
- `app/routes.py` sigue creando `app = Flask(__name__)`, registra blueprints y define cientos de rutas.
- Existen duplicidades de bootstrap y colisiones potenciales como `GET /` definido en mas de un lugar.
- Tambien existen varias implementaciones SMT que se registran desde distintos puntos.

## Archivos y modulos involucrados

- `app_factory.py`
- `run.py`
- `api/index.py`
- `app/routes.py`
- `app/smt_routes.py`
- `app/smt_routes_clean.py`
- `app/smt_routes_date_fixed.py`
- `app/smt_routes_fixed.py`
- `app/smt_routes_simple.py`
- `app/api_po_wo.py`
- `app/aoi_api.py`
- `app/api_raw_modelos.py`

## Problemas que resuelve

- Evita registro doble de blueprints y rutas.
- Reduce side-effects pesados al importar modulos.
- Facilita pruebas, despliegue y lectura del backend.
- Abre el camino para extraer dominios fuera de `app/routes.py`.

## Entregables concretos

- Definicion documental de `create_app()` como raiz de composicion.
- Mapa de registro de blueprints por entorno.
- Inventario de colisiones y duplicidades de arranque.
- Criterio para escoger la implementacion SMT canonica.

## Checklist ejecutable

- [ ] Documentar la secuencia deseada de composicion de app para local y serverless.
- [ ] Marcar que registro debe salir de `app/routes.py` y que puede quedarse temporalmente.
- [ ] Enumerar rutas/blueprints registrados en mas de un entrypoint.
- [ ] Definir politica para `GET /` y otros endpoints compartidos.
- [ ] Elegir la implementacion SMT canon y marcar las demas como legacy o candidatas a retiro.
- [ ] Definir criterio de "import seguro" sin efectos colaterales de DB o blueprint registration.

## Criterios de salida

- Existe un solo flujo documental de composicion de la app.
- Estan identificadas las piezas que deben salir de `app/routes.py`.
- Existe una decision cerrada sobre la implementacion SMT canonica.
- Estan listadas las colisiones de rutas y la estrategia para resolverlas.

## Riesgos y bloqueos

- `app/routes.py` concentra demasiada logica y puede ocultar dependencias de import.
- Hay piezas que dependen de registrarse en orden.
- La composicion de `api/index.py` puede divergir de local si no se unifica.
- Retirar una variante SMT equivocada puede romper historial o reportes existentes.

## Validacion requerida

- Confirmar que el flujo deseado de `create_app()` cubra local y serverless.
- Confirmar que no quede ningun blueprint sin owner claro.
- Confirmar que el inventario de colisiones coincida con la arquitectura documentada vigente.

## Progreso de la fase

- Estado: `En progreso`
- Avance: `15`
- Ultima actualizacion: `2026-03-11`
- Siguiente accion: documentar la composicion canonica con lista de registros que deben migrarse fuera de `app/routes.py`.

## Notas de continuidad

- La existencia de `app/routes`, `app/services`, `app/core` y `app/database` no implica que el backend ya este modularizado.
- Esta fase debe cerrar primero el bootstrap antes de mover dominios grandes.
