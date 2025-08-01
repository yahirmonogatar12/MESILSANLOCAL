# admin_api.py - API para gestión de permisos de dropdowns
from flask import Blueprint, jsonify, request, render_template
from app.db import get_db_connection
import sqlite3

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/permisos-dropdowns')
def gestionar_permisos_dropdowns():
    """Página principal de gestión de permisos"""
    return render_template('admin/gestionar_permisos_dropdowns.html')

@admin_bp.route('/api/roles')
def get_roles():
    """Obtener todos los roles disponibles"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT nombre, descripcion 
            FROM roles 
            WHERE activo = 1
            ORDER BY nombre
        """)
        
        roles_raw = cursor.fetchall()
        
        roles = []
        for role_row in roles_raw:
            roles.append({
                'nombre': role_row[0],
                'descripcion': role_row[1] or f'Rol {role_row[0]}'
            })
        
        conn.close()
        return jsonify(roles)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/dropdowns')
def get_dropdowns():
    """Obtener todos los dropdowns disponibles con estructura jerárquica"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener todos los dropdowns con estructura completa
        cursor.execute("""
            SELECT DISTINCT pagina, seccion, boton, descripcion 
            FROM permisos_botones 
            WHERE pagina IS NOT NULL AND seccion IS NOT NULL AND boton IS NOT NULL
            ORDER BY pagina, seccion, boton
        """)
        
        dropdowns_raw = cursor.fetchall()
        
        dropdowns = []
        for dropdown_row in dropdowns_raw:
            pagina = dropdown_row[0]
            seccion = dropdown_row[1] 
            boton = dropdown_row[2]
            descripcion = dropdown_row[3] if dropdown_row[3] else f'{pagina} > {seccion} > {boton}'
            
            dropdowns.append({
                'pagina': pagina,
                'seccion': seccion,
                'boton': boton,
                'descripcion': descripcion,
                'key': f"{pagina}|{seccion}|{boton}",  # Clave única para identificar
                'display_name': f"{pagina} > {seccion} > {boton}"
            })
        
        conn.close()
        return jsonify(dropdowns)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/role-permissions/<role_name>')
def get_role_permissions(role_name):
    """Obtener permisos de un rol específico con estructura jerárquica"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pb.pagina, pb.seccion, pb.boton 
            FROM rol_permisos_botones rpb
            JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
            JOIN roles r ON rpb.rol_id = r.id
            WHERE r.nombre = %s
            ORDER BY pb.pagina, pb.seccion, pb.boton
        """, (role_name,))
        
        permisos = cursor.fetchall()
        
        permissions = []
        for permiso in permisos:
            pagina = permiso[0]
            seccion = permiso[1]
            boton = permiso[2]
            
            permissions.append({
                'pagina': pagina,
                'seccion': seccion,
                'boton': boton,
                'key': f"{pagina}|{seccion}|{boton}",
                'display_name': f"{pagina} > {seccion} > {boton}",
                'rol': role_name
            })
        
        conn.close()
        return jsonify(permissions)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/toggle-permission', methods=['POST'])
def toggle_permission():
    """Alternar permiso para un rol usando estructura jerárquica"""
    try:
        data = request.get_json()
        role = data.get('role')
        permission_key = data.get('permission_key')  # formato: "pagina|seccion|boton"
        action = data.get('action')  # 'add' o 'remove'
        
        if not all([role, permission_key, action]):
            return jsonify({'error': 'Faltan parámetros requeridos'}), 400
        
        # Dividir la clave de permiso
        try:
            pagina, seccion, boton = permission_key.split('|')
        except ValueError:
            return jsonify({'error': 'Formato de permiso inválido'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener IDs de rol y permiso
        cursor.execute("SELECT id FROM roles WHERE nombre = %s", (role,))
        rol_result = cursor.fetchone()
        if not rol_result:
            return jsonify({'error': f'Rol {role} no encontrado'}), 404
        rol_id = rol_result[0]
        
        cursor.execute("""
            SELECT id FROM permisos_botones 
            WHERE pagina = %s AND seccion = %s AND boton = %s
        """, (pagina, seccion, boton))
        permiso_result = cursor.fetchone()
        if not permiso_result:
            return jsonify({'error': f'Permiso {pagina}>{seccion}>{boton} no encontrado'}), 404
        permiso_id = permiso_result[0]
        
        message = ''
        
        if action == 'add':
            # Verificar si ya existe
            cursor.execute("""
                SELECT COUNT(*) FROM rol_permisos_botones 
                WHERE rol_id = %s AND permiso_boton_id = %s
            """, (rol_id, permiso_id))
            
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO rol_permisos_botones (rol_id, permiso_boton_id, fecha_asignacion) 
                    VALUES (%s, %s, NOW())
                """, (rol_id, permiso_id))
                message = f'Permiso {pagina}>{seccion}>{boton} asignado a {role}'
            else:
                message = f'El permiso ya existía para {role}'
                
        elif action == 'remove':
            cursor.execute("""
                DELETE FROM rol_permisos_botones 
                WHERE rol_id = %s AND permiso_boton_id = %s
            """, (rol_id, permiso_id))
            message = f'Permiso {pagina}>{seccion}>{boton} removido de {role}'
        else:
            message = f'Acción {action} no válida'
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/enable-all-permissions', methods=['POST'])
def enable_all_permissions():
    """Habilitar todos los permisos de dropdown para un rol"""
    try:
        data = request.get_json()
        role = data.get('role')
        
        if not role:
            return jsonify({'error': 'Falta el parámetro rol'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener ID del rol
        cursor.execute("SELECT id FROM roles WHERE nombre = %s", (role,))
        rol_result = cursor.fetchone()
        if not rol_result:
            return jsonify({'error': f'Rol {role} no encontrado'}), 404
        rol_id = rol_result[0]
        
        # Obtener todos los IDs de permisos disponibles
        cursor.execute("SELECT id FROM permisos_botones")
        all_permisos = cursor.fetchall()
        
        added_count = 0
        for permiso_row in all_permisos:
            permiso_id = permiso_row[0]
            
            # Insertar solo si no existe (ignorar duplicados)
            cursor.execute("""
                INSERT OR IGNORE INTO rol_permisos_botones (rol_id, permiso_boton_id, fecha_asignacion) 
                VALUES (%s, %s, NOW())
            """, (rol_id, permiso_id))
            
            if cursor.rowcount > 0:
                added_count += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'{added_count} permisos habilitados para {role}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/disable-all-permissions', methods=['POST'])
def disable_all_permissions():
    """Deshabilitar todos los permisos de dropdown para un rol"""
    try:
        data = request.get_json()
        role = data.get('role')
        
        if not role:
            return jsonify({'error': 'Falta el parámetro rol'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener ID del rol
        cursor.execute("SELECT id FROM roles WHERE nombre = %s", (role,))
        rol_result = cursor.fetchone()
        if not rol_result:
            return jsonify({'error': f'Rol {role} no encontrado'}), 404
        rol_id = rol_result[0]
        
        # Eliminar todos los permisos para este rol
        cursor.execute("""
            DELETE FROM rol_permisos_botones 
            WHERE rol_id = %s
        """, (rol_id,))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'{affected} permisos deshabilitados para {role}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
