# 📸 Instrucciones para Agregar las Imágenes

## Imágenes Requeridas

Por favor, guarda las siguientes imágenes en esta carpeta:

### 1. Logo ILSAN (PNG)
- **Nombre del archivo:** `ilsan-logo.png`
- **Descripción:** Logo circular verde de ILSAN Electronics
- **Uso:** 
  - Navbar superior (45x45px)
  - Hero banner (70x70px)
- **Formato:** PNG con fondo transparente

### 2. Vista Aérea de Instalaciones (WebP/JPG)
- **Nombre del archivo:** `ilsan-facility.jpg` o `ilsan-facility.webp`
- **Descripción:** Fotografía aérea de las instalaciones de ILSAN
- **Uso:** Fondo del hero banner
- **Tamaño recomendado:** 1920x1080px o superior
- **Formato:** WebP (preferido) o JPG

## 🔧 Cómo Agregar las Imágenes

### Opción 1: Arrastra y Suelta (Más Fácil)
1. Abre esta carpeta en el explorador de archivos de Windows:
   ```
   c:\Users\jesus\OneDrive\Documents\Desarrollo\Defect MS\MESILSANLOCAL\app\static\images
   ```
2. Arrastra las imágenes desde donde las tengas guardadas
3. Asegúrate de nombrarlas correctamente:
   - Logo → `ilsan-logo.png`
   - Instalaciones → `ilsan-facility.jpg` (o .webp)

### Opción 2: Copiar desde PowerShell
```powershell
# Desde la ubicación donde tengas las imágenes:
Copy-Item "ruta\a\tu\logo.png" "c:\Users\jesus\OneDrive\Documents\Desarrollo\Defect MS\MESILSANLOCAL\app\static\images\ilsan-logo.png"
Copy-Item "ruta\a\tu\facility.webp" "c:\Users\jesus\OneDrive\Documents\Desarrollo\Defect MS\MESILSANLOCAL\app\static\images\ilsan-facility.jpg"
```

##  Verificación

Una vez agregadas las imágenes, refresca el navegador (F5) en:
- http://127.0.0.1:5000/inicio

Deberías ver:
-  Logo circular verde en la navbar superior
-  Logo en el hero banner junto a "ILSAN Electronics"
-  Imagen de fondo en el hero banner (opcional)

## 🎨 Optimización Opcional

Si las imágenes son muy grandes, puedes optimizarlas:

**Para el logo:**
- Tamaño: 200x200px máximo
- Formato: PNG con transparencia
- Peso: <50KB

**Para la vista aérea:**
- Tamaño: 1920x1080px
- Formato: WebP o JPG
- Calidad: 85%
- Peso: <500KB

---

**Estado Actual:**
- [ ] Logo PNG agregado
- [ ] Imagen de instalaciones agregada
- [ ] Navegador refrescado

**Última actualización:** 2025-10-16
