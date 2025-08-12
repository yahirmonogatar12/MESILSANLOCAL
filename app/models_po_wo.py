"""
Modelos para el sistema PO → WO
Embarques (Purchase Orders) y Work Orders
"""
from app.db_mysql import db
from datetime import datetime
from sqlalchemy.exc import IntegrityError

class Embarque(db.Model):
    """
    Tabla embarques (Purchase Orders - PO)
    """
    __tablename__ = 'embarques'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    codigo_po = db.Column(db.String(32), unique=True, nullable=False, index=True)
    cliente = db.Column(db.String(64), nullable=True)
    fecha_registro = db.Column(db.Date, nullable=True)
    estado = db.Column(
        db.Enum('PLAN', 'PREPARACION', 'EMBARCADO', 'EN_TRANSITO', 'ENTREGADO', name='estado_embarque'),
        default='PLAN',
        nullable=False
    )
    modificado = db.Column(
        db.DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relación con Work Orders
    work_orders = db.relationship('WorkOrder', backref='embarque', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'codigo_po': self.codigo_po,
            'cliente': self.cliente,
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None,
            'estado': self.estado,
            'modificado': self.modificado.isoformat() if self.modificado else None
        }
    
    def __repr__(self):
        return f'<Embarque {self.codigo_po}: {self.estado}>'


class WorkOrder(db.Model):
    """
    Tabla work_orders (WO)
    """
    __tablename__ = 'work_orders'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    codigo_wo = db.Column(db.String(32), unique=True, nullable=False, index=True)
    codigo_po = db.Column(
        db.String(32), 
        db.ForeignKey('embarques.codigo_po', ondelete='CASCADE'), 
        nullable=False,
        index=True
    )
    modelo = db.Column(db.String(64), nullable=True)
    cantidad_planeada = db.Column(db.Integer, nullable=False)
    fecha_operacion = db.Column(db.Date, nullable=True)
    modificador = db.Column(db.String(64), nullable=True)
    estado_wo = db.Column(
        db.Enum('CREADA', 'PLANIFICADA', 'EN_PRODUCCION', 'CERRADA', name='estado_wo'),
        default='CREADA',
        nullable=False
    )
    fecha_modificacion = db.Column(
        db.DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint('cantidad_planeada > 0', name='check_cantidad_positiva'),
    )
    
    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'codigo_wo': self.codigo_wo,
            'codigo_po': self.codigo_po,
            'modelo': self.modelo,
            'cantidad_planeada': self.cantidad_planeada,
            'fecha_operacion': self.fecha_operacion.isoformat() if self.fecha_operacion else None,
            'modificador': self.modificador,
            'estado_wo': self.estado_wo,
            'fecha_modificacion': self.fecha_modificacion.isoformat() if self.fecha_modificacion else None
        }
    
    def __repr__(self):
        return f'<WorkOrder {self.codigo_wo}: {self.codigo_po}>'


def crear_tablas_po_wo():
    """
    Crear tablas del sistema PO → WO
    """
    try:
        print(" Creando tablas del sistema PO → WO...")
        
        # Crear las tablas
        db.create_all()
        
        print(" Tablas embarques y work_orders creadas/verificadas")
        return True
        
    except Exception as e:
        print(f"❌ Error creando tablas PO → WO: {e}")
        return False


def validar_codigo_po(codigo_po):
    """
    Validar formato de código PO: PO-YYMMDD-####
    """
    import re
    pattern = r'^PO-\d{6}-\d{4}$'
    return bool(re.match(pattern, codigo_po))


def validar_codigo_wo(codigo_wo):
    """
    Validar formato de código WO: WO-YYMMDD-####
    """
    import re
    pattern = r'^WO-\d{6}-\d{4}$'
    return bool(re.match(pattern, codigo_wo))


def generar_codigo_po():
    """
    Generar código PO único: PO-YYMMDD-####
    """
    from datetime import date
    
    hoy = date.today()
    fecha_str = hoy.strftime('%y%m%d')  # YYMMDD
    
    # Buscar el último número de secuencia para hoy
    ultimo_po = db.session.query(Embarque).filter(
        Embarque.codigo_po.like(f'PO-{fecha_str}-%')
    ).order_by(Embarque.codigo_po.desc()).first()
    
    if ultimo_po:
        # Extraer número de secuencia del último PO
        ultimo_numero = int(ultimo_po.codigo_po.split('-')[-1])
        nuevo_numero = ultimo_numero + 1
    else:
        nuevo_numero = 1
    
    # Formatear con 4 dígitos
    secuencia = f"{nuevo_numero:04d}"
    
    return f"PO-{fecha_str}-{secuencia}"


def generar_codigo_wo():
    """
    Generar código WO único: WO-YYMMDD-####
    """
    from datetime import date
    
    hoy = date.today()
    fecha_str = hoy.strftime('%y%m%d')  # YYMMDD
    
    # Buscar el último número de secuencia para hoy
    ultimo_wo = db.session.query(WorkOrder).filter(
        WorkOrder.codigo_wo.like(f'WO-{fecha_str}-%')
    ).order_by(WorkOrder.codigo_wo.desc()).first()
    
    if ultimo_wo:
        # Extraer número de secuencia del último WO
        ultimo_numero = int(ultimo_wo.codigo_wo.split('-')[-1])
        nuevo_numero = ultimo_numero + 1
    else:
        nuevo_numero = 1
    
    # Formatear con 4 dígitos
    secuencia = f"{nuevo_numero:04d}"
    
    return f"WO-{fecha_str}-{secuencia}"
