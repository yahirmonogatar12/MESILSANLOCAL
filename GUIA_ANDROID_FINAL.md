# 🚀 RUTAS API PARA ANDROID - CONFIGURACIÓN SIMPLE

## ✅ LO QUE ESTÁ LISTO

### 📍 Rutas Disponibles (SIN LOGIN REQUERIDO)

#### 1. API MySQL Simple
- **URL**: `http://127.0.0.1:5000/api/mysql`
- **Método**: POST
- **Función**: Ejecuta consultas SQL directamente a tu base de datos MySQL
- **Credenciales**: Ya configuradas automáticamente

**Ejemplo de uso:**
```json
POST http://127.0.0.1:5000/api/mysql
Content-Type: application/json

{
  "sql": "SELECT * FROM materiales LIMIT 10"
}
```

#### 2. Archivo PHP Original
- **URL**: `http://127.0.0.1:5000/mysql-proxy.php`
- **Método**: GET/POST
- **Función**: Accede a tu archivo PHP original
- **Ubicación**: `app/php/mysql-proxy.php`

### 🔧 Credenciales de Base de Datos (Configuradas Automáticamente)
```
Database: db_rrpq0erbdujn
Username: db_rrpq0erbdujn
Password: 5fUNbSRcPP3LN9K2I33Pr0ge
Host: up-de-fra1-mysql-1.db.run-on-seenode.com
Port: 11550
```

## 📱 PARA TU APLICACIÓN ANDROID

### URLs para usar en tu App:
- **Desarrollo local**: `http://127.0.0.1:5000/api/mysql`
- **Red local**: `http://192.168.0.211:5000/api/mysql`

### Formato de respuesta:
```json
{
  "success": true,
  "data": [
    {
      "codigo_material": "M001",
      "numero_parte": "CAP-001",
      "especificacion_material": "10uF 16V"
    }
  ],
  "count": 1
}
```

## 🧪 CÓMO PROBAR

1. **Ejecuta tu servidor Flask**: `python run.py`
2. **Abre en navegador**: `test-android-simple.html`
3. **Prueba los botones** para verificar funcionamiento
4. **Usa las URLs** en tu aplicación Android

## 🔒 SEGURIDAD

- ✅ Headers CORS configurados para acceso desde Android
- ✅ Conexión directa a base de datos MySQL configurada
- ✅ Sin autenticación requerida para APIs de Android
- ✅ Respuestas en formato JSON estándar

## 📋 EJEMPLO CÓDIGO ANDROID

```java
// URL de tu API
String apiUrl = "http://192.168.0.211:5000/api/mysql";

// JSON de la consulta
JSONObject queryData = new JSONObject();
queryData.put("sql", "SELECT * FROM materiales WHERE numero_parte LIKE '%CAP%'");

// Realizar petición HTTP POST
// ... (tu código de HTTP request)
```

## ✅ ESTADO ACTUAL

- ✅ Servidor Flask funcionando en puerto 5000
- ✅ Conexión a MySQL establecida
- ✅ Rutas API creadas y probadas
- ✅ Headers CORS configurados
- ✅ Sin login requerido para Android

**¡Tu sistema MES está listo para la aplicación Android!**
