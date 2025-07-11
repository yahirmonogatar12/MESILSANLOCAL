from app.routes import app

# Test the endpoint with login simulation
with app.test_client() as client:
    # Simulate login
    with client.session_transaction() as sess:
        sess['usuario'] = '2222'  # Simulate being logged in as production user
    
    print("Testing buscar_codigo_recibido endpoint with login...")
    response = client.get('/buscar_codigo_recibido?codigo_material_recibido=0RH5602C622/202507100001')
    print(f"Status: {response.status_code}")
    print(f"Data: {response.get_json()}")
    
    if response.status_code == 200:
        print("✅ El endpoint funciona correctamente!")
    else:
        print("❌ Hay un problema con el endpoint")
        print(f"Response text: {response.get_data(as_text=True)}")
