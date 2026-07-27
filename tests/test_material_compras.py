from decimal import Decimal
from types import SimpleNamespace

from app.api.control_material.compras_core import service as compras_service


def _line(
    transaction,
    part,
    quantity="10.0000",
    unit_cost="1.2500",
    total="12.5000",
    date="2026-07-10",
):
    return {
        "numero_transaccion": transaction,
        "raw_part_num": part,
        "numero_parte": part,
        "numero_parte_sistema": part,
        "fecha_compra": date,
        "cantidad": Decimal(quantity),
        "costo_unitario": Decimal(unit_cost),
        "costo_total": Decimal(total),
        "fecha_factura": date,
        "proveedor": "ILSÁN",
        "factura": "F-1",
        "modelo": "LG",
        "categoria": "PCB",
    }


class _ExistingLinesCursor:
    def __init__(self, rows):
        self.rows = rows
        self.result = []
        self.calls = []

    def execute(self, query, params=None):
        params = list(params or [])
        self.calls.append((" ".join(query.split()), params))
        tipo = params[0]
        if "numero_transaccion = ''" in query:
            keys = {""}
        else:
            keys = {compras_service._transaction_key(v) for v in params[1:]}
        self.result = [
            row
            for row in self.rows
            if row["tipo"] == tipo
            and compras_service._transaction_key(row["numero_transaccion"]) in keys
        ]

    def fetchall(self):
        return self.result

    def close(self):
        pass


def _db_row(row, row_id, tipo="LG"):
    return {"id": row_id, "tipo": tipo, **row}


def test_transaction_key_ignora_mayusculas_y_acentos():
    variants = {"Remision", "REMISION", "REMISIÓN", "REMISIÒN"}

    assert {compras_service._transaction_key(value) for value in variants} == {
        "remision"
    }


def test_filter_new_lines_no_reinserta_variantes_de_la_misma_compra():
    stored = _line("Remision", "MCK67482303")
    cursor = _ExistingLinesCursor([_db_row(stored, 1)])
    same_purchase = _line("REMISIÓN", "MCK67482303")

    new_lines, matched, transaction_keys = compras_service._filter_new_lines(
        cursor, "LG", [same_purchase]
    )

    assert new_lines == []
    assert matched == 1
    assert transaction_keys == {"remision"}


def test_filter_new_lines_permite_nueva_parte_en_transaccion_existente():
    stored = _line("900006127615", "PARTE-A")
    cursor = _ExistingLinesCursor([_db_row(stored, 1, "OVEN")])
    incoming = [stored.copy(), _line("900006127615", "PARTE-B")]

    new_lines, matched, _ = compras_service._filter_new_lines(
        cursor, "OVEN", incoming
    )

    assert matched == 1
    assert [line["raw_part_num"] for line in new_lines] == ["PARTE-B"]


def test_filter_new_lines_conserva_multiplicidad_de_renglones_identicos():
    stored = _line("transaction", "EAN60665801")
    cursor = _ExistingLinesCursor([_db_row(stored, 1, "OVEN")])
    incoming = [stored.copy(), stored.copy()]

    new_lines, matched, _ = compras_service._filter_new_lines(
        cursor, "OVEN", incoming
    )

    assert matched == 1
    assert len(new_lines) == 1


def test_existing_lines_consulta_transacciones_en_bloques():
    cursor = _ExistingLinesCursor([])
    incoming = [_line(f"TX-{i:04d}", "PARTE") for i in range(1201)]

    compras_service._existing_lines(cursor, "LG", incoming)

    assert len(cursor.calls) == 3
    assert max(len(params) for _, params in cursor.calls) == 501


def test_parse_cached_reutiliza_preview_y_devuelve_copias_independientes(monkeypatch):
    calls = []

    def fake_parse(file_bytes, filename):
        calls.append((file_bytes, filename))
        return {"lineas": [{"numero_transaccion": "TX-1"}], "warnings": []}

    monkeypatch.setattr(compras_service, "parse_compras_workbook", fake_parse)
    compras_service._parse_cache.clear()

    first, first_hash = compras_service._parse_cached(b"same-excel", "lg.xlsx")
    first["lineas"][0]["numero_transaccion"] = "MUTATED"
    second, second_hash = compras_service._parse_cached(b"same-excel", "lg.xlsx")

    assert len(calls) == 1
    assert first_hash == second_hash
    assert second["lineas"][0]["numero_transaccion"] == "TX-1"


def test_preview_actualizacion_muestra_solamente_renglones_nuevos(monkeypatch):
    stored = _line("TX-1", "PARTE-A")
    incoming = [stored.copy(), _line("TX-1", "PARTE-B")]
    cursor = _ExistingLinesCursor([_db_row(stored, 1)])

    class Connection:
        def close(self):
            pass

    monkeypatch.setattr(
        compras_service,
        "_parse_cached",
        lambda *_: ({"lineas": incoming, "warnings": []}, "file-hash"),
    )
    monkeypatch.setattr(
        compras_service, "_db", lambda: (Connection(), cursor, None)
    )

    payload, status = compras_service.preview_compras(
        {"file": SimpleNamespace(filename="lg.xlsx", read=lambda: b"excel")},
        {"tipo": "LG", "modo": "ACTUALIZACION"},
    )

    assert status == 200
    assert payload["total_lineas"] == 2
    assert payload["lineas_existentes"] == 1
    assert payload["lineas_nuevas"] == 1
    assert [row["raw_part_num"] for row in payload["sample"]] == ["PARTE-B"]


class _SyncCursor(_ExistingLinesCursor):
    """_ExistingLinesCursor + la consulta de lotes aplicados por linea."""

    def __init__(self, rows, ids_con_lote=()):
        super().__init__(rows)
        self.ids_con_lote = set(ids_con_lote)

    def execute(self, query, params=None):
        if "lista_compras_lot_links" in query:
            self.calls.append((" ".join(query.split()), list(params or [])))
            self.result = [
                {"transaccion_linea_id": value}
                for value in (params or [])
                if value in self.ids_con_lote
            ]
            return
        if "raw_part_num IN" in query:  # candidatos a cambio de transaccion
            params = list(params or [])
            self.calls.append((" ".join(query.split()), params))
            partes = {compras_service._text_key(value) for value in params[1:]}
            self.result = [
                row
                for row in self.rows
                if row["tipo"] == params[0]
                and compras_service._text_key(row["raw_part_num"]) in partes
            ]
            return
        super().execute(query, params)


def test_sync_plan_detecta_nuevas_modificadas_y_faltantes():
    guardada = _db_row(_line("TX-1", "PARTE-A"), 1)
    borrada = _db_row(_line("TX-1", "PARTE-B"), 2)
    cursor = _SyncCursor([guardada, borrada])
    excel = [
        _line("TX-1", "PARTE-A", quantity="20.0000"),  # cambio de cantidad
        _line("TX-1", "PARTE-C"),  # nueva
    ]

    plan = compras_service._sync_plan(cursor, "LG", excel)

    assert [l["raw_part_num"] for l in plan["nuevas"]] == ["PARTE-C"]
    assert [row_id for row_id, _ in plan["modificadas"]] == [1]
    assert [row["id"] for row in plan["faltantes"]] == [2]
    assert plan["sin_cambio"] == 0


def test_sync_plan_detecta_cambio_de_numero_de_transaccion():
    guardada = _db_row(_line("TX-VIEJA", "PARTE-A"), 1)
    cursor = _SyncCursor([guardada])
    # Mismo renglon, mismo todo, otro numero de transaccion.
    excel = [_line("TX-NUEVA", "PARTE-A")]

    plan = compras_service._sync_plan(cursor, "LG", excel)

    assert plan["nuevas"] == [] and plan["faltantes"] == []
    row_id, linea, anterior = plan["renombradas"][0]
    assert (row_id, anterior, linea["numero_transaccion"]) == (1, "TX-VIEJA", "TX-NUEVA")


def test_sync_plan_renombra_aunque_tenga_lote_aplicado():
    guardada = _db_row(_line("TX-VIEJA", "PARTE-A"), 1)
    cursor = _SyncCursor([guardada], ids_con_lote={1})

    plan = compras_service._sync_plan(cursor, "LG", [_line("TX-NUEVA", "PARTE-A")])

    # El lote no bloquea: viaja con el renglon en vez de desaplicarse.
    assert len(plan["renombradas"]) == 1
    assert plan["bloqueadas"] == []


def test_rename_lineas_mueve_el_renglon_y_sus_links():
    ejecutadas = []

    class Cursor:
        def execute(self, query, params=None):
            ejecutadas.append((" ".join(query.split()), tuple(params or ())))

    compras_service._rename_lineas(Cursor(), 7, [(1, _line("TX-NUEVA", "PARTE-A"), "TX-VIEJA")])

    assert ejecutadas[0][0].startswith("UPDATE lista_compras_lineas SET numero_transaccion")
    assert ejecutadas[0][1] == ("TX-NUEVA", 7, 1)
    assert ejecutadas[1][0].startswith("UPDATE lista_compras_lot_links SET numero_transaccion")
    assert ejecutadas[1][1] == ("TX-NUEVA", 1)


def test_sync_plan_no_renombra_si_hay_varios_candidatos():
    cursor = _SyncCursor([
        _db_row(_line("TX-A", "PARTE-A"), 1),
        _db_row(_line("TX-B", "PARTE-A"), 2),
    ])
    # Dos salen y dos entran con la misma firma: no se puede parear 1 a 1.
    excel = [_line("TX-C", "PARTE-A"), _line("TX-D", "PARTE-A")]

    plan = compras_service._sync_plan(cursor, "LG", excel)

    # Entran como nuevas; TX-A y TX-B no se tocan porque el archivo ni las menciona.
    assert plan["renombradas"] == []
    assert len(plan["nuevas"]) == 2 and plan["faltantes"] == []


def test_sync_plan_no_toca_lineas_con_lote_aplicado():
    guardada = _db_row(_line("TX-1", "PARTE-A"), 1)
    borrada = _db_row(_line("TX-1", "PARTE-B"), 2)
    cursor = _SyncCursor([guardada, borrada], ids_con_lote={1, 2})
    excel = [_line("TX-1", "PARTE-A", quantity="20.0000")]

    plan = compras_service._sync_plan(cursor, "LG", excel)

    assert plan["modificadas"] == [] and plan["faltantes"] == []
    assert {b["id"] for b in plan["bloqueadas"]} == {1, 2}
    assert all(b["motivo"] == "lote aplicado" for b in plan["bloqueadas"])


def test_sync_plan_protege_el_historico_cerrado():
    historica = {**_db_row(_line("TX-1", "PARTE-A"), 1), "estado": "CERRADA"}
    viva = {**_db_row(_line("TX-1", "PARTE-B"), 2), "estado": "ABIERTA"}
    cursor = _SyncCursor([historica, viva])

    # El Excel ya no trae PARTE-A: la viva se borraria, la del historico no.
    plan = compras_service._sync_plan(cursor, "LG", [_line("TX-1", "PARTE-C")])

    assert [row["id"] for row in plan["faltantes"]] == [2]
    assert [row["id"] for row in plan["protegidas"]] == [1]
    assert plan["protegidas"][0]["motivo"].startswith("histórico")


def test_sync_plan_solo_compara_transacciones_del_archivo():
    otra = _db_row(_line("TX-9", "PARTE-X"), 5)
    cursor = _SyncCursor([otra])

    plan = compras_service._sync_plan(cursor, "LG", [_line("TX-1", "PARTE-A")])

    assert plan["faltantes"] == []
    assert [l["raw_part_num"] for l in plan["nuevas"]] == ["PARTE-A"]


class _TransactionConnection:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        pass


class _CloseTransactionCursor:
    def __init__(self):
        self.queries = []
        self._row = None

    def execute(self, query, params=None):
        normalized = " ".join(query.split())
        self.queries.append((normalized, tuple(params or ())))
        self._row = {"id": 1} if normalized.startswith("SELECT id") else None

    def fetchone(self):
        return self._row

    def close(self):
        pass


def test_set_transaccion_closed_cierra_sin_tocar_links(monkeypatch):
    conn = _TransactionConnection()
    cursor = _CloseTransactionCursor()
    monkeypatch.setattr(compras_service, "_db", lambda: (conn, cursor, None))

    payload, status = compras_service.set_transaccion_closed("TX-1", "LG", True)

    assert status == 200
    assert payload["cerrada"] is True
    assert conn.commits == 1
    update = next(query for query, _ in cursor.queries if query.startswith("UPDATE"))
    assert "SET estado = 'CERRADA'" in update
    assert "lista_compras_lot_links" not in update


def test_set_transaccion_closed_reabre_recalculando_aplicada_o_abierta(monkeypatch):
    conn = _TransactionConnection()
    cursor = _CloseTransactionCursor()
    monkeypatch.setattr(compras_service, "_db", lambda: (conn, cursor, None))

    payload, status = compras_service.set_transaccion_closed("TX-1", "OVEN", False)

    assert status == 200
    assert payload["cerrada"] is False
    update = next(query for query, _ in cursor.queries if query.startswith("UPDATE"))
    assert "LEFT JOIN" in update
    assert "THEN 'APLICADA'" in update
    assert "ELSE 'ABIERTA'" in update


class _DetailCursor:
    def __init__(self):
        self.result = []
        self.calls = []

    def execute(self, query, params=None):
        normalized = " ".join(query.split())
        self.calls.append((normalized, tuple(params or ())))
        if normalized.startswith("SELECT l.*"):
            self.result = [
                {
                    **_line("TX-1", "PARTE-A"),
                    "id": 10,
                    "tipo": "LG",
                    "estado": "ABIERTA",
                    "aplicado": Decimal("5"),
                    "pendiente": Decimal("5"),
                }
            ]
        elif normalized.startswith("SELECT ll.*"):
            self.result = [
                {
                    "id": 20,
                    "transaccion_linea_id": 10,
                    "codigo_material_recibido": "LOTE-001",
                    "numero_parte_sistema": "PARTE-A",
                    "cantidad_aplicada": Decimal("5"),
                    "costo_unitario": Decimal("1.25"),
                    "moneda": "USD",
                    "estado": "APLICADO",
                }
            ]

    def fetchall(self):
        return self.result

    def close(self):
        pass


def test_get_transaccion_detail_incluye_lotes_vinculados(monkeypatch):
    conn = _TransactionConnection()
    cursor = _DetailCursor()
    monkeypatch.setattr(compras_service, "_db", lambda: (conn, cursor, None))

    payload, status = compras_service.get_transaccion_detail("TX-1", "LG")

    assert status == 200
    assert payload["transaccion"] == {
        "numero_transaccion": "TX-1",
        "tipo": "LG",
        "estado": "ABIERTA",
        "cerrada": False,
    }
    assert payload["links"][0]["codigo_material_recibido"] == "LOTE-001"
    assert cursor.calls[0][1] == ("TX-1", "LG")


class _DeleteCargaCursor:
    def __init__(self, links_activos):
        self.links_activos = links_activos
        self.queries = []
        self._row = None

    def execute(self, query, params=None):
        normalized = " ".join(query.split())
        self.queries.append((normalized, tuple(params or ())))
        if normalized.startswith("SELECT archivo_ruta"):
            self._row = {"archivo_ruta": "2026/07/compras__abc.xlsx"}
        elif normalized.startswith("SELECT COUNT(*)"):
            self._row = {"total": self.links_activos}

    def fetchone(self):
        return self._row

    def close(self):
        pass


def test_delete_carga_bloquea_si_hay_lotes_aplicados(monkeypatch):
    conn = _TransactionConnection()
    cursor = _DeleteCargaCursor(links_activos=2)
    monkeypatch.setattr(compras_service, "_db", lambda: (conn, cursor, None))

    payload, status = compras_service.delete_carga(7)

    assert status == 409
    assert payload["links"] == 2
    assert conn.commits == 0 and conn.rollbacks == 1
    assert not any(query.startswith("DELETE") for query, _ in cursor.queries)


def test_delete_carga_limpia_links_desaplicados(monkeypatch):
    conn = _TransactionConnection()
    cursor = _DeleteCargaCursor(links_activos=0)
    monkeypatch.setattr(compras_service, "_db", lambda: (conn, cursor, None))
    monkeypatch.setattr(compras_service, "delete_file", lambda ruta: None)

    payload, status = compras_service.delete_carga(7)

    assert (payload, status) == ({"success": True}, 200)
    assert conn.commits == 1
    deletes = [query for query, _ in cursor.queries if query.startswith("DELETE")]
    assert deletes[0].startswith("DELETE ll FROM lista_compras_lot_links")
    assert len(deletes) == 3


class _LinksCursor:
    """Cursor falso para desaplicar/reaplicar: guarda queries y sirve filas fijas."""

    def __init__(self, links, lote_ya_aplicado=False):
        self.links = links
        self.lote_ya_aplicado = lote_ya_aplicado
        self.queries = []
        self._rows = []
        self._row = None

    def execute(self, query, params=None):
        normalized = " ".join(query.split())
        self.queries.append((normalized, tuple(params or ())))
        self._rows, self._row = [], None
        if normalized.startswith("SELECT id FROM lista_compras_lineas"):
            self._row = {"id": 1}
        elif normalized.startswith("SELECT id, codigo_material_recibido"):
            self._rows = list(self.links)
        elif normalized.startswith("SELECT id FROM lista_compras_lot_links"):
            self._row = {"id": 99} if self.lote_ya_aplicado else None

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._row

    def close(self):
        pass


def test_unapply_transaccion_marca_links_y_recalcula(monkeypatch):
    conn = _TransactionConnection()
    cursor = _LinksCursor([{"id": 10, "codigo_material_recibido": "LOTE-1"}])
    recalculados = []
    monkeypatch.setattr(compras_service, "_db", lambda: (conn, cursor, None))
    monkeypatch.setattr(compras_service, "_usuario_actual", lambda: "TESTER")
    monkeypatch.setattr(
        compras_service, "recalculate_lot_cost",
        lambda _cursor, codigo, _usuario: recalculados.append(codigo) or True,
    )

    payload, status = compras_service.unapply_transaccion("TX-1", "LG", {"motivo": "error de captura"})

    assert status == 200
    assert payload["links_desaplicados"] == 1
    assert conn.commits == 1
    assert recalculados == ["LOTE-1"]
    update = next(q for q, _ in cursor.queries if q.startswith("UPDATE lista_compras_lot_links"))
    assert "SET estado = 'DESAPLICADO'" in update
    # El historico de la carga inicial no debe reabrirse al desaplicar un lote.
    estados = next(q for q, _ in cursor.queries if q.startswith("UPDATE lista_compras_lineas"))
    assert "l.estado <> 'CERRADA'" in estados


def test_reapply_transaccion_omite_lotes_con_otra_compra_activa(monkeypatch):
    conn = _TransactionConnection()
    cursor = _LinksCursor(
        [{"id": 10, "codigo_material_recibido": "LOTE-1"}], lote_ya_aplicado=True
    )
    monkeypatch.setattr(compras_service, "_db", lambda: (conn, cursor, None))
    monkeypatch.setattr(compras_service, "_usuario_actual", lambda: "TESTER")
    monkeypatch.setattr(compras_service, "recalculate_lot_cost", lambda *_: True)

    payload, status = compras_service.reapply_transaccion("TX-1", "LG")

    assert status == 200
    assert payload["links_reaplicados"] == 0
    assert payload["omitidos"] == ["LOTE-1"]
    assert not any(q.startswith("UPDATE lista_compras_lot_links") for q, _ in cursor.queries)


def test_reapply_transaccion_restaura_link_libre(monkeypatch):
    conn = _TransactionConnection()
    cursor = _LinksCursor([{"id": 10, "codigo_material_recibido": "LOTE-1"}])
    monkeypatch.setattr(compras_service, "_db", lambda: (conn, cursor, None))
    monkeypatch.setattr(compras_service, "_usuario_actual", lambda: "TESTER")
    monkeypatch.setattr(compras_service, "recalculate_lot_cost", lambda *_: True)

    payload, status = compras_service.reapply_transaccion("TX-1", "LG")

    assert (status, payload["links_reaplicados"], payload["omitidos"]) == (200, 1, [])
    update = next(q for q, _ in cursor.queries if q.startswith("UPDATE lista_compras_lot_links"))
    assert "SET estado = 'APLICADO'" in update
    assert "fecha_desaplicado = NULL" in update


def test_material_compras_registra_rutas_de_aplicacion(app):
    rules = {str(rule): set(rule.methods or []) for rule in app.url_map.iter_rules()}

    for accion in ("unapply", "reapply"):
        path = f"/api/material_admin/compras/transacciones/<path:numero>/{accion}"
        assert path in rules and "POST" in rules[path]


def test_material_compras_registra_ruta_de_cierre(app):
    rules = {str(rule): set(rule.methods or []) for rule in app.url_map.iter_rules()}

    close_path = "/api/material_admin/compras/transacciones/<path:numero>/close"
    assert close_path in rules
    assert "POST" in rules[close_path]
