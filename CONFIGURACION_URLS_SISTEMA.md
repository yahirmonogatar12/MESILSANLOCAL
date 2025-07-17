# 🌐 CONFIGURACIÓN DE URLs DEL SISTEMA

## 🎯 **CONFIGURACIÓN ACTUAL**

El sistema ahora está preparagetPrintServiceUrl('/print')               // ✅ Siempre localhost:5003o para funcionar con **cualquier servidor o dominio**:

### **📁 ARCHIVOS MODIFICADOS:**

1. **`Control de material de almacen.html`**
   - ✅ Configuración centralizada de URLs
   - ✅ Separación entre servidor principal y servicio de impresión
   - ✅ Funciones helper para construcción de URLs

2. **`configurar_urls_sistema.bat`**
   - ✅ Script automático para cambiar URLs
   - ✅ Múltiples opciones predefinidas
   - ✅ Backup automático antes de cambios

---

## 🔧 **CONFIGURACIÓN ACTUAL**

```javascript
// En Control de material de almacen.html:
let configuracion = {
    // Servidor principal (aplicación web) - CAMBIAR SEGÚN NECESIDAD
    server_url: 'http://localhost:5000',        // Para desarrollo local
    // server_url: 'https://mi-dominio.com',    // Para dominio web
    // server_url: 'http://192.168.0.211:5000', // Para servidor específico
    
    // Servicio de impresión (SIEMPRE local en cada PC)
    service_url: 'http://localhost:5003'
};
```

---

## 🚀 **FORMAS DE CAMBIAR LA URL**

### **Opción 1: Script Automático (RECOMENDADO)**

```bash
# Ejecutar:
configurar_urls_sistema.bat

# Seleccionar opción:
1. Desarrollo Local    → http://localhost:5000
2. IP Específica       → http://192.168.x.x:5000  
3. Dominio Web         → https://mi-dominio.com
4. Servidor Externo    → http://servidor:puerto
5. Configuración Manual
```

### **Opción 2: Edición Manual**

1. **Abrir:** `app\templates\Control de material\Control de material de almacen.html`
2. **Buscar:** línea `server_url: 'http://localhost:5000'`
3. **Cambiar** por la nueva URL
4. **Guardar** archivo

---

## 🌐 **EJEMPLOS DE CONFIGURACIÓN**

### **Desarrollo Local:**
```javascript
server_url: 'http://localhost:5000'
```

### **Servidor en Red Local:**
```javascript
server_url: 'http://192.168.0.211:5000'
```

### **Dominio Web (Producción):**
```javascript
server_url: 'https://sistema-mes.miempresa.com'
```

### **Servidor con Puerto Personalizado:**
```javascript
server_url: 'http://servidor-central:8080'
```

### **Subdirectorio en Dominio:**
```javascript
server_url: 'https://miempresa.com/sistema-mes'
```

---

## ✅ **FUNCIONAMIENTO AUTOMÁTICO**

### **URLs Relativas (Automáticas):**
```javascript
// Estas se adaptan automáticamente al dominio:
fetch('/consultar_control_almacen')        // ✅ Funciona en cualquier dominio
fetch('/guardar_control_almacen')          // ✅ Funciona en cualquier dominio
fetch('/obtener_codigos_material')         // ✅ Funciona en cualquier dominio
```

### **URLs Absolutas (Específicas):**
```javascript
// Estas usan la configuración específica:
fetch(configuracion.server_url + '/')      // ✅ Usa URL configurada
getPrintServiceUrl('/print')               // ✅ Siempre localhost:5002
```

---

## 🎯 **CASOS DE USO COMUNES**

### **1. Desarrollo Local:**
- Desarrollar en tu PC
- URL: `http://localhost:5000`
- **Usar:** Opción 1 del script

### **2. Servidor en Oficina:**
- Servidor dedicado en red local
- URL: `http://192.168.0.211:5000`
- **Usar:** Opción 2 del script

### **3. Hosting Web:**
- Servidor en internet con dominio
- URL: `https://sistema-mes.miempresa.com`
- **Usar:** Opción 3 del script

### **4. Servidor Empresarial:**
- Servidor interno con nombre/puerto específico
- URL: `http://servidor-mes:8080`
- **Usar:** Opción 4 del script

---

## 🔄 **PROCESO DE MIGRACIÓN**

### **De Desarrollo a Producción:**

1. **Configurar servidor de producción**
2. **Subir archivos** al servidor/hosting
3. **Ejecutar:** `configurar_urls_sistema.bat`
4. **Seleccionar** configuración de producción
5. **Probar** acceso desde dispositivos

### **Cambio de Servidor:**

1. **Ejecutar:** `configurar_urls_sistema.bat`
2. **Seleccionar** nueva URL
3. **Reiniciar** servicio Flask
4. **Actualizar** accesos directos/favoritos

---

## 🖨️ **IMPRESIÓN (NO CAMBIA)**

El servicio de impresión **SIEMPRE** usa `localhost:5003` porque:

- ✅ Cada PC tiene su propia Zebra
- ✅ Impresión directa sin latencia
- ✅ Sin conflictos entre PCs
- ✅ Funciona aunque el servidor principal esté remoto

---

## 🔧 **TROUBLESHOOTING**

### **Si no funciona después del cambio:**

1. **Verificar URL:** ¿Es accesible desde navegador?
2. **Revisar consola:** F12 → Console (errores de red)
3. **Comprobar CORS:** ¿El servidor permite peticiones cross-origin?
4. **Restaurar backup:** Usar archivo `.backup` si hay problemas

### **Errores comunes:**

- **CORS:** Configurar `Access-Control-Allow-Origin` en servidor
- **HTTPS mixto:** No mezclar HTTP/HTTPS en misma página
- **Puerto bloqueado:** Verificar firewall/antivirus
- **URL incorrecta:** Revisar protocolo (http/https) y puerto

---

## 💾 **BACKUPS AUTOMÁTICOS**

Cada vez que uses `configurar_urls_sistema.bat` se crea un backup:

```
Control de material de almacen.html.backup-20250716
```

Para restaurar:
```bash
copy "archivo.backup-FECHA" "Control de material de almacen.html"
```

---

## 🎉 **¡LISTO PARA CUALQUIER DESPLIEGUE!**

Tu sistema ahora puede funcionar en:
- ✅ Desarrollo local
- ✅ Servidores de red
- ✅ Hosting web
- ✅ Dominios personalizados
- ✅ Configuraciones empresariales

**¡Solo ejecuta el script configurador y selecciona tu opción!** 🚀
