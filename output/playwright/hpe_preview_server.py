"""Servidor local de QA visual para Historial de produccion ensamble."""

import os
import sys
import time
from datetime import date, time as clock_time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("MES_SKIP_STARTUP_INIT", "1")
os.environ.setdefault("SECRET_KEY", "hpe-visual-qa-only")

from flask import redirect, session

from app import routes
from app.api.control_resultados import historial_produccion_ensamble as hpe
from app_factory import create_app


app = create_app()
app.config.update(TESTING=False)

# La ruta de acceso QA se agrega despues del allowlist de produccion. Para este
# servidor aislado se retira solo el gate global; los decoradores reales de cada
# ruta siguen activos y se prueban con la sesion creada abajo.
app.before_request_funcs[None].remove(routes.require_login_by_default)

routes.auth_system.obtener_rol_principal_usuario = lambda _username: "superadmin"


def _fake_execute_query(_sql, params, fetch):
    if fetch == "one":
        return {"n": 225}
    per_page, offset = params[-2:]
    amount = max(0, min(per_page, 225 - offset))
    return [
        {
            "id": 1002548 - offset - index,
            "fecha": date(2026, 9, 18),
            "hora": clock_time(8 + ((offset + index) % 9), (offset + index) % 60, 12),
            "linea": f"M{1 + ((offset + index) % 4)}",
            "qr": f"I{22609000000 + offset + index};MAIN;LOT-{900 + ((offset + index) % 15)}",
            "barcode": f"EBR4103915{292260000 + offset + index}",
            "lote": f"LOT-{900 + ((offset + index) % 15)}",
        }
        for index in range(amount)
    ]


hpe.execute_query = _fake_execute_query


@app.route("/qa-login")
def qa_login():
    session["usuario"] = "qa_visual"
    session["nombre_completo"] = "QA Visual"
    session["roles"] = ["superadmin"]
    session["rol_principal"] = "superadmin"
    session["permisos"] = {}
    session["_last_activity_touch_ts"] = int(time.time())
    return redirect("/ILSAN-ELECTRONICS")


routes.PUBLIC_ROUTE_ENDPOINTS.add("qa_login")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5055, debug=False, use_reloader=False)
