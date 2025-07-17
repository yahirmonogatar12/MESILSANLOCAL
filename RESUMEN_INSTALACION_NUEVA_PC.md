# 🚀 INSTALACIÓN RÁPIDA - NUEVA COMPUTADORA

## ⚡ **MÉTODO ULTRA RÁPIDO (Recomendado)**

### 1. **Prerequisitos (5 minutos):**
```
✅ Conectar Zebra ZT230 por USB
✅ Instalar Python 3.8+ con "Add to PATH" marcado
✅ Copiar TODA la carpeta del proyecto a la nueva PC
```

### 2. **Instalación Automática (1 clic):**
```
📁 Ir a la carpeta del proyecto
🖱️  Doble clic en: instalacion_completa_nueva_pc.bat
⏱️  Esperar 2-3 minutos
✅ ¡Listo!
```

---

## 🛠️ **MÉTODO MANUAL (Si el automático falla)**

### 1. **Configurar IP:**
```bash
# Doble clic en:
configurar_ip_nueva_computadora.bat
```

### 2. **Instalar Servicio:**
```bash
# Doble clic en:
start_print_service_local.bat
```

### 3. **Iniciar Aplicación:**
```bash
# En CMD ejecutar:
python run.py
```

---

## 🧪 **VERIFICACIÓN (2 minutos)**

### Test en navegador:
```javascript
// F12 → Console → Ejecutar:
testServicioWin32()

// Resultado esperado:
✅ Impresora Zebra detectada: ZDesigner ZT230-300dpi ZPL
```

---

## 📋 **ARCHIVOS CLAVE PARA NUEVA PC**

```
📁 Copiar estos archivos:
├── instalacion_completa_nueva_pc.bat    ⭐ USAR ESTE
├── configurar_ip_nueva_computadora.bat  📄 Alternativo
├── start_print_service_local.bat        📄 Solo servicio
├── print_service.py                     📄 Código principal
├── print_requirements.txt               📄 Dependencias
├── run.py                              📄 App web
└── app\templates\Control de material\
    └── Control de material de almacen.html
```

---

## 🎯 **RESULTADO FINAL**

```
🌐 Aplicación Flask: CENTRALIZADA en servidor (ej: 192.168.0.211:5000)
🖨️  Servicio de impresión: LOCAL en cada PC (localhost:5002)
🏷️  Impresión automática sin confirmaciones en Zebra local
📱 Acceso: Desde cualquier dispositivo al servidor central
🖨️  Impresión: Dirigida a la Zebra local de cada PC
```

---

## 🏭 **VENTAJAS DE CONFIGURACIÓN HÍBRIDA**

- ✅ **Aplicación centralizada** (un solo punto de acceso)
- ✅ **Impresión distribuida** (sin latencia ni conflictos)
- ✅ **Acceso universal** (desde cualquier dispositivo)
- ✅ **Base de datos única** (datos centralizados)
- ✅ **Zebras locales** (máximo rendimiento de impresión)

---

## 📞 **SI ALGO FALLA**

1. **Leer:** `GUIA_INSTALACION_NUEVA_COMPUTADORA.md`
2. **Verificar:** Impresora conectada y Python instalado
3. **Ejecutar:** Los scripts paso a paso manualmente

---

## ⚠️ **IMPORTANTE - CONFIGURACIÓN HÍBRIDA**

- **🌐 Aplicación Flask:** Centralizada en un servidor (ej: 192.168.0.211:5000)
- **🖨️ Servicio de impresión:** Local en cada PC (localhost:5002)
- **🖨️ Zebra ZT230:** Una por PC, conectada por USB localmente
- **📄 Base de datos:** Centralizada en red (datos compartidos)
- **⚡ Impresión:** Dirigida automáticamente a la Zebra local de cada PC
