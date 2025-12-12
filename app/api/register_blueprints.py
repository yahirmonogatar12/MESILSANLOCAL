# -*- coding: utf-8 -*-
"""
Registro Centralizado de Blueprints
Punto único de registro para todas las APIs modulares v2
"""

from flask import Flask


def register_v2_blueprints(app: Flask) -> None:
    """
    Registra todos los blueprints de la API v2 en la aplicación Flask
    
    Args:
        app: Instancia de la aplicación Flask
    
    Blueprints registrados:
        - /api/v2/plan - Gestión del plan de producción
        - /api/v2/materials - Gestión de materiales
        - /api/v2/bom - Gestión de listas de materiales
        - /api/v2/inventario - Consulta y gestión de inventario
        - /api/v2/work-orders - Gestión de órdenes de trabajo
    """
    try:
        # Importar blueprints
        from app.api.plan_api import plan_api
        from app.api.material_api import material_api
        from app.api.bom_api import bom_api
        from app.api.inventario_api import inventario_bp
        from app.api.work_orders_api import work_orders_bp
        
        # Registrar blueprints
        blueprints = [
            (plan_api, 'Plan API'),
            (material_api, 'Material API'),
            (bom_api, 'BOM API'),
            (inventario_bp, 'Inventario API'),
            (work_orders_bp, 'Work Orders API')
        ]
        
        for bp, name in blueprints:
            try:
                app.register_blueprint(bp)
                print(f"  ✅ {name} registrado: {bp.url_prefix}")
            except Exception as e:
                print(f"  ❌ Error registrando {name}: {e}")
        
        print(f"\n📋 Total de APIs v2 registradas: {len(blueprints)}")
        print("   Endpoints base:")
        print("   - /api/v2/plan")
        print("   - /api/v2/materials")
        print("   - /api/v2/bom")
        print("   - /api/v2/inventario")
        print("   - /api/v2/work-orders")
        
    except ImportError as e:
        print(f"❌ Error de importación al registrar blueprints: {e}")
        raise
    except Exception as e:
        print(f"❌ Error general al registrar blueprints: {e}")
        raise


def get_all_v2_endpoints() -> list:
    """
    Retorna lista de todos los endpoints v2 disponibles
    
    Returns:
        Lista de diccionarios con información de cada endpoint
    """
    return [
        # Plan API
        {'method': 'GET', 'endpoint': '/api/v2/plan/health', 'description': 'Health check'},
        {'method': 'GET', 'endpoint': '/api/v2/plan', 'description': 'Listar plan de producción'},
        {'method': 'GET', 'endpoint': '/api/v2/plan/<id>', 'description': 'Detalle de registro'},
        {'method': 'POST', 'endpoint': '/api/v2/plan', 'description': 'Crear registro en plan'},
        {'method': 'PUT', 'endpoint': '/api/v2/plan/<id>', 'description': 'Actualizar registro'},
        {'method': 'DELETE', 'endpoint': '/api/v2/plan/<id>', 'description': 'Eliminar registro'},
        
        # Material API
        {'method': 'GET', 'endpoint': '/api/v2/materials/health', 'description': 'Health check'},
        {'method': 'GET', 'endpoint': '/api/v2/materials', 'description': 'Listar materiales'},
        {'method': 'GET', 'endpoint': '/api/v2/materials/<id>', 'description': 'Detalle de material'},
        {'method': 'POST', 'endpoint': '/api/v2/materials', 'description': 'Crear material'},
        
        # BOM API
        {'method': 'GET', 'endpoint': '/api/v2/bom/health', 'description': 'Health check'},
        {'method': 'GET', 'endpoint': '/api/v2/bom', 'description': 'Listar BOMs'},
        {'method': 'GET', 'endpoint': '/api/v2/bom/<modelo>', 'description': 'BOM por modelo'},
        
        # Inventario API
        {'method': 'GET', 'endpoint': '/api/v2/inventario/health', 'description': 'Health check'},
        {'method': 'POST', 'endpoint': '/api/v2/inventario/consultar', 'description': 'Consultar inventario'},
        {'method': 'GET', 'endpoint': '/api/v2/inventario/detalle/<np>', 'description': 'Detalle por número de parte'},
        {'method': 'GET', 'endpoint': '/api/v2/inventario/historial', 'description': 'Historial de movimientos'},
        {'method': 'POST', 'endpoint': '/api/v2/inventario/ajuste', 'description': 'Registrar ajuste'},
        {'method': 'GET', 'endpoint': '/api/v2/inventario/resumen', 'description': 'Resumen de inventario'},
        {'method': 'GET', 'endpoint': '/api/v2/inventario/buscar', 'description': 'Búsqueda rápida'},
        
        # Work Orders API
        {'method': 'GET', 'endpoint': '/api/v2/work-orders/health', 'description': 'Health check'},
        {'method': 'GET', 'endpoint': '/api/v2/work-orders', 'description': 'Listar work orders'},
        {'method': 'GET', 'endpoint': '/api/v2/work-orders/<wo>', 'description': 'Detalle de work order'},
        {'method': 'POST', 'endpoint': '/api/v2/work-orders', 'description': 'Crear work order'},
        {'method': 'PUT', 'endpoint': '/api/v2/work-orders/<wo>/estado', 'description': 'Actualizar estado'},
        {'method': 'POST', 'endpoint': '/api/v2/work-orders/<wo>/importar', 'description': 'Importar a plan'},
        {'method': 'GET', 'endpoint': '/api/v2/work-orders/estadisticas', 'description': 'Estadísticas'},
        {'method': 'GET', 'endpoint': '/api/v2/work-orders/buscar', 'description': 'Búsqueda rápida'},
        {'method': 'GET', 'endpoint': '/api/v2/work-orders/pendientes', 'description': 'Listar pendientes'},
        {'method': 'GET', 'endpoint': '/api/v2/work-orders/no-importados', 'description': 'Listar no importados'},
    ]
