# -*- coding: utf-8 -*-
"""
Aplicación Flask MES - Inicialización Principal
Sistema de Gestión de Manufactura Electrónica
"""

import os

# Intentar importar MySQLdb, si no está disponible usar PyMySQL como alternativa
try:
    import MySQLdb
except ImportError:
    import pymysql
    pymysql.install_as_MySQLdb()
    import MySQLdb

from flask import Flask

# Importar módulos del sistema (desde nuevas ubicaciones)
from .database.db import init_db
from .core.auth_system import AuthSystem
from .core.user_admin import user_admin_bp

# Importar APIs desde app/api/
from .api.admin_api import admin_bp
from .api.smd_inventory_api import register_smd_inventory_routes
from .api.raw_modelos_api import api_raw
from .api.aoi_api import aoi_api
from .api.po_wo_api import registrar_rutas_po_wo

# Importar rutas SMT desde app/routes/
from .routes.smt_routes_clean import register_smt_routes
from .routes.smt_routes_date_fixed import smt_bp as smt_date_bp

# Importar herramientas especiales
from .py.control_modelos_smt import control_modelos_bp

# Importar APIs modulares v2
from .api.plan_api import plan_api
from .api.material_api import material_api
from .api.bom_api import bom_api
from .api.inventario_api import inventario_bp
from .api.work_orders_api import work_orders_bp

# Importar registro de rutas modulares
from .routes import register_all_routes, init_database_tables


def create_app():
    """
    Factory function para crear la aplicación Flask
    
    Returns:
        Flask: Instancia configurada de la aplicación
    """
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY', 'fallback_key_for_development_only')
    
    print("\n" + "="*60)
    print("🏭 SISTEMA MES - Iniciando aplicación...")
    print("="*60)
    
    # =========================================================================
    # INICIALIZACIÓN DE BASE DE DATOS
    # =========================================================================
    print("\n📊 Inicializando bases de datos...")
    init_db()  # Base de datos original SQLite/legacy
    
    # Inicializar sistema de autenticación
    auth_system = AuthSystem()
    auth_system.init_database()
    print("✅ Sistema de autenticación inicializado")
    
    # =========================================================================
    # REGISTRO DE BLUEPRINTS CORE
    # =========================================================================
    print("\n📦 Registrando blueprints core...")
    
    # Blueprints de administración
    app.register_blueprint(user_admin_bp, url_prefix='/admin')
    app.register_blueprint(admin_bp)
    print("  ✅ Admin blueprints")
    
    # API RAW (modelos desde tabla raw)
    try:
        if 'api_raw' not in app.blueprints:
            app.register_blueprint(api_raw)
            print("  ✅ API RAW (part_no)")
    except Exception as e:
        print(f"  ⚠️ Error registrando API RAW: {e}")
    
    # Rutas SMD Inventory
    register_smd_inventory_routes(app)
    print("  ✅ SMD Inventory routes")
    
    # SMT Routes Simple
    try:
        app.register_blueprint(smt_date_bp)
        print("  ✅ SMT Routes Simple")
    except Exception as e:
        print(f"  ⚠️ Error importando SMT Routes Simple: {e}")
    
    # =========================================================================
    # REGISTRO DE RUTAS MODULARES (app/routes/)
    # =========================================================================
    register_all_routes(app)
    
    # Inicializar tablas de base de datos para módulos
    try:
        init_database_tables()
    except Exception as e:
        print(f"⚠️ Error inicializando tablas de módulos: {e}")
    
    print("\n" + "="*60)
    print("✅ Aplicación MES iniciada correctamente")
    print("="*60 + "\n")
    
    # =========================================================================
    # REGISTRO DE APIs ADICIONALES (legacy en app/)
    # =========================================================================
    print("\n🔧 Registrando APIs adicionales...")
    
    # SMT Routes Clean
    register_smt_routes(app)
    
    # PO/WO API
    registrar_rutas_po_wo(app)
    print("  ✅ Rutas PO/WO registradas")
    
    # AOI API
    if 'aoi_api' not in app.blueprints:
        app.register_blueprint(aoi_api)
        print("  ✅ AOI API")
    
    # Control Modelos SMT
    if 'control_modelos_bp' not in app.blueprints:
        app.register_blueprint(control_modelos_bp)
        print("  ✅ Control Modelos SMT")
    
    # =========================================================================
    # REGISTRO DE APIs v2 MODULARES (app/api/)
    # =========================================================================
    print("\n🚀 Registrando APIs v2 modulares...")
    
    if 'plan_api' not in app.blueprints:
        app.register_blueprint(plan_api)
    if 'material_api' not in app.blueprints:
        app.register_blueprint(material_api)
    if 'bom_api' not in app.blueprints:
        app.register_blueprint(bom_api)
    if 'inventario_bp' not in app.blueprints:
        app.register_blueprint(inventario_bp)
    if 'work_orders_bp' not in app.blueprints:
        app.register_blueprint(work_orders_bp)
    
    print("✅ APIs v2 registradas:")
    print("   - /api/v2/plan")
    print("   - /api/v2/materials")
    print("   - /api/v2/bom")
    print("   - /api/v2/inventario")
    print("   - /api/v2/work-orders")
    
    return app


# Crear instancia global de la app para compatibilidad con imports existentes
app = create_app()