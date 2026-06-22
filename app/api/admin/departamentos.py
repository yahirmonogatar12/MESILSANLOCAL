"""Gestion de departamentos (catalogo).

Antes los departamentos eran listas hardcodeadas (DEFAULT_USER_DEPARTMENTS +
AVAILABLE_DEPARTMENTS). Ahora viven en la tabla `departamentos` y se gestionan
desde el Panel de Administracion. Solo superadmin.

Fuente unica: `obtener_departamentos_activos()` -> usada por los dropdowns de
usuarios y roles.

DDL idempotente al import (startup) para instalaciones nuevas; siembra con los
valores legacy si la tabla esta vacia.
"""

import logging

from flask import Blueprint, jsonify, request, session

from app.api.shared import auth_system
from app.db_mysql import get_db_connection
from app.api.admin.usuarios import get_dict_cursor, requiere_superadmin

logger = logging.getLogger(__name__)

bp = Blueprint("admin_departamentos", __name__, url_prefix="/admin")

# Semilla legacy (lo que antes estaba hardcodeado).
_SEED_DEPARTAMENTOS = [
    "Almacén", "Producción", "Calidad", "Administración",
    "Sistemas", "Gerencia", "Almacén de Embarques",
]


def _ensure_tabla():
    """Crea la tabla y la siembra si esta vacia. Idempotente."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS departamentos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(255) UNIQUE NOT NULL,
                activo TINYINT(1) DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('SELECT COUNT(*) FROM departamentos')
        fila = cursor.fetchone()
        total = (fila[0] if not isinstance(fila, dict) else list(fila.values())[0]) if fila else 0
        if not total:
            for nombre in _SEED_DEPARTAMENTOS:
                cursor.execute(
                    'INSERT IGNORE INTO departamentos (nombre) VALUES (%s)', (nombre,)
                )
        conn.commit()
    except Exception as e:
        logger.error("Error asegurando tabla departamentos: %s", e)
    finally:
        if conn:
            conn.close()


def obtener_departamentos_activos():
    """Lista de nombres de departamentos activos. Fuente unica para dropdowns."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT nombre FROM departamentos WHERE activo = 1 ORDER BY nombre'
        )
        return [
            (row[0] if not isinstance(row, dict) else row['nombre'])
            for row in cursor.fetchall()
        ]
    except Exception as e:
        logger.error("Error obteniendo departamentos: %s", e)
        return list(_SEED_DEPARTAMENTOS)
    finally:
        if conn:
            conn.close()


@bp.route('/listar_departamentos')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def listar_departamentos():
    """Lista todos los departamentos con conteo de usuarios."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)
        cursor.execute('''
            SELECT d.id, d.nombre, d.activo,
                   (SELECT COUNT(*) FROM usuarios_sistema u WHERE u.departamento = d.nombre) AS total_usuarios
            FROM departamentos d
            ORDER BY d.nombre
        ''')
        return jsonify(cursor.fetchall())
    except Exception as e:
        logger.error("Error listando departamentos: %s", e)
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@bp.route('/crear_departamento', methods=['POST'])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
@requiere_superadmin
def crear_departamento():
    """Crear un departamento nuevo."""
    conn = None
    try:
        nombre = ((request.json or {}).get('nombre') or '').strip()
        if not nombre:
            return jsonify({'error': 'El nombre es requerido'}), 400

        conn = get_db_connection()
        cursor = get_dict_cursor(conn)
        cursor.execute('SELECT id FROM departamentos WHERE nombre = %s', (nombre,))
        if cursor.fetchone():
            return jsonify({'error': 'Ya existe un departamento con ese nombre'}), 400

        cursor.execute('INSERT INTO departamentos (nombre) VALUES (%s)', (nombre,))
        conn.commit()
        auth_system.registrar_auditoria(
            usuario=session.get('usuario'), modulo='sistema',
            accion='crear_departamento', descripcion=f'Departamento "{nombre}" creado',
        )
        return jsonify({'success': True, 'mensaje': f'Departamento "{nombre}" creado'})
    except Exception as e:
        logger.error("Error creando departamento: %s", e)
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@bp.route('/actualizar_departamento/<int:dep_id>', methods=['PUT'])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
@requiere_superadmin
def actualizar_departamento(dep_id):
    """Renombrar o activar/desactivar un departamento.

    Al renombrar, propaga el cambio a usuarios_sistema y roles para no romper
    las referencias (departamento es texto, no FK)."""
    conn = None
    try:
        data = request.json or {}
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('SELECT * FROM departamentos WHERE id = %s', (dep_id,))
        dep = cursor.fetchone()
        if not dep:
            return jsonify({'error': 'Departamento no encontrado'}), 404

        nombre_actual = dep['nombre']
        nombre_nuevo = (data.get('nombre') or nombre_actual).strip()
        activo = 1 if data.get('activo', dep['activo']) else 0

        if not nombre_nuevo:
            return jsonify({'error': 'El nombre es requerido'}), 400

        if nombre_nuevo != nombre_actual:
            cursor.execute(
                'SELECT id FROM departamentos WHERE nombre = %s AND id != %s',
                (nombre_nuevo, dep_id),
            )
            if cursor.fetchone():
                return jsonify({'error': 'Ya existe otro departamento con ese nombre'}), 400

        cursor.execute(
            'UPDATE departamentos SET nombre = %s, activo = %s WHERE id = %s',
            (nombre_nuevo, activo, dep_id),
        )

        # Propagar rename a las referencias por texto.
        if nombre_nuevo != nombre_actual:
            cursor.execute(
                'UPDATE usuarios_sistema SET departamento = %s WHERE departamento = %s',
                (nombre_nuevo, nombre_actual),
            )
            cursor.execute(
                'UPDATE roles SET departamento = %s WHERE departamento = %s',
                (nombre_nuevo, nombre_actual),
            )

        conn.commit()
        auth_system.registrar_auditoria(
            usuario=session.get('usuario'), modulo='sistema',
            accion='actualizar_departamento',
            descripcion=f'Departamento "{nombre_actual}" -> "{nombre_nuevo}" (activo={activo})',
        )
        return jsonify({'success': True, 'mensaje': 'Departamento actualizado'})
    except Exception as e:
        logger.error("Error actualizando departamento: %s", e)
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@bp.route('/eliminar_departamento/<int:dep_id>', methods=['DELETE'])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
@requiere_superadmin
def eliminar_departamento(dep_id):
    """Eliminar un departamento. Bloquea si tiene usuarios asignados."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('SELECT nombre FROM departamentos WHERE id = %s', (dep_id,))
        dep = cursor.fetchone()
        if not dep:
            return jsonify({'error': 'Departamento no encontrado'}), 404

        cursor.execute(
            'SELECT COUNT(*) AS n FROM usuarios_sistema WHERE departamento = %s',
            (dep['nombre'],),
        )
        if cursor.fetchone()['n'] > 0:
            return jsonify({
                'error': 'No se puede eliminar: hay usuarios en este departamento. Desactívalo en su lugar.',
            }), 400

        cursor.execute('DELETE FROM departamentos WHERE id = %s', (dep_id,))
        conn.commit()
        auth_system.registrar_auditoria(
            usuario=session.get('usuario'), modulo='sistema',
            accion='eliminar_departamento', descripcion=f'Departamento "{dep["nombre"]}" eliminado',
        )
        return jsonify({'success': True, 'mensaje': 'Departamento eliminado'})
    except Exception as e:
        logger.error("Error eliminando departamento: %s", e)
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


# DDL idempotente al cargar el modulo (startup).
_ensure_tabla()
