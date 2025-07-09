import sqlite3
from flask import Flask, session
import json

# Crear una sesión de prueba para simular login
def test_with_session():
    app = Flask(__name__)
    app.secret_key = 'test'
    
    with app.test_client() as client:
        # Simular login
        with client.session_transaction() as sess:
            sess['usuario'] = 'test_user'
        
        # Probar endpoint de consulta
        response = client.get('/consultar_control_almacen')
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"Data: {response.get_data(as_text=True)[:500]}...")
        
        if response.status_code == 200:
            try:
                data = json.loads(response.get_data(as_text=True))
                print(f"JSON parsed successfully. Records: {len(data)}")
                if data:
                    print("First record:", json.dumps(data[0], indent=2, default=str))
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")

if __name__ == '__main__':
    # Primero verificar la base de datos directamente
    print("=== Verificación directa de la base de datos ===")
    conn = sqlite3.connect('app/database/ISEMM_MES.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM control_material_almacen')
    count = cursor.fetchone()[0]
    print(f"Total de registros en la tabla: {count}")
    conn.close()
    
    # Después probar con Flask
    print("\n=== Prueba con Flask ===")
    
    # Import the app
    import sys
    sys.path.append('.')
    from app import app
    
    app.secret_key = 'test_secret_key'
    
    with app.test_client() as client:
        # Simular login
        with client.session_transaction() as sess:
            sess['usuario'] = 'test_user'
        
        # Probar endpoint de consulta
        response = client.get('/consultar_control_almacen')
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            try:
                data = response.get_json()
                print(f"JSON parsed successfully. Records: {len(data)}")
                if data:
                    print("First record keys:", list(data[0].keys()))
            except Exception as e:
                print(f"Error: {e}")
                print(f"Raw response: {response.get_data(as_text=True)[:200]}...")
