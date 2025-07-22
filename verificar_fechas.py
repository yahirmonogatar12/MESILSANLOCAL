"""
Script de prueba para verificar las fechas y horarios
"""

from datetime import datetime, timezone, timedelta
import sqlite3
import os

# Función para obtener hora de México
def get_mexico_time():
    mexico_tz = timezone(timedelta(hours=-6))
    return datetime.now(mexico_tz)

def verificar_fechas():
    """Verificar las fechas en la base de datos"""
    
    db_path = os.path.join('app', 'database', 'ISEMM_MES.db')
    
    if not os.path.exists(db_path):
        print("❌ No se encontró la base de datos")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print("🔍 VERIFICACIÓN DE FECHAS Y HORARIOS")
        print("=" * 50)
        
        # Mostrar hora actual del sistema vs México
        print(f"⏰ Hora sistema (UTC): {datetime.now()}")
        print(f"⏰ Hora México (GMT-6): {get_mexico_time()}")
        print()
        
        # Verificar último acceso de usuarios
        print("📋 ÚLTIMOS ACCESOS DE USUARIOS:")
        cursor.execute('''
            SELECT username, ultimo_acceso, nombre_completo
            FROM usuarios_sistema 
            WHERE ultimo_acceso IS NOT NULL
            ORDER BY ultimo_acceso DESC
            LIMIT 5
        ''')
        
        for row in cursor.fetchall():
            if row['ultimo_acceso']:
                # Intentar parsear la fecha
                try:
                    fecha = datetime.fromisoformat(row['ultimo_acceso'])
                    if fecha.tzinfo:
                        # Si tiene timezone, convertir a hora local para mostrar
                        fecha_local = fecha.astimezone()
                        print(f"  👤 {row['username']:10} -> {fecha_local.strftime('%Y-%m-%d %H:%M:%S')} (con TZ)")
                    else:
                        # Si no tiene timezone, asumir que es UTC y convertir
                        print(f"  👤 {row['username']:10} -> {fecha.strftime('%Y-%m-%d %H:%M:%S')} (sin TZ)")
                except Exception as e:
                    print(f"  👤 {row['username']:10} -> {row['ultimo_acceso']} (error: {e})")
            else:
                print(f"  👤 {row['username']:10} -> Nunca")
        
        print()
        
        # Verificar auditoría reciente
        print("📝 REGISTROS DE AUDITORÍA RECIENTES:")
        cursor.execute('''
            SELECT usuario, accion, fecha_hora
            FROM auditoria 
            ORDER BY fecha_hora DESC
            LIMIT 5
        ''')
        
        for row in cursor.fetchall():
            if row['fecha_hora']:
                try:
                    fecha = datetime.fromisoformat(row['fecha_hora'])
                    if fecha.tzinfo:
                        fecha_local = fecha.astimezone()
                        print(f"  📄 {row['usuario']:10} {row['accion']:20} -> {fecha_local.strftime('%Y-%m-%d %H:%M:%S')} (con TZ)")
                    else:
                        print(f"  📄 {row['usuario']:10} {row['accion']:20} -> {fecha.strftime('%Y-%m-%d %H:%M:%S')} (sin TZ)")
                except Exception as e:
                    print(f"  📄 {row['usuario']:10} {row['accion']:20} -> {row['fecha_hora']} (error: {e})")
        
        conn.close()
        
        print()
        print("✅ Verificación completada")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verificar_fechas()
