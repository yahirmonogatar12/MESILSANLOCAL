from flask import Blueprint, jsonify, request
from app.db_mysql import execute_query


api_raw = Blueprint('api_raw', __name__, url_prefix='/api/raw')


@api_raw.route('/modelos', methods=['GET'])
def listar_modelos_raw():
    """Listar modelos desde la tabla RAW tomando la columna part_no.

    Respuesta JSON:
    { success: bool, data: [str], count: int }
    """
    try:
        query = (
            "SELECT DISTINCT part_no "
            "FROM raw "
            "WHERE part_no IS NOT NULL AND TRIM(part_no) <> '' "
            "ORDER BY part_no"
        )
        result = execute_query(query, fetch='all') or []
        modelos = [row.get('part_no') for row in result if row.get('part_no')]
        return jsonify({'success': True, 'data': modelos, 'count': len(modelos)})
    except Exception as e:
        print(f"Error listando modelos RAW (part_no): {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_raw.route('/ct_uph', methods=['GET'])
def obtener_ct_uph():
    """Obtener CT y UPH desde tabla raw_smd por part_no y lnea opcional.

    Params:
    - part_no: requerido
    - linea: opcional (ej. 'SMT A')

    Respuesta:
    { success: True, part_no, model, ct, uph }
    """
    try:
        part_no = (request.args.get('part_no') or '').strip()
        linea = (request.args.get('linea') or '').strip()
        if not part_no:
            return jsonify({'success': False, 'error': 'part_no requerido'}), 400

        base_sql = (
            "SELECT part_no, model, ct, uph "
            "FROM raw_smd WHERE TRIM(part_no)=TRIM(%s)"
        )
        params = [part_no]
        if linea:
            base_sql += " AND TRIM(linea)=TRIM(%s)"
            params.append(linea)
        base_sql += " ORDER BY updated_at DESC, id DESC LIMIT 1"

        row = execute_query(base_sql, tuple(params), fetch='one') or {}
        return jsonify({
            'success': True,
            'part_no': row.get('part_no') or part_no,
            'model': row.get('model') or None,
            'ct': row.get('ct') if row.get('ct') is not None else None,
            'uph': row.get('uph') if row.get('uph') is not None else None
        })
    except Exception as e:
        print(f"Error obteniendo CT/UPH raw_smd: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
