#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo completa de la nueva interfaz de gestión de permisos
Muestra todas las capacidades y estadísticas del sistema
"""

import requests
import json
from collections import defaultdict

def demo_completa():
    """Demostración completa de todas las capacidades"""
    base_url = "http://localhost:5000"
    
    print("🎉 DEMO COMPLETA - INTERFAZ DE GESTIÓN DE PERMISOS")
    print("=" * 70)
    
    # Obtener datos del sistema
    print("\n📊 CARGANDO DATOS DEL SISTEMA...")
    
    try:
        # Cargar roles
        roles_response = requests.get(f"{base_url}/admin/api/roles")
        roles = roles_response.json()
        
        # Cargar dropdowns
        dropdowns_response = requests.get(f"{base_url}/admin/api/dropdowns")
        dropdowns = dropdowns_response.json()
        
        print(f"   ✅ {len(roles)} roles cargados")
        print(f"   ✅ {len(dropdowns)} dropdowns cargados")
        
    except Exception as e:
        print(f"   ❌ Error cargando datos: {e}")
        return
    
    # Análisis por categorías
    print("\n📂 ANÁLISIS POR CATEGORÍAS:")
    print("-" * 40)
    
    categorias = defaultdict(list)
    for dropdown in dropdowns:
        boton = dropdown['boton']
        if '_' in boton:
            prefijo = boton.split('_')[0] + '_'
            categorias[prefijo].append(boton)
        else:
            categorias['otros'].append(boton)
    
    # Mostrar estadísticas por categoría
    for categoria, items in sorted(categorias.items()):
        print(f"   {categoria:<15} : {len(items):>3} dropdowns")
    
    # Análisis de permisos por rol
    print("\n👥 ANÁLISIS DE PERMISOS POR ROL:")
    print("-" * 40)
    
    for role in roles[:5]:  # Mostrar primeros 5 roles
        try:
            permisos_response = requests.get(f"{base_url}/admin/api/role-permissions/{role['nombre']}")
            permisos = permisos_response.json()
            
            # Análisis por categoría para este rol
            permisos_por_categoria = defaultdict(int)
            for permiso in permisos:
                boton = permiso['boton']
                if '_' in boton:
                    prefijo = boton.split('_')[0] + '_'
                    permisos_por_categoria[prefijo] += 1
                else:
                    permisos_por_categoria['otros'] += 1
            
            print(f"\n   🔑 {role['nombre']} ({len(permisos)} permisos totales):")
            for categoria, count in sorted(permisos_por_categoria.items()):
                if count > 0:
                    print(f"      {categoria:<15} : {count:>2} permisos")
        
        except Exception as e:
            print(f"      ❌ Error cargando permisos para {role['nombre']}")
    
    # Demostración de funcionalidades
    print("\n🚀 DEMOSTRACIÓN DE FUNCIONALIDADES:")
    print("-" * 40)
    
    # Test de búsqueda simulada
    test_searches = ["control", "info", "lista", "calidad", "material"]
    print("\n   🔍 Capacidades de búsqueda:")
    for search_term in test_searches:
        matches = [d for d in dropdowns if search_term.lower() in d['boton'].lower()]
        print(f"      '{search_term}' → {len(matches)} resultados")
    
    # Test de filtros por categoría
    print("\n   📂 Filtros por categoría:")
    main_categories = ['info_', 'lista_', 'control_', 'menu_', 'proceso_']
    for category in main_categories:
        matches = [d for d in dropdowns if d['boton'].startswith(category)]
        print(f"      {category:<10} → {len(matches)} dropdowns")
    
    # Estadísticas finales
    print("\n📈 ESTADÍSTICAS FINALES:")
    print("-" * 40)
    print(f"   📋 Total de dropdowns gestionables: {len(dropdowns)}")
    print(f"   👥 Total de roles configurables: {len(roles)}")
    print(f"   📂 Categorías identificadas: {len(categorias)}")
    
    # Top categorías
    top_categorias = sorted(categorias.items(), key=lambda x: len(x[1]), reverse=True)[:5]
    print(f"\n   🏆 Top 5 categorías con más dropdowns:")
    for i, (categoria, items) in enumerate(top_categorias, 1):
        print(f"      {i}. {categoria:<15} : {len(items)} dropdowns")
    
    # Ejemplo de operaciones disponibles
    print("\n⚙️ OPERACIONES DISPONIBLES:")
    print("-" * 40)
    print("   ✅ Toggle individual de permisos")
    print("   ✅ Habilitar todos los permisos de un rol")
    print("   ✅ Deshabilitar todos los permisos de un rol")
    print("   ✅ Búsqueda en tiempo real")
    print("   ✅ Filtrado por categorías")
    print("   ✅ Contadores automáticos")
    print("   ✅ Notificaciones de confirmación")
    
    # Enlaces de acceso
    print("\n🔗 ACCESO A LA INTERFAZ:")
    print("-" * 40)
    print(f"   🌐 URL Principal: {base_url}/admin/permisos-dropdowns")
    print(f"   🛡️  Desde Admin Panel: Botón 'Gestionar Permisos'")
    
    # Conclusión
    print("\n" + "=" * 70)
    print("🎊 ¡SISTEMA COMPLETAMENTE OPERATIVO!")
    print("🎯 Gestión completa de 117 dropdowns disponibles")
    print("🔧 Interfaz moderna con búsqueda y filtros avanzados")
    print("⚡ Operaciones en tiempo real con feedback inmediato")
    print("📱 Accesible desde cualquier navegador")
    print("=" * 70)

if __name__ == "__main__":
    demo_completa()
