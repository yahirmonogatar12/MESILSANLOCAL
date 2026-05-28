"""Allowlist de rutas API que no usan la sesion web del portal."""

PUBLIC_API_EXACT_PATHS = frozenset(
    {
        "/api/shipping/auth/login",
        "/api/shipping/auth/logout",
        "/api/shipping/permissions/available",
        "/api/shipping/departments",
        "/api/shipping/cargos",
        "/api/shipping/entries",
        "/api/shipping/stats/today",
        "/api/shipping/stats/summary",
        "/api/shipping/material/entries",
        "/api/shipping/material/entries/boxes",
        "/api/shipping/material/exits",
        "/api/shipping/material/exits/boxes",
        "/api/shipping/material/returns",
        "/api/shipping/material/inventory",
        "/api/shipping/material/stats/today",
    }
)

PUBLIC_API_PREFIXES = (
    "/api/shipping/auth/verify/",
    "/api/shipping/users/",
    "/api/shipping/quality/",
    "/api/shipping/entries/",
    "/api/shipping/material/boxes/",
)


def is_public_api_route(path):
    """Return True when `path` is exempt from the portal web session."""
    normalized_path = (path or "").rstrip("/")
    return normalized_path in PUBLIC_API_EXACT_PATHS or any(
        normalized_path.startswith(prefix) for prefix in PUBLIC_API_PREFIXES
    )
