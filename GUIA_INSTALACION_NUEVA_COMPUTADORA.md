# 🖨️ Guía de Instalación - Sistema de Impresión Automática
## Para instalar en una computadora nueva

---

## 📋 **PREREQUISITOS**

### 1. **Hardware Requerido:**
- ✅ Computadora con Windows 10/11
- ✅ Impresora Zebra ZT230 conectada por USB
- ✅ Cable USB para conectar la impresora
- ✅ Conexión a la red (para acceder a los archivos del proyecto)

### 2. **Software Requerido:**
- ✅ Python 3.8+ (se instala en el proceso)
- ✅ Navegador web moderno (Chrome, Firefox, Edge)
- ✅ Acceso de administrador (para instalar drivers)

---

## 🚀 **PASOS DE INSTALACIÓN**

### **PASO 1: Configurar la Impresora Zebra ZT230**

1. **Conectar la impresora:**
   ```
   - Conecte la Zebra ZT230 por USB a la computadora
   - Encienda la impresora
   - Espere a que Windows la reconozca
   ```

2. **Instalar drivers (si es necesario):**
   ```
   - Vaya a Panel de Control > Dispositivos e Impresoras
   - Verifique que aparezca como "ZDesigner ZT230-300dpi ZPL"
   - Si no aparece, descargue drivers desde: zebra.com
   ```

3. **Probar impresión básica:**
   ```
   - Clic derecho en la impresora > Propiedades
   - Imprimir página de prueba
   - Verificar que imprime correctamente
   ```

### **PASO 2: Instalar Python**

1. **Descargar Python:**
   ```
   - Vaya a: https://python.org/downloads/
   - Descargue la versión más reciente (3.8+)
   ```

2. **Instalar Python:**
   ```
   ⚠️  IMPORTANTE: Durante la instalación:
   ✅ Marque "Add Python to PATH"
   ✅ Marque "Install for all users" (si tiene permisos)
   ```

3. **Verificar instalación:**
   ```
   - Abra CMD (Símbolo del sistema)
   - Ejecute: python --version
   - Debe mostrar: Python 3.x.x
   ```

### **PASO 3: Obtener los Archivos del Sistema**

1. **Copiar archivos desde la red:**
   ```
   - Navegue a: \\192.168.1.230\qa\ILSAN_MES\ISEMM_MES
   - Copie TODA la carpeta a su computadora local
   - Ubicación recomendada: C:\ILSAN_MES\
   ```

2. **Archivos principales necesarios:**
   ```
   📁 C:\ILSAN_MES\
   ├── print_service.py              ⭐ SERVICIO PRINCIPAL
   ├── print_requirements.txt        ⭐ DEPENDENCIAS
   ├── start_print_service_local.bat ⭐ INSTALADOR RECOMENDADO
   ├── start_print_service.bat       📄 Instalador alternativo
   ├── run_print_service.bat         📄 Para uso diario
   └── app\templates\Control de material\
       └── Control de material de almacen.html ⭐ PÁGINA WEB
   ```

### **PASO 4: Instalar el Servicio de Impresión**

1. **Ejecutar instalador automático:**
   ```
   - Navegue a la carpeta copiada: C:\ILSAN_MES\
   - Doble clic en: start_print_service_local.bat
   - Siga las instrucciones en pantalla
   ```

2. **Verificar instalación exitosa:**
   ```
   Debe ver:
   🚀 Ejecutándose en:
      http://localhost:5002
      http://127.0.0.1:5002
      http://192.168.0.211:5002
   
   🖨️ Impresora Zebra detectada: ZDesigner ZT230-300dpi ZPL
   ```

### **PASO 5: Configurar la Aplicación Web**

1. **Actualizar URLs en el código:**
   ```
   - Abra: app\templates\Control de material\Control de material de almacen.html
   - Busque todas las líneas que contengan: "http://192.168.0.211:5002"
   - Cambie la IP por la IP de la nueva computadora
   ```

2. **Encontrar la IP de la nueva computadora:**
   ```
   - Abra CMD
   - Ejecute: ipconfig
   - Busque "Dirección IPv4": 192.168.x.x
   - Use esa IP en lugar de 192.168.0.211
   ```

### **PASO 6: Configurar la Aplicación Principal (Flask)**

1. **Actualizar archivo run.py:**
   ```python
   # Edite: run.py
   # Cambie la línea:
   app.run(host='192.168.0.211', port=5001, debug=True)
   
   # Por (usando la IP de la nueva computadora):
   app.run(host='192.168.x.x', port=5001, debug=True)
   ```

2. **Iniciar aplicación principal:**
   ```
   - Abra CMD en la carpeta del proyecto
   - Ejecute: python run.py
   - Debe mostrar: Running on http://192.168.x.x:5001
   ```

---

## 🔧 **CONFIGURACIÓN DE MÚLTIPLES COMPUTADORAS**

### **Opción A: Cada computadora con su propio servicio**
```
Computadora 1: 192.168.0.211:5002 (original)
Computadora 2: 192.168.0.212:5002 (nueva)
Computadora 3: 192.168.0.213:5002 (otra nueva)
```

### **Opción B: Servicio centralizado**
```
Servidor central: 192.168.0.211:5002
Todas las computadoras apuntan al mismo servicio
```

---

## 🧪 **PRUEBAS Y VERIFICACIÓN**

### **Test 1: Verificar Servicio de Impresión**
```javascript
// En la consola del navegador (F12):
testServicioWin32()

// Resultado esperado:
✅ http://192.168.x.x:5002 - JSON válido
🖨️ Impresora Zebra detectada: ZDesigner ZT230-300dpi ZPL
```

### **Test 2: Prueba de Impresión Directa**
```javascript
// En la consola del navegador:
testImpresionDirecta('TEST123,20250716001')

// Resultado esperado:
✅ Impresión enviada correctamente
📄 La impresora debe imprimir una etiqueta de prueba
```

### **Test 3: Prueba Completa de Flujo**
```
1. Acceda a la página de control de material
2. Escaneé o ingrese un código de material
3. Complete los campos del formulario
4. Haga clic en "Guardar"
5. Verifique que se imprima automáticamente la etiqueta
```

---

## 📞 **SOLUCIÓN DE PROBLEMAS COMUNES**

### **Error: "Python no está instalado"**
```
Solución:
1. Reinstale Python desde python.org
2. Marque "Add Python to PATH" durante instalación
3. Reinicie la computadora
4. Ejecute el script nuevamente
```

### **Error: "No se encuentra la impresora"**
```
Solución:
1. Verifique conexión USB de la impresora
2. Reinstale drivers de Zebra
3. Verifique en Panel de Control > Dispositivos
4. Ejecute testServicioWin32() para diagnóstico
```

### **Error: "CORS" o "NetworkError"**
```
Solución:
1. Verifique que el servicio esté ejecutándose
2. Confirme que use puerto 5002 (no 5000)
3. Actualice las IPs en el código HTML
4. Reinicie el servicio de impresión
```

### **Error: "ModuleNotFoundError"**
```
Solución:
1. Ejecute: pip install flask flask-cors pywin32
2. O use start_print_service_local.bat que instala automáticamente
```

---

## 🎯 **CHECKLIST DE INSTALACIÓN COMPLETA**

- [ ] Impresora Zebra ZT230 conectada y funcionando
- [ ] Python 3.8+ instalado con PATH configurado
- [ ] Archivos del proyecto copiados localmente
- [ ] Servicio de impresión ejecutándose en puerto 5002
- [ ] IPs actualizadas en el código HTML
- [ ] Aplicación principal ejecutándose en puerto 5001
- [ ] Test de conectividad pasando exitosamente
- [ ] Test de impresión directa funcionando
- [ ] Impresión automática al guardar material

---

## 📝 **ARCHIVOS DE CONFIGURACIÓN RÁPIDA**

### **Para nueva computadora con IP 192.168.0.220:**

**1. Actualizar HTML (buscar y reemplazar):**
```
Buscar: http://192.168.0.211:5002
Reemplazar: http://192.168.0.220:5002
```

**2. Actualizar run.py:**
```python
app.run(host='192.168.0.220', port=5001, debug=True)
```

**3. Ejecutar instalación:**
```bash
start_print_service_local.bat
```

---

## 🚀 **USO DIARIO**

Una vez instalado correctamente:

1. **Iniciar servicios:**
   ```
   - Doble clic: run_print_service.bat
   - Ejecutar: python run.py
   ```

2. **Acceder al sistema:**
   ```
   - Navegador: http://192.168.x.x:5001
   - Usar normalmente el control de material
   ```

3. **Apagar sistema:**
   ```
   - Ctrl+C en ambas ventanas de CMD
   - Cerrar navegador
   ```

---

¿Necesita ayuda específica con algún paso? 📞
