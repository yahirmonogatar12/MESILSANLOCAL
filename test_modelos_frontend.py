#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar que los modelos aparezcan correctamente en el frontend de Control de BOM
"""

import requests
import re

def hacer_login():
    """Hacer login con credenciales correctas"""
    try:
        session = requests.Session()
        
        # Credenciales correctas encontradas
        login_data = {
            'username': 'Problema',
            'password': 'Problema'
        }
        
        response = session.post(
            'http://127.0.0.1:5000/login',
            data=login_data,
            allow_redirects=False
        )
        
        if response.status_code == 302:
            print("✓ Login exitoso")
            return session
        else:
            print(f"✗ Login falló: código {response.status_code}")
            return None
            
    except Exception as e:
        print(f"✗ Error en login: {e}")
        return None

def probar_endpoint_modelos(session):
    """Probar el endpoint de modelos"""
    try:
        response = session.get('http://127.0.0.1:5000/listar_modelos_bom')
        
        print(f"\nEndpoint /listar_modelos_bom: código {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Modelos obtenidos: {len(data)}")
            
            if len(data) > 0:
                print(f"📋 Estructura del primer modelo: {data[0]}")
                print(f"🏷️ Primeros 3 modelos:")
                for i, modelo in enumerate(data[:3]):
                    if isinstance(modelo, dict) and 'modelo' in modelo:
                        print(f"  {i+1}. {modelo['modelo']}")
                    else:
                        print(f"  {i+1}. {modelo} (formato incorrecto)")
                return True
            else:
                print("⚠️ Lista vacía")
                return False
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def probar_pagina_control_bom(session):
    """Probar que la página de Control de BOM cargue con modelos"""
    try:
        response = session.get('http://127.0.0.1:5000/informacion_basica/control_de_bom')
        
        print(f"\nPágina Control de BOM: código {response.status_code}")
        
        if response.status_code == 200:
            html_content = response.text
            
            # Buscar elementos del dropdown
            dropdown_items = re.findall(r'<div class="bom-dropdown-item"[^>]*>([^<]+)</div>', html_content)
            
            print(f"✓ Página cargada correctamente")
            print(f"📊 Modelos encontrados en HTML: {len(dropdown_items)}")
            
            if len(dropdown_items) > 0:
                print(f"🏷️ Primeros 5 modelos en HTML:")
                for i, modelo in enumerate(dropdown_items[:5]):
                    print(f"  {i+1}. {modelo.strip()}")
                return True
            else:
                print("⚠️ No se encontraron modelos en el HTML")
                
                # Verificar si hay estructura del dropdown
                if 'bomDropdownList' in html_content:
                    print("✓ Estructura del dropdown presente")
                    if '{% if modelos %}' in html_content:
                        print("⚠️ Template no procesado - posible problema en el servidor")
                    else:
                        print("⚠️ Template procesado pero sin modelos")
                else:
                    print("❌ Estructura del dropdown no encontrada")
                
                return False
        else:
            print(f"❌ Error cargando página: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    print("=== Prueba de modelos en frontend de Control de BOM ===")
    print("Verificando que los modelos aparezcan correctamente...\n")
    
    # 1. Hacer login
    session = hacer_login()
    if not session:
        print("❌ No se puede continuar sin login")
        return
    
    # 2. Probar endpoint de modelos
    endpoint_ok = probar_endpoint_modelos(session)
    
    # 3. Probar página de Control de BOM
    pagina_ok = probar_pagina_control_bom(session)
    
    # Resumen
    print("\n=== RESUMEN ===")
    if endpoint_ok and pagina_ok:
        print("🎉 ¡Los modelos aparecen correctamente en el frontend!")
        print("✅ Endpoint de modelos funciona")
        print("✅ Modelos visibles en la página HTML")
        print("\n💡 Los usuarios ahora pueden ver y seleccionar modelos en Control de BOM")
    else:
        print("❌ Aún hay problemas:")
        if not endpoint_ok:
            print("  - Problema con el endpoint de modelos")
        if not pagina_ok:
            print("  - Los modelos no aparecen en la página HTML")

if __name__ == '__main__':
    main()