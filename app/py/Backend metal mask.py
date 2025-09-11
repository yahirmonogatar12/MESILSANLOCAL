# app.py - Flask REST API for Mask Management
import os
from datetime import datetime, date
from decimal import Decimal
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DB", ""),
    "autocommit": True,
    "ssl_disabled": True if os.getenv("MYSQL_SSL_DISABLED", "true").lower() in ("1","true","yes") else False,
    "connection_timeout": 10,
}

app = Flask(__name__, static_folder=".")
CORS(app, resources={r"/api/*": {"origins": "*"}})

pool = pooling.MySQLConnectionPool(pool_name="mm_pool", pool_size=5, **DB_CONFIG)

def get_conn():
    return pool.get_connection()

def create_table_if_needed():
    # Masks table
    masks_ddl = """
    CREATE TABLE IF NOT EXISTS masks (
      id BIGINT PRIMARY KEY AUTO_INCREMENT,
      numero_gestion VARCHAR(64) UNIQUE,
      caja_almacenamiento   VARCHAR(64),
      codigo_pcb      VARCHAR(64),
      lado          VARCHAR(16),
      fecha_produccion DATE,
      conteo_usado    INT DEFAULT 0,
      conteo_maximo     INT DEFAULT 0,
      tolerancia     INT DEFAULT 0,
      nombre_modelo    VARCHAR(255),
      tension_min   DECIMAL(6,2),
      tension_max   DECIMAL(6,2),
      grosor     DECIMAL(6,2),
      proveedor      VARCHAR(128),
      fecha_registro VARCHAR(64),
      disuse        ENUM('Uso','Desuso','Scrap') DEFAULT 'Uso',
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    
    # Storage boxes table
    storage_ddl = """
    CREATE TABLE IF NOT EXISTS storage_boxes (
      id BIGINT PRIMARY KEY AUTO_INCREMENT,
      management_no VARCHAR(64) UNIQUE,
      code VARCHAR(64),
      name VARCHAR(64),
      location VARCHAR(64),
      storage_status ENUM('Disponible','Ocupado','Mantenimiento') DEFAULT 'Disponible',
      used_status ENUM('Usado','No Usado') DEFAULT 'Usado',
      note TEXT,
      registration_date VARCHAR(64),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    
    with get_conn() as cn:
        cur = cn.cursor()
        # Create masks table
        cur.execute(masks_ddl)
        # First, expand the enum to include new values without removing old ones
        cur.execute("ALTER TABLE masks MODIFY COLUMN disuse ENUM('Use','Disuse','Uso','Desuso','Scrap') DEFAULT 'Uso';")
        # Update existing data to match new enum values
        cur.execute("UPDATE masks SET disuse = 'Uso' WHERE disuse = 'Use';")
        cur.execute("UPDATE masks SET disuse = 'Desuso' WHERE disuse = 'Disuse';")
        # Now, set the final enum
        cur.execute("ALTER TABLE masks MODIFY COLUMN disuse ENUM('Uso','Desuso','Scrap') DEFAULT 'Uso';")
        
        # Create storage boxes table
        cur.execute(storage_ddl)
        cur.close()

@app.get("/")
def index():
    return send_from_directory(".", "index.html")

@app.get("/storage")
def storage():
    return send_from_directory(".", "storage.html")

@app.get("/storage.html")
def storage_html():
    return send_from_directory(".", "storage.html")

# Serve static files
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(".", filename)

@app.get("/api/masks")
def list_masks():
    disuse = request.args.get("disuse", "ALL")
    # Use the actual column names that exist in the database
    sql = "SELECT id,management_no,storage_box,pcb_code,side,COALESCE(DATE_FORMAT(production_date,'%Y-%m-%d'), '') as production_date,used_count,max_count,allowance,model_name,tension_min,tension_max,thickness,supplier,registration_date,disuse FROM masks"
    params = []
    if disuse and disuse != "ALL":
        sql += " WHERE disuse=%s"
        params.append(disuse)
    sql += " ORDER BY id DESC"
    with get_conn() as cn:
        cur = cn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]
        out = []
        for r in rows:
            obj = {k: v for k, v in zip(cols, r)}
            for k in ("used_count","max_count","allowance"):
                obj[k] = int(obj.get(k) or 0)
            for k in ("tension_min","tension_max","thickness"):
                v = obj.get(k)
                try:
                    obj[k] = float(v) if v is not None else None
                except Exception:
                    pass
            out.append(obj)
        cur.close()
    return jsonify(out)

@app.post("/api/masks")
def create_mask():
    data = request.get_json(force=True) or {}
    data.setdefault("used_count", 0)
    data.setdefault("max_count", 0)
    data.setdefault("allowance", 0)
    data.setdefault("disuse", "Uso")
    pd = data.get("production_date")
    if pd and isinstance(pd, str) and len(pd)>=10:
        data["production_date"] = pd[:10]
    else:
        data["production_date"] = None

    cols = ("management_no","storage_box","pcb_code","side","production_date",
            "used_count","max_count","allowance","model_name","tension_min",
            "tension_max","thickness","supplier","registration_date","disuse")
    placeholders = ",".join(["%s"]*len(cols))
    values = [data.get(c) for c in cols]

    sql = f"INSERT INTO masks ({','.join(cols)}) VALUES ({placeholders})"
    with get_conn() as cn:
        cur = cn.cursor()
        cur.execute(sql, values)
        cn.commit()
        cur.close()
    return jsonify(data), 201

@app.route('/api/storage', methods=['GET'])
def get_storage():
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 100))
    search = request.args.get('search', '').strip()
    filter_storage_status = request.args.get('filter_storage_status', '').strip()
    filter_used_status = request.args.get('filter_used_status', '').strip()
    
    where_clauses = []
    if search:
        where_clauses.append(f"(management_no LIKE '%{search}%' OR code LIKE '%{search}%' OR name LIKE '%{search}%' OR location LIKE '%{search}%' OR note LIKE '%{search}%')")
    if filter_storage_status:
        where_clauses.append(f"storage_status = '{filter_storage_status}'")
    if filter_used_status:
        where_clauses.append(f"used_status = '{filter_used_status}'")
    
    where_clause = ' AND '.join(where_clauses) if where_clauses else '1=1'
    
    with get_conn() as cn:
        cur = cn.cursor(dictionary=True)
        
        # Count total records
        count_query = f"SELECT COUNT(*) as total FROM storage_boxes WHERE {where_clause};"
        cur.execute(count_query)
        total = cur.fetchone()['total']
        
        # Get records
        query = f"""
        SELECT id, management_no, code, name, location, storage_status, used_status, note, registration_date
        FROM storage_boxes 
        WHERE {where_clause}
        ORDER BY id DESC 
        LIMIT {limit} OFFSET {offset};
        """
        cur.execute(query)
        data = cur.fetchall()
        cur.close()
    
    return jsonify({'data': data, 'total': total})

@app.route('/api/storage', methods=['POST'])
def add_storage():
    try:
        payload = request.get_json()
        print(f"DEBUG - Payload recibido: {payload}")
        
        management_no = payload.get('management_no', '').strip()
        code = payload.get('code', '').strip()
        name = payload.get('name', '').strip()
        location = payload.get('location', '').strip()
        storage_status = payload.get('storage_status', 'Disponible')
        used_status = payload.get('used_status', 'Usado')
        note = payload.get('note', '').strip()
        registration_date = payload.get('registration_date', '').strip()
        
        print(f"DEBUG - management_no: '{management_no}'")
        print(f"DEBUG - code: '{code}'")
        print(f"DEBUG - location: '{location}'")
        
        if not management_no:
            return jsonify({'error': 'Número de Gestión es requerido'}), 400
            
        with get_conn() as cn:
            cur = cn.cursor()
            query = """
            INSERT INTO storage_boxes (management_no, code, name, location, storage_status, used_status, note, registration_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(query, (management_no, code, name, location, storage_status, used_status, note, registration_date))
            cur.close()
        
        return jsonify({'success': True, 'message': 'Caja de almacenamiento registrada exitosamente'})
    
    except Exception as e:
        print(f"DEBUG - Error completo: {str(e)}")
        print(f"DEBUG - Tipo de error: {type(e)}")
        if 'Duplicate entry' in str(e):
            return jsonify({'error': f'El Número de Gestión "{management_no}" ya existe. Por favor use un código/ubicación diferente.'}), 400
        return jsonify({'error': f'Error al registrar la caja de almacenamiento: {str(e)}'}), 500

@app.route('/api/storage/<int:storage_id>', methods=['PUT'])
def update_storage(storage_id):
    try:
        payload = request.get_json()
        management_no = payload.get('management_no', '').strip()
        code = payload.get('code', '').strip()
        name = payload.get('name', '').strip()
        location = payload.get('location', '').strip()
        storage_status = payload.get('storage_status', 'Disponible')
        used_status = payload.get('used_status', 'Usado')
        note = payload.get('note', '').strip()
        registration_date = payload.get('registration_date', '').strip()
        
        if not management_no:
            return jsonify({'error': 'Número de Gestión es requerido'}), 400
            
        with get_conn() as cn:
            cur = cn.cursor()
            query = """
            UPDATE storage_boxes 
            SET management_no=%s, code=%s, name=%s, location=%s, storage_status=%s, used_status=%s, note=%s, registration_date=%s
            WHERE id=%s
            """
            cur.execute(query, (management_no, code, name, location, storage_status, used_status, note, registration_date, storage_id))
            
            if cur.rowcount == 0:
                return jsonify({'error': 'Caja de almacenamiento no encontrada'}), 404
            
            cur.close()
        
        return jsonify({'success': True, 'message': 'Caja de almacenamiento actualizada exitosamente'})
    
    except Exception as e:
        if 'Duplicate entry' in str(e):
            return jsonify({'error': 'El Número de Gestión ya existe'}), 400
        return jsonify({'error': f'Error al actualizar la caja de almacenamiento: {str(e)}'}), 500

@app.route('/api/masks/<int:mask_id>', methods=['PUT'])
def update_mask(mask_id):
    try:
        payload = request.get_json()
        
        # Use the actual column names that exist in the database
        management_no = payload.get('management_no', '').strip()
        storage_box = payload.get('storage_box', '').strip()
        pcb_code = payload.get('pcb_code', '').strip()
        side = payload.get('side', '').strip()
        production_date = payload.get('production_date', '').strip()
        used_count = payload.get('used_count', 0)
        max_count = payload.get('max_count', 0)
        allowance = payload.get('allowance', 0)
        model_name = payload.get('model_name', '').strip()
        tension_min = payload.get('tension_min', 0)
        tension_max = payload.get('tension_max', 0)
        thickness = payload.get('thickness', 0)
        supplier = payload.get('supplier', '').strip()
        registration_date = payload.get('registration_date', '').strip()
        disuse = payload.get('disuse', 'Uso')
        
        if not management_no:
            return jsonify({'error': 'Número de Gestión es requerido'}), 400
            
        with get_conn() as cn:
            cur = cn.cursor()
            query = """
            UPDATE masks 
            SET management_no=%s, storage_box=%s, pcb_code=%s, side=%s, 
                production_date=%s, used_count=%s, max_count=%s, allowance=%s,
                model_name=%s, tension_min=%s, tension_max=%s, thickness=%s,
                supplier=%s, registration_date=%s, disuse=%s
            WHERE id=%s
            """
            cur.execute(query, (management_no, storage_box, pcb_code, side, 
                              production_date, used_count, max_count, allowance,
                              model_name, tension_min, tension_max, thickness,
                              supplier, registration_date, disuse, mask_id))
            
            if cur.rowcount == 0:
                return jsonify({'error': 'Máscara no encontrada'}), 404
            
            cur.close()
        
        return jsonify({'success': True, 'message': 'Máscara actualizada exitosamente'})
    
    except Exception as e:
        if 'Duplicate entry' in str(e):
            return jsonify({'error': 'El Número de Gestión ya existe'}), 400
        return jsonify({'error': f'Error al actualizar la máscara: {str(e)}'}), 500

if __name__ == "__main__":
    create_table_if_needed()
    app.run(host="0.0.0.0", port=8000, debug=True)

