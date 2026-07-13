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


def test_material_compras_registra_ruta_de_cierre(app):
    rules = {str(rule): set(rule.methods or []) for rule in app.url_map.iter_rules()}

    close_path = "/api/material_admin/compras/transacciones/<path:numero>/close"
    assert close_path in rules
    assert "POST" in rules[close_path]
