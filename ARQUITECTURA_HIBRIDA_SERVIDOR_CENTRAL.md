# 🏭 ARQUITECTURA HÍBRIDA - SERVIDOR CENTRAL + IMPRESIÓN LOCAL

## 🎯 **CONFIGURACIÓN RECOMENDADA**

```
🌐 SERVIDOR CENTRAL (192.168.0.211):
   ├── 📱 Aplicación Flask (puerto 5000)
   ├── 📄 Base de Datos (centralizada)
   └── 🌍 Acceso web desde cualquier dispositivo

📍 PC ESTACIÓN #1 (192.168.0.212):
   ├── 🖨️ Servicio Impresión Local (localhost:5002)
   └── 🖨️ Zebra ZT230 #1 (USB)

📍 PC ESTACIÓN #2 (192.168.0.213):
   ├── 🖨️ Servicio Impresión Local (localhost:5002)
   └── 🖨️ Zebra ZT230 #2 (USB)

📍 PC ESTACIÓN #3 (192.168.0.214):
   ├── 🖨️ Servicio Impresión Local (localhost:5002)
   └── 🖨️ Zebra ZT230 #3 (USB)
```

---

## 🔄 **FLUJO DE TRABAJO**

### **Acceso Universal:**
```
📱 Tablet/Celular/PC ──→ 🌐 http://192.168.0.211:5000
                          │
                          ├── 📄 Base de datos centralizada
                          ├── 🔐 Autenticación única
                          └── 📋 Interfaz web unificada
```

### **Proceso de Registro de Material:**
```
1. 👤 Usuario accede desde cualquier dispositivo
   ↓
2. 🌐 Interfaz web centralizada (servidor)
   ↓
3. 📝 Registra material en BD centralizada
   ↓
4. 🎯 Sistema detecta desde qué PC/área se registró
   ↓
5. 📡 Envía comando de impresión a servicio local
   ↓
6. 🖨️ Imprime en Zebra local de esa PC/área
```

---

## ✅ **VENTAJAS DE ESTA ARQUITECTURA**

### 🌐 **Centralización (Aplicación):**
- ✅ Un solo punto de acceso web
- ✅ Base de datos centralizada
- ✅ Mantenimiento simplificado
- ✅ Actualizaciones centralizadas
- ✅ Autenticación unificada

### 🖨️ **Distribución (Impresión):**
- ✅ Impresión instantánea (sin latencia)
- ✅ Sin colas compartidas
- ✅ Sin conflictos de red
- ✅ Cada área independiente
- ✅ Escalabilidad ilimitada

---

## 🔧 **CONFIGURACIÓN TÉCNICA**

### **Servidor Central:**
```python
# run.py en servidor
app.run(host='192.168.0.211', port=5000)
```

### **Cada PC con Impresora:**
```python
# print_service.py en cada PC
app.run(host='localhost', port=5002)  # Solo local
```

### **Frontend (HTML):**
```javascript
// Configuración híbrida
service_url: 'http://localhost:5002'  // Impresión local
web_url: 'http://192.168.0.211:5000'  // Aplicación central
```

---

## 📋 **INSTALACIÓN POR TIPO DE EQUIPO**

### **🌐 SERVIDOR CENTRAL (Solo 1):**
```bash
1. Instalar proyecto completo
2. Configurar base de datos
3. Ejecutar: python run.py
4. Accesible desde: http://192.168.0.211:5000
```

### **🖨️ PC CON IMPRESORA (Múltiples):**
```bash
1. Conectar Zebra ZT230 por USB
2. Copiar archivos del proyecto
3. Ejecutar: instalacion_completa_nueva_pc.bat
4. Solo ejecuta servicio de impresión local
```

---

## 🎯 **SELECCIÓN DE IMPRESORA**

### **Opción A: Detección Automática por IP**
```javascript
// El sistema detecta desde qué PC se accede
// y dirige la impresión a esa Zebra local
function detectarPCLocal() {
    const clientIP = getClientIP();
    return `http://${clientIP}:5002`;
}
```

### **Opción B: Selector Manual de Área**
```html
<!-- En la interfaz web -->
<select id="area_impresion">
    <option value="http://192.168.0.212:5002">Área 1</option>
    <option value="http://192.168.0.213:5002">Área 2</option>
    <option value="http://192.168.0.214:5002">Área 3</option>
</select>
```

### **Opción C: Configuración por Usuario**
```javascript
// Cada usuario configura su área preferida
localStorage.setItem('area_preferida', 'http://192.168.0.212:5002');
```

---

## 🚀 **ESCALABILIDAD**

### **Agregar nueva PC/Área:**
```bash
1. Conectar nueva Zebra ZT230
2. Instalar servicio local: instalacion_completa_nueva_pc.bat
3. Agregar área al selector (opcional)
4. ¡Listo! Nueva estación funcionando
```

### **Sin límites:**
```
✅ Servidor central: Maneja ilimitados clientes
✅ Base de datos: Centralizada y compartida
✅ Impresoras: Una por área/PC sin conflictos
✅ Acceso: Desde cualquier dispositivo
```

---

## 🔄 **FLUJO COMPLETO DE EJEMPLO**

```
1. 📱 Operario con tablet accede a: http://192.168.0.211:5000
2. 🔐 Se autentica en sistema centralizado
3. 📝 Registra material recibido
4. 🎯 Selecciona "Área 2" para impresión
5. 💾 Datos se guardan en BD centralizada
6. 📡 Sistema envía comando a: http://192.168.0.213:5002
7. 🖨️ Zebra ZT230 del Área 2 imprime automáticamente
8. ✅ Proceso completado - material registrado e impreso
```

---

## 📊 **RESUMEN DE PUERTOS**

| Servicio | Puerto | Scope | Función |
|----------|--------|-------|---------|
| Aplicación Web | 5000 | Red | Interfaz central |
| Impresión PC #1 | 5002 | Local | Zebra local |
| Impresión PC #2 | 5002 | Local | Zebra local |
| Impresión PC #N | 5002 | Local | Zebra local |

**¡Esta arquitectura combina lo mejor de ambos mundos!** 🎉
