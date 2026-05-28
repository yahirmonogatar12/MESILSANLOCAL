"""DDL del modulo Trazabilidad (LOTE por WO/LINEA con estados).

La tabla `trazabilidad` guarda el ciclo de vida de cada lote en planta
(estados PLANEADO -> INICIADO -> PAUSA -> FINALIZADO). La consumen los
modulos de planeacion (plan_smd, plan_assy) para resolver el estado actual
de un lote dado su `lot_no` o `codigo_wo`.

No expone endpoints HTTP — solo el bootstrap DDL invocado desde
`app/startup_init.py`. Por eso este modulo NO define un Blueprint y NO se
registra en `app/api/__init__.py::_MODULOS_REGISTRADOS`.

Migrado desde `app/routes.py::crear_tabla_trazabilidad` el 2026-05-28.
"""

from app.db_mysql import execute_query


def crear_tabla_trazabilidad():
    """Crear tabla de trazabilidad si no existe."""
    try:
        query = """
        CREATE TABLE IF NOT EXISTS trazabilidad (
            id INT AUTO_INCREMENT PRIMARY KEY,
            linea VARCHAR(32) NOT NULL,
            lot_no VARCHAR(32) NOT NULL,
            plan_id INT NULL,
            codigo_wo VARCHAR(32) NULL,
            estado ENUM('PLANEADO','INICIADO','PAUSA','FINALIZADO') DEFAULT 'PLANEADO',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            usuario VARCHAR(64) DEFAULT 'sistema',
            INDEX idx_linea (linea),
            INDEX idx_lot (lot_no),
            INDEX idx_estado (estado)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        execute_query(query)
        print(" Tabla trazabilidad creada/verificada")
    except Exception as e:
        print(f" Error creando tabla trazabilidad: {e}")
