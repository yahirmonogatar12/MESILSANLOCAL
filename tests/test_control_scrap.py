import inspect

from flask import Flask

from app.api.control_proceso import control_scrap as m

ACTUAL = dict(
    scanned_original="X", scanned_original_norm="X", assy_type=None, part_no="P",
    raw_barcode=None, modelo="M", area="SMD", proceso="SMT", motivo_scrap_id=70,
    motivo_scrap_texto="Pasta", comentarios=None, cantidad=1,
)


class FakeCur:
    def __init__(self, motivo):
        self.q, self._next, self.motivo = [], None, motivo

    def execute(self, sql, params=()):
        assert sql.count("%s") == len(params), sql
        self.q.append((sql, params))
        self._next = ACTUAL if "FROM scrap_records" in sql else self.motivo

    def fetchone(self):
        return self._next

    def close(self):
        pass


class FakeConn:
    committed = rolled = False

    def begin(self):
        pass

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled = True

    def close(self):
        pass


def llamar(monkeypatch, body, motivo=None):
    cur, conn = FakeCur(motivo or {"motivo": "FALTANTE", "activo": 1}), FakeConn()
    monkeypatch.setattr(m, "conexion_o_error", lambda: (conn, None))
    monkeypatch.setattr(m, "dict_cursor", lambda c: cur)
    app = Flask(__name__)
    app.secret_key = "t"
    with app.test_request_context(json=body):
        resp = inspect.unwrap(m.api_control_scrap_update)()
    return (resp[1] if isinstance(resp, tuple) else 200), cur, conn


def test_cantidad_cero_se_guarda_con_auditoria(monkeypatch):
    status, cur, conn = llamar(monkeypatch, {"id": 1, "cantidad": 0, "motivo_scrap_id": 4, "edit_reason": "ajuste"})
    assert status == 200 and conn.committed
    assert next(p for s, p in cur.q if s.startswith("UPDATE"))[0] == 0
    audit = next(p for s, p in cur.q if s.startswith("INSERT INTO scrap_record_edits"))
    assert audit[23:25] == (1, 0)  # old/new cantidad


def test_rechaza_negativa_y_sin_motivo_de_edicion(monkeypatch):
    assert llamar(monkeypatch, {"id": 1, "cantidad": -1, "motivo_scrap_id": 4, "edit_reason": "x"})[0] == 400
    assert llamar(monkeypatch, {"id": 1, "cantidad": 2, "motivo_scrap_id": 4})[0] == 400


def test_filtros_de_columna_solo_lista_blanca():
    app = Flask(__name__)
    url = "/?start=2026-09-01&end=2026-09-02&cf_motivo=FALT&cf_xx=1;DROP&cf_cantidad=0"
    with app.test_request_context(url):
        where, params = m._filtros()
    assert "COALESCE(motivo_scrap_texto, '') LIKE %s" in where
    assert "CAST(cantidad AS CHAR) LIKE %s" in where
    assert "DROP" not in where and "%1;DROP%" not in params
    assert params[-2:] == ["%FALT%", "%0%"]


def test_motivo_inactivo_solo_si_es_el_actual(monkeypatch):
    inactivo = {"motivo": "Pasta", "activo": 0}
    assert llamar(monkeypatch, {"id": 1, "cantidad": 1, "motivo_scrap_id": 70, "edit_reason": "x"}, inactivo)[0] == 200
    status, _, conn = llamar(monkeypatch, {"id": 1, "cantidad": 1, "motivo_scrap_id": 99, "edit_reason": "x"}, inactivo)
    assert status == 400 and conn.rolled
