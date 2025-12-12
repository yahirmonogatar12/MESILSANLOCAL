"""
Módulo de APIs - Inicialización
Blueprints modulares para las APIs del sistema
"""

# APIs v2 (nuevas)
from .plan_api import plan_api
from .material_api import material_api
from .bom_api import bom_api
from .inventario_api import inventario_bp
from .work_orders_api import work_orders_bp

# APIs legacy (movidas desde app/)
from .admin_api import admin_bp
from .aoi_api import aoi_api
from .po_wo_api import api_po_wo, registrar_rutas_po_wo
from .raw_modelos_api import api_raw
from .smd_inventory_api import smd_inventory_api, register_smd_inventory_routes

__all__ = [
    # APIs v2
    'plan_api',
    'material_api',
    'bom_api',
    'inventario_bp',
    'work_orders_bp',
    # APIs legacy
    'admin_bp',
    'aoi_api',
    'api_po_wo',
    'registrar_rutas_po_wo',
    'api_raw',
    'smd_inventory_api',
    'register_smd_inventory_routes',
]

