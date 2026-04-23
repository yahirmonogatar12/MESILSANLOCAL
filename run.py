import os
import sys


def _env_flag(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on", "si")


def _configure_stdio():
    """Force UTF-8 stdio early for Windows consoles before importing the app."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_configure_stdio()

from waitress import serve

from app_factory import create_app

os.environ.setdefault("MES_USE_RELOADER", "0")
app = create_app()


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    threads = int(os.environ.get("WAITRESS_THREADS", "8"))
    expose_tracebacks = _env_flag(
        "WAITRESS_EXPOSE_TRACEBACKS",
        os.environ.get("FLASK_ENV", "").strip().lower() == "development",
    )

    print(
        f"Servidor iniciado en http://{host}:{port} "
        f"(waitress, threads={threads}, expose_tracebacks={expose_tracebacks})"
    )
    serve(
        app,
        host=host,
        port=port,
        threads=threads,
        expose_tracebacks=expose_tracebacks,
    )
