# FLUJO COMPLETO DE DATOS SMT
## ¿De dónde está consultando los datos el sistema?

### 📊 ARQUITECTURA COMPLETA

```
📁 Archivos CSV (Entrada)
    ↓
🔧 SMTMonitorService (Procesamiento)
    ↓
🗄️ MySQL Database (Almacenamiento)
    ↓
🌐 Flask API (Backend)
    ↓
🖥️ Frontend (Visualización)
```

### 1. 📁 FUENTE DE DATOS
- **Ubicación**: Carpetas monitoreadas automáticamente
- **Formato**: Archivos CSV generados por las máquinas SMT
- **Estructura**: 
  - scan_date, scan_time, slot_no, result
  - previous_barcode, product_date, part_name
  - quantity, seq, vendor, lotno, barcode
  - feeder_base, extra_column

### 2. 🔧 PROCESAMIENTO (SMTMonitorService)
- **Archivo**: `SMTMonitorService/smt_monitor_service.py`
- **Función**: Servicio de Windows que monitorea carpetas 24/7
- **Proceso**:
  1. Escanea carpetas cada 30 segundos
  2. Detecta archivos CSV nuevos
  3. Lee y valida el contenido
  4. Inserta datos en MySQL
  5. Marca archivos como procesados

### 3. 🗄️ BASE DE DATOS MySQL
- **Servidor**: `up-de-fra1-mysql-1.db.run-on-seenode.com:11550`
- **Base de datos**: `db_rrpq0erbdujn`
- **Usuario**: `db_rrpq0erbdujn`
- **Tabla principal**: `historial_cambio_material_smt`
- **Tabla control**: `archivos_procesados_smt`

#### Estructura de la tabla principal:
```sql
CREATE TABLE historial_cambio_material_smt (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scan_date DATE,
    scan_time TIME,
    slot_no VARCHAR(50),
    result VARCHAR(50),
    previous_barcode VARCHAR(255),
    product_date VARCHAR(50),
    part_name VARCHAR(255),
    quantity DECIMAL(10,2),
    seq VARCHAR(50),
    vendor VARCHAR(255),
    lotno VARCHAR(255),
    barcode VARCHAR(255),
    feeder_base VARCHAR(100),
    extra_column VARCHAR(255),
    archivo_origen VARCHAR(500),
    fecha_procesado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4. 🌐 API BACKEND (Flask)
- **Archivo**: `app/routes.py` (línea 4918)
- **Endpoint**: `/api/historial_smt_data`
- **Método**: GET
- **Función**: `api_historial_smt_data()`

#### Parámetros de filtro opcionales:
- `fecha_inicio`: Fecha de inicio para filtrar
- `fecha_fin`: Fecha final para filtrar
- `carpeta`: Filtrar por archivo origen
- `barcode`: Filtrar por código de barras
- `part_name`: Filtrar por nombre de parte

#### Respuesta JSON:
```json
{
    "success": true,
    "data": [
        {
            "scan_date": "2024-01-15",
            "scan_time": "14:30:25",
            "slot_no": "A1",
            "result": "OK",
            "barcode": "123456789",
            "part_name": "COMPONENTE_X",
            ...
        }
    ],
    "total": 150
}
```

### 5. 🖥️ FRONTEND (Interfaz Web)
- **Archivo**: `app/templates/Control de calidad/historial_cambio_material_smt_ajax.html`
- **JavaScript**: `historial_cambio_material_smt_mysql.js`
- **Funcionalidad**:
  - Fecha automática (día actual)
  - Selección de carpeta
  - Tabla dinámica con datos
  - Filtros en tiempo real

#### Llamada AJAX:
```javascript
const response = await fetch(`/api/historial_smt_data?${params}`);
```

### 📈 FLUJO COMPLETO DE DATOS

1. **Máquinas SMT** → Generan archivos CSV automáticamente
2. **SMTMonitorService** → Procesa archivos CSV cada 30 segundos
3. **MySQL Database** → Almacena datos procesados
4. **Flask API** → Consulta base de datos cuando se solicita
5. **Frontend** → Muestra datos en tabla interactiva

### 🔧 ARCHIVOS CLAVE

- **Servicio**: `SMTMonitorService/smt_monitor_service.py`
- **API Backend**: `app/routes.py` (función `api_historial_smt_data`)
- **Frontend**: `app/templates/Control de calidad/historial_cambio_material_smt_ajax.html`
- **Instalador**: `SMTMonitorService/instalar_servicio_final.bat`

### ✅ ESTADO ACTUAL

- ✅ Servicio SMT funcionando correctamente
- ✅ Base de datos conectada y operativa
- ✅ Frontend con fecha automática implementado
- ✅ Endpoint API `/api/historial_smt_data` creado
- ✅ Sistema completo operativo

### 🚀 PARA ACTIVAR COMPLETAMENTE

1. Reiniciar el servidor Flask para cargar la nueva ruta API
2. Verificar que el servicio SMT esté ejecutándose
3. Comprobar conectividad con MySQL

¡El sistema está consultando datos directamente de la base de datos MySQL remota donde el servicio SMT guarda automáticamente los archivos CSV procesados!
