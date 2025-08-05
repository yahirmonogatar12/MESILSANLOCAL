# Configuración para SMT CSV Monitor

# Base de datos MySQL
DATABASE = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4',
    'autocommit': True
}

# Carpetas a monitorear (estructura real según tu servidor)
WATCH_FOLDERS = [
    # Línea 1
    r'\\192.168.1.230\qa\ILSAN_MES\Mounter_LogFile\1line\L1 m1',
    r'\\192.168.1.230\qa\ILSAN_MES\Mounter_LogFile\1line\L1 m2',
    r'\\192.168.1.230\qa\ILSAN_MES\Mounter_LogFile\1line\L1 m3',
    
    # Línea 2 (agregar las carpetas reales cuando las veas)
    r'\\192.168.1.230\qa\ILSAN_MES\Mounter_LogFile\2line',
    
    # Línea 3 (agregar las carpetas reales cuando las veas)
    r'\\192.168.1.230\qa\ILSAN_MES\Mounter_LogFile\3line',
    
    # Línea 4 (agregar las carpetas reales cuando las veas)
    r'\\192.168.1.230\qa\ILSAN_MES\Mounter_LogFile\4line',
    
    # Para monitorear recursivamente todas las subcarpetas de cada línea
    # El monitor buscará archivos CSV en todas las subcarpetas
]

# Configuración del monitor
MONITOR_CONFIG = {
    'batch_size': 500,              # Registros por lote
    'file_timeout': 30,             # Segundos para esperar archivo listo
    'process_existing': True,       # Procesar archivos existentes al inicio
    'log_level': 'INFO',           # DEBUG, INFO, WARNING, ERROR
    'max_retries': 3               # Reintentos por archivo
}

# Patrones de archivos CSV a procesar
FILE_PATTERNS = [
    '*.csv',
    '*.CSV',
    # Agregar más patrones si necesario
]

# Configuración de logging
LOGGING = {
    'filename': 'smt_monitor.log',
    'max_size_mb': 50,             # Tamaño máximo del log
    'backup_count': 5              # Archivos de backup
}

# Configuración de red (si accedes a carpetas compartidas)
NETWORK_CONFIG = {
    'retry_delay': 5,              # Segundos entre reintentos
    'max_network_retries': 3,      # Reintentos para archivos de red
    'connection_timeout': 10       # Timeout de conexión
}
