"""DEPRECATED: este archivo fue migrado a `app/api/control_material/material_admin.py`.

El contenido original (852 lineas) se movio al nuevo paquete `app.api/`
organizado por seccion del navbar. Las rutas y nombres de blueprint
quedaron identicos para no romper el frontend.

Este shim re-exporta el blueprint nuevo bajo el nombre legacy
`material_admin_bp` por si algun import externo no migrado lo necesita.
Cuando confirmes que nada lo usa, borra este archivo.

Migrado: 2026-05-22
"""

from app.api.control_material.material_admin import bp as material_admin_bp

__all__ = ["material_admin_bp"]
