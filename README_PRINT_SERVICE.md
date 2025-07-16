# 🖨️ Sistema de Impresión Automática Zebra ZT230

## 📋 Descripción

Sistema de impresión automática para etiquetas QR usando impresora Zebra ZT230. Implementa impresión directa sin diálogos ni confirmaciones mediante un servicio Flask con Win32 API.

## 🚀 Instalación Rápida

### ⚡ Opción 1: Método Local (MÁS CONFIABLE para rutas UNC)
```bash
# Copia archivos localmente - Siempre funciona
start_print_service_local.bat
```

### 🔧 Opción 2: Método PowerShell (Recomendado para rutas UNC)
```bash
# Usa PowerShell que soporta rutas UNC
start_print_service_powershell.bat
```

### 🗂️ Opción 3: Script con Mapeo de Unidad
```bash
# Mapea temporalmente la unidad de red
start_print_service_direct.bat
```

### 📁 Opción 4: Instalación Automática 
```bash
# Método original - puede fallar con rutas UNC
start_print_service.bat
```

### 🛠️ Opción 5: Si hay problemas con la instalación automática
```bash
# Instalación manual paso a paso
install_print_service_manual.bat
```

### ⭐ Opción 6: Solo ejecutar (si ya está instalado)
```bash
# Ejecutar servicio directamente
run_print_service.bat
```

### 🔧 Opción 7: Instalación completamente manual
```bash
# En PowerShell o CMD como Administrador
pip install flask
pip install pywin32
python print_service.py
```

### 2. Verificar Funcionamiento
```javascript
// En la consola del navegador
testServicioWin32()
```

## 📦 Instalación Manual

### Prerequisitos
- Windows 10/11
- Python 3.8+
- Impresora Zebra ZT230 conectada por USB
- Navegador web moderno

### Paso a Paso

1. **Instalar Python** (si no está instalado)
   ```
   https://python.org/downloads/
   ✅ Marcar "Add Python to PATH"
   ```

2. **Instalar Dependencias**
   ```bash
   pip install -r print_requirements.txt
   ```

3. **Configurar Impresora**
   - Conectar Zebra ZT230 por USB
   - Instalar drivers desde el sitio de Zebra
   - Verificar en Panel de Control > Dispositivos

4. **Iniciar Servicio**
   ```bash
   python print_service.py
   ```

## 🔧 Configuración

### Configuración Automática
El sistema se configura automáticamente al cargar la página. No requiere configuración manual.

### Configuración Manual
```javascript
// En la consola del navegador
localStorage.setItem('zebra_config', JSON.stringify({
    ip: '192.168.1.100',
    tipo: 'material',          // 'material' o 'simple'
    metodo: 'usb',             // 'usb' o 'red'
    service_url: 'http://localhost:5000',
    use_win32_service: true
}));
```

## 🧪 Testing

### Test Básico
```javascript
testImpresionDirecta()
```

### Test Completo del Servicio
```javascript
testServicioWin32()
```

### Test Desde Terminal
```bash
# Verificar estado
curl http://localhost:5000/

# Test de impresión
curl -X POST http://localhost:5000/test
```

## 📊 Endpoints del Servicio

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Estado del servicio |
| `/print` | POST | Impresión de ZPL |
| `/test` | GET/POST | Test de impresión |
| `/printers` | GET | Lista de impresoras |

### Ejemplo de Uso
```javascript
fetch('http://localhost:5000/print', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        zpl: '^XA^FO50,50^ADN,18,10^FDTest^FS^XZ',
        codigo: 'TEST123'
    })
});
```

## 🔄 Flujo de Funcionamiento

1. **Usuario llena formulario** de material
2. **Hace clic en "Guardar"**
3. **Sistema guarda** en base de datos
4. **Genera comando ZPL** automáticamente
5. **Envía al servicio Win32** en puerto 5000
6. **Servicio imprime** directamente en ZT230
7. **Muestra notificación** de éxito
8. **Recarga siguiente secuencial**

## 🛠️ Troubleshooting

### Problemas Comunes

**❌ Error: "Could not open requirements file"**
```bash
# Solución 1: Usar instalación manual
install_print_service_manual.bat

# Solución 2: Instalar dependencias manualmente
pip install flask pywin32

# Solución 3: Verificar ubicación de archivos
# Asegúrese de ejecutar desde la carpeta correcta
```

**❌ Error: "print_service.py no encontrado"**
- Verificar que está ejecutando desde la carpeta ILSAN_MES
- Verificar que el archivo print_service.py existe
- Usar `run_print_service.bat` para diagnóstico

**❌ Error: "Python no está instalado"**
- Descargar Python desde https://python.org/downloads/
- Durante instalación marcar "Add Python to PATH"
- Reiniciar la terminal después de instalar

**❌ Error: "Servicio no disponible"**
```bash
# Solución: Iniciar el servicio
start_print_service.bat
```

**❌ Error: "No se detectó impresora"**
- Verificar que ZT230 esté conectada por USB
- Verificar drivers instalados
- Revisar nombre en Panel de Control

**❌ Error: "Puerto 5000 ocupado"**
```bash
# Verificar qué usa el puerto
netstat -ano | findstr :5000

# Cambiar puerto en print_service.py
app.run(port=5001)  # Usar puerto diferente
```

**❌ Error: "ModuleNotFoundError: win32print"**
```bash
pip install pywin32
```

### Logs y Diagnóstico

**Ver logs del servicio:**
```bash
# Se genera automáticamente: print_service.log
type print_service.log
```

**Verificar impresoras disponibles:**
```javascript
// En consola del navegador
fetch('http://localhost:5000/printers')
    .then(r => r.json())
    .then(console.log);
```

### 🔥 SOLUCIÓN A ERRORES COMUNES

**ERROR: "CMD no es compatible con las rutas de acceso UNC como directorio actual"**
```
CAUSA: Windows CMD no puede usar rutas de red (\\servidor\carpeta) como directorio actual
SOLUCIONES (en orden de recomendación):
1. start_print_service_local.bat (copia archivos localmente)
2. start_print_service_powershell.bat (usa PowerShell)
3. start_print_service_direct.bat (mapea unidad temporal)
```

**ERROR: "print_service.py no encontrado" / "Directorio actual: C:\Windows"**
```
CAUSA: El script se ejecuta desde el directorio incorrecto
SOLUCIÓN: Usar start_print_service_local.bat (más confiable)
```

**ERROR: "Could not open requirements file"**
```
CAUSA: El script no puede encontrar print_requirements.txt en rutas UNC
SOLUCIÓN: 
1. Usar start_print_service_local.bat (copia archivos localmente)
2. O instalar manualmente: pip install flask pywin32
```

**ERROR: "Python no está instalado"**
```
SOLUCIÓN:
1. Descargar Python desde https://python.org/downloads/
2. Durante instalación marcar "Add Python to PATH"
3. Reiniciar scripts
```

**ERROR: "No se encuentra la impresora"**
```
SOLUCIÓN:
1. Conectar ZT230 por USB
2. Instalar drivers de Zebra
3. Verificar en Panel de Control > Dispositivos
4. Ejecutar testServicioWin32() para diagnóstico
```

## 📁 Archivos del Sistema

```
ILSAN_MES/
├── print_service.py                    # Servicio principal
├── print_requirements.txt              # Dependencias
├── start_print_service.bat            # Instalación automática
├── install_print_service_manual.bat   # Instalación manual
├── run_print_service.bat              # Solo ejecutar
├── print_service.log                  # Log del servicio (generado)
└── app/templates/Control de material/
    └── Control de material de almacen.html  # Frontend
```

### Descripción de Scripts

| Archivo | Propósito | Uso |
|---------|-----------|-----|
| `start_print_service.bat` | Instalación automática completa | Primera vez |
| `install_print_service_manual.bat` | Instalación paso a paso | Si hay problemas |
| `run_print_service.bat` | Solo ejecutar servicio | Uso diario |
| `print_service.py` | Servicio de impresión | Ejecutado por scripts |

## 🔒 Seguridad

- El servicio solo acepta conexiones desde localhost por defecto
- Para acceso remoto, modificar `host="0.0.0.0"` en print_service.py
- Los comandos ZPL se validan antes de enviar a impresora

## 🚀 Ventajas del Sistema

✅ **Impresión Totalmente Automática** - Sin diálogos ni confirmaciones
✅ **Detección Automática** - Encuentra la ZT230 automáticamente  
✅ **Robusto** - Múltiples métodos de fallback
✅ **Logs Detallados** - Para diagnóstico y debug
✅ **Fácil Instalación** - Un solo comando para iniciar
✅ **Compatible** - Funciona con cualquier Zebra ZPL

## 📞 Soporte

Para problemas o dudas:
1. Revisar logs en `print_service.log`
2. Ejecutar `testServicioWin32()` para diagnóstico
3. Verificar que todos los prerequisitos estén instalados

---
**Versión:** 1.0  
**Compatibilidad:** Windows 10/11, Python 3.8+, Zebra ZT230  
**Licencia:** Uso interno ILSAN Electronics
