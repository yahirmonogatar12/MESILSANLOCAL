"""Tests de la capa de datos: execute_query fail-loud + convert pass-through."""

import pytest

import app.config_mysql as cm


def test_execute_query_relanza_si_mysql_no_disponible(monkeypatch):
    monkeypatch.setattr(cm, "MYSQL_AVAILABLE", False)
    with pytest.raises(RuntimeError):
        cm.execute_query("SELECT 1", fetch="all")


def test_execute_query_relanza_si_no_hay_conexion(monkeypatch):
    monkeypatch.setattr(cm, "MYSQL_AVAILABLE", True)
    monkeypatch.setattr(cm, "_get_pooled_connection", lambda: None)
    with pytest.raises(RuntimeError):
        cm.execute_query("SELECT 1", fetch="all")


def test_convert_sqlite_to_mysql_es_passthrough_y_no_corrompe():
    # Antes, reemplazos de substring ciegos corrompian identificadores/literales
    # que contuvieran REAL / CURRENT_TIMESTAMP / BLOB / AUTOINCREMENT.
    q = "SELECT AREAL, GLOBAL_X FROM t WHERE nota = 'CURRENT_TIMESTAMP'"
    assert cm.convert_sqlite_to_mysql(q) == q


def test_convert_sqlite_to_mysql_preserva_limit_offset():
    q = "SELECT * FROM t LIMIT 10 OFFSET 20"
    assert cm.convert_sqlite_to_mysql(q) == q
