"""
Script para procesar y optimizar imágenes para la landing page de ILSAN
Ejecutar: python process_images.py
"""

from PIL import Image
import os

IMAGES_DIR = os.path.dirname(__file__)

def process_logo(input_path):
    """Procesa el logo ILSAN"""
    try:
        img = Image.open(input_path)
        
        # Convertir a RGBA si no lo está
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Redimensionar manteniendo proporción
        max_width = 400
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        # Guardar como PNG optimizado
        output_path = os.path.join(IMAGES_DIR, 'ilsan-logo.png')
        img.save(output_path, 'PNG', optimize=True)
        print(f"✅ Logo procesado: {output_path}")
        print(f"   Dimensiones: {img.width}x{img.height}px")
        
    except Exception as e:
        print(f"❌ Error procesando logo: {e}")

def process_facility(input_path):
    """Procesa la imagen de las instalaciones"""
    try:
        img = Image.open(input_path)
        
        # Convertir a RGB si es necesario
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Redimensionar a tamaño óptimo para web
        max_width = 1920
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        # Guardar como JPEG optimizado
        output_path = os.path.join(IMAGES_DIR, 'ilsan-facility.jpg')
        img.save(output_path, 'JPEG', quality=85, optimize=True)
        print(f"✅ Imagen de instalaciones procesada: {output_path}")
        print(f"   Dimensiones: {img.width}x{img.height}px")
        
    except Exception as e:
        print(f"❌ Error procesando imagen de instalaciones: {e}")

def main():
    print("🖼️  Procesador de Imágenes - ILSAN Landing Page")
    print("=" * 50)
    
    # Buscar archivos en el directorio actual
    files = os.listdir(IMAGES_DIR)
    
    # Procesar logo
    logo_files = [f for f in files if 'logo' in f.lower() and f.endswith(('.png', '.jpg', '.jpeg'))]
    if logo_files:
        print(f"\n📌 Procesando logo: {logo_files[0]}")
        process_logo(os.path.join(IMAGES_DIR, logo_files[0]))
    else:
        print("\n⚠️  No se encontró archivo de logo")
        print("   Copia el archivo del logo aquí y ejecútalo como: logo-original.png")
    
    # Procesar facility
    facility_files = [f for f in files if any(word in f.lower() for word in ['facility', 'instalacion', 'drone', 'aerial']) 
                     and f.endswith(('.png', '.jpg', '.jpeg'))]
    if facility_files:
        print(f"\n📌 Procesando imagen de instalaciones: {facility_files[0]}")
        process_facility(os.path.join(IMAGES_DIR, facility_files[0]))
    else:
        print("\n⚠️  No se encontró imagen de instalaciones")
        print("   Copia el archivo aquí y nómbralo: facility-original.jpg")
    
    print("\n" + "=" * 50)
    print("✨ Proceso completado")
    print("\n💡 Las imágenes procesadas están listas para usar en la landing page")
    print("   Refresca el navegador para ver los cambios")

if __name__ == "__main__":
    main()
