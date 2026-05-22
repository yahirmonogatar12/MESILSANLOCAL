"""Endpoints HTTP para apps moviles PDA (Zebra TC15 y similares).

No estan en el navbar del MES web; son APIs consumidas por las apps
moviles de embarques, almacen, calidad, etc. Cada modulo expone su
propio blueprint con prefijo `/api/<modulo>` o equivalente.

Modulos:
  - shipping.py          -> APP Registro de Embarques (entradas/salidas/auth)
                            (ex `app/shipping_api.py`)
"""
