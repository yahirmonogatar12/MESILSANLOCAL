from datetime import date

import pytest

from app.api.control_produccion import part_planning as pp


PROPOSAL_PUBLIC_ID = "11111111-1111-4111-8111-111111111111"


def _header(**overrides):
    row = {
        "id": 41,
        "public_id": PROPOSAL_PUBLIC_ID,
        "version": 1,
        "date_from": date(2026, 7, 20),
        "date_to": date(2026, 7, 25),
        "input_hash": "hash-vigente",
        "engine_version": pp.PPY_PROPOSAL_ENGINE_VERSION,
        "status": "PENDING_CONFIRMATION",
        "total_items": 1,
    }
    row.update(overrides)
    return row


def test_aplicar_propuesta_ya_aplicada_es_idempotente(monkeypatch):
    header = _header(status="APPLIED", total_items=7)
    def fake_query(sql, *_args, **_kwargs):
        if "FROM lg_plan_proposal_items" in sql:
            return {
                "aplicadas": 5,
                "modificadas": 2,
                "excluidas": 2,
                "total_qty": 900,
            }
        return header

    monkeypatch.setattr(pp, "execute_query", fake_query)
    monkeypatch.setattr(
        pp,
        "_ppy_simular_schedule",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Una propuesta aplicada no debe recalcularse")
        ),
    )
    monkeypatch.setattr(
        pp,
        "get_pooled_connection",
        lambda: (_ for _ in ()).throw(
            AssertionError("Una propuesta aplicada no debe abrir otra transaccion")
        ),
    )

    result = pp._ppy_aplicar_propuesta(PROPOSAL_PUBLIC_ID, "ana", version=1)

    assert result == {
        "proposal_id": PROPOSAL_PUBLIC_ID,
        "status": "APPLIED",
        "aplicadas": 5,
        "modificadas": 2,
        "excluidas": 2,
        "total_qty": 900,
        "already_applied": True,
    }


def test_aplicar_propuesta_rechaza_hash_stale_y_marca_estado(monkeypatch):
    header = _header(input_hash="hash-original")
    sql_calls = []

    def fake_execute_query(sql, params=(), **kwargs):
        sql_calls.append((sql, params, kwargs))
        if sql.startswith("SELECT * FROM lg_plan_proposals"):
            return header
        return None

    monkeypatch.setattr(pp, "execute_query", fake_execute_query)
    monkeypatch.setattr(
        pp,
        "_ppy_simular_schedule",
        lambda *_args, **_kwargs: ([], [], [{"code": "INPUT_CHANGED"}]),
    )
    monkeypatch.setattr(pp, "_ppy_proposal_hash", lambda *_args: "hash-actual")
    cursor = _ProposalCursor(header, {})
    connection = _ProposalConnection()
    monkeypatch.setattr(pp, "get_pooled_connection", lambda: connection)
    monkeypatch.setattr(pp, "get_dict_cursor", lambda _connection: cursor)

    with pytest.raises(pp.PPYProposalStaleError, match="genera una propuesta nueva"):
        pp._ppy_aplicar_propuesta(PROPOSAL_PUBLIC_ID, "ana", version=1)

    stale_updates = [
        (sql, params)
        for sql, params in cursor.calls
        if "SET status='STALE'" in sql
    ]
    assert stale_updates
    assert all(params == ("ana", 41) for _sql, params in stale_updates)


class _ProposalCursor:
    def __init__(self, locked_header, stored_item, schedule_rows=None,
                 confirmed_rows=None):
        self.locked_header = locked_header
        self.stored_item = stored_item
        self.schedule_rows = list(schedule_rows or [])
        self.confirmed_rows = list(confirmed_rows or [])
        self.calls = []
        self._one = None
        self._many = []
        self.closed = False

    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        self._one = None
        self._many = []
        if "FROM lg_plan_proposals WHERE id=%s FOR UPDATE" in sql:
            self._one = self.locked_header
        elif "FROM lg_plan_proposal_items" in sql:
            self._many = [self.stored_item]
        elif "FROM lg_lote_plan" in sql:
            self._many = (
                list(self.confirmed_rows) if "status='CONFIRMADO'" in sql else []
            )
        elif "FROM lg_schedule_daily" in sql and sql.lstrip().startswith("SELECT"):
            self._many = list(self.schedule_rows)

    def fetchone(self):
        return self._one

    def fetchall(self):
        return list(self._many)

    def close(self):
        self.closed = True


class _ProposalConnection:
    def __init__(self):
        self.autocommit_values = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def autocommit(self, enabled):
        self.autocommit_values.append(enabled)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


def _stored_item(**overrides):
    row = {
        "id": 91,
        "public_id": "22222222-2222-4222-8222-222222222222",
        "proposal_id": 41,
        "part_no": "EBR80757421",
        "sched_date": date(2026, 7, 20),
        "linea": "M1",
        "turno": "DIA",
        "qty_proposed": 200,
        "ct": 36,
        "uph": 100,
        "pack_size": 20,
        "base_sched_qty": 0,
        "base_sched_linea": None,
        "base_sched_turno": None,
    }
    row.update(overrides)
    return row


def _mock_apply_dependencies(monkeypatch, stored_item, schedule_rows=None,
                            confirmed_rows=None):
    header = _header()
    cursor = _ProposalCursor(
        header, stored_item, schedule_rows=schedule_rows,
        confirmed_rows=confirmed_rows,
    )
    connection = _ProposalConnection()
    monkeypatch.setattr(pp, "execute_query", lambda *_args, **_kwargs: header)
    monkeypatch.setattr(
        pp, "_ppy_simular_schedule", lambda *_args, **_kwargs: ([], [], [])
    )
    monkeypatch.setattr(pp, "_ppy_proposal_hash", lambda *_args: header["input_hash"])
    monkeypatch.setattr(pp, "get_pooled_connection", lambda: connection)
    monkeypatch.setattr(pp, "get_dict_cursor", lambda _connection: cursor)
    monkeypatch.setattr(pp, "_ppy_config_lineas", lambda *_args: ["M1", "M2"])
    monkeypatch.setattr(pp, "_ppy_lineas_permitidas_map", lambda *_args: ({}, {}))
    monkeypatch.setattr(
        pp,
        "_ppy_datos_raw",
        lambda parts, *_args: {
            part: {"uph": 100, "c_t": 36, "estandar_pack": 20}
            for part in parts
        },
    )
    return cursor, connection


@pytest.mark.parametrize(
    ("change", "mensaje"),
    [
        ({"included": "false"}, "included debe ser booleano"),
        ({"included": True, "sched_date": "20/07/2026"}, "Fecha invalida"),
    ],
)
def test_aplicar_propuesta_rechaza_tipos_de_item_invalidos(
    monkeypatch, change, mensaje
):
    stored_item = _stored_item()
    cursor, connection = _mock_apply_dependencies(monkeypatch, stored_item)
    item_change = {"item_id": stored_item["public_id"], **change}

    with pytest.raises(ValueError, match=mensaje):
        pp._ppy_aplicar_propuesta(
            PROPOSAL_PUBLIC_ID,
            "ana",
            version=1,
            items=[item_change],
        )

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert not any(
        sql.startswith("INSERT INTO lg_schedule_daily")
        for sql, _params in cursor.calls
    )


def test_aplicar_propuesta_puede_optimizar_linea_y_reemplaza_schedule(monkeypatch):
    stored_item = _stored_item(
        linea="M2",
        base_sched_qty=100,
        base_sched_linea="M1",
        base_sched_turno="DIA",
    )
    schedule_rows = [
        {
            "part_no": stored_item["part_no"],
            "sched_date": stored_item["sched_date"],
            "sched_qty": 100,
            "linea": "M1",
            "turno": "DIA",
        }
    ]
    cursor, connection = _mock_apply_dependencies(
        monkeypatch, stored_item, schedule_rows=schedule_rows
    )

    result = pp._ppy_aplicar_propuesta(
        PROPOSAL_PUBLIC_ID,
        "ana",
        version=1,
        items=[
            {
                "item_id": stored_item["public_id"],
                "included": True,
                "linea": "M2",
                "turno": "DIA",
            }
        ],
    )

    upserts = [
        params for sql, params in cursor.calls
        if sql.startswith("INSERT INTO lg_schedule_daily")
    ]
    assert upserts == [(
        stored_item["part_no"], stored_item["sched_date"], 200,
        "M2", "DIA", PROPOSAL_PUBLIC_ID, "ana",
    )]
    assert result["schedule_change_summary"]["MODIFICAR"] == 1
    assert connection.commits == 1
    assert connection.rollbacks == 0


def test_aplicar_propuesta_nunca_borra_un_lote_confirmado(monkeypatch):
    """El motor optimiza libremente el Schedule, pero un CONFIRMADO es el piso:
    aunque no quede en el plan nuevo, se conserva; jamas se elimina."""
    stored_item = _stored_item()  # propuesta de OTRA parte (EBR80757421 / M1)
    # una parte con schedule capturado y un lote CONFIRMADO detras, que la
    # propuesta NO incluye: sin la guarda, seria candidata a ELIMINAR.
    confirmada_dia = date(2026, 7, 21)
    schedule_rows = [{
        "part_no": "EBR30299369", "sched_date": confirmada_dia,
        "sched_qty": 500, "linea": "M2", "turno": "DIA",
    }]
    confirmed_rows = [{
        "part_no": "EBR30299369", "plan_date": confirmada_dia,
        "linea": "M2", "turno": "DIA", "qty_plan": 500, "uph": 100,
    }]
    cursor, connection = _mock_apply_dependencies(
        monkeypatch, stored_item,
        schedule_rows=schedule_rows, confirmed_rows=confirmed_rows,
    )

    result = pp._ppy_aplicar_propuesta(PROPOSAL_PUBLIC_ID, "ana", version=1)

    # NO se borra el confirmado
    deletes = [
        params for sql, params in cursor.calls
        if sql.startswith("DELETE FROM lg_schedule_daily")
    ]
    assert ("EBR30299369", confirmada_dia) not in deletes
    assert deletes == []
    # se conserva su cantidad via UPDATE (piso inamovible)
    updates = [
        params for sql, params in cursor.calls
        if sql.startswith("UPDATE lg_schedule_daily")
    ]
    assert (500, PROPOSAL_PUBLIC_ID, "ana", "EBR30299369", confirmada_dia) in updates
    assert result["schedule_change_summary"]["ELIMINAR"] == 0
    assert result["schedule_change_summary"]["CONSERVAR"] == 1  # el confirmado
    assert connection.commits == 1 and connection.rollbacks == 0


def test_aplicar_propuesta_elimina_schedule_que_no_quedo_en_plan(monkeypatch):
    stored_item = _stored_item()
    extra = {
        "part_no": "EBR30299369",
        "sched_date": date(2026, 7, 21),
        "sched_qty": 1200,
        "linea": "M2",
        "turno": "DIA",
    }
    cursor, _connection = _mock_apply_dependencies(
        monkeypatch, stored_item, schedule_rows=[extra]
    )

    result = pp._ppy_aplicar_propuesta(PROPOSAL_PUBLIC_ID, "ana", version=1)

    deletes = [
        params for sql, params in cursor.calls
        if sql.startswith("DELETE FROM lg_schedule_daily")
    ]
    assert deletes == [("EBR30299369", date(2026, 7, 21))]
    assert result["schedule_change_summary"] == {
        "CONSERVAR": 0,
        "MODIFICAR": 0,
        "AGREGAR": 1,
        "ELIMINAR": 1,
    }


def test_aplicar_propuesta_preserva_linea_turno_y_origen_en_schedule(monkeypatch):
    header = _header()
    stored_item = {
        "id": 91,
        "public_id": "22222222-2222-4222-8222-222222222222",
        "proposal_id": header["id"],
        "part_no": "EBR80757421",
        "sched_date": date(2026, 7, 20),
        "linea": "M1",
        "turno": "DIA",
        "qty_proposed": 200,
        "ct": 36,
        "uph": 100,
        "pack_size": 20,
        "base_sched_qty": 0,
        "base_sched_linea": None,
        "base_sched_turno": None,
    }
    cursor = _ProposalCursor(header, stored_item)
    connection = _ProposalConnection()

    monkeypatch.setattr(pp, "execute_query", lambda *_args, **_kwargs: header)
    monkeypatch.setattr(
        pp, "_ppy_simular_schedule", lambda *_args, **_kwargs: ([], [], [])
    )
    monkeypatch.setattr(pp, "_ppy_proposal_hash", lambda *_args: header["input_hash"])
    monkeypatch.setattr(pp, "get_pooled_connection", lambda: connection)
    monkeypatch.setattr(pp, "get_dict_cursor", lambda _connection: cursor)
    monkeypatch.setattr(pp, "_ppy_config_lineas", lambda *_args: ["M1", "M2"])
    monkeypatch.setattr(pp, "_ppy_lineas_permitidas_map", lambda *_args: ({}, {}))
    monkeypatch.setattr(pp, "_ppy_datos_raw", lambda *_args: {})

    result = pp._ppy_aplicar_propuesta(PROPOSAL_PUBLIC_ID, "ana", version=1)

    schedule_upserts = [
        (sql, params)
        for sql, params in cursor.calls
        if sql.startswith("INSERT INTO lg_schedule_daily")
    ]
    assert len(schedule_upserts) == 1
    sql, params = schedule_upserts[0]
    assert "linea, turno, proposal_public_id" in sql
    assert params == (
        "EBR80757421",
        date(2026, 7, 20),
        200,
        "M1",
        "DIA",
        PROPOSAL_PUBLIC_ID,
        "ana",
    )
    assert result == {
        "proposal_id": PROPOSAL_PUBLIC_ID,
        "status": "APPLIED",
        "aplicadas": 1,
        "modificadas": 0,
        "excluidas": 0,
        "total_qty": 200,
        "schedule_change_summary": {
            "CONSERVAR": 0,
            "MODIFICAR": 0,
            "AGREGAR": 1,
            "ELIMINAR": 0,
        },
    }
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.autocommit_values == [False, True]
    assert connection.closed is True
    assert cursor.closed is True
