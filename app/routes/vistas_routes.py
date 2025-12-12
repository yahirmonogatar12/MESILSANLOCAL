# -*- coding: utf-8 -*-
"""
Rutas de Vistas y Templates
Páginas HTML, landing pages y templates del sistema
"""

import os
from flask import Blueprint, render_template, redirect, url_for, session, send_from_directory
from .utils import login_requerido
from ..database.db_mysql import execute_query
from ..core.auth_system import AuthSystem

vistas_bp = Blueprint('vistas', __name__)
auth_system = AuthSystem()


def render_landing_page(login_error=None, login_username=None):
    """Renderiza la landing page con o sin sesión activa."""
    from ..database.db_mysql import get_mysql_connection
    
    authenticated = 'usuario' in session
    nombre_completo = None
    permisos = {}
    roles = []

    if authenticated:
        usuario = session.get('usuario')
        nombre_completo = session.get('nombre_completo', usuario)
        permisos = session.get('permisos', {})

        try:
            conn = get_mysql_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT r.nombre
                FROM usuarios_sistema u
                JOIN usuario_roles ur ON u.id = ur.usuario_id
                JOIN roles r ON ur.rol_id = r.id
                WHERE u.username = %s AND u.activo = 1 AND r.activo = 1
            ''', (usuario,))
            roles = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"⚠️ Error obteniendo roles: {e}")

    upcoming_apps = [
        {
            'name': 'Más Herramientas',
            'description': 'Expansión futura',
            'long_description': 'Nuevas aplicaciones serán agregadas pronto.',
            'icon': 'rocket'
        }
    ]

    return render_template(
        'landing.html',
        nombre_usuario=nombre_completo,
        permisos=permisos,
        roles=roles,
        upcoming_apps=upcoming_apps,
        usuario_autenticado=authenticated,
        login_error=login_error,
        login_username=login_username
    )


@vistas_bp.route('/')
def index():
    """Página raíz - redirige al inicio"""
    return redirect(url_for('vistas.inicio'))


@vistas_bp.route('/inicio')
def inicio():
    """Landing page / Hub de aplicaciones"""
    return render_landing_page()


@vistas_bp.route('/calendario')
@login_requerido
def calendario():
    """Página del calendario de producción"""
    return render_template('calendario.html')


@vistas_bp.route('/defect-management')
@login_requerido
def defect_management():
    """Módulo de Gestión de Defectos"""
    return render_template('info.html', 
                         titulo="Gestión de Defectos",
                         mensaje="Módulo en desarrollo.",
                         tipo="warning")


@vistas_bp.route('/favicon.ico')
def favicon():
    """Servir favicon"""
    from flask import current_app
    return send_from_directory(
        os.path.join(current_app.root_path, 'static', 'icons'),
        'produccion.png',
        mimetype='image/png'
    )


@vistas_bp.route('/sistemas')
@login_requerido
def sistemas():
    """Redirige al hub de inicio"""
    return redirect(url_for('vistas.inicio'))


@vistas_bp.route('/soporte')
@login_requerido
def soporte():
    """Página de soporte técnico"""
    return render_template('soporte.html') if os.path.exists('app/templates/soporte.html') else \
           f"<h1>Soporte Técnico</h1><p>En construcción. <a href='/inicio'>Volver</a></p>"


@vistas_bp.route('/documentacion')
@login_requerido
def documentacion():
    """Página de documentación"""
    return render_template('documentacion.html') if os.path.exists('app/templates/documentacion.html') else \
           f"<h1>Documentación</h1><p>En construcción. <a href='/inicio'>Volver</a></p>"


@vistas_bp.route('/ILSAN-ELECTRONICS')
@login_requerido
def material():
    """Página principal de materiales"""
    usuario = session.get('usuario', 'Invitado')
    nombre_completo = session.get('nombre_completo', None)
    
    if not nombre_completo and usuario != 'Invitado':
        info_usuario = auth_system.obtener_informacion_usuario(usuario)
        if info_usuario and info_usuario['nombre_completo']:
            nombre_completo = info_usuario['nombre_completo']
            session['nombre_completo'] = nombre_completo
        else:
            nombre_completo = usuario
            session['nombre_completo'] = usuario
    
    if not nombre_completo:
        nombre_completo = usuario
        
    permisos = session.get('permisos', {})
    tiene_permisos_usuarios = False
    if isinstance(permisos, dict) and 'sistema' in permisos:
        tiene_permisos_usuarios = 'usuarios' in permisos['sistema']
    
    return render_template('MaterialTemplate.html', 
                        usuario=nombre_completo,
                        tiene_permisos_usuarios=tiene_permisos_usuarios)


@vistas_bp.route('/dashboard')
@login_requerido
def dashboard():
    """Alias para la página principal"""
    usuario = session.get('usuario')
    nombre_completo = session.get('nombre_completo')
    
    if not nombre_completo and usuario:
        try:
            result = execute_query("SELECT nombre_completo FROM users WHERE usuario = %s", (usuario,), fetch='one')
            if result and result.get('nombre_completo'):
                nombre_completo = result['nombre_completo']
                session['nombre_completo'] = nombre_completo
        except Exception:
            nombre_completo = usuario
    
    if not nombre_completo:
        nombre_completo = usuario
        
    permisos = session.get('permisos', {})
    tiene_permisos_usuarios = False
    if isinstance(permisos, dict) and 'sistema' in permisos:
        tiene_permisos_usuarios = 'usuarios' in permisos['sistema']
    
    return render_template('MaterialTemplate.html', 
                        usuario=nombre_completo,
                        tiene_permisos_usuarios=tiene_permisos_usuarios)


@vistas_bp.route('/Prueba')
@login_requerido
def produccion():
    """Página de producción (prueba)"""
    usuario = session.get('usuario', 'Invitado')
    return render_template('Control de material/Control de salida.html', usuario=usuario)


@vistas_bp.route('/DESARROLLO')
@login_requerido
def desarrollo():
    """Página de desarrollo"""
    usuario = session.get('usuario', 'Invitado')
    return render_template('Control de material/Control de salida.html', usuario=usuario)


# ============== LISTAS Y MENÚS ==============

@vistas_bp.route('/listas/informacion_basica')
@login_requerido
def lista_informacion_basica():
    """Cargar dinámicamente la lista de Información Básica"""
    try:
        return render_template('LISTAS/LISTA_INFORMACIONBASICA.html')
    except Exception as e:
        print(f"Error al cargar LISTA_INFORMACIONBASICA: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/listas/control_material')
@login_requerido
def lista_control_material():
    """Cargar dinámicamente la lista de Control de Material"""
    try:
        return render_template('LISTAS/LISTA_DE_MATERIALES.html')
    except Exception as e:
        print(f"Error al cargar LISTA_DE_MATERIALES: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/listas/control_produccion')
@login_requerido
def lista_control_produccion():
    """Cargar dinámicamente la lista de Control de Producción"""
    try:
        return render_template('LISTAS/LISTA_CONTROLDEPRODUCCION.html')
    except Exception as e:
        print(f"Error al cargar LISTA_CONTROLDEPRODUCCION: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/listas/control_proceso')
@login_requerido
def lista_control_proceso():
    """Cargar dinámicamente la lista de Control de Proceso"""
    try:
        return render_template('LISTAS/LISTA_CONTROL_DE_PROCESO.html')
    except Exception as e:
        print(f"Error al cargar LISTA_CONTROL_DE_PROCESO: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/listas/control_calidad')
@login_requerido
def lista_control_calidad():
    """Cargar dinámicamente la lista de Control de Calidad"""
    try:
        return render_template('LISTAS/LISTA_CONTROL_DE_CALIDAD.html')
    except Exception as e:
        print(f"Error al cargar LISTA_CONTROL_DE_CALIDAD: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/listas/control_resultados')
@login_requerido
def lista_control_resultados():
    """Cargar dinámicamente la lista de Control de Resultados"""
    try:
        return render_template('LISTAS/LISTA_DE_CONTROL_DE_RESULTADOS.html')
    except Exception as e:
        print(f"Error al cargar LISTA_DE_CONTROL_DE_RESULTADOS: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/listas/control_reporte')
@login_requerido
def lista_control_reporte():
    """Cargar dinámicamente la lista de Control de Reporte"""
    try:
        return render_template('LISTAS/LISTA_DE_CONTROL_DE_REPORTE.html')
    except Exception as e:
        print(f"Error al cargar LISTA_DE_CONTROL_DE_REPORTE: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/listas/configuracion_programa')
@login_requerido
def lista_configuracion_programa():
    """Cargar dinámicamente la lista de Configuración de Programa"""
    try:
        return render_template('LISTAS/LISTA_DE_CONFIGPG.html')
    except Exception as e:
        print(f"Error al cargar LISTA_DE_CONFIGPG: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/templates/LISTAS/<filename>')
@login_requerido
def serve_list_template(filename):
    """Servir templates de listas"""
    from flask import current_app
    templates_dir = os.path.join(current_app.root_path, 'templates', 'LISTAS')
    
    if not filename.endswith('.html'):
        filename += '.html'
    
    filepath = os.path.join(templates_dir, filename)
    
    if os.path.exists(filepath):
        return render_template(f'LISTAS/{filename}')
    
    return f"<p>Template no encontrado: {filename}</p>", 404


# ============== PÁGINAS DE INFORMACIÓN ==============

@vistas_bp.route('/informacion_basica/control_de_material')
@login_requerido
def control_de_material_ajax():
    """Cargar dinámicamente Control de Material"""
    try:
        return render_template('INFORMACION BASICA/CONTROL_DE_MATERIAL.html')
    except Exception as e:
        print(f"Error al cargar CONTROL_DE_MATERIAL: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/informacion_basica/control_de_bom')
@login_requerido
def control_de_bom_ajax():
    """Cargar dinámicamente Control de BOM"""
    try:
        return render_template('INFORMACION BASICA/CONTROL_DE_BOM.html')
    except Exception as e:
        print(f"Error al cargar CONTROL_DE_BOM: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# ============== PÁGINAS DE MATERIAL ==============

@vistas_bp.route('/material/info')
@login_requerido
def material_info():
    """Cargar dinámicamente la información general de material"""
    try:
        return render_template('info.html')
    except Exception as e:
        print(f"Error al cargar info.html: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/material/control_almacen')
@login_requerido
def material_control_almacen():
    """Cargar dinámicamente el control de almacén"""
    try:
        return render_template('Control de material/Control de material de almacen.html')
    except Exception as e:
        print(f"Error al cargar Control de material de almacen: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/material/control_salida')
@login_requerido
def material_control_salida():
    """Cargar dinámicamente el control de salida"""
    try:
        return render_template('Control de material/Control de salida.html')
    except Exception as e:
        print(f"Error al cargar Control de salida: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/material/control_calidad')
@login_requerido
def material_control_calidad():
    """Cargar dinámicamente el control de calidad"""
    try:
        return render_template('Control de material/Control de calidad.html')
    except Exception as e:
        print(f"Error al cargar Control de calidad: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/material/historial_inventario')
@login_requerido
def material_historial_inventario():
    """Cargar dinámicamente el historial de inventario real"""
    try:
        return render_template('Control de material/Historial de inventario real.html')
    except Exception as e:
        print(f"Error al cargar Historial de inventario real: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/material/registro_material')
@login_requerido
def material_registro_material():
    """Cargar dinámicamente el registro de material real"""
    try:
        return render_template('Control de material/Registro de material real.html')
    except Exception as e:
        print(f"Error al cargar Registro de material real: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/material/control_retorno')
@login_requerido
def material_control_retorno():
    """Cargar dinámicamente el control de material de retorno"""
    try:
        return render_template('Control de material/Control de material de retorno.html')
    except Exception as e:
        print(f"Error al cargar Control de material de retorno: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/material/estatus_material')
@login_requerido
def material_estatus_material():
    """Cargar dinámicamente el estatus de material"""
    try:
        return render_template('Control de material/Estatus de material.html')
    except Exception as e:
        print(f"Error al cargar Estatus de material: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/material/recibo_pago')
@login_requerido
def material_recibo_pago():
    """Cargar dinámicamente el recibo y pago del material"""
    try:
        return render_template('Control de material/Recibo y pago del material.html')
    except Exception as e:
        print(f"Error al cargar Recibo y pago del material: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/material/historial_material')
@login_requerido
def material_historial_material():
    """Cargar dinámicamente el historial de material"""
    try:
        return render_template('Control de material/Historial de material.html')
    except Exception as e:
        print(f"Error al cargar Historial de material: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/material/material_sustituto')
@login_requerido
def material_material_sustituto():
    """Cargar dinámicamente el material sustituto"""
    try:
        return render_template('Control de material/Material sustituto.html')
    except Exception as e:
        print(f"Error al cargar Material sustituto: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/material/consultar_peps')
@login_requerido
def material_consultar_peps():
    """Cargar dinámicamente consultar PEPS"""
    try:
        return render_template('Control de material/Consultar PEPS.html')
    except Exception as e:
        print(f"Error al cargar Consultar PEPS: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/material/longterm_inventory')
@login_requerido
def material_longterm_inventory():
    """Cargar dinámicamente el control de Long-Term Inventory"""
    try:
        return render_template('Control de material/Control de Long-Term Inventory.html')
    except Exception as e:
        print(f"Error al cargar Control de Long-Term Inventory: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@vistas_bp.route('/material/ajuste_numero')
@login_requerido
def material_ajuste_numero():
    """Cargar dinámicamente el ajuste de número de parte"""
    try:
        return render_template('Control de material/Ajuste de número de parte.html')
    except Exception as e:
        print(f"Error al cargar Ajuste de número de parte: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# ============== PÁGINAS DE PRODUCCIÓN ==============

@vistas_bp.route('/produccion/info')
@login_requerido
def produccion_info():
    return render_template('Control de produccion/info_produccion.html')


@vistas_bp.route('/control_produccion/control_embarque')
@login_requerido
def control_embarque():
    return render_template('Control de produccion/Control de embarque.html')


@vistas_bp.route('/Control de embarque')
@login_requerido
def control_embarque_ajax():
    return render_template('Control de produccion/Control de embarque.html')


@vistas_bp.route('/control_produccion/crear_plan')
@login_requerido
def crear_plan_produccion():
    return render_template('Control de produccion/Crear plan de produccion.html')


@vistas_bp.route('/control_produccion/plan_smt')
@login_requerido
def plan_smt_ajax():
    return render_template('Control de produccion/Plan SMT.html')


# ============== PÁGINAS DE PROCESO ==============

@vistas_bp.route('/control_proceso/control_produccion_smt')
@login_requerido
def control_produccion_smt_ajax():
    return render_template('Control de proceso/Control de produccion SMT.html')


@vistas_bp.route('/control_proceso/inventario_imd_terminado')
@login_requerido
def inventario_imd_terminado_ajax():
    return render_template('Control de proceso/Inventario IMD terminado.html')


# ============== FRONT PLAN ==============

@vistas_bp.route('/front-plan/static/<path:filename>')
def front_plan_static(filename):
    """Servir assets de FRONT PLAN"""
    from flask import current_app
    try:
        base_dir = os.path.join(current_app.root_path, 'FRONT PLAN', 'static')
        return send_from_directory(base_dir, filename)
    except Exception as e:
        return {'error': f'Recurso no encontrado: {str(e)}'}, 404


@vistas_bp.route('/plan-main')
@login_requerido
def view_plan_main():
    """Página de planeación"""
    return render_template('Control de proceso/Control_produccion_assy.html')


@vistas_bp.route('/control-main')
@login_requerido
def view_control_main():
    """Panel de control de operación"""
    return render_template('Control de proceso/Control de operacion de linea Main.html')


# ============== VISTAS AJAX ==============

@vistas_bp.route('/plan-main-assy-ajax')
@login_requerido
def plan_main_assy_ajax():
    return render_template('Control de proceso/Control_produccion_assy.html')


@vistas_bp.route('/control-operacion-linea-main-ajax')
@login_requerido
def ctrl_operacion_linea_main_ajax():
    return render_template('Control de proceso/Control de operacion de linea Main.html')


@vistas_bp.route('/visor-mysql')
@login_requerido
def visor_mysql():
    """Visor MySQL general"""
    return render_template('visor_mysql.html')


@vistas_bp.route("/plan-smd-diario")
@login_requerido
def plan_smd_diario():
    return render_template('Control de proceso/plan_smd_diario.html')


@vistas_bp.route("/control-operacion-linea-smt")
@login_requerido
def control_operacion_linea_smt():
    return render_template('Control de proceso/Control de operacion de linea SMT.html')
