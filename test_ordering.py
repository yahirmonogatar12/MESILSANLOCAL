#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Probar ordenamiento de líneas y máquinas
"""

def test_line_sorting():
    """Probar ordenamiento de líneas"""
    lineas_test = ['4line', '1line', '3line', '2line', '10line', '5line']
    
    print("🧪 Prueba de ordenamiento de líneas:")
    print(f"Original: {lineas_test}")
    
    # Simular el ordenamiento JavaScript
    lineas_ordenadas = sorted(lineas_test, key=lambda x: int(x.replace('line', '')) if x.replace('line', '').isdigit() else 0)
    
    print(f"Ordenado: {lineas_ordenadas}")
    return lineas_ordenadas

def test_machine_sorting():
    """Probar ordenamiento de máquinas"""
    maquinas_test = ['L2 m3', 'L1 m1', 'L4 m2', 'L1 m2', 'L3 m1', 'L2 m1', 'L1 m3', 'L4 m1']
    
    print("\n🧪 Prueba de ordenamiento de máquinas:")
    print(f"Original: {maquinas_test}")
    
    # Simular el ordenamiento JavaScript
    def parse_line_machine(s):
        import re
        match = re.search(r'L(\d+)\s*m(\d+)', s, re.IGNORECASE)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        return (0, 0)
    
    maquinas_ordenadas = sorted(maquinas_test, key=parse_line_machine)
    
    print(f"Ordenado: {maquinas_ordenadas}")
    return maquinas_ordenadas

def generate_test_data():
    """Generar datos de prueba para verificar ordenamiento"""
    import random
    
    lineas = ['1line', '2line', '3line', '4line']
    maquinas = ['L1 m1', 'L1 m2', 'L1 m3', 'L2 m1', 'L2 m2', 'L2 m3', 'L3 m1', 'L3 m2', 'L4 m1', 'L4 m2']
    
    print("\n📊 Datos de prueba generados:")
    print(f"Líneas disponibles: {lineas}")
    print(f"Máquinas disponibles: {maquinas}")
    
    # Generar combinaciones aleatorias
    datos_test = []
    for i in range(20):
        datos_test.append({
            'linea': random.choice(lineas),
            'maquina': random.choice(maquinas),
            'ScanDate': f"2025080{random.randint(1, 5)}",
            'Result': random.choice(['OK', 'NG'])
        })
    
    print(f"\n📋 Muestra de datos generados:")
    for i, dato in enumerate(datos_test[:5], 1):
        print(f"  {i}. Línea: {dato['linea']}, Máquina: {dato['maquina']}, Resultado: {dato['Result']}")
    
    return datos_test

if __name__ == "__main__":
    print("🧪 Probando ordenamiento de filtros SMT\n")
    
    # Probar ordenamiento
    lineas_ok = test_line_sorting()
    maquinas_ok = test_machine_sorting()
    
    # Verificar que está correcto
    expected_lines = ['1line', '2line', '3line', '4line', '5line', '10line']
    expected_machines = ['L1 m1', 'L1 m2', 'L1 m3', 'L2 m1', 'L2 m3', 'L3 m1', 'L4 m1', 'L4 m2']
    
    print(f"\n✅ Ordenamiento de líneas: {'Correcto' if lineas_ok == expected_lines else 'Incorrecto'}")
    print(f"✅ Ordenamiento de máquinas: {'Correcto' if maquinas_ok == expected_machines else 'Incorrecto'}")
    
    # Generar datos de prueba
    generate_test_data()
    
    print("\n🎉 Pruebas completadas!")
    print("📋 Los filtros deberían mostrar:")
    print("   • Líneas: 1line, 2line, 3line, 4line...")
    print("   • Máquinas: L1 m1, L1 m2, L1 m3, L2 m1, L2 m2...")
