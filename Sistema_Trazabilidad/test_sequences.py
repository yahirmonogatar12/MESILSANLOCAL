#!/usr/bin/env python3
"""
Script de prueba para el sistema de secuencias
"""
import json
import sys
import os

# Agregar el directorio actual al path para importar funciones
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_Version2 import apply_sequence_rule, apply_rule

def test_sequence_rules():
    print("=== PRUEBAS DEL SISTEMA DE SECUENCIAS ===\n")
    
    # Ejemplo 1: ROHM con 2 espacios
    print("1. Prueba ROHM con 2 espacios:")
    rohm_text = "ROHM  MCR50JZHJ181  0040002446102223HA05"
    rohm_rule = {
        'sequence_pattern': [
            {'type': 'spaces', 'count': 2}
        ],
        'partNumberIndex': 1,
        'lotNumberIndex': 2,
        'partNumberMaxLength': 15,
        'lotNumberMaxLength': 20
    }
    
    result = apply_sequence_rule(rohm_text, rohm_rule)
    print(f"Texto: '{rohm_text}'")
    print(f"Secuencia: 2 espacios")
    print(f"Resultado: {result}")
    print()
    
    # Ejemplo 2: Con tabs
    print("2. Prueba con tabulaciones:")
    tab_text = "SUPPLIER\tPART123\tLOT456"
    tab_rule = {
        'sequence_pattern': [
            {'type': 'tabs', 'count': 1}
        ],
        'partNumberIndex': 1,
        'lotNumberIndex': 2
    }
    
    result = apply_sequence_rule(tab_text, tab_rule)
    print(f"Texto: '{tab_text}'")
    print(f"Secuencia: 1 tab")
    print(f"Resultado: {result}")
    print()
    
    # Ejemplo 3: Separador personalizado
    print("3. Prueba con separador personalizado:")
    custom_text = "VENDOR||PART789||BATCH101"
    custom_rule = {
        'sequence_pattern': [
            {'type': 'custom', 'separator': '|', 'count': 2}
        ],
        'partNumberIndex': 1,
        'lotNumberIndex': 2
    }
    
    result = apply_sequence_rule(custom_text, custom_rule)
    print(f"Texto: '{custom_text}'")
    print(f"Secuencia: 2 pipes (||)")
    print(f"Resultado: {result}")
    print()
    
    # Ejemplo 4: Secuencias mixtas
    print("4. Prueba con secuencias mixtas:")
    mixed_text = "BRAND  PART123\tLOT456"
    mixed_rule = {
        'sequence_pattern': [
            {'type': 'spaces', 'count': 2},
            {'type': 'tabs', 'count': 1}
        ],
        'partNumberIndex': 1,
        'lotNumberIndex': 2
    }
    
    result = apply_sequence_rule(mixed_text, mixed_rule)
    print(f"Texto: '{mixed_text}'")
    print(f"Secuencia: 2 espacios, luego 1 tab")
    print(f"Resultado: {result}")
    print()
    
    # Ejemplo 5: Con longitudes máximas
    print("5. Prueba con longitudes máximas:")
    long_text = "ROHM  MCR50JZHJ181EXTRA  0040002446102223HA05EXTRA"
    long_rule = {
        'sequence_pattern': [
            {'type': 'spaces', 'count': 2}
        ],
        'partNumberIndex': 1,
        'lotNumberIndex': 2,
        'partNumberMaxLength': 12,
        'lotNumberMaxLength': 15
    }
    
    result = apply_sequence_rule(long_text, long_rule)
    print(f"Texto: '{long_text}'")
    print(f"Secuencia: 2 espacios con límites de longitud")
    print(f"Resultado: {result}")
    print()
    
    print("=== COMPARACIÓN CON REGLAS EXISTENTES ===\n")
    
    # Cargar reglas existentes
    try:
        with open('rules.json', 'r') as f:
            rules = json.load(f)
        
        # Probar con ROHM_SEQUENCE
        if 'ROHM_SEQUENCE' in rules:
            test_text = "ROHM  MCR50JZHJ181  0040002446102223HA05"
            result = apply_rule(test_text, rules['ROHM_SEQUENCE'])
            print(f"ROHM_SEQUENCE con texto: '{test_text}'")
            print(f"Resultado: {result}")
            print()
        
        # Mostrar todas las reglas disponibles
        print("Reglas disponibles:")
        for supplier, rule in rules.items():
            if 'sequence_pattern' in rule:
                print(f"  {supplier}: Secuencias - {rule['sequence_pattern']}")
            elif 'character_pattern' in rule:
                print(f"  {supplier}: Carácter por carácter - {rule['character_pattern']}")
            else:
                print(f"  {supplier}: Regex flexible - {rule.get('pattern', 'N/A')}")
    
    except FileNotFoundError:
        print("Archivo rules.json no encontrado")

if __name__ == '__main__':
    test_sequence_rules()
