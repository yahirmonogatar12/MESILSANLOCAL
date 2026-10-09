"""Papeleria de ECOs: validacion de subida y entrega segura del HTML."""

import os
import time

from app.api.informacion_basica import eco_files


def _sin_bd(monkeypatch, tmp_path):
    inserts = []
    monkeypatch.setattr(eco_files, "STORAGE_ROOT", str(tmp_path))
    monkeypatch.setattr(eco_files, "execute_query", lambda q, p=None, fetch=None: inserts.append(p) or 1)
    return inserts


def test_guardar_valida_tipo_vacio_y_tamano(monkeypatch, tmp_path):
    _sin_bd(monkeypatch, tmp_path)
    monkeypatch.setattr(eco_files, "MAX_BYTES", 10)

    assert "HTML, PPT/PPTX o PDF" in eco_files.guardar(1, "virus.exe", b"x", "ana")
    assert "vacio" in eco_files.guardar(1, "a.html", b"", "ana")
    assert "excede" in eco_files.guardar(1, "a.pptx", b"x" * 11, "ana")
    assert not (tmp_path / "1").exists()


def test_guardar_no_usa_el_nombre_subido_como_ruta(monkeypatch, tmp_path):
    inserts = _sin_bd(monkeypatch, tmp_path)

    assert eco_files.guardar(7, "..\\..\\Papeleria ECO.HTML", b"<p>hola</p>", "ana") is None

    eco_id, nombre, extension, ruta, size, usuario = inserts[0]
    assert (eco_id, nombre, extension, size, usuario) == (7, "Papeleria ECO.HTML", ".html", 11, "ana")
    assert os.path.dirname(ruta) == "7" and ruta.endswith(".html")
    assert (tmp_path / ruta).read_bytes() == b"<p>hola</p>"
    # Una ruta guardada que escape del root nunca se sirve.
    assert eco_files.ruta_absoluta({"archivo_ruta": os.path.join("..", "x.html")}) is None


def _login(client):
    with client.session_transaction() as sess:
        sess["usuario"] = "ana"
        sess["_last_activity_touch_ts"] = int(time.time())


def test_archivos_del_modelo_buscan_el_numero_de_parte_exacto(client, monkeypatch):
    buscadas = []
    monkeypatch.setattr(eco_files, "ultimo_eco_con_papeleria", lambda pn: buscadas.append(pn) or ({"id": 9, "eco_no": "E1"} if pn == "EBR80757421" else None))
    monkeypatch.setattr(eco_files, "listar", lambda eco_id: [{"id": 1, "nombre_original": "dibujo.pdf"}])
    _login(client)

    data = client.get("/api/bom/papeleria?part_no=ebr80757421").get_json()
    assert buscadas == ["EBR80757421"]
    assert data["eco"]["eco_no"] == "E1" and data["files"][0]["nombre_original"] == "dibujo.pdf"

    # Otro modelo de la misma familia no hereda los archivos.
    data = client.get("/api/bom/papeleria?part_no=EBR80757422").get_json()
    assert data["eco"] is None and data["files"] == []


def test_html_se_sirve_en_sandbox(client, monkeypatch, tmp_path):
    _sin_bd(monkeypatch, tmp_path)
    (tmp_path / "3").mkdir()
    (tmp_path / "3" / "doc.html").write_bytes(b"<script>alert(1)</script>")
    row = {"id": 5, "extension": ".html", "archivo_ruta": os.path.join("3", "doc.html"), "nombre_original": "doc.html"}
    monkeypatch.setattr(eco_files, "obtener", lambda eco_id, file_id: row)
    with client.session_transaction() as sess:
        sess["usuario"] = "ana"
        sess["_last_activity_touch_ts"] = int(time.time())

    response = client.get("/api/ecos/3/files/5")

    assert response.status_code == 200
    assert response.headers["Content-Security-Policy"] == "sandbox"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.mimetype == "text/html"
