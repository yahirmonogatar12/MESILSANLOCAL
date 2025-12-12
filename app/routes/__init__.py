# -*- coding: utf-8 -*-
"""
Módulo de Rutas Modulares
Organización de rutas por área funcional del sistema MES

Estructura de archivos:
- auth_routes.py      : Autenticación y sesiones
- vistas_routes.py    : Templates y vistas HTML
- materiales_routes.py: Control de materiales e inventario
- bom_routes.py       : Bill of Materials
- produccion_routes.py: Plan de producción principal
- smt_routes.py       : Líneas SMT y CSV viewer
- calidad_routes.py   : Control de calidad y AOI
- metal_mask_routes.py: Máscaras metálicas y cajas
- mysql_routes.py     : Visor MySQL y operaciones DB
- plan_smd_routes.py  : Plan SMD y runs de producción
- ict_routes.py       : Historial ICT y defectos
"""

from .auth_routes import auth_bp
from .materiales_routes import materiales_bp
from .produccion_routes import produccion_bp
from .bom_routes import bom_bp
from .smt_routes import smt_bp
from .calidad_routes import calidad_bp
from .metal_mask_routes import metal_mask_bp
from .vistas_routes import vistas_bp
from .mysql_routes import mysql_bp
from .plan_smd_routes import plan_smd_bp
from .ict_routes import ict_bp

__all__ = [
    'auth_bp',
    'materiales_bp',
    'produccion_bp',
    'bom_bp',
    'smt_bp',
    'calidad_bp',
    'metal_mask_bp',
    'vistas_bp',
    'mysql_bp',
    'plan_smd_bp',
    'ict_bp'
]


def register_all_routes(app):
    """
    Registra todos los blueprints de rutas en la aplicación Flask
    
    Args:
        app: Instancia de la aplicación Flask
    """
    blueprints = [
        (auth_bp, 'Autenticación'),
        (materiales_bp, 'Materiales/Inventario'),
        (produccion_bp, 'Producción/Plan'),
        (bom_bp, 'BOM'),
        (smt_bp, 'SMT'),
        (calidad_bp, 'Calidad'),
        (metal_mask_bp, 'Metal Mask'),
        (vistas_bp, 'Vistas/Templates'),
        (mysql_bp, 'MySQL/Utilidades'),
        (plan_smd_bp, 'Plan SMD/Runs'),
        (ict_bp, 'ICT/Defectos')
    ]
    
    print("\n📦 Registrando rutas modulares...")
    for bp, nombre in blueprints:
        try:
            app.register_blueprint(bp)
            print(f"  ✅ {nombre}")
        except Exception as e:
            print(f"  ❌ Error registrando {nombre}: {e}")
    
    print(f"📋 Total de módulos de rutas: {len(blueprints)}\n")


# Inicialización de tablas necesarias
def init_database_tables():
    """Inicializa las tablas necesarias para los módulos de rutas"""
    try:
        from .metal_mask_routes import init_metal_mask_tables
        from .plan_smd_routes import crear_tabla_plan_smd_runs, crear_tabla_trazabilidad
        
        print("\n🗄️ Inicializando tablas de base de datos...")
        init_metal_mask_tables()
        crear_tabla_plan_smd_runs()
        crear_tabla_trazabilidad()
        print("✅ Tablas inicializadas correctamente\n")
    except Exception as e:
        print(f"⚠️ Error inicializando tablas: {e}")
