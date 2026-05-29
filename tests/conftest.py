"""Configuracion compartida de pytest.

Fija variables de entorno seguras para que la app arranque en CI / local
sin tocar inicializaciones de BD ni depender de un MySQL real:

  - MES_SKIP_STARTUP_INIT=1  -> no corre DDL/workers al crear la app.
  - SECRET_KEY               -> evita la clave efimera (sesiones estables).
"""

import os

os.environ.setdefault("MES_SKIP_STARTUP_INIT", "1")
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-prod")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import pytest


@pytest.fixture(scope="session")
def app():
    from app_factory import create_app

    application = create_app()
    application.config.update(TESTING=True)
    return application


@pytest.fixture()
def client(app):
    return app.test_client()
