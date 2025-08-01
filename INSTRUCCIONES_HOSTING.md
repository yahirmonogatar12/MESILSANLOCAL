# Instrucciones para Despliegue en Hosting

## Problema Resuelto: Conflicto de Dependencias Werkzeug

El error que experimentaste:
```
ERROR: Cannot install -r requirements.txt (line 7) and Werkzeug==2.2.3 because these package versions have conflicting dependencies.
```

## Solución Implementada

### 1. Requirements.txt Actualizado
Se actualizó el archivo `requirements.txt` con versiones compatibles usando rangos en lugar de versiones fijas:

```
# Antes (versiones fijas - causaban conflictos)
Flask==2.3.3
Werkzeug==2.3.6

# Ahora (rangos compatibles)
Flask>=2.3.0,<3.0.0
Werkzeug>=2.3.0,<3.0.0
```

### 2. Archivos de Requirements Disponibles

- **`requirements.txt`**: Versión principal con rangos compatibles
- **`requirements_hosting.txt`**: Versión minimalista específica para hosting

### 3. Instrucciones de Instalación para Hosting

#### Opción 1: Usar requirements.txt principal
```bash
pip install -r requirements.txt
```

#### Opción 2: Usar requirements_hosting.txt (recomendado)
```bash
pip install -r requirements_hosting.txt
```

#### Opción 3: Instalación manual (si persisten conflictos)
```bash
pip install "Flask>=2.3.0,<3.0.0"
pip install "Werkzeug>=2.3.0,<3.0.0"
pip install "pymysql>=1.0.0"
pip install "python-dotenv>=1.0.0"
pip install "flask-cors>=4.0.0"
pip install "requests>=2.30.0"
pip install "pandas>=2.0.0"
pip install "openpyxl>=3.1.0"
pip install "psutil>=5.9.0"
pip install "pytz>=2023.3"
```

### 4. Configuración del Hosting

1. **Subir archivos**:
   - Todo el contenido del proyecto
   - Usar `hosting_config.env` como archivo de configuración

2. **Variables de entorno** (desde `hosting_config.env`):
   ```
   USE_HTTP_PROXY=true
   MYSQL_PROXY_URL=http://TU_IP_PUBLICA:5000
   PROXY_API_KEY=tu_api_key_generada
   ```

3. **Iniciar el proxy local**:
   ```bash
   python mysql_proxy_server.py
   ```

### 5. Verificación

Puedes usar el script `test_dependencies.py` para verificar que todas las dependencias estén instaladas:

```bash
python test_dependencies.py
```

### 6. Notas Importantes

- **Werkzeug**: Las versiones 2.2.3 y 2.3.x son compatibles con Flask 2.3.x
- **Rangos de versiones**: Permiten mayor flexibilidad y evitan conflictos
- **Proxy MySQL**: Necesario para conectar el hosting con tu base de datos local
- **Seguridad**: Asegúrate de configurar correctamente la API Key y los hosts permitidos

### 7. Troubleshooting

Si aún tienes problemas:

1. **Limpiar caché de pip**:
   ```bash
   pip cache purge
   ```

2. **Crear entorno virtual limpio**:
   ```bash
   python -m venv venv_hosting
   source venv_hosting/bin/activate  # Linux/Mac
   venv_hosting\Scripts\activate     # Windows
   pip install -r requirements_hosting.txt
   ```

3. **Verificar versiones de Python**:
   - Asegúrate de usar Python 3.8 o superior
   - Verifica: `python --version`

---

**Estado actual**: ✅ Todas las dependencias funcionan correctamente en el entorno local.
**Próximo paso**: Probar en el hosting con `requirements_hosting.txt`