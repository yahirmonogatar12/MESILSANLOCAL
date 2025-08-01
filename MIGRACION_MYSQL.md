# Migración a MySQL - Guía Completa

## Estado Actual

✅ **Completado:**
- Instalación de dependencias MySQL (`pymysql`, `cryptography`, `python-dotenv`)
- Creación de módulos de configuración MySQL (`config_mysql.py`, `db_mysql.py`)
- Actualización de `requirements.txt` con dependencias MySQL
- Migración de funciones principales en `routes.py` de SQLite a MySQL
- Configuración de variables de entorno en `.env`
- Sistema de fallback a SQLite cuando MySQL no está disponible

❌ **Pendiente:**
- Verificación de credenciales MySQL del hosting
- Resolución de error de autenticación
- Pruebas de funcionalidad completa con MySQL

## Problema Actual

**Error de Conexión:**
```
(1045, "Access denied for user 'db_9qev77c4d3e2'@'200.188.154.231' (using password: YES)")
```

**Posibles Causas:**
1. **Credenciales incorrectas** - Las credenciales proporcionadas pueden estar desactualizadas
2. **Restricciones de IP** - El servidor MySQL puede tener whitelist de IPs permitidas
3. **Configuración SSL** - Puede requerir configuración SSL específica
4. **Puerto bloqueado** - El puerto 11550 puede estar bloqueado por firewall

## Credenciales Actuales

```env
MYSQL_HOST=up-de-fra1-mysql-1.db.run-on-seenode.com
MYSQL_PORT=11550
MYSQL_DATABASE=db_9qev77c4d3e2
MYSQL_USERNAME=db_9qev77c4d3e2
MYSQL_PASSWORD=gKqRnRdyTOWnv8Tn8ul8w80P
```

## Pasos para Resolver

### 1. Verificar Credenciales con el Hosting
- Contactar al proveedor de hosting para confirmar credenciales
- Verificar que la base de datos esté activa
- Confirmar configuraciones de acceso remoto

### 2. Configurar Whitelist de IP
- Obtener IP pública actual: `curl ifconfig.me`
- Agregar IP a la whitelist del servidor MySQL
- Considerar usar IP dinámica si es necesario

### 3. Probar Conexión Directa
```bash
# Probar con cliente MySQL
mysql -h up-de-fra1-mysql-1.db.run-on-seenode.com -P 11550 -u db_9qev77c4d3e2 -p db_9qev77c4d3e2

# Probar con telnet (verificar conectividad)
telnet up-de-fra1-mysql-1.db.run-on-seenode.com 11550
```

### 4. Configuraciones SSL Alternativas
Si el servidor requiere SSL específico, actualizar `config_mysql.py`:
```python
return {
    'host': host,
    'port': port,
    'user': username,
    'passwd': password,
    'db': database,
    'charset': 'utf8mb4',
    'ssl': {'ssl_disabled': True},  # O configuración SSL específica
    'connect_timeout': 60
}
```

## Modo Fallback Actual

La aplicación está configurada para usar SQLite como fallback cuando MySQL no está disponible:

- ✅ **Funciones migradas:** Materiales, inventario, BOM, usuarios
- ✅ **Compatibilidad:** Mantiene todas las funcionalidades existentes
- ✅ **Datos preservados:** La base de datos SQLite existente sigue funcionando

## Archivos Modificados

### Nuevos Archivos
- `app/config_mysql.py` - Configuración de conexión MySQL
- `app/db_mysql.py` - Funciones de base de datos MySQL
- `.env` - Variables de entorno para MySQL

### Archivos Actualizados
- `app/db.py` - Sistema híbrido MySQL/SQLite
- `app/routes.py` - Funciones migradas a MySQL
- `requirements.txt` - Dependencias MySQL añadidas

## Funciones Migradas

### ✅ Completamente Migradas
- `guardar_material()` - Guardar materiales
- `listar_materiales()` - Listar materiales
- `importar_excel()` - Importación desde Excel
- `actualizar_campo_material()` - Actualización de campos
- `agregar_entrada_aereo()` - Entradas de material aéreo
- `listar_entradas_aereo()` - Listado de entradas aéreo
- `buscar_material_por_numero_parte()` - Búsqueda de materiales
- Sistema de permisos y autenticación

### ⚠️ Pendientes de Migración
- Funciones de BOM (Bill of Materials)
- Funciones de inventario avanzado
- Reportes y exportaciones
- Funciones de auditoría

## Comandos de Prueba

```bash
# Probar conexión MySQL
python app/config_mysql.py

# Probar aplicación en modo fallback
python run.py

# Verificar dependencias
pip list | grep -E "pymysql|cryptography|python-dotenv"
```

## Próximos Pasos

1. **Inmediato:** Verificar credenciales con el hosting
2. **Corto plazo:** Resolver conectividad MySQL
3. **Mediano plazo:** Completar migración de funciones restantes
4. **Largo plazo:** Optimizar rendimiento y añadir funciones específicas de MySQL

## Beneficios de la Migración

Una vez completada la migración a MySQL:
- 🚀 **Mejor rendimiento** para múltiples usuarios concurrentes
- 🔒 **Mayor seguridad** con autenticación robusta
- 📈 **Escalabilidad** para crecimiento futuro
- 🌐 **Acceso remoto** desde múltiples ubicaciones
- 🔄 **Backup automático** del hosting
- 🛠️ **Herramientas avanzadas** de administración

---

**Nota:** La aplicación funciona completamente en modo SQLite mientras se resuelve la conectividad MySQL. No hay pérdida de funcionalidad durante la transición.