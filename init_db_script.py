#!/usr/bin/env python
# Script para inicializar la base de datos con las nuevas tablas

try:
    from app.db import init_db
    print("Inicializando base de datos...")
    init_db()
    print("✅ Base de datos inicializada correctamente!")
    print("✅ Tabla 'configuraciones_usuario' creada/actualizada")
except Exception as e:
    print(f"❌ Error al inicializar la base de datos: {e}")
    import traceback
    traceback.print_exc()
