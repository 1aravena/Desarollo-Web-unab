"""
============================================================================
Modelos de Base de Datos - Pizzeria La Fornace
============================================================================
ORM: SQLAlchemy con soporte asincrono
Base de Datos: PostgreSQL

Este archivo define el modelo de dominio del sistema, mapeando las
entidades del negocio a tablas de la base de datos.

Entidades Principales:
----------------------
- Usuario: Clientes, administradores y cocineros (E-01, E-06, E-07, B-01)
- Categoria: Clasificacion de productos
- Producto: Pizzas y otros items del menu (B-06, B-07, E-03)
- Tamanio: Tamanios disponibles para pizzas
- Extra: Ingredientes adicionales
- Carrito/CarritoItem: Carrito de compras (B-03)
- Pedido: Pedidos confirmados (B-02, B-04, E-04, E-05)
- SolicitudAnulacion: Anulaciones de pedidos (B-05)
- ColaImpresion: Ordenes para cocina (B-08)
- EmailConfirmacion: Registro de emails enviados (B-12)
- PreferenciaPromo: Preferencias de notificaciones (B-13)
- CampaniaSegmentada: Campanias de marketing (B-14)
- RankingProducto: Productos mas vendidos (B-10)
- PDFExport: Exportaciones de reportes (B-11)

Relaciones:
-----------
- Usuario 1:N Pedido (un cliente puede tener muchos pedidos)
- Usuario 1:1 Carrito (cada usuario tiene un carrito)
- Categoria 1:N Producto (una categoria agrupa varios productos)
- Producto N:M Extra (un producto puede tener varios extras)
- Pedido 1:1 SolicitudAnulacion (un pedido puede tener una anulacion)
============================================================================
"""
from sqlalchemy import Boolean, Column, Integer, String, Numeric, DateTime, ForeignKey, Table, Text, JSON
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


# ============================================================================
# TABLAS INTERMEDIAS (Relaciones Muchos a Muchos)
# ============================================================================

# Tabla intermedia para extras en items del carrito
carrito_item_extras = Table(
    'carrito_item_extras',
    Base.metadata,
    Column('carrito_item_id', Integer, ForeignKey('carrito_items.id', ondelete='CASCADE')),
    Column('extra_id', Integer, ForeignKey('extras.id', ondelete='CASCADE'))
)

# Tabla intermedia para relacion Producto-Extra (Muchos a Muchos)
producto_extras = Table(
    'producto_extras',
    Base.metadata,
    Column('producto_id', Integer, ForeignKey('productos.id', ondelete='CASCADE'), primary_key=True),
    Column('extra_id', Integer, ForeignKey('extras.id', ondelete='CASCADE'), primary_key=True)
)


# ============================================================================
# MODELO DE USUARIO
# ============================================================================

class Usuario(Base):
    """
    Modelo de Usuario
    
    Historias relacionadas:
    - E-01: Registro con validacion de email
    - E-06: Login con credenciales cifradas
    - E-07: Roles y permisos (cliente, administrador, cocinero)
    - E-08: Recuperacion de contrasena
    - B-01: Edicion de datos de contacto
    
    Roles disponibles: 'cliente', 'administrador', 'cocinero'
    """
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    telefono = Column(String(20), nullable=True)
    direccion = Column(String(500), nullable=True)
    nombre = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    email_verificado = Column(Boolean, default=False)
    token_verificacion = Column(String(255), nullable=True)
    token_recuperacion = Column(String(255), nullable=True)
    token_expiracion = Column(DateTime, nullable=True)
    rol = Column(String(50), default="cliente")  # cliente, administrador, cocinero
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=func.now())
    fecha_actualizacion = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relaciones
    pedidos = relationship("Pedido", back_populates="usuario", cascade="all, delete-orphan")
    carrito = relationship("Carrito", back_populates="usuario", uselist=False, cascade="all, delete-orphan")
    preferencias_promo = relationship("PreferenciaPromo", back_populates="cliente", uselist=False, cascade="all, delete-orphan")


class Categoria(Base):
    """Modelo de Categoría de Productos"""
    __tablename__ = "categorias"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False)
    descripcion = Column(String(500), nullable=True)
    activo = Column(Boolean, default=True)
    
    # Relaciones
    productos = relationship("Producto", back_populates="categoria")


class Producto(Base):
    """Modelo de Producto (B-06, B-07, E-03)"""
    __tablename__ = "productos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    precio = Column(Numeric(10, 2), nullable=False)
    image_url = Column(String(500), nullable=True)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=False)
    disponible = Column(Boolean, default=True)
    stock = Column(Integer, default=100)  # E-03: Control de stock
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=func.now())
    fecha_actualizacion = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relaciones
    categoria = relationship("Categoria", back_populates="productos")
    rankings = relationship("RankingProducto", back_populates="producto")
    extras = relationship("Extra", secondary=producto_extras, back_populates="productos")


class Tamanio(Base):
    """Modelo de Tamaño de Pizza"""
    __tablename__ = "tamanios"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)  # Personal, Mediana, Familiar
    precio_adicional = Column(Numeric(10, 2), default=0)
    activo = Column(Boolean, default=True)


class Extra(Base):
    """Modelo de Extras/Ingredientes adicionales"""
    __tablename__ = "extras"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    precio = Column(Numeric(10, 2), nullable=False)
    disponible = Column(Boolean, default=True)
    activo = Column(Boolean, default=True)

    # Relaciones
    productos = relationship("Producto", secondary=producto_extras, back_populates="extras")

    @property
    def productos_ids(self):
        return [p.id for p in self.productos]


class Carrito(Base):
    """Modelo de Carrito de Compras (B-03)"""
    __tablename__ = "carritos"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True, nullable=False)
    fecha_creacion = Column(DateTime, default=func.now())
    fecha_actualizacion = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relaciones
    usuario = relationship("Usuario", back_populates="carrito")
    items = relationship("CarritoItem", back_populates="carrito", cascade="all, delete-orphan")


class CarritoItem(Base):
    """Modelo de Item del Carrito"""
    __tablename__ = "carrito_items"
    
    id = Column(Integer, primary_key=True, index=True)
    carrito_id = Column(Integer, ForeignKey("carritos.id", ondelete="CASCADE"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    tamanio_id = Column(Integer, ForeignKey("tamanios.id"), nullable=True)
    cantidad = Column(Integer, default=1)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    notas = Column(Text, nullable=True)
    
    # Relaciones
    carrito = relationship("Carrito", back_populates="items")
    producto = relationship("Producto")
    tamanio = relationship("Tamanio")
    extras = relationship("Extra", secondary=carrito_item_extras)


class Pedido(Base):
    """Modelo de Pedido (B-02, B-04, E-04, E-05)"""
    __tablename__ = "pedidos"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha = Column(DateTime, default=func.now())
    estado = Column(String(50), default="pendiente")  # pendiente, confirmado, preparando, enviado, entregado, cancelado
    subtotal = Column(Numeric(10, 2), nullable=False)
    costo_envio = Column(Numeric(10, 2), default=0)
    impuestos = Column(Numeric(10, 2), default=0)
    descuento = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), nullable=False)
    
    # Detalles de entrega (E-04, E-05)
    direccion = Column(String(500), nullable=False)
    telefono = Column(String(20), nullable=False)
    instrucciones_especiales = Column(Text, nullable=True)
    eta_minutos = Column(Integer, nullable=True)  # E-04: Tiempo estimado de entrega
    latitud = Column(Numeric(10, 7), nullable=True)  # E-05: Validación de cobertura
    longitud = Column(Numeric(10, 7), nullable=True)
    
    # Datos del pedido
    items_json = Column(JSON, nullable=False)  # Snapshot de los items al momento de confirmar
    metodo_pago = Column(String(50), nullable=True)  # E-02
    transaccion_id = Column(String(255), nullable=True)  # ID de transacción de la pasarela
    
    fecha_actualizacion = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relaciones
    usuario = relationship("Usuario", back_populates="pedidos")
    anulacion = relationship("SolicitudAnulacion", back_populates="pedido", uselist=False)
    cola_impresion = relationship("ColaImpresion", back_populates="pedido", uselist=False)
    email_confirmacion = relationship("EmailConfirmacion", back_populates="pedido", uselist=False)


class SolicitudAnulacion(Base):
    """Modelo de Solicitud de Anulación (B-05)"""
    __tablename__ = "solicitudes_anulacion"
    
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), unique=True, nullable=False)
    motivo = Column(Text, nullable=False)
    estado = Column(String(50), default="pendiente")  # pendiente, aprobada, rechazada
    monto_reembolso = Column(Numeric(10, 2), nullable=False)
    fecha_solicitud = Column(DateTime, default=func.now())
    fecha_procesado = Column(DateTime, nullable=True)
    
    # Relaciones
    pedido = relationship("Pedido", back_populates="anulacion")
    reembolso = relationship("Reembolso", back_populates="anulacion", uselist=False)


class Reembolso(Base):
    """Modelo de Reembolso"""
    __tablename__ = "reembolsos"
    
    id = Column(Integer, primary_key=True, index=True)
    anulacion_id = Column(Integer, ForeignKey("solicitudes_anulacion.id"), unique=True, nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    metodo_pago = Column(String(50), nullable=False)
    estado = Column(String(50), default="pendiente")  # pendiente, procesado, completado, fallido
    transaccion_id = Column(String(255), nullable=True)
    fecha_proceso = Column(DateTime, default=func.now())
    
    # Relaciones
    anulacion = relationship("SolicitudAnulacion", back_populates="reembolso")


class ColaImpresion(Base):
    """Modelo de Cola de Impresión (B-08)"""
    __tablename__ = "cola_impresion"
    
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), unique=True, nullable=False)
    estado = Column(String(50), default="pendiente")  # pendiente, impreso, error
    fecha_envio_cocina = Column(DateTime, default=func.now())
    fecha_impresion = Column(DateTime, nullable=True)
    reintentos = Column(Integer, default=0)
    
    # Relaciones
    pedido = relationship("Pedido", back_populates="cola_impresion")


class RankingProducto(Base):
    """Modelo de Ranking de Productos (B-10)"""
    __tablename__ = "ranking_productos"
    
    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    periodo_inicio = Column(DateTime, nullable=False)
    periodo_fin = Column(DateTime, nullable=False)
    posicion = Column(Integer, nullable=False)
    cantidad_vendida = Column(Integer, nullable=False)
    ingreso_total = Column(Numeric(10, 2), nullable=False)
    fecha_calculo = Column(DateTime, default=func.now())
    
    # Relaciones
    producto = relationship("Producto", back_populates="rankings")


class PDFExport(Base):
    """Modelo de Exportación PDF (B-11)"""
    __tablename__ = "pdf_exports"
    
    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(50), nullable=False)  # reporte_ventas, ranking, pedido
    nombre_archivo = Column(String(255), nullable=False)
    ruta_archivo = Column(String(500), nullable=False)
    tamano_bytes = Column(Integer, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    fecha_generacion = Column(DateTime, default=func.now())
    fecha_expiracion = Column(DateTime, nullable=True)


class EmailConfirmacion(Base):
    """Modelo de Email de Confirmación (B-12)"""
    __tablename__ = "emails_confirmacion"
    
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    email_destino = Column(String(255), nullable=False)
    asunto = Column(String(500), nullable=False)
    enviado = Column(Boolean, default=False)
    fecha_envio = Column(DateTime, nullable=True)
    reintentos = Column(Integer, default=0)
    error_mensaje = Column(Text, nullable=True)
    
    # Relaciones
    pedido = relationship("Pedido", back_populates="email_confirmacion")


class PreferenciaPromo(Base):
    """Modelo de Preferencias Promocionales (B-13)"""
    __tablename__ = "preferencias_promo"
    
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True, nullable=False)
    email_opt_in = Column(Boolean, default=True)
    sms_opt_in = Column(Boolean, default=False)
    whatsapp_opt_in = Column(Boolean, default=False)
    fecha_ultima_actualizacion = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relaciones
    cliente = relationship("Usuario", back_populates="preferencias_promo")


class CampaniaSegmentada(Base):
    """Modelo de Campaña Segmentada (B-14)"""
    __tablename__ = "campanias_segmentadas"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    criterios_json = Column(JSON, nullable=False)  # Criterios de segmentación
    mensaje = Column(Text, nullable=False)
    canal = Column(String(50), nullable=False)  # email, sms, whatsapp
    estado = Column(String(50), default="draft")  # draft, enviada, programada
    cliente_count = Column(Integer, default=0)
    fecha_creacion = Column(DateTime, default=func.now())
    fecha_envio = Column(DateTime, nullable=True)
