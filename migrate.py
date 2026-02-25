import os
import time

# Forzar ejecución de bootstrap pesado una sola vez.
os.environ["MES_USE_RELOADER"] = "0"
os.environ["MES_FORCE_STARTUP_INIT"] = "1"
os.environ.pop("MES_SKIP_STARTUP_INIT", None)


def main():
    t0 = time.time()
    print("[migrate] Inicio de bootstrap de base de datos...")

    from app_factory import create_app

    create_app()
    elapsed = round(time.time() - t0, 2)
    print(f"[migrate] Bootstrap completado en {elapsed}s")


if __name__ == "__main__":
    main()

