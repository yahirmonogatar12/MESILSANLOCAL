# Guía de Despliegue - API MySQL Proxy para Android

## 1. ARCHIVOS PARA SUBIR AL SERVIDOR WEB

### Archivo Principal:
- mysql-proxy.php (archivo principal de la API)

### Estructura de carpetas recomendada en tu servidor:
`
tu-sitio-web.com/
 api/
    mysql-proxy.php
 index.html (tu sitio principal)
`

## 2. CONFIGURACIÓN DEL SERVIDOR

### Requisitos del hosting:
- PHP 7.4 o superior
- Extensión PDO MySQL habilitada
- SSL habilitado (recomendado)
- Soporte para CORS headers

### URL de la API desplegada:
https://tu-sitio-web.com/api/mysql-proxy.php

## 3. PRUEBAS DE LA API

### Prueba básica con curl:
`ash
curl -X POST https://tu-sitio-web.com/api/mysql-proxy.php \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT COUNT(*) as total FROM materiales"}'
`

### Respuesta esperada:
`json
{
  "success": true,
  "data": [{"total": 262}]
}
`

## 4. CONFIGURACIÓN EN ANDROID

### URL base para tu app Android:
`java
private static final String API_URL = "https://tu-sitio-web.com/api/mysql-proxy.php";
`

### Ejemplo de uso en Android (Java):
`java
// POST request con JSON
String jsonInputString = "{"sql": "SELECT * FROM materiales LIMIT 10"}";

URL url = new URL(API_URL);
HttpURLConnection conn = (HttpURLConnection) url.openConnection();
conn.setRequestMethod("POST");
conn.setRequestProperty("Content-Type", "application/json");
conn.setDoOutput(true);

try(OutputStream os = conn.getOutputStream()) {
    byte[] input = jsonInputString.getBytes("utf-8");
    os.write(input, 0, input.length);
}

// Leer respuesta...
`

## 5. SEGURIDAD RECOMENDADA

### A. Validación de consultas (agregar al PHP):
- Lista blanca de tablas permitidas
- Validación de tipos de consulta
- Límites de registros por consulta

### B. Autenticación:
- Token de API
- Rate limiting
- IP whitelist (opcional)

### C. HTTPS obligatorio:
- Certificado SSL instalado
- Redirect HTTP  HTTPS

## 6. MONITOREO

### Logs del servidor:
- Activar logs de PHP
- Monitorear errores de conexión
- Registrar consultas problemáticas

### Métricas importantes:
- Tiempo de respuesta
- Número de consultas por minuto
- Errores de conexión a BD
