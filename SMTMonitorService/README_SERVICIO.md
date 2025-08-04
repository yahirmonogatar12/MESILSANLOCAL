# SMT Monitor Service

## Descripción
Servicio de Windows que monitorea automáticamente las carpetas de archivos CSV de SMT y los procesa en la base de datos.

## Carpetas Monitoreadas
- `C:\LOT CHECK  ALL\1line\L1 m1`
- `C:\LOT CHECK  ALL\1line\L1 m2`
- `C:\LOT CHECK  ALL\1line\L1 m3`
- `C:\LOT CHECK  ALL\2line\L2 m1`
- `C:\LOT CHECK  ALL\2line\L2 m2`
- `C:\LOT CHECK  ALL\2line\L2 m3`
- `C:\LOT CHECK  ALL\3line\L3 m1`
- `C:\LOT CHECK  ALL\3line\L3 m2`
- `C:\LOT CHECK  ALL\3line\L3 m3`
- `C:\LOT CHECK  ALL\4line\L4 m1`
- `C:\LOT CHECK  ALL\4line\L4 m2`
- `C:\LOT CHECK  ALL\4line\L4 m3`

## Requisitos
- Windows con permisos de Administrador
- Python 3.7+
- Dependencias: `pywin32`, `mysql-connector-python`
- Acceso a la base de datos MySQL (up-de-fra1-mysql-1.db.run-on-seenode.com:11550)

## Instalación

### 1. Preparar el sistema
```bash
# Instalar dependencias
pip install pywin32 mysql-connector-python
```

### 2. Crear estructura de carpetas
Crear las carpetas que va a monitorear:
```
C:\LOT CHECK  ALL\
├── 1line\
│   ├── L1 m1\
│   ├── L1 m2\
│   └── L1 m3\
├── 2line\
│   ├── L2 m1\
│   ├── L2 m2\
│   └── L2 m3\
├── 3line\
│   ├── L3 m1\
│   ├── L3 m2\
│   └── L3 m3\
└── 4line\
    ├── L4 m1\
    ├── L4 m2\
    └── L4 m3\
```

### 3. Instalar servicio
**Ejecutar como Administrador:**
```bash
instalar_servicio.bat
```

## Administración

### Administrar servicio
```bash
administrar_servicio.bat
```

### Comandos manuales
```bash
# Iniciar servicio
net start SMTMonitorService

# Detener servicio
net stop SMTMonitorService

# Ver estado
sc query SMTMonitorService
```

## Configuración

### Base de datos
El servicio se conecta a:
- Host: `up-de-fra1-mysql-1.db.run-on-seenode.com`
- Puerto: `11550`
- Usuario: `db_rrpq0erbdujn`
- Contraseña: `5fUNbSRcPP3LN9K2I33Pr0ge`
- Base de datos: `db_rrpq0erbdujn`

### Tablas utilizadas
- `historial_cambio_material_smt`: Datos procesados
- `archivos_procesados_smt`: Control de archivos

## Logs
- Archivo: `smt_monitor_service.log`
- Nivel: INFO
- Rotación: Manual

## Estructura de archivos CSV
El servicio procesa archivos CSV con 14 columnas:
1. ScanDate
2. ScanTime  
3. SlotNo
4. Result
5. PreviousBarcode
6. ProductDate
7. PartName
8. Quantity
9. SEQ
10. Vendor
11. LOTNO
12. Barcode
13. FeederBase
14. Extra

## Funcionamiento
1. **Inicio automático**: El servicio inicia con Windows
2. **Monitoreo continuo**: Revisa las carpetas cada 30 segundos
3. **Detección de archivos**: Procesa archivos .csv nuevos o modificados
4. **Control de duplicados**: Evita procesar el mismo registro dos veces
5. **Logging**: Registra todas las actividades

## Troubleshooting

### Servicio no inicia
1. Verificar permisos de administrador
2. Comprobar dependencias instaladas
3. Revisar conectividad a base de datos
4. Verificar logs: `smt_monitor_service.log`

### Archivos no se procesan
1. Verificar que las carpetas existen
2. Comprobar formato del CSV (14 columnas)
3. Revisar permisos de lectura en las carpetas
4. Verificar logs para errores específicos

### Problemas de base de datos
1. Verificar conectividad: `ping up-de-fra1-mysql-1.db.run-on-seenode.com`
2. Comprobar credenciales de MySQL
3. Verificar que las tablas existen
4. Revisar logs de MySQL

## Desinstalación
**Ejecutar como Administrador:**
```bash
desinstalar_servicio.bat
```
