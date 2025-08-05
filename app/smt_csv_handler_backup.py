import os
import pandas as pd
import mysql.connector
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

# Configuración de conexión MySQL
DB_HOST = 'up-de-fra1-mysql-1.db.run-on-seenode.com'
DB_USER = 'db_rrpq0erbdujn'
DB_PASS = '5fUNbSRcPP3LN9K2I33Pr0ge' 
DB_NAME = 'db_rrpq0erbdujn'
DB_PORT = 11550
TABLE_NAME = 'historial_cambio_material_smt'

# Carpeta principal (ruta de red Windows)
WATCH_DIR = r'\\192.168.1.230\qa\ILSAN_MES\Mounter_LogFile'

def get_conn():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        port=DB_PORT
    )

def extrae_linea_maquina(file_path):
    rel_path = os.path.relpath(file_path, WATCH_DIR)
    partes = rel_path.split(os.sep)
    linea = partes[0] if len(partes) > 1 else None
    maquina = partes[1] if len(partes) > 2 else None
    archivo = partes[-1]
    return linea, maquina, archivo

def csv_to_mysql(file_path):
    try:
        df = pd.read_csv(file_path)
        linea, maquina, archivo = extrae_linea_maquina(file_path)
        conn = get_conn()
        cursor = conn.cursor()
        for _, row in df.iterrows():
            valores = [linea, maquina, archivo] + [row.get(col, None) if pd.notna(row.get(col, None)) else None for col in df.columns]
            cursor.execute(
                f"""INSERT INTO {TABLE_NAME} 
                (linea, maquina, archivo, ScanDate, ScanTime, SlotNo, Result, PreviousBarcode, Productdate, PartName, Quantity, SEQ, Vendor, LOTNO, Barcode, FeederBase)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                valores
            )
        conn.commit()
        cursor.close()
        conn.close()
        print(f"{archivo} ({linea} - {maquina}) cargado a MySQL.")
    except Exception as e:
        print(f"Error subiendo {file_path}: {e}")

class NewCSVHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.lower().endswith('.csv'):
            print(f"Detectado nuevo archivo: {event.src_path}")
            time.sleep(2)
            csv_to_mysql(event.src_path)

if __name__ == "__main__":
    event_handler = NewCSVHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=True)
    observer.start()
    print("Vigilando carpeta y subcarpetas de logs...")
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
