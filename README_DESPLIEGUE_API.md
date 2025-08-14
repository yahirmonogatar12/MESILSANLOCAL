# INSTRUCCIONES DE DESPLIEGUE - API MES PARA ANDROID

##  ARCHIVOS GENERADOS

1. **mysql-proxy.php** - API principal (actualizada con credenciales correctas)
2. **mysql-proxy-seguro.php** - Versión con validaciones de seguridad adicionales
3. **test-api.html** - Página web para probar la API
4. **AndroidAPIHelper.java** - Clase helper para Android
5. **MainActivity.java** - Ejemplo de Activity Android

##  PASOS PARA DESPLEGAR

### PASO 1: Subir archivos al servidor web
`
1. Accede a tu panel de hosting (cPanel, Plesk, etc.)
2. Ve al administrador de archivos
3. Crea carpeta: public_html/api/
4. Sube el archivo: mysql-proxy.php (o mysql-proxy-seguro.php)
5. Sube test-api.html para pruebas
`

### PASO 2: Configurar permisos
`
- Archivo PHP: 644 (rw-r--r--)
- Carpeta api: 755 (rwxr-xr-x)
`

### PASO 3: Probar la API
`
1. Abre: https://tu-sitio.com/test-api.html
2. Haz clic en "Probar Conexión"
3. Si funciona, prueba "Obtener Materiales"
4. Verifica que los datos se muestren correctamente
`

##  CONFIGURACIÓN EN ANDROID

### PASO 4: Agregar permisos en AndroidManifest.xml
`xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
`

### PASO 5: Configurar red (para pruebas locales)
En AndroidManifest.xml, dentro de <application>:
`xml
android:usesCleartextTraffic="true"
android:networkSecurityConfig="@xml/network_security_config"
`

### PASO 6: Integrar código Android
`
1. Copia AndroidAPIHelper.java a tu proyecto
2. Actualiza la URL en AndroidAPIHelper:
   private static final String API_URL = "https://tu-sitio.com/api/mysql-proxy.php";
3. Usa los ejemplos de MainActivity.java
`

##  CONFIGURACIÓN DE SEGURIDAD (OPCIONAL)

### Para usar API Key:
1. En mysql-proxy-seguro.php, descomenta líneas de API Key
2. Cambia 'tu_api_key_secreta_aqui' por tu clave
3. En Android, agrega header:
`java
conn.setRequestProperty("Authorization", "Bearer tu_api_key_secreta_aqui");
`

##  PRUEBAS LOCALES

### Probar con curl:
`ash
curl -X POST https://tu-sitio.com/api/mysql-proxy.php \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT COUNT(*) as total FROM materiales"}'
`

### Respuesta esperada:
`json
{
  "success": true,
  "data": [{"total": 262}],
  "count": 1
}
`

##  CONSULTAS DISPONIBLES PARA ANDROID

### Materiales:
`sql
SELECT * FROM materiales WHERE codigo_material LIKE '%texto%'
SELECT * FROM materiales LIMIT 50
`

### Inventarios:
`sql
SELECT * FROM InventarioRollosSMD WHERE cantidad > 0
SELECT * FROM InventarioRollosIMD WHERE cantidad > 0  
SELECT * FROM InventarioRollosMAIN WHERE cantidad > 0
`

### Movimientos:
`sql
SELECT * FROM movimientos_inventario WHERE fecha >= CURDATE()
INSERT INTO movimientos_inventario (numero_rollo, accion, cantidad, usuario, fecha) VALUES (?, ?, ?, ?, NOW())
`

### Control de Calidad:
`sql
SELECT * FROM control_calidad WHERE fecha >= CURDATE()
`

##  CONSIDERACIONES IMPORTANTES

1. **SSL/HTTPS**: Usar siempre HTTPS en producción
2. **Rate Limiting**: Implementar límites de consultas por IP
3. **Validación**: Validar todas las entradas en Android y PHP
4. **Logs**: Activar logs de errores en el servidor
5. **Backup**: Hacer respaldo antes de cualquier cambio

##  TROUBLESHOOTING

### Error de conexión:
- Verificar credenciales de base de datos
- Revisar que el puerto 11550 esté accesible
- Comprobar SSL en servidor MySQL

### Error 404:
- Verificar que la URL de la API sea correcta
- Comprobar permisos de archivo
- Revisar configuración del servidor web

### Error de CORS:
- Verificar headers CORS en el PHP
- Para desarrollo, usar proxy o deshabilitar CORS en navegador

##  URLs FINALES

- **API Endpoint**: https://tu-sitio.com/api/mysql-proxy.php
- **Página de pruebas**: https://tu-sitio.com/test-api.html
- **Documentación**: Este archivo README

Tu API está lista para usarse con tu aplicación Android!
