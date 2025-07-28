#!/usr/bin/env python3
"""
Ejemplo práctico del sistema de secuencias para ROHM
"""

def demo_rohm_sequence():
    """
    Demuestra cómo funciona el sistema de secuencias con el ejemplo de ROHM
    """
    print("=== DEMO: SISTEMA DE SECUENCIAS PARA ROHM ===\n")
    
    # Ejemplo real basado en la imagen proporcionada
    ejemplos_rohm = [
        "ROHM  MCR50JZHJ181  0040002446102223HA05",
        "ROHM  MCR03EZPFX2001  0050002510014G2VA75", 
        "ROHM  MCR01MZPF1002  0100002514006I0VB33",
        "ROHM  MCR03EZPFX1001  0050002508051333VA52",
        "ROHM  MCR03EZPFX1622  0050002508025471V002",
        "ROHM  KTR18EZPF4993  0050002517104181HA39"
    ]
    
    print("Ejemplos de texto ROHM detectados:")
    for i, texto in enumerate(ejemplos_rohm, 1):
        print(f"{i}. '{texto}'")
    print()
    
    # Configuración de la regla por secuencias
    regla_secuencia = {
        'sequence_pattern': [
            {'type': 'spaces', 'count': 2}  # Después de 2 espacios consecutivos
        ],
        'partNumberIndex': 1,     # El número de parte está en la posición 1
        'lotNumberIndex': 2,      # El lote está en la posición 2  
        'partNumberMaxLength': 15, # Limitar número de parte a 15 caracteres
        'lotNumberMaxLength': 25   # Limitar lote a 25 caracteres
    }
    
    print("Configuración de la regla:")
    print(f"- Separador: {regla_secuencia['sequence_pattern'][0]['count']} espacios")
    print(f"- Número de parte en posición: {regla_secuencia['partNumberIndex']}")
    print(f"- Lote en posición: {regla_secuencia['lotNumberIndex']}")
    print(f"- Longitud máxima número de parte: {regla_secuencia['partNumberMaxLength']}")
    print(f"- Longitud máxima lote: {regla_secuencia['lotNumberMaxLength']}")
    print()
    
    # Simular el procesamiento
    print("Procesamiento simulado:")
    print("-" * 60)
    
    for i, texto in enumerate(ejemplos_rohm, 1):
        # Dividir por 2 espacios consecutivos
        partes = texto.split('  ')  # 2 espacios
        
        if len(partes) >= 3:
            proveedor = partes[0].strip()
            numero_parte = partes[1].strip()[:regla_secuencia['partNumberMaxLength']]
            lote = partes[2].strip()[:regla_secuencia['lotNumberMaxLength']]
            
            print(f"Ejemplo {i}:")
            print(f"  Original: '{texto}'")
            print(f"  Dividido: {partes}")
            print(f"  → Proveedor: '{proveedor}'")
            print(f"  → Número de parte: '{numero_parte}'")
            print(f"  → Lote: '{lote}'")
            print()
        else:
            print(f"Ejemplo {i}: ERROR - No se pudo dividir correctamente")
            print()
    
    # Mostrar JSON para crear la regla
    print("=== CÓDIGO JSON PARA CREAR LA REGLA ===")
    json_config = {
        "supplier": "ROHM",
        "fullText": ejemplos_rohm[0],
        "sequences": [
            {"type": "spaces", "count": 2}
        ],
        "partNumberIndex": 1,
        "lotNumberIndex": 2,
        "partNumberMaxLength": 15,
        "lotNumberMaxLength": 25
    }
    
    import json
    print(json.dumps(json_config, indent=2))
    print()
    
    print("=== CÓMO USAR ===")
    print("1. Usar POST /api/save_sequence_rule con el JSON de arriba")
    print("2. O usar POST /api/test_sequence para probar antes de guardar")
    print("3. El sistema automáticamente detectará textos con este patrón")
    print()
    
    print("=== VENTAJAS DE ESTE MÉTODO ===")
    print("✅ Funciona con cualquier número de parte ROHM")
    print("✅ Funciona con cualquier lote ROHM") 
    print("✅ No depende de números específicos")
    print("✅ Solo requiere que haya exactamente 2 espacios entre campos")
    print("✅ Más robusto que regex flexible")
    print("✅ Más simple que carácter por carácter")

if __name__ == '__main__':
    demo_rohm_sequence()
