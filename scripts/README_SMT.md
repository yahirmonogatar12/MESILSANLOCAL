# SMT CSV Monitor - Sistema de Monitoreo en Tiempo Real

## 📋 Descripción

Este sistema permite monitorear carpetas compartidas donde se generan archivos CSV de SMT y automáticamente subirlos a una base de datos MySQL para consulta en tiempo real desde la aplicación web.

## 🚀 Características

- **Monitoreo en tiempo real** de carpetas compartidas
- **Detección automática** de nuevos archivos CSV
- **Procesamiento inmediato** sin intervención manual
- **Base de datos MySQL** para consultas rápidas
- **API REST** para integración con frontend
- **Prevención de duplicados** mediante hashing
- **Logs detallados** para seguimiento
- **Servicio Windows** para ejecución automática

## 📁 Estructura de Archivos

```
scripts/
├── smt_csv_monitor.py          # Script principal de monitoreo
├── smt_csv_handler.py          # Clase para manejo de CSV y MySQL  
├── smt_routes.py               # Rutas API Flask
├── config.py                   # Configuración del sistema
├── setup.py                    # Instalador automático
├── requirements_monitor.txt    # Dependencias Python
└── README_SMT.md              # Esta documentación

app/static/js/
└── historial_cambio_material_smt_mysql.js  # Frontend JavaScript

templates/
└── historial_cambio_material_smt_ajax.html # Template HTML
```

## ⚙️ Instalación

### 1. Instalación Automática
```bash
cd scripts
python setup.py
```

### 2. Instalación Manual
```bash
# Instalar dependencias
pip install -r requirements_monitor.txt

# Configurar base de datos MySQL
# Crear base de datos 'isemm_mes' si no existe
```

### 3. Configuración

Editar `config.py`:

```python
# Base de datos MySQL
DATABASE = {
    'host': 'localhost',           # Tu servidor MySQL
    'user': 'root',               # Tu usuario MySQL  
    'password': 'tu_password',    # Tu password MySQL
    'database': 'isemm_mes',      # Tu base de datos
}

# Carpetas a monitorear
WATCH_FOLDERS = [
    r'\\SERVIDOR\SMT\1Line\M1',   # Carpetas de red
    r'\\SERVIDOR\SMT\1Line\M2',   # o locales
    r'C:\SMT_Data\Line1',         # según tu configuración
    # Agregar todas las carpetas necesarias
]
```

## 🔧 Configuración de Flask

### 1. Registrar las rutas SMT

En tu archivo principal Flask (`run.py` o `app.py`):

```python
from app.smt_routes import register_smt_routes

# Después de crear la app
register_smt_routes(app)
```

### 2. Agregar dependencias

En tu `requirements.txt` principal:
```
mysql-connector-python==8.0.33
watchdog==3.0.0
```

## 🗄️ Base de Datos

### Estructura de Tablas

El sistema crea automáticamente estas tablas:

```sql
-- Tabla principal de datos
CREATE TABLE historial_cambio_material_smt (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scan_date DATE NOT NULL,
    scan_time TIME NOT NULL,
    slot_no VARCHAR(50),
    result VARCHAR(10),
    part_name VARCHAR(100),
    quantity INT,
    vendor VARCHAR(100),
    lot_no VARCHAR(100),
    barcode VARCHAR(200),
    feeder_base VARCHAR(100),
    previous_barcode VARCHAR(200),
    source_file VARCHAR(255),
    line_number INT NOT NULL,
    mounter_number INT NOT NULL,
    file_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Índices para optimización
    INDEX idx_scan_date (scan_date),
    INDEX idx_part_name (part_name),
    INDEX idx_result (result),
    INDEX idx_line_mounter (line_number, mounter_number)
);

-- Tabla de control de archivos procesados
CREATE TABLE smt_files_processed (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) UNIQUE NOT NULL,
    filepath VARCHAR(500),
    line_number INT NOT NULL,
    mounter_number INT NOT NULL,
    file_hash VARCHAR(64),
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    records_count INT DEFAULT 0,
    file_size BIGINT
);
```

## 🚀 Ejecución

### Modo Manual (Desarrollo)
```bash
cd scripts
python smt_csv_monitor.py
```

### Modo Servicio (Producción)
```bash
# Instalar como servicio Windows
python smt_monitor_service.py install
python smt_monitor_service.py start

# O usar el script batch
instalar_servicio.bat
```

### Usando Scripts Batch
```bash
# Ejecución manual
ejecutar_monitor.bat

# Instalar servicio
instalar_servicio.bat
```

## 📊 API Endpoints

### GET /api/smt/historial/data
Obtiene datos del historial con filtros opcionales.

**Parámetros:**
- `folder`: Línea y mounter (ej: "1Line_M1")
- `part_name`: Nombre de parte (búsqueda parcial)
- `result`: Resultado (OK/NG)
- `date_from`: Fecha desde (YYYY-MM-DD)
- `date_to`: Fecha hasta (YYYY-MM-DD)

**Respuesta:**
```json
{
    "success": true,
    "data": [
        {
            "scan_date": "2024-01-15",
            "scan_time": "10:30:25",
            "slot_no": "1",
            "result": "OK",
            "part_name": "R0603_100K",
            "quantity": 1,
            "vendor": "VENDOR_A",
            "lot_no": "LOT123",
            "barcode": "BAR456",
            "feeder_base": "FB01",
            "previous_barcode": "PREV789",
            "source_file": "data_20240115.csv"
        }
    ],
    "stats": {
        "total": 1500,
        "ok": 1450,
        "ng": 50
    }
}
```

### GET /api/smt/historial/export
Exporta datos para descarga (mismos filtros que `/data`).

### POST /api/smt/historial/upload
Sube archivo CSV manualmente.

**Parámetros:**
- `csvFile`: Archivo CSV (multipart/form-data)
- `lineNumber`: Número de línea (opcional)
- `mounterNumber`: Número de mounter (opcional)

### GET /api/smt/folders
Obtiene carpetas/líneas disponibles.

### GET /api/smt/stats
Estadísticas generales del sistema.

## 🔄 Flujo de Trabajo

1. **Monitor detecta** nuevo archivo CSV en carpeta compartida
2. **Verifica** que no haya sido procesado anteriormente (hash)
3. **Extrae** línea y mounter del path/nombre del archivo
4. **Parsea** el CSV y valida datos
5. **Inserta** en MySQL en lotes de 500 registros
6. **Marca** archivo como procesado
7. **Frontend** puede consultar datos inmediatamente

## 🛠️ Mantenimiento

### Logs
```bash
# Ver logs del monitor
tail -f smt_monitor.log

# Ver logs del servicio Windows
eventvwr.msc # Buscar "SMT CSV Monitor Service"
```

### Comandos Útiles
```bash
# Verificar servicio
sc query SMTCSVMonitor

# Reiniciar servicio
net stop SMTCSVMonitor
net start SMTCSVMonitor

# Ver estadísticas de base de datos
SELECT 
    line_number, 
    mounter_number, 
    COUNT(*) as total_records,
    MAX(created_at) as last_update
FROM historial_cambio_material_smt 
GROUP BY line_number, mounter_number;
```

## ⚠️ Troubleshooting

### Problemas Comunes

1. **Error de conexión MySQL**
   - Verificar credenciales en `config.py`
   - Asegurar que MySQL esté corriendo
   - Verificar permisos de usuario

2. **Archivos no se procesan**
   - Verificar que las carpetas existan y sean accesibles
   - Revisar permisos de red
   - Verificar logs para errores específicos

3. **Duplicados en base de datos**
   - El sistema previene duplicados por hash
   - Verificar tabla `smt_files_processed`

4. **Performance lenta**
   - Verificar índices en MySQL
   - Considerar particionado por fecha
   - Monitorear uso de memoria

### Optimización

```sql
-- Crear índices adicionales si es necesario
CREATE INDEX idx_created_at ON historial_cambio_material_smt(created_at);
CREATE INDEX idx_compound ON historial_cambio_material_smt(line_number, mounter_number, scan_date);

-- Limpiar datos antiguos (opcional)
DELETE FROM historial_cambio_material_smt 
WHERE scan_date < DATE_SUB(NOW(), INTERVAL 6 MONTH);
```

## 📞 Soporte

Para problemas o mejoras:

1. Revisar logs: `smt_monitor.log`
2. Verificar configuración: `config.py` 
3. Comprobar conectividad: Base de datos y carpetas de red
4. Revisar permisos: Usuario del servicio

## 🔄 Próximas Mejoras

- [ ] Dashboard en tiempo real
- [ ] Alertas por email/Slack
- [ ] Compresión de datos antiguos
- [ ] Backup automático
- [ ] Métricas de performance
- [ ] Interfaz web de configuración
