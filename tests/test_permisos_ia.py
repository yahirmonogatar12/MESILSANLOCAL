"""Los permisos del asistente deben sobrevivir a la sincronizacion.

sincronizar_permisos_dropdowns() apaga (activo=0) todo permiso que no encuentre
en los archivos LISTAS. Los del asistente no salen de ahi, asi que cada
sincronizacion los marcaba obsoletos y desaparecian del administrador, que
filtra por activo = 1.
"""

from app.api.admin.usuarios import EXTRA_DROPDOWN_PERMISSIONS
from app.api.portal import ai_store
from app.auth_system import AI_DROPDOWN_PERMISSIONS


def _clave(permiso):
    return (permiso["pagina"], permiso["seccion"], permiso["boton"])


def test_los_permisos_de_ia_estan_en_la_lista_que_la_sincronizacion_respeta():
    extras = {_clave(p) for p in EXTRA_DROPDOWN_PERMISSIONS}
    for permiso in AI_DROPDOWN_PERMISSIONS:
        assert _clave(permiso) in extras, permiso["boton"]


def test_coinciden_con_las_constantes_que_usa_el_asistente():
    """Un typo aqui deja el permiso huerfano: nadie podria concederlo."""
    declarados = {p["boton"] for p in AI_DROPDOWN_PERMISSIONS}
    usados = {
        ai_store.AI_PERMISSION_USE,
        ai_store.AI_PERMISSION_ARTIFACTS,
        ai_store.AI_PERMISSION_AUDIT,
        ai_store.AI_PERMISSION_LIMITS,
    }
    assert declarados == usados, declarados.symmetric_difference(usados)

    for permiso in AI_DROPDOWN_PERMISSIONS:
        assert permiso["pagina"] == ai_store.AI_PAGE
        assert permiso["seccion"] == ai_store.AI_SECTION
        assert permiso["descripcion"].strip(), "sin descripcion no se entiende en la UI"


def test_el_seeder_reactiva_un_permiso_apagado():
    """INSERT IGNORE no corregia una fila ya puesta en activo = 0."""
    import pathlib

    codigo = pathlib.Path("app/api/portal/ai_store.py").read_text(encoding="utf-8")
    indice = codigo.index("INSERT INTO permisos_botones")
    bloque = codigo[indice:indice + 400]
    assert "ON DUPLICATE KEY UPDATE activo = 1" in bloque
    assert "INSERT IGNORE INTO permisos_botones" not in codigo
