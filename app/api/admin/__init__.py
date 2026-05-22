"""Endpoints HTTP del Panel de Administracion.

Accesible desde el boton 'Panel de Administracion' del navbar
(MaterialTemplate.html linea 338, ruta `/admin/panel`). NO esta en
ninguna LISTA_*.html porque es su propia entidad paralela a las 8
secciones del navbar.

Modulos:
  - permisos.py  -> gestion de roles y permisos de dropdowns
                    (ex `app/admin_api.py`, blueprint name 'admin', prefix '/admin')
  - usuarios.py  -> CRUD de usuarios, roles, auditoria
                    (ex `app/user_admin.py`, blueprint name 'user_admin', prefix '/admin')
"""
