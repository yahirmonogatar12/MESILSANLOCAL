"""
SMT CSV Handler - Maneja la integración con MySQL para archivos CSV de SMT
"""

import os
import mysql.connector
from mysql.connector import Error
import csv
import logging
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

class SMTCSVHandler:
    """Maneja operaciones CSV y MySQL para SMT"""
    
    def __init__(self, db_config):
        self.db_config = db_config
    
    def get_connection(self):
        """Obtiene conexión a MySQL"""
        try:
            return mysql.connector.connect(**self.db_config)
        except Error as e:
            logger.error(f"Error conectando a MySQL: {e}")
            raise
    
    def get_historial_data(self, filters=None):
        """Obtiene datos del historial con filtros opcionales"""
        connection = None
        cursor = None
        
        try:
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Query base con conversión de tipos para JSON
            query = """
                SELECT
                    scan_date,
                    scan_time,
                    slot_no,
                    result,
                    part_name,
                    quantity,
                    vendor,
                    lot_no,
                    l_position,
                    m_position,
                    seq,
                    barcode,
                    feeder_base,
                    previous_barcode,
                    product_date,
                    source_file,
                    line_number,
                    mounter_number
                FROM historial_cambio_material_smt
                WHERE 1=1
            """
            params = []
            
            # Aplicar filtros
            if filters:
                if filters.get('folder'):
                    # Parsear folder para obtener línea y mounter
                    line_num, mounter_num = self.parse_folder_name(filters['folder'])
                    query += " AND line_number = %s AND mounter_number = %s"
                    params.extend([line_num, mounter_num])
                
                if filters.get('part_name'):
                    query += " AND part_name LIKE %s"
                    params.append(f"%{filters['part_name']}%")
                
                if filters.get('result'):
                    query += " AND result = %s"
                    params.append(filters['result'])
                
                if filters.get('date_from'):
                    query += " AND scan_date >= %s"
                    params.append(filters['date_from'])
                
                if filters.get('date_to'):
                    query += " AND scan_date <= %s"
                    params.append(filters['date_to'])
            
            query += " ORDER BY scan_date ASC, scan_time ASC LIMIT 5000"
            
            cursor.execute(query, params)
            data = cursor.fetchall()
            
            # Convertir objetos datetime a strings para JSON
            for row in data:
                if row.get('scan_date'):
                    row['scan_date'] = row['scan_date'].strftime('%Y-%m-%d')
                if row.get('product_date'):
                    row['product_date'] = row['product_date'].strftime('%Y-%m-%d')
                if row.get('scan_time'):
                    # scan_time es un timedelta, convertirlo a string HH:MM:SS
                    total_seconds = int(row['scan_time'].total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    row['scan_time'] = f'{hours:02d}:{minutes:02d}:{seconds:02d}'
            
            # Obtener estadísticas
            stats = self.get_statistics(filters)
            
            return {
                'success': True,
                'data': data,
                'stats': stats
            }
            
        except Error as e:
            logger.error(f"Error obteniendo datos: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def get_statistics(self, filters=None):
        """Obtiene estadísticas de los datos"""
        connection = None
        cursor = None
        
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            # Query para estadísticas
            query = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN result = 'OK' THEN 1 ELSE 0 END) as ok,
                    SUM(CASE WHEN result = 'NG' THEN 1 ELSE 0 END) as ng
                FROM historial_cambio_material_smt
                WHERE 1=1
            """
            
            params = []
            
            # Aplicar los mismos filtros
            if filters:
                if filters.get('folder'):
                    line_num, mounter_num = self.parse_folder_name(filters['folder'])
                    query += " AND line_number = %s AND mounter_number = %s"
                    params.extend([line_num, mounter_num])
                
                if filters.get('part_name'):
                    query += " AND part_name LIKE %s"
                    params.append(f"%{filters['part_name']}%")
                
                if filters.get('result'):
                    query += " AND result = %s"
                    params.append(filters['result'])
                
                if filters.get('date_from'):
                    query += " AND scan_date >= %s"
                    params.append(filters['date_from'])
                
                if filters.get('date_to'):
                    query += " AND scan_date <= %s"
                    params.append(filters['date_to'])
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            return {
                'total': result[0] or 0,
                'ok': result[1] or 0,
                'ng': result[2] or 0
            }
            
        except Error as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {'total': 0, 'ok': 0, 'ng': 0}
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def get_available_folders(self):
        """Obtiene lista de carpetas/líneas disponibles"""
        connection = None
        cursor = None
        
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            query = """
                SELECT DISTINCT 
                    line_number, 
                    mounter_number,
                    COUNT(*) as record_count
                FROM historial_cambio_material_smt 
                GROUP BY line_number, mounter_number
                ORDER BY line_number, mounter_number
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            folders = []
            for row in results:
                folder_name = f"{row[0]}Line_M{row[1]}"
                folders.append({
                    'name': folder_name,
                    'display': f"Línea {row[0]} - Mounter {row[1]} ({row[2]} registros)",
                    'line': row[0],
                    'mounter': row[1],
                    'count': row[2]
                })
            
            return {
                'success': True,
                'folders': folders
            }
            
        except Error as e:
            logger.error(f"Error obteniendo carpetas: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def upload_csv_file(self, file_content, filename, line_number=None, mounter_number=None):
        """Procesa y sube archivo CSV"""
        connection = None
        cursor = None
        
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            # Verificar si ya fue procesado
            file_hash = hashlib.md5(file_content.encode()).hexdigest()
            
            # Obtener línea y mounter del nombre si no se especificaron
            if not line_number or not mounter_number:
                line_number, mounter_number = self.parse_filename(filename)
            
            records_inserted = 0
            
            # Procesar CSV
            csv_reader = csv.reader(file_content.split('\n'))
            
            # Saltar encabezados si existen
            first_row = next(csv_reader, None)
            if first_row and any(header.lower() in ['date', 'time', 'scan', 'result'] 
                               for header in first_row):
                pass  # Es encabezado
            else:
                # No es encabezado, volver a procesarlo
                csv_reader = csv.reader(file_content.split('\n'))
            
            insert_query = """
                INSERT INTO historial_cambio_material_smt
                (scan_date, scan_time, slot_no, result, part_name, quantity,
                 vendor, lot_no, l_position, m_position, seq, barcode, feeder_base, 
                 previous_barcode, product_date, source_file, line_number, mounter_number, file_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            batch_data = []
            for row in csv_reader:
                if len(row) < 4:  # Filtrar filas vacías
                    continue
                
                parsed_data = self.parse_csv_row(row, filename, file_hash, 
                                               line_number, mounter_number)
                if parsed_data:
                    batch_data.append(parsed_data)
                    
                    if len(batch_data) >= 100:  # Insertar en lotes
                        cursor.executemany(insert_query, batch_data)
                        records_inserted += len(batch_data)
                        batch_data = []
            
            # Insertar registros restantes
            if batch_data:
                cursor.executemany(insert_query, batch_data)
                records_inserted += len(batch_data)
            
            connection.commit()
            
            return {
                'success': True,
                'message': f'Archivo procesado exitosamente. {records_inserted} registros insertados.',
                'records_inserted': records_inserted
            }
            
        except Exception as e:
            logger.error(f"Error subiendo archivo: {e}")
            if connection:
                connection.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def parse_folder_name(self, folder_name):
        """Parsea nombre de carpeta para extraer línea y mounter"""
        # Formato esperado: "1Line_M1", "2Line_M2", etc.
        import re
        
        match = re.search(r'(\d+)line[/\\]?.*?L(\d+)\s*m(\d+)', folder_name, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(3))
        
        # Fallback
        return 1, 1
    
    def parse_filename(self, filename):
        """Extrae línea y mounter del nombre de archivo"""
        import re
        
        # Buscar patrones comunes
        line_match = re.search(r'(\d+)line|line(\d+)|l(\d+)', filename.lower())
        mounter_match = re.search(r'm(\d+)|mounter(\d+)', filename.lower())
        
        line_number = 1
        mounter_number = 1
        
        if line_match:
            line_number = int(next(g for g in line_match.groups() if g))
        
        if mounter_match:
            mounter_number = int(next(g for g in mounter_match.groups() if g))
        
        return line_number, mounter_number
    
    def parse_csv_row(self, row, filename, file_hash, line_number, mounter_number):
        """Parsea fila CSV con estructura real de 14 columnas"""
        try:
            # Estructura REAL basada en archivo 20250804.csv (14 columnas):
            # 0=ScanDate, 1=ScanTime, 2=SlotNo, 3=Result, 4=PreviousBarcode, 5=ProductDate,
            # 6=PartName, 7=Quantity, 8=SEQ, 9=Vendor, 10=LOTNO, 11=Barcode, 12=FeederBase, 13=Extra
            scan_date = self.parse_date(row[0]) if len(row) > 0 else datetime.now().date()
            scan_time = self.parse_time(row[1]) if len(row) > 1 else datetime.now().time()
            slot_no = row[2] if len(row) > 2 else ''
            result = row[3] if len(row) > 3 else ''
            previous_barcode = row[4] if len(row) > 4 else ''
            product_date = self.parse_date(row[5]) if len(row) > 5 else None
            part_name = row[6] if len(row) > 6 else ''
            quantity = self.parse_int(row[7]) if len(row) > 7 else 0
            l_position = ''  # No disponible en estructura real
            m_position = ''  # No disponible en estructura real
            seq = row[8] if len(row) > 8 else ''  # CORREGIDO: columna 8, no 10
            vendor = row[9] if len(row) > 9 else ''  # CORREGIDO: columna 9, no 11
            lot_no = row[10] if len(row) > 10 else ''  # CORREGIDO: columna 10, no 12
            barcode = row[11] if len(row) > 11 else ''  # CORREGIDO: columna 11, no 13
            feeder_base = row[12] if len(row) > 12 else ''  # CORREGIDO: columna 12, no 14
            
            return (scan_date, scan_time, slot_no, result, part_name, quantity,
                   vendor, lot_no, l_position, m_position, seq, barcode, feeder_base, 
                   previous_barcode, product_date, filename, line_number, mounter_number, file_hash)
                   
        except Exception as e:
            logger.error(f"Error parseando fila: {e}")
            return None
    
    def parse_date(self, date_str):
        """Parsea fecha"""
        date_formats = ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except:
                continue
        
        return datetime.now().date()
    
    def parse_time(self, time_str):
        """Parsea hora"""
        time_formats = ['%H:%M:%S', '%H:%M', '%I:%M:%S %p', '%I:%M %p']
        
        for fmt in time_formats:
            try:
                return datetime.strptime(time_str.strip(), fmt).time()
            except:
                continue
        
        return datetime.now().time()
    
    def parse_int(self, int_str):
        """Parsea entero"""
        try:
            return int(float(int_str.strip()))
        except:
            return 0
