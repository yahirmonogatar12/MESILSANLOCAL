#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar que el mapeo de datos BOM funcione correctamente
"""

import requests
import json

def hacer_login():
    """Hacer login con credenciales correctas"""
    try:
        session = requests.Session()
        
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

def probar_endpoint_con_mapeo(session, modelo):
    """Probar el endpoint /listar_bom con el nuevo mapeo"""
    try:
        data = {'modelo': modelo}
        
        response = session.post(
            'http://127.0.0.1:5000/listar_bom',
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"\n=== Endpoint /listar_bom para modelo {modelo} (con mapeo) ===")
        print(f"Código de respuesta: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    print(f"✓ Datos recibidos: {len(data)} registros")
                    
                    if len(data) > 0:
                        print(f"\n🔍 Primer registro con mapeo:")
                        primer_registro = data[0]
                        
                        # Verificar que los nombres mapeados estén presentes
                        campos_esperados = [
                            'codigoMaterial', 'numeroParte', 'side', 'tipoMaterial',
                            'classification', 'especificacionMaterial', 'vender',
                            'cantidadTotal', 'cantidadOriginal', 'ubicacion',
                            'materialSustituto', 'materialOriginal'
                        ]
                        
                        print(f"  📋 Campos mapeados:")
                        for campo in campos_esperados:
                            valor = primer_registro.get(campo, 'N/A')
                            print(f"    {campo:25} = {valor}")
                        
                        # Verificar que no haya campos con nombres de BD
                        campos_bd = [
                            'codigo_material', 'numero_parte', 'tipo_material',
                            'especificacion_material', 'cantidad_total', 'cantidad_original',
                            'material_sustituto', 'material_original'
                        ]
                        
                        campos_bd_encontrados = []
                        for campo in campos_bd:
                            if campo in primer_registro:
                                campos_bd_encontrados.append(campo)
                        
                        if campos_bd_encontrados:
                            print(f"\n  ⚠️ Campos de BD aún presentes: {campos_bd_encontrados}")
                        else:
                            print(f"\n  ✅ Mapeo correcto: no hay campos de BD en la respuesta")
                        
                        # Mostrar algunos registros más para verificar
                        if len(data) >= 3:
                            print(f"\n🔍 Resumen de primeros 3 registros:")
                            for i, registro in enumerate(data[:3], 1):
                                print(f"  {i}. {registro.get('numeroParte', 'N/A')} - {registro.get('codigoMaterial', 'N/A')}")
                                print(f"     Vendor: {registro.get('vender', 'N/A')} | Cantidad: {registro.get('cantidadTotal', 'N/A')}")
                        
                        # Verificar que todos los registros tengan los campos mapeados
                        registros_sin_mapeo = 0
                        for registro in data:
                            if not registro.get('codigoMaterial') and not registro.get('numeroParte'):
                                registros_sin_mapeo += 1
                        
                        if registros_sin_mapeo > 0:
                            print(f"\n  ⚠️ {registros_sin_mapeo} registros sin mapeo correcto")
                        else:
                            print(f"\n  ✅ Todos los {len(data)} registros tienen mapeo correcto")
                    
                    return len(data)
                else:
                    print(f"❌ Formato de respuesta incorrecto: {type(data)}")
                    return 0
                    
            except Exception as e:
                print(f"❌ Error parseando JSON: {e}")
                print(f"Respuesta raw: {response.text[:200]}...")
                return 0
        else:
            print(f"❌ Error en endpoint: {response.text}")
            return 0
            
    except Exception as e:
        print(f"✗ Error probando endpoint: {e}")
        return 0

def verificar_carga_frontend(session):
    """Verificar que la página de Control de BOM cargue correctamente"""
    try:
        print(f"\n=== Verificando carga del frontend ===")
        
        # Cargar la página de Control de BOM
        response = session.get('http://127.0.0.1:5000/informacion_basica/control_de_bom')
        
        if response.status_code == 200:
            html_content = response.text
            
            # Verificar que la página contenga elementos esperados
            elementos_esperados = [
                'bom-search-dropdown',
                'mostrarDatosEnTabla',
                'cargarDatosBOM',
                'codigoMaterial',
                'numeroParte'
            ]
            
            elementos_encontrados = []
            for elemento in elementos_esperados:
                if elemento in html_content:
                    elementos_encontrados.append(elemento)
            
            print(f"✓ Página cargada correctamente")
            print(f"📋 Elementos encontrados: {len(elementos_encontrados)}/{len(elementos_esperados)}")
            
            for elemento in elementos_esperados:
                estado = "✓" if elemento in elementos_encontrados else "✗"
                print(f"  {estado} {elemento}")
            
            return len(elementos_encontrados) == len(elementos_esperados)
        else:
            print(f"❌ Error cargando página: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error verificando frontend: {e}")
        return False

def main():
    modelo_test = 'EBR30299301'
    
    print(f"Probando mapeo de datos BOM para modelo {modelo_test}...\n")
    
    # 1. Hacer login
    session = hacer_login()
    if not session:
        print("❌ No se puede continuar sin login")
        return
    
    # 2. Probar endpoint con mapeo
    total_registros = probar_endpoint_con_mapeo(session, modelo_test)
    
    # 3. Verificar frontend
    frontend_ok = verificar_carga_frontend(session)
    
    # Resumen final
    print(f"\n=== RESUMEN FINAL ===")
    print(f"📊 Registros obtenidos: {total_registros}")
    print(f"🌐 Frontend funcional: {'✅ Sí' if frontend_ok else '❌ No'}")
    
    if total_registros == 121 and frontend_ok:
        print(f"\n🎉 ¡ÉXITO! El mapeo de datos funciona correctamente")
        print(f"✅ Se obtienen todos los 121 registros esperados")
        print(f"✅ Los nombres de campos están mapeados correctamente")
        print(f"✅ El frontend puede procesar los datos")
    elif total_registros == 121:
        print(f"\n⚠️ Los datos se obtienen correctamente pero hay problemas en el frontend")
    elif frontend_ok:
        print(f"\n⚠️ El frontend funciona pero faltan datos ({total_registros}/121)")
    else:
        print(f"\n❌ Hay problemas tanto en datos como en frontend")

if __name__ == '__main__':
    main()