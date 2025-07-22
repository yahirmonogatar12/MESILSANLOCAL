#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test completo del flujo de permisos
Verificar que tanto la protección visual como el bloqueo de contenido funcionen
"""

import sqlite3
import requests
from datetime import datetime

# Configuración
DB_PATH = 'app/database/ISEMM_MES.db'
SERVER_URL = 'http://localhost:5000'

def verificar_usuario_test():
    """Verificar que el usuario de prueba existe y tiene permisos limitados"""
    print("1. Verificando usuario de prueba...")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar usuario
        cursor.execute("""
            SELECT u.id, u.username, u.nombre_completo, r.nombre as rol
            FROM usuarios_sistema u 
            LEFT JOIN usuario_roles ur ON u.id = ur.usuario_id
            LEFT JOIN roles r ON ur.rol_id = r.id
            WHERE u.username = 'test_user'
        """)
        
        usuario = cursor.fetchone()
        if usuario:
            print(f"   ✓ Usuario encontrado: {usuario[1]} ({usuario[2]}) - Rol: {usuario[3]}")
        else:
            print("   ✗ Usuario 'test_user' no encontrado")
            return False
            
        # Verificar permisos específicos
        cursor.execute("""
            SELECT pb.pagina, pb.seccion, pb.boton, 1 as permitido
            FROM rol_permisos_botones rpb
            JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
            JOIN usuario_roles ur ON rpb.rol_id = ur.rol_id
            JOIN usuarios_sistema u ON ur.usuario_id = u.id
            WHERE u.username = 'test_user' 
            AND pb.pagina = 'informacion_basica'
            ORDER BY pb.seccion, pb.boton
        """)
        
        permisos = cursor.fetchall()
        print(f"   Permisos para informacion_basica ({len(permisos)} encontrados):")
        
        permisos_dict = {}
        for p in permisos:
            subcategoria = p[1]
            elemento = p[2]
            permitido = bool(p[3])
            
            if subcategoria not in permisos_dict:
                permisos_dict[subcategoria] = {}
            permisos_dict[subcategoria][elemento] = permitido
            
            status = "✓" if permitido else "✗"
            print(f"     {status} {subcategoria} -> {elemento}")
        
        conn.close()
        return permisos_dict
        
    except Exception as e:
        print(f"   ✗ Error verificando usuario: {e}")
        return False

def test_login():
    """Probar login del usuario de prueba"""
    print("\n2. Probando login...")
    
    session = requests.Session()
    
    try:
        # Obtener página de login
        response = session.get(f"{SERVER_URL}/login")
        if response.status_code != 200:
            print(f"   ✗ Error obteniendo página de login: {response.status_code}")
            return None
            
        # Intentar login
        login_data = {
            'username': 'test_user',
            'password': 'test123'
        }
        
        response = session.post(f"{SERVER_URL}/login", data=login_data)
        
        print(f"     Status code: {response.status_code}")
        print(f"     URL final: {response.url}")
        print(f"     Contiene MaterialTemplate: {'MaterialTemplate.html' in response.text}")
        print(f"     Es redirect: {len(response.history) > 0}")
        
        if response.status_code == 200 and ('/ILSAN-ELECTRONICS' in response.url or '/admin/panel' in response.url or 'MaterialTemplate.html' in response.text):
            print("   ✓ Login exitoso")
            return session
        else:
            print(f"   ✗ Login fallido: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"   ✗ Error en login: {e}")
        return None

def test_permisos_endpoint(session):
    """Probar endpoint de permisos"""
    print("\n3. Probando endpoint de permisos...")
    
    try:
        response = session.get(f"{SERVER_URL}/obtener_permisos_usuario_actual")
        
        if response.status_code == 200:
            permisos = response.json()
            print("   ✓ Endpoint de permisos funciona")
            print(f"   Respuesta completa: {permisos}")
            
            # Verificar estructura de permisos
            if 'permisos' in permisos and 'informacion_basica' in permisos['permisos']:
                info_basica = permisos['permisos']['informacion_basica']
                print(f"   Permisos en 'informacion_basica': {len(info_basica)} subcategorías")
                
                for subcategoria, elementos in info_basica.items():
                    print(f"     {subcategoria}: {elementos}")
                    
                return permisos['permisos']
            else:
                print("   ✗ No se encontró informacion_basica en permisos")
                if 'permisos' in permisos:
                    print(f"   Permisos disponibles: {list(permisos['permisos'].keys())}")
                else:
                    print(f"   Estructura de respuesta: {list(permisos.keys())}")
                # Continuar el test aún sin estos permisos específicos
                return permisos.get('permisos', {})
        else:
            print(f"   ✗ Error en endpoint: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"   ✗ Error obteniendo permisos: {e}")
        return None

def test_rutas_protegidas(session, permisos):
    """Probar acceso a rutas protegidas"""
    print("\n4. Probando acceso a rutas protegidas...")
    
    rutas_test = [
        ('/informacion_basica/control_de_bom', 'Lista Elements', 'info_control_bom'),
        ('/informacion_basica/control_de_material', 'Lista Elements', 'info_informacion_material')
    ]
    
    for ruta, subcategoria, elemento in rutas_test:
        print(f"\n   Probando: {ruta}")
        
        # Verificar si debería tener permiso
        tiene_permiso = False
        if 'informacion_basica' in permisos:
            if subcategoria in permisos['informacion_basica']:
                elementos_permitidos = permisos['informacion_basica'][subcategoria]
                tiene_permiso = elemento in elementos_permitidos
        
        print(f"     Permiso esperado: {'SÍ' if tiene_permiso else 'NO'}")
        
        try:
            response = session.get(f"{SERVER_URL}{ruta}")
            
            if tiene_permiso:
                if response.status_code == 200:
                    print("     ✓ Acceso permitido correctamente")
                else:
                    print(f"     ✗ Acceso denegado cuando debería estar permitido: {response.status_code}")
            else:
                if response.status_code == 403:
                    print("     ✓ Acceso denegado correctamente")
                elif response.status_code == 200:
                    print("     ✗ PROBLEMA: Acceso permitido cuando debería estar denegado")
                else:
                    print(f"     ? Respuesta inesperada: {response.status_code}")
                    
        except Exception as e:
            print(f"     ✗ Error probando ruta: {e}")

def main():
    """Ejecutar test completo"""
    print("=== TEST COMPLETO DEL SISTEMA DE PERMISOS ===")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verificar usuario
    permisos_db = verificar_usuario_test()
    if not permisos_db:
        print("\n❌ No se puede continuar sin usuario de prueba válido")
        return
    
    # Test login
    session = test_login()
    if not session:
        print("\n❌ No se puede continuar sin login exitoso")
        return
    
    # Test endpoint permisos
    permisos_api = test_permisos_endpoint(session)
    if not permisos_api:
        print("\n❌ No se puede continuar sin endpoint de permisos funcional")
        return
    
    # Test rutas protegidas
    test_rutas_protegidas(session, permisos_api)
    
    print("\n=== RESUMEN DEL TEST ===")
    print("✓ Usuario de prueba verificado")
    print("✓ Login funcional") 
    print("✓ Endpoint de permisos funcional")
    print("✓ Rutas protegidas probadas")
    print("\n⚠️  IMPORTANTE: Verifica manualmente en el navegador que:")
    print("   1. Los dropdowns sin permiso están bloqueados visualmente")
    print("   2. No se puede cargar contenido sin permisos")
    print("   3. Los mensajes de error son apropiados")

if __name__ == "__main__":
    main()
