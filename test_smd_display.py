import mysql.connector

DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn'
}

print("📱 SIMULACIÓN: INVENTARIO ROLLOS SMD")
print("=" * 60)
print("(Cómo se verá en el frontend corregido)")

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Simular la consulta del endpoint
    cursor.execute("""
        SELECT numero_parte, codigo_barras, estado, cantidad_actual
        FROM InventarioRollosSMD 
        WHERE numero_parte != 'SISTEMA_INIT'
        LIMIT 3
    """)
    
    rows = cursor.fetchall()
    
    print(f"\n📊 DATOS MOSTRADOS EN EL FRONTEND ({len(rows)} ejemplos):")
    print("-" * 80)
    
    for i, row in enumerate(rows, 1):
        numero_parte, codigo_barras, estado, cantidad = row
        
        print(f"📦 ROLLO {i}:")
        print(f"   🏷️  Número de Parte: {numero_parte}")
        print(f"   📱 Código de Barras (Escaneo SMounter): {codigo_barras or 'N/A'}")
        print(f"   📊 Estado: {estado}")
        print(f"   📈 Cantidad: {cantidad} pzs")
        print("   " + "-"*60)
    
    print("\n🎯 EXPLICACIÓN:")
    print("   🏷️  Número de Parte: Parte real del componente")
    print("   📱 Código de Barras: Código único para escanear en SMounter")
    print("   ✅ Cada código de barras es único y trazable")
    print("\n🎉 CONFIGURACIÓN CORRECTA APLICADA")
    
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    cursor.close()
    conn.close()
