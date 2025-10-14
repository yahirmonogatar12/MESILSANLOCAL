# Database Patterns

## Database Access

### Connection Management
- MySQL via PyMySQL and mysql-connector-python
- Connection wrapper: `execute_query()` in `db_mysql.py`
- No connection pooling at application level (handled by MySQL)
- Environment variables or hardcoded config in `db_mysql.py`

### Query Execution Pattern
```python
from app.db_mysql import execute_query

# Single row
result = execute_query("SELECT * FROM materiales WHERE id = %s", (id,), fetch='one')

# Multiple rows
results = execute_query("SELECT * FROM materiales", fetch='all')

# Insert/Update/Delete (returns affected rows)
affected = execute_query("INSERT INTO materiales (...) VALUES (...)", (params,))
```

### No ORM
- Direct SQL queries throughout the codebase
- Manual result mapping to dictionaries
- Parameterized queries for SQL injection prevention

## Key Tables

### User Management
- `usuarios_sistema` - User accounts
- `roles` - Role definitions
- `permisos` - Module permissions (legacy)
- `permisos_botones` - Button/dropdown permissions
- `usuario_roles` - User-role mapping
- `rol_permisos` - Role-module permission mapping
- `rol_permisos_botones` - Role-button permission mapping
- `sesiones_activas` - Active sessions
- `auditoria` - Audit log

### Material Management
- `materiales` - Material master data
- `inventario` - Current inventory levels
- `movimientos_inventario` - Inventory movement history
- `bom` - Bill of materials

### Production
- `plan_main` - Production planning
- `historial_cambio_material_smt` - SMT material changes
- `InventarioRollosSMD` - SMD roll inventory
- `HistorialMovimientosRollosSMD` - SMD roll movement history

### Configuration
- `configuracion` - System configuration key-value pairs

## Common Patterns

### Insert or Update (Upsert)
```python
query = """
    INSERT INTO materiales (numero_parte, descripcion, ...)
    VALUES (%s, %s, ...)
    ON DUPLICATE KEY UPDATE
        descripcion = VALUES(descripcion),
        ...
"""
execute_query(query, params)
```

### Fetching with Joins
```python
query = """
    SELECT u.*, r.nombre as rol_nombre
    FROM usuarios_sistema u
    LEFT JOIN usuario_roles ur ON u.id = ur.usuario_id
    LEFT JOIN roles r ON ur.rol_id = r.id
    WHERE u.username = %s
"""
result = execute_query(query, (username,), fetch='one')
```

### Aggregation
```python
query = """
    SELECT COUNT(*) as total, SUM(cantidad) as suma
    FROM inventario
    WHERE categoria = %s
"""
result = execute_query(query, (categoria,), fetch='one')
total = result['total']
```

### Transactions
Transactions are auto-committed by `execute_query()`. For multi-statement transactions:
```python
from app.db_mysql import get_connection

conn = get_connection()
cursor = conn.cursor()
try:
    cursor.execute("UPDATE ...", params1)
    cursor.execute("INSERT ...", params2)
    conn.commit()
except Exception as e:
    conn.rollback()
    raise
finally:
    conn.close()
```

## Data Types

### Common Field Types
- `VARCHAR(255)` - Short text (usernames, codes)
- `VARCHAR(512)` - Medium text (part numbers, descriptions)
- `TEXT` - Long text (specifications, comments)
- `INT` - Integers (quantities, IDs)
- `DATETIME` - Timestamps (use `NOW()` for current time)
- `BOOLEAN` - True/false (stored as TINYINT)

### Character Set
- All tables use `CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci`
- Supports full Unicode including emojis
- Important for international part numbers and descriptions

## Timezone Handling

### Mexico Timezone (GMT-6)
```python
from app.auth_system import AuthSystem

# Get current Mexico time
mexico_time = AuthSystem.get_mexico_time()

# For MySQL DATETIME format
mysql_time = AuthSystem.get_mexico_time_mysql()  # 'YYYY-MM-DD HH:MM:SS'
```

### Storing Timestamps
- Always use `DATETIME` type
- Store in Mexico timezone (GMT-6)
- Use `NOW()` in SQL or `get_mexico_time_mysql()` in Python

## Foreign Keys

### Current Status
Foreign keys to `materiales` table are **disabled** by design:
- No FK constraints on `inventario.numero_parte`
- No FK constraints on `movimientos_inventario.numero_parte`
- No FK constraints on `bom.numero_parte`

### Rationale
- Allows flexible data import without strict referential integrity
- Prevents cascade delete issues
- Application-level integrity checks instead

### Indexes
Key indexes for performance:
- `materiales.numero_parte` - Primary lookup
- `materiales.codigo_material` - Alternative lookup
- `usuarios_sistema.username` - Login queries
- `bom(modelo, numero_parte, side)` - Unique constraint

## Migration Patterns

### Adding Columns
```python
def agregar_columna_si_no_existe(tabla, columna, tipo):
    try:
        check_query = f"""
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = '{tabla}'
            AND COLUMN_NAME = '{columna}'
        """
        result = execute_query(check_query, fetch='one')
        
        if result['count'] == 0:
            alter_query = f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}"
            execute_query(alter_query)
            print(f"✅ Columna {columna} agregada a {tabla}")
    except Exception as e:
        print(f"❌ Error agregando columna: {e}")
```

### Data Validation Before Insert
```python
def validar_registro(data):
    errores = []
    
    # Required fields
    if not data.get('numero_parte'):
        errores.append("numero_parte requerido")
    
    # Length checks
    if len(data.get('numero_parte', '')) > 512:
        errores.append("numero_parte demasiado largo")
    
    return errores
```

## Performance Considerations

### Avoid N+1 Queries
Bad:
```python
usuarios = execute_query("SELECT * FROM usuarios", fetch='all')
for usuario in usuarios:
    rol = execute_query("SELECT * FROM roles WHERE id = %s", (usuario['rol_id'],), fetch='one')
```

Good:
```python
usuarios = execute_query("""
    SELECT u.*, r.nombre as rol_nombre
    FROM usuarios u
    LEFT JOIN roles r ON u.rol_id = r.id
""", fetch='all')
```

### Use Indexes
- Always index foreign key columns
- Index columns used in WHERE clauses
- Index columns used in JOIN conditions

### Limit Result Sets
```python
# Add LIMIT for large tables
query = "SELECT * FROM auditoria ORDER BY fecha_hora DESC LIMIT 1000"
```
