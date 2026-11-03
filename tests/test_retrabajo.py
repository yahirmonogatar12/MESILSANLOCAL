from pathlib import Path

from app.api.control_produccion import retrabajo

ROOT = Path(__file__).resolve().parents[1]


def _payload(**overrides):
    data = {
        "np_origen": "EBR11111111",
        "np_destino": "EBR22222222",
        "tipo_material": "ASSY",
        "origenes": [{"origen": "EMBARQUES", "cantidad": 3}, {"origen": "SMD", "cantidad": 2}],
    }
    data.update(overrides)
    return data


def test_retrabajo_routes_are_registered(app):
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/control_produccion/retrabajo" in rules
    assert "/api/retrabajo" in rules
    assert "/api/retrabajo/<int:solicitud_id>/cancelar" in rules
    assert "/api/retrabajo/export" in rules
    # Embarques surte con su salida normal (departure = folio RT), sin rutas propias.
    assert not any(r.startswith("/api/retrabajo/embarques") or r.endswith("salida-embarques") for r in rules)


def test_filtros_de_lista_por_fecha_y_codigo():
    where, params = retrabajo._filtros_lista({"desde": "2026-10-01", "hasta": "2026-10-21"})
    assert "s.created_at >= %s" in where and "DATE_ADD(%s, INTERVAL 1 DAY)" in where
    assert params == ["2026-10-01", "2026-10-21"]
    # Fechas invalidas se ignoran (no llegan al SQL).
    assert retrabajo._filtros_lista({"desde": "01/10/2026", "hasta": "x"}) == ("", [])
    # El codigo busca en todo el historial: ignora fechas.
    where, params = retrabajo._filtros_lista({"codigo": "rt-1", "desde": "2026-10-01"})
    assert "created_at" not in where and params[:3] == ["RT-1"] * 3 and params[3:7] == ["rt-1"] * 4
    assert params[7:] == ["RT-1", "rt-1"]  # folio de salida EMB-SAL o caja de la salida


def test_programming_label_matches_control_produccion_port():
    option = retrabajo.opcion_programacion(
        {"item_no": "SAA30091701_(IC1)", "spec": "0x52DE", "location_text": "IC1"}
    )
    assert option == {"ic_location": "IC1", "micom_part_no": "SAA30091701", "programming_label": "SAA30091 701(52DE)"}
    assert retrabajo.opcion_programacion({"item_no": "SAA30091701", "spec": "", "location_text": ""}) is None


def test_solicitud_suma_origenes_y_deriva_cambio_de_etiquetas():
    payload, errors = retrabajo.validar_solicitud(_payload(np_origen=" ebr11111111 "))
    assert errors == []
    assert payload["cantidad"] == 5
    assert payload["np_origen"] == "EBR11111111"
    assert payload["cambio_etiquetas"] is True


def test_solicitud_rechaza_datos_invalidos():
    cases = [
        _payload(origenes=[]),
        _payload(origenes=[{"origen": "SMD", "cantidad": 1}, {"origen": "SMD", "cantidad": 2}]),
        _payload(origenes=[{"origen": "PRODUCCION", "cantidad": 1000}]),
        _payload(np_destino="EBR11111111"),  # sin cambio de NP, programacion ni componentes
        _payload(np_origen="12345"),
        _payload(tipo_material="OTRO"),
        _payload(np_destino="EBR11111111", componentes=[{"tipo": "THT", "ubicacion": "c12"}]),
    ]
    for data in cases:
        _, errors = retrabajo.validar_solicitud(data)
        assert errors, data

    _, errors = retrabajo.validar_solicitud(
        _payload(np_destino="EBR11111111", componentes=[{"tipo": "IMD", "ubicacion": "c12"}])
    )
    assert errors == []


def test_areas_y_estado_general():
    row = {
        "status": "ACTIVA", "cantidad": 5, "cambio_etiquetas": 1,
        "emb_solicitado": 3, "emb_surtido": 3,
        "prog_total": 2, "prog_completas": 1, "prog_iniciadas": 1,
        "impresas": 0, "comp_assy": 1, "comp_smd": 0,
        "esc_cp_retrabajo": 0, "esc_cp_reparacion": 0, "esc_smd_reparacion": 0,
    }
    areas, estado = retrabajo.calcular_areas(row)
    por_area = {a["area"]: a["estado"] for a in areas}
    assert por_area == {
        "EMBARQUES": "COMPLETADA",
        "MICOM": "EN_PROCESO",
        "IMPRESION": "PENDIENTE",
        "CP_RETRABAJO": "PENDIENTE",
        "CP_REPARACION": "PENDIENTE",
    }
    assert estado == "EN_PROCESO"

    done = {**row, "prog_completas": 2, "impresas": 5, "esc_cp_retrabajo": 5, "esc_cp_reparacion": 5}
    assert retrabajo.calcular_areas(done)[1] == "COMPLETADA"
    assert retrabajo.calcular_areas({**done, "status": "CANCELADA"})[1] == "CANCELADA"


class _Cursor:
    """Responde segun la tabla consultada; registra cada SQL."""

    def __init__(self, orden, solicitado=0, surtido=0):
        self.respuestas = {
            "retrabajo_solicitudes": orden,
            "retrabajo_origenes": {"total": solicitado},
            "embarques_salida_material": {"total": surtido},
        }
        self.sql = []

    def execute(self, sql, params=None):
        self.sql.append(sql)
        self.ultimo = next(v for k, v in self.respuestas.items() if k in sql)

    def fetchone(self):
        return self.ultimo


def test_departure_retrabajo_valida_orden_np_y_pendiente():
    validar = retrabajo.validar_departure_retrabajo
    orden = {"id": 1, "status": "ACTIVA", "np_origen": "EBR11111111"}

    # Un departure normal no consulta nada.
    cursor = _Cursor(orden)
    assert validar(cursor, "DEP-5521", "EBR11111111", 10) is None and cursor.sql == []

    # Pidio 5 a Embarques y ya salieron 2 con este folio: caben 3, en una o varias salidas.
    assert validar(_Cursor(orden, 5, 2), "rt-20261022-1", "ebr11111111", 3) is None
    assert "(3)" in validar(_Cursor(orden, 5, 2), "RT-20261022-1", "EBR11111111", 4)
    cursor = _Cursor(orden, 5, 2)
    validar(cursor, "RT-20261022-1", "EBR11111111", 1)
    assert "FOR UPDATE" in cursor.sql[0]  # serializa salidas concurrentes al mismo folio

    assert validar(_Cursor(None), "RT-20261022-9", "EBR11111111", 1)
    assert validar(_Cursor({**orden, "status": "CANCELADA"}, 5), "RT-20261022-1", "EBR11111111", 1)
    assert validar(_Cursor(orden, 5), "RT-20261022-1", "EBR99999999", 1)
    assert validar(_Cursor(orden, 0), "RT-20261022-1", "EBR11111111", 1)


def test_menu_permiso_y_modales_wf_008():
    lista = (ROOT / "app/templates/LISTAS/LISTA_CONTROLDEPRODUCCION.html").read_text(encoding="utf-8")
    template = (ROOT / "app/templates/Control de produccion/retrabajo_ajax.html").read_text(encoding="utf-8")
    salidas = (ROOT / "app/templates/Control de proceso/almacen_embarques_salidas_ajax.html").read_text(encoding="utf-8")
    javascript = (ROOT / "app/static/js/retrabajo.js").read_text(encoding="utf-8")

    assert 'data-permiso-seccion="Retrabajo"' in lista
    assert 'data-permiso-boton="Solicitud de retrabajo"' in lista
    assert "rtb-modal" not in template
    assert "document.body.appendChild(modal)" in javascript
    assert "function ensureModal(id, overlayClose)" in javascript  # WF_008: idempotente
    assert "function ensureStylesheet()" in javascript  # WF_004
    assert "window.limpiarRetrabajo" in javascript  # WF_003 cleanup
    # Filtro por columna estilo ICT en la tabla principal y en las de los modales.
    assert 'data-rtb-table="lista"' in template
    assert "function aplicarFiltros(table)" in javascript
    for clave in ("detalle_programacion", "detalle_componentes", "detalle_salidas",
                  "detalle_escaneos"):
        assert f'"{clave}"' in javascript, clave
    tabs = (ROOT / "app/static/js/sidebar-tabs.js").read_text(encoding="utf-8")
    assert "container: 'retrabajo-unique-container'" in tabs  # WF_006 paso 6
    assert "retrabajo" not in salidas
    shipping = (ROOT / "app/api/pda/shipping_material.py").read_text(encoding="utf-8")
    # Las 3 rutas que ponen departure (2 altas de salida + asignacion) validan el folio RT.
    assert shipping.count("validar_departure_retrabajo(") == 3
