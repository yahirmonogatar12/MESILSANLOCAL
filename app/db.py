import sqlite3
import os

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'database', 'ISEMM_MES.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entrada_aereo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            forma_material TEXT,
            cliente TEXT,
            codigo_material TEXT,
            fecha_fabricacion TEXT,
            origen_material TEXT,
            cantidad_actual INTEGER,
            fecha_recibo TEXT,
            lote_material TEXT,
            codigo_recibido TEXT,
            numero_parte TEXT,
            propiedad TEXT
        )
    ''')
    conn.commit()
    conn.close()