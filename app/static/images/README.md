# Imágenes para Landing Page

## Instrucciones

Por favor guarda las siguientes imágenes en esta carpeta:

### 1. Logo ILSAN
- **Archivo:** `ilsan-logo.png`
- **Descripción:** Logo corporativo de ILSAN Electronics (imagen circular verde)
- **Uso:** Banner principal del hero section
- **Tamaño recomendado:** 180px de ancho (se ajustará automáticamente)

### 2. Vista Aérea de Instalaciones
- **Archivo:** `ilsan-facility.jpg`
- **Descripción:** Fotografía aérea de las instalaciones de ILSAN
- **Uso:** Imagen de fondo del hero banner
- **Tamaño recomendado:** 1920x1080px o superior para mejor calidad

## Ubicación de las imágenes
```
MESILSANLOCAL/
└── app/
    └── static/
        └── images/
            ├── ilsan-logo.png        ← Guardar aquí
            ├── ilsan-facility.jpg    ← Guardar aquí
            └── README.md (este archivo)
```

## Resultado
Una vez guardadas las imágenes, el banner mostrará:
- Logo ILSAN centrado
- Fondo con la vista aérea de las instalaciones
- Overlay oscuro para mejorar legibilidad del texto
- Gradiente azul sutil del tema ILSAN

## Si las imágenes no están disponibles
El sistema mostrará:
- Logo: Se oculta automáticamente si no existe (onerror handler)
- Fondo: Gradiente con colores del tema ILSAN
