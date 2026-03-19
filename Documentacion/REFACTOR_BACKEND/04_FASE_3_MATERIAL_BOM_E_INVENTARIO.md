# Fase 3 - Material, BOM e Inventario

## Objetivo de la fase

Separar el dominio de materiales, BOM e inventario del monolito para que las rutas, servicios y acceso a datos del area operen con ownership claro y menor duplicacion.

## Estado actual observado

- `app/routes.py` concentra gran parte de los endpoints de materiales, entradas, salidas, control de almacen, historial e importaciones.
- Tambien concentra endpoints BOM como consulta, listado, importacion y actualizacion.
- Existen carpetas `app/services` y `app/routes`, pero hoy no son la base activa del dominio.
- El dominio mezcla vistas HTML, endpoints AJAX, importaciones Excel y operaciones de inventario en un mismo archivo.
- El alcance backend puro obliga a documentar dependencias con templates AJAX sin entrar a reescribir frontend en esta etapa.

## Archivos y modulos involucrados

- `app/routes.py`
- `app/db_mysql.py`
- `app/db.py`
- `app/services`
- `app/routes`
- `Documentacion/MODULO_BOM_DEEP_DIVE.md`
- `Documentacion/CATALOGO_MODULOS_Y_RUTAS.md`

## Problemas que resuelve

- Reduce el tamano funcional de `app/routes.py`.
- Evita repetir consultas y reglas de negocio de inventario.
- Da fronteras separadas para materiales, BOM e historial.
- Facilita pruebas de regresion por dominio.

## Entregables concretos

- Inventario de endpoints criticos de materiales, BOM e inventario.
- Mapa de dependencias compartidas entre rutas, servicios y queries.
- Definicion de servicios minimos por subdominio.
- Orden de extraccion de rutas fuera del monolito.

## Checklist ejecutable

- [ ] Catalogar endpoints de materiales, inventario y BOM que siguen en `app/routes.py`.
- [ ] Identificar queries repetidas y utilidades compartidas del dominio.
- [ ] Definir servicios minimos: material, inventario y BOM.
- [ ] Definir que rutas HTML quedan temporalmente y que APIs deben migrarse primero.
- [ ] Registrar dependencias con importaciones Excel y con templates AJAX.
- [ ] Marcar endpoints de alto riesgo por impacto operativo y datos productivos.

## Criterios de salida

- Existe un inventario claro del dominio material/BOM/inventario.
- El orden de extraccion esta definido por riesgo y dependencia.
- Hay una estructura objetivo minima de servicios/repositorios para el dominio.
- Queda documentado que parte sigue temporalmente en el monolito y por que.

## Riesgos y bloqueos

- Mucha logica de negocio esta mezclada con renderizado y parsing de archivos.
- Varias rutas del dominio mutan datos productivos.
- Hay dependencias con reglas de trazabilidad e inventario consolidado.
- El dominio puede depender de patrones SQL heredados y diferencias MySQL/SQLite.

## Validacion requerida

- Confirmar que el inventario cubra operaciones de consulta, mutacion, importacion y exportacion.
- Confirmar que el plan no omita rutas criticas de BOM ni control de material.
- Confirmar que las dependencias AJAX esten registradas como restriccion, no como objetivo de esta fase.

## Progreso de la fase

- Estado: `No iniciado`
- Avance: `5`
- Ultima actualizacion: `2026-03-11`
- Siguiente accion: levantar el inventario de endpoints criticos del dominio y sus dependencias de query compartida.

## Notas de continuidad

- Esta fase debe arrancar despues de estabilizar bootstrap y auth.
- No conviene mover importaciones Excel al inicio; primero hay que sacar rutas mas simples y reutilizables.
