# API Conventions

## Endpoint Patterns

### AJAX Template Endpoints
Format: `/[module]-ajax`
- Returns HTML template for dynamic loading
- No authentication check (handled by container page)
- Example: `/plan-main-assy-ajax`, `/smt-simple-ajax`

### REST API Endpoints
Format: `/api/[module]/[action]`
- Returns JSON data
- Requires authentication
- Example: `/api/plan`, `/api/smd/inventario/rollos`

### Admin Endpoints
Format: `/admin/[resource]`
- Admin panel routes
- Requires admin permissions
- Example: `/admin/panel`, `/admin/listar_usuarios`

## HTTP Methods

### GET - Read Operations
```python
@app.route('/api/materiales', methods=['GET'])
def get_materiales():
    materiales = obtener_materiales()
    return jsonify(materiales)
```

### POST - Create/Action Operations
```python
@app.route('/api/material', methods=['POST'])
def crear_material():
    data = request.get_json()
    result = guardar_material(data)
    return jsonify({'success': True, 'id': result})
```

### PUT - Update Operations (rarely used)
```python
@app.route('/api/material/<id>', methods=['PUT'])
def actualizar_material(id):
    data = request.get_json()
    result = actualizar_material_completo(id, data)
    return jsonify({'success': True})
```

### DELETE - Delete Operations
```python
@app.route('/api/material/<id>', methods=['DELETE'])
def eliminar_material(id):
    result = eliminar_material(id)
    return jsonify({'success': True})
```

## Request/Response Formats

### Request Body (POST/PUT)
```json
{
    "numero_parte": "ABC123",
    "descripcion": "Material de prueba",
    "cantidad": 100
}
```

### Success Response
```json
{
    "success": true,
    "data": { ... },
    "message": "Operación exitosa"
}
```

### Error Response
```json
{
    "error": "Descripción del error",
    "details": "Detalles adicionales"
}
```

### List Response
```json
[
    { "id": 1, "nombre": "Item 1" },
    { "id": 2, "nombre": "Item 2" }
]
```

## Query Parameters

### Filtering
```
GET /api/materiales?categoria=SMD&proveedor=ABC
```

### Pagination
```
GET /api/materiales?page=1&limit=50
```

### Date Ranges
```
GET /api/movimientos?start=2024-01-01&end=2024-12-31
```

### Sorting
```
GET /api/materiales?sort=numero_parte&order=asc
```

## Authentication & Authorization

### Route Protection
```python
@app.route('/api/material', methods=['POST'])
@login_requerido
@requiere_permiso_dropdown('LISTA_DE_MATERIALES', 'Control de material', 'Crear material')
def crear_material():
    pass
```

### Getting Current User
```python
from flask import session

usuario = session.get('usuario')
nombre_completo = session.get('nombre_completo')
```

## Error Handling

### Standard Pattern
```python
@app.route('/api/material', methods=['POST'])
def crear_material():
    try:
        data = request.get_json()
        
        # Validation
        if not data.get('numero_parte'):
            return jsonify({'error': 'numero_parte requerido'}), 400
        
        # Business logic
        result = guardar_material(data)
        
        # Success
        return jsonify({'success': True, 'id': result})
        
    except Exception as e:
        # Log error
        print(f"❌ Error en crear_material: {e}")
        
        # Return error response
        return jsonify({'error': 'Error interno del servidor'}), 500
```

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `401` - Unauthorized (not logged in)
- `403` - Forbidden (no permission)
- `404` - Not Found
- `500` - Internal Server Error

## Data Validation

### Input Validation
```python
def validar_material(data):
    errores = []
    
    if not data.get('numero_parte'):
        errores.append('numero_parte es requerido')
    
    if len(data.get('numero_parte', '')) > 512:
        errores.append('numero_parte demasiado largo')
    
    return errores

@app.route('/api/material', methods=['POST'])
def crear_material():
    data = request.get_json()
    
    errores = validar_material(data)
    if errores:
        return jsonify({'error': ', '.join(errores)}), 400
    
    # Continue with creation
```

## File Uploads

### Excel Import
```python
@app.route('/api/importar-excel', methods=['POST'])
def importar_excel():
    if 'file' not in request.files:
        return jsonify({'error': 'No se proporcionó archivo'}), 400
    
    file = request.files['file']
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'Formato de archivo inválido'}), 400
    
    # Process file
    df = pd.read_excel(file)
    # ... process data
    
    return jsonify({'success': True, 'rows': len(df)})
```

### File Downloads
```python
from flask import send_file

@app.route('/api/exportar-excel')
def exportar_excel():
    # Generate file
    filepath = generar_excel()
    
    return send_file(
        filepath,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='export.xlsx'
    )
```

## Blueprints

### Creating a Blueprint
```python
from flask import Blueprint

mi_modulo_bp = Blueprint('mi_modulo', __name__, url_prefix='/mi-modulo')

@mi_modulo_bp.route('/data')
def get_data():
    return jsonify([])

# In routes.py or run.py
app.register_blueprint(mi_modulo_bp)
```

### Blueprint Examples
- `user_admin_bp` - User administration (`/admin/*`)
- `admin_bp` - Admin API (`/admin/api/*`)
- `aoi_api` - AOI operations
- `control_modelos_bp` - SMT model control
- `api_raw` - Raw models API
- `smt_bp` - SMT routes

## CORS Configuration

### Enabling CORS
```python
from flask_cors import CORS

# Enable for all routes
CORS(app)

# Enable for specific blueprint
CORS(mi_modulo_bp)

# Enable for specific route
@app.route('/api/public')
@cross_origin()
def public_api():
    return jsonify({'data': 'public'})
```

## Rate Limiting

Currently not implemented, but recommended for production:
```python
# Future implementation
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: session.get('usuario'))

@app.route('/api/expensive-operation')
@limiter.limit("10 per minute")
def expensive_operation():
    pass
```

## API Documentation

### Inline Documentation
```python
@app.route('/api/material', methods=['POST'])
def crear_material():
    """
    Crear nuevo material
    
    Request Body:
        numero_parte (str): Número de parte único
        descripcion (str): Descripción del material
        cantidad (int): Cantidad inicial
    
    Returns:
        JSON: {'success': True, 'id': material_id}
    
    Raises:
        400: Si faltan campos requeridos
        500: Si hay error en la base de datos
    """
    pass
```

## Testing APIs

### Using curl
```bash
# GET request
curl http://localhost:5000/api/materiales

# POST request
curl -X POST http://localhost:5000/api/material \
  -H "Content-Type: application/json" \
  -d '{"numero_parte":"ABC123","descripcion":"Test"}'

# With authentication (session cookie)
curl -X POST http://localhost:5000/api/material \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"numero_parte":"ABC123"}'
```

### Using Axios (Frontend)
```javascript
// GET
const response = await axios.get('/api/materiales');

// POST
const response = await axios.post('/api/material', {
    numero_parte: 'ABC123',
    descripcion: 'Test'
});

// With error handling
try {
    const response = await axios.post('/api/material', data);
    console.log('Success:', response.data);
} catch (error) {
    if (error.response) {
        console.error('Error:', error.response.data.error);
    }
}
```
