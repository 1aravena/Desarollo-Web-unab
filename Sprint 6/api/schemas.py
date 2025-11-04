"""
Schemas de Pydantic para validación de datos
Implementa los DTOs del diagrama de clases
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# ============================================
# SCHEMAS DE USUARIO Y AUTENTICACIÓN (E-01, E-06, E-07, E-08, B-01)
# ============================================

class UsuarioBase(BaseModel):
    email: EmailStr
    nombre: str = Field(..., min_length=2, max_length=255)
    telefono: Optional[str] = Field(None, max_length=20)
    direccion: Optional[str] = Field(None, max_length=500)


class UsuarioCreate(UsuarioBase):
    """Schema para registro de usuario (E-01)"""
    password: str = Field(..., min_length=8, max_length=100)


class UsuarioLogin(BaseModel):
    """Schema para login (E-06)"""
    email: EmailStr
    password: str


class UsuarioUpdate(BaseModel):
    """Schema para actualización de perfil (B-01)"""
    nombre: Optional[str] = Field(None, min_length=2, max_length=255)
    telefono: Optional[str] = Field(None, max_length=20)
    direccion: Optional[str] = Field(None, max_length=500)


class ContactoUpdateInput(BaseModel):
    """Schema específico para actualización de contacto (B-01)"""
    email: Optional[EmailStr] = None
    telefono: Optional[str] = Field(None, max_length=20)
    direccion: Optional[str] = Field(None, max_length=500)


class UsuarioResponse(UsuarioBase):
    """Schema de respuesta de usuario"""
    id: int
    rol: str
    activo: bool
    email_verificado: bool
    fecha_registro: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema de respuesta de autenticación"""
    access_token: str
    token_type: str = "bearer"
    user: UsuarioResponse


class RecuperacionPasswordRequest(BaseModel):
    """Schema para solicitar recuperación de password (E-08)"""
    email: EmailStr


class RecuperacionPasswordReset(BaseModel):
    """Schema para resetear password con token (E-08)"""
    token: str
    nueva_password: str = Field(..., min_length=8, max_length=100)


# ============================================
# SCHEMAS DE PRODUCTOS (B-06, B-07, E-03)
# ============================================

class CategoriaBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)


class CategoriaCreate(CategoriaBase):
    pass


class CategoriaResponse(CategoriaBase):
    id: int
    activo: bool
    
    class Config:
        from_attributes = True


class ProductoBase(BaseModel):
    nombre: str = Field(..., max_length=255)
    descripcion: Optional[str] = None
    precio: Decimal = Field(..., ge=0, decimal_places=2)
    categoria_id: int
    image_url: Optional[str] = Field(None, max_length=500)
    disponible: bool = True
    stock: int = Field(default=100, ge=0)


class ProductoCreate(ProductoBase):
    """Schema para crear producto (B-06)"""
    pass


class ProductoUpdate(BaseModel):
    """Schema para actualizar producto (B-06)"""
    nombre: Optional[str] = Field(None, max_length=255)
    descripcion: Optional[str] = None
    precio: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    categoria_id: Optional[int] = None
    image_url: Optional[str] = Field(None, max_length=500)
    disponible: Optional[bool] = None
    stock: Optional[int] = Field(None, ge=0)
    activo: Optional[bool] = None


class ProductoResponse(ProductoBase):
    """Schema de respuesta de producto (B-07)"""
    id: int
    activo: bool
    fecha_creacion: datetime
    categoria: Optional[CategoriaResponse] = None
    
    class Config:
        from_attributes = True


class MenuQueryInput(BaseModel):
    """Schema para consultar menú (B-07)"""
    categoria_id: Optional[int] = None
    busqueda: Optional[str] = None
    solo_disponibles: bool = True


# ============================================
# SCHEMAS DE TAMAÑOS Y EXTRAS
# ============================================

class TamanioBase(BaseModel):
    nombre: str = Field(..., max_length=50)
    precio_adicional: Decimal = Field(default=0, ge=0, decimal_places=2)


class TamanioResponse(TamanioBase):
    id: int
    activo: bool
    
    class Config:
        from_attributes = True


class ExtraBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    precio: Decimal = Field(..., ge=0, decimal_places=2)


class ExtraResponse(ExtraBase):
    id: int
    disponible: bool
    activo: bool
    
    class Config:
        from_attributes = True


# ============================================
# SCHEMAS DE CARRITO (B-03)
# ============================================

class CarritoItemInput(BaseModel):
    """Schema para agregar item al carrito (B-03)"""
    producto_id: int
    tamanio_id: Optional[int] = None
    extras_ids: List[int] = Field(default_factory=list)
    cantidad: int = Field(default=1, ge=1)
    notas: Optional[str] = None


class CarritoItemResponse(BaseModel):
    """Schema de respuesta de item del carrito"""
    id: int
    producto_id: int
    nombre: str
    descripcion: Optional[str]
    precio_unitario: Decimal
    tamanio: Optional[TamanioResponse] = None
    extras: List[ExtraResponse] = Field(default_factory=list)
    cantidad: int
    notas: Optional[str] = None
    
    class Config:
        from_attributes = True


class CarritoResponse(BaseModel):
    """Schema de respuesta del carrito completo"""
    id: int
    items: List[CarritoItemResponse]
    total: Decimal
    
    class Config:
        from_attributes = True


# ============================================
# SCHEMAS DE PEDIDOS (B-02, B-04, E-04, E-05)
# ============================================

class DetalleEntrega(BaseModel):
    """Schema para detalles de entrega (E-04, E-05)"""
    direccion: str = Field(..., max_length=500)
    telefono: str = Field(..., max_length=20)
    instrucciones_especiales: Optional[str] = None
    latitud: Optional[Decimal] = Field(None, ge=-90, le=90, decimal_places=7)
    longitud: Optional[Decimal] = Field(None, ge=-180, le=180, decimal_places=7)


class CostosDetalle(BaseModel):
    """Schema para desglose de costos (B-04)"""
    subtotal: Decimal = Field(..., decimal_places=2)
    costo_envio: Decimal = Field(default=0, decimal_places=2)
    impuestos: Decimal = Field(default=0, decimal_places=2)
    descuento: Decimal = Field(default=0, decimal_places=2)
    total: Decimal = Field(..., decimal_places=2)


class ResumenPedidoQuery(BaseModel):
    """Schema para obtener resumen de pedido (B-04)"""
    incluir_desglose: bool = True


class ResumenPedidoResponse(BaseModel):
    """Schema de respuesta del resumen de pedido (B-04)"""
    items: List[CarritoItemResponse]
    costos: CostosDetalle
    detalle_entrega: Optional[DetalleEntrega] = None
    eta_minutos: Optional[int] = None


class PedidoCreate(BaseModel):
    """Schema para crear/confirmar pedido (B-04, E-02)"""
    detalle_entrega: DetalleEntrega
    metodo_pago: str = Field(..., max_length=50)
    notas_adicionales: Optional[str] = None


class PedidoResponse(BaseModel):
    """Schema de respuesta de pedido"""
    id: int
    user_id: int
    fecha: datetime
    estado: str
    subtotal: Decimal
    costo_envio: Decimal
    impuestos: Decimal
    descuento: Decimal
    total: Decimal
    direccion: str
    telefono: str
    instrucciones_especiales: Optional[str] = None
    eta_minutos: Optional[int] = None
    metodo_pago: Optional[str] = None
    items_json: dict
    
    class Config:
        from_attributes = True


class PedidoQueryInput(BaseModel):
    """Schema para consultar pedidos (B-02)"""
    user_id: Optional[int] = None
    estado: Optional[str] = None
    fecha_desde: Optional[datetime] = None
    fecha_hasta: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ValidacionDireccionRequest(BaseModel):
    """Schema para validar dirección dentro del radio de cobertura (E-05)"""
    direccion: str
    latitud: Decimal = Field(..., ge=-90, le=90, decimal_places=7)
    longitud: Decimal = Field(..., ge=-180, le=180, decimal_places=7)


class ValidacionDireccionResponse(BaseModel):
    """Schema de respuesta de validación de dirección (E-05)"""
    valida: bool
    distancia_km: Optional[Decimal] = None
    mensaje: str
    eta_minutos: Optional[int] = None


# ============================================
# SCHEMAS DE ANULACIÓN Y REEMBOLSO (B-05)
# ============================================

class AnulacionInput(BaseModel):
    """Schema para solicitar anulación de pedido (B-05)"""
    pedido_id: int
    motivo: str = Field(..., min_length=10)


class AnulacionResponse(BaseModel):
    """Schema de respuesta de anulación"""
    id: int
    pedido_id: int
    motivo: str
    estado: str
    monto_reembolso: Decimal
    fecha_solicitud: datetime
    
    class Config:
        from_attributes = True


class ReembolsoResponse(BaseModel):
    """Schema de respuesta de reembolso"""
    id: int
    anulacion_id: int
    monto: Decimal
    metodo_pago: str
    estado: str
    transaccion_id: Optional[str] = None
    fecha_proceso: datetime
    
    class Config:
        from_attributes = True


# ============================================
# SCHEMAS DE IMPRESIÓN (B-08)
# ============================================

class ImpresionInput(BaseModel):
    """Schema para imprimir orden en cocina (B-08)"""
    pedido_id: int
    tipo_cocina: str = Field(default="general", max_length=50)


class ImpresionResponse(BaseModel):
    """Schema de respuesta de impresión"""
    id: int
    pedido_id: int
    estado: str
    fecha_envio_cocina: datetime
    fecha_impresion: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============================================
# SCHEMAS DE REPORTES Y RANKINGS (B-09, B-10, B-11)
# ============================================

class ReporteQueryInput(BaseModel):
    """Schema para generar reporte de ventas (B-09)"""
    fecha_inicio: datetime
    fecha_fin: datetime
    tipo_reporte: str = Field(default="ventas", max_length=50)


class ReporteVentasResponse(BaseModel):
    """Schema de respuesta de reporte de ventas (B-09)"""
    fecha_inicio: datetime
    fecha_fin: datetime
    ventas_totales: Decimal
    cantidad_pedidos: int
    ticket_promedio: Decimal
    productos_mas_vendidos: List[dict]


class RankingQueryInput(BaseModel):
    """Schema para consultar ranking de productos (B-10)"""
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    top_n: int = Field(default=10, ge=1, le=100)


class RankingProductoResponse(BaseModel):
    """Schema de respuesta de ranking de productos (B-10)"""
    posicion: int
    producto: ProductoResponse
    cantidad_vendida: int
    ingreso_total: Decimal
    
    class Config:
        from_attributes = True


class PDFExportInput(BaseModel):
    """Schema para exportar reporte a PDF (B-11)"""
    tipo: str = Field(..., max_length=50)  # reporte_ventas, ranking, pedido
    metadata: Optional[dict] = None


class PDFExportResponse(BaseModel):
    """Schema de respuesta de exportación PDF (B-11)"""
    id: int
    nombre_archivo: str
    ruta_descarga: str
    tamano_bytes: Optional[int] = None
    fecha_generacion: datetime
    
    class Config:
        from_attributes = True


# ============================================
# SCHEMAS DE NOTIFICACIONES (B-12, B-13, B-14)
# ============================================

class EmailConfirmacionInput(BaseModel):
    """Schema para enviar email de confirmación (B-12)"""
    pedido_id: int
    email_destino: EmailStr


class EmailConfirmacionResponse(BaseModel):
    """Schema de respuesta de email de confirmación"""
    id: int
    pedido_id: int
    email_destino: str
    enviado: bool
    fecha_envio: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PreferenciaPromoInput(BaseModel):
    """Schema para actualizar preferencias promocionales (B-13)"""
    email_opt_in: Optional[bool] = None
    sms_opt_in: Optional[bool] = None
    whatsapp_opt_in: Optional[bool] = None


class PreferenciaPromoResponse(BaseModel):
    """Schema de respuesta de preferencias promocionales"""
    id: int
    cliente_id: int
    email_opt_in: bool
    sms_opt_in: bool
    whatsapp_opt_in: bool
    fecha_ultima_actualizacion: datetime
    
    class Config:
        from_attributes = True


class CampaignInput(BaseModel):
    """Schema para crear campaña segmentada (B-14)"""
    nombre: str = Field(..., max_length=255)
    criterios: dict  # Criterios de segmentación JSON
    mensaje: str = Field(..., min_length=10)
    canal: str = Field(..., max_length=50)  # email, sms, whatsapp


class CampaniaResponse(BaseModel):
    """Schema de respuesta de campaña"""
    id: int
    nombre: str
    criterios_json: dict
    mensaje: str
    canal: str
    estado: str
    cliente_count: int
    fecha_creacion: datetime
    fecha_envio: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============================================
# SCHEMAS DE RESPUESTA GENÉRICA
# ============================================

class Response(BaseModel):
    """Schema de respuesta genérica"""
    status: int
    message: str
    data: Optional[dict] = None


class PaginatedResponse(BaseModel):
    """Schema de respuesta paginada"""
    items: List[dict]
    total: int
    page: int
    page_size: int
    total_pages: int
