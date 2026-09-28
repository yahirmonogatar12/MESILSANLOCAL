"""Constantes compartidas para invoices de material."""

ESTADOS_INVOICE = {
    "BORRADOR",
    "VALIDADA",
    "CON_DIFERENCIAS",
    "PARCIALMENTE_APLICADA",
    "APLICADA",
    "CANCELADA",
}
MONEDA_DEFAULT = "USD"
ERROR_INTERNO = "Error interno del servidor."

# Ambitos de invoice. Almacen y Embarques cargan sus propios invoices y no
# deben verse entre si; cada uno entra por su boton del sidebar y el ambito
# viaja en la ruta, nunca se infiere del usuario.
AMBITO_ALMACEN = "ALMACEN"
AMBITO_EMBARQUES = "EMBARQUES"
AMBITOS = (AMBITO_ALMACEN, AMBITO_EMBARQUES)

# Permiso de boton que habilita cada ambito (WF_001). Los nombres van sin
# apostrofes ni caracteres especiales: WF_005 documenta que rompen el guardado
# en /admin/permisos-dropdowns.
PERMISOS_POR_AMBITO = {
    AMBITO_ALMACEN: ("LISTA_DE_MATERIALES", "Control de material", "Facturas / Invoice"),
    AMBITO_EMBARQUES: ("LISTA_DE_MATERIALES", "Control de material", "Invoice Embarques"),
}

# Los invoices de embarques son solo documentales: se suben, consultan,
# exportan y cierran, pero no aplican a inventario ni generan costos.
AMBITOS_SOLO_DOCUMENTAL = {AMBITO_EMBARQUES}


def normalizar_ambito(valor):
    """Ambito valido en mayusculas, o None si no lo es."""
    clave = str(valor or "").strip().upper()
    return clave if clave in AMBITOS else None
