"""
Router de Carrito y Pedidos
Implementa: B-02, B-03, B-04, E-04, E-05
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, delete
from sqlalchemy.orm import joinedload
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
import math

from database import get_db
from models import (
    Carrito, CarritoItem, Producto, Tamanio, Extra, Pedido, Usuario,
    ColaImpresion, EmailConfirmacion
)
from schemas import (
    CarritoItemInput, CarritoResponse, CarritoItemResponse,
    ProductoResponse, TamanioResponse, ExtraResponse,
    ResumenPedidoResponse, PedidoCreate, PedidoResponse,
    PedidoQueryInput, ValidacionDireccionRequest, ValidacionDireccionResponse,
    CostosDetalle, DetalleEntrega, Response, PaginatedResponse
)
from auth import get_current_user
from config import settings

router_carrito = APIRouter(prefix="/api/v1/carrito", tags=["Carrito"])
router_pedidos = APIRouter(prefix="/api/v1/pedidos", tags=["Pedidos"])


# ============================================
# UTILIDADES
# ============================================

def calcular_distancia_km(lat1: Decimal, lon1: Decimal, lat2: Decimal, lon2: Decimal) -> Decimal:
    """Calcular distancia entre dos puntos geográficos usando fórmula de Haversine"""
    R = 6371  # Radio de la Tierra en km
    
    lat1_rad = math.radians(float(lat1))
    lat2_rad = math.radians(float(lat2))
    dlat = math.radians(float(lat2 - lat1))
    dlon = math.radians(float(lon2 - lon1))
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return Decimal(str(R * c))


def calcular_eta(distancia_km: Decimal) -> int:
    """Calcular tiempo estimado de entrega en minutos (E-04)"""
    tiempo_preparacion = 25  # minutos base de preparación
    tiempo_por_km = 3  # minutos por kilómetro
    
    return tiempo_preparacion + int(float(distancia_km) * tiempo_por_km)


async def calcular_precio_item(
    producto: Producto,
    tamanio: Optional[Tamanio],
    extras: List[Extra]
) -> Decimal:
    """Calcular precio unitario de un item del carrito"""
    precio = producto.precio
    
    if tamanio:
        precio += tamanio.precio_adicional
    
    for extra in extras:
        precio += extra.precio
    
    return precio


# ============================================
# ENDPOINTS DE CARRITO (B-03)
# ============================================

@router_carrito.get("", response_model=CarritoResponse)
async def get_carrito(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener carrito del usuario actual (B-03)
    
    Si no existe, se crea automáticamente
    """
    # Buscar o crear carrito
    result = await db.execute(select(Carrito).where(Carrito.user_id == current_user.id))
    carrito = result.scalar_one_or_none()
    
    if not carrito:
        carrito = Carrito(user_id=current_user.id)
        db.add(carrito)
        await db.commit()
        await db.refresh(carrito)
    
    # Cargar items con sus relaciones
    result = await db.execute(
        select(CarritoItem, Producto)
        .join(Producto, CarritoItem.producto_id == Producto.id)
        .options(
            joinedload(CarritoItem.tamanio),
            joinedload(CarritoItem.extras)
        )
        .where(CarritoItem.carrito_id == carrito.id)
        .order_by(CarritoItem.id)
    )
    rows = result.unique().all()
    
    items = []
    for carrito_item, producto in rows:
        item_data = {
            "id": carrito_item.id,
            "producto_id": producto.id,
            "nombre": producto.nombre,
            "descripcion": producto.descripcion,
            "precio_unitario": carrito_item.precio_unitario,
            "tamanio": carrito_item.tamanio,
            "extras": carrito_item.extras,
            "cantidad": carrito_item.cantidad,
            "notas": carrito_item.notas
        }
        items.append(CarritoItemResponse(**item_data))
    
    # Calcular total
    total = sum(item.precio_unitario * item.cantidad for item in items)
    
    return {
        "id": carrito.id,
        "items": items,
        "total": total
    }


@router_carrito.post("/items", response_model=CarritoResponse)
async def add_item_to_carrito(
    item_data: CarritoItemInput,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Agregar item al carrito (B-03)
    
    Validaciones:
    - Producto existe y está disponible
    - Stock suficiente (E-03)
    - Tamaño y extras válidos
    """
    # Obtener o crear carrito
    result = await db.execute(select(Carrito).where(Carrito.user_id == current_user.id))
    carrito = result.scalar_one_or_none()
    
    if not carrito:
        carrito = Carrito(user_id=current_user.id)
        db.add(carrito)
        await db.flush()
    
    # Validar producto
    result = await db.execute(select(Producto).where(Producto.id == item_data.producto_id))
    producto = result.scalar_one_or_none()
    
    if not producto or not producto.activo or not producto.disponible:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Producto no disponible"
        )
    
    # Validar stock (E-03)
    if producto.stock < item_data.cantidad:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stock insuficiente. Solo quedan {producto.stock} unidades"
        )
    
    # Validar tamaño
    tamanio = None
    if item_data.tamanio_id:
        result = await db.execute(select(Tamanio).where(Tamanio.id == item_data.tamanio_id))
        tamanio = result.scalar_one_or_none()
        
        if not tamanio or not tamanio.activo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tamaño no válido"
            )
    
    # Validar extras
    extras = []
    if item_data.extras_ids:
        result = await db.execute(
            select(Extra).where(Extra.id.in_(item_data.extras_ids))
        )
        extras = result.scalars().all()
        
        if len(extras) != len(item_data.extras_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uno o más extras no son válidos"
            )
    
    # Calcular precio unitario
    precio_unitario = await calcular_precio_item(producto, tamanio, extras)
    
    # Crear item del carrito
    nuevo_item = CarritoItem(
        carrito_id=carrito.id,
        producto_id=producto.id,
        tamanio_id=item_data.tamanio_id,
        cantidad=item_data.cantidad,
        precio_unitario=precio_unitario,
        notas=item_data.notas
    )
    
    db.add(nuevo_item)
    
    # Asociar extras
    if extras:
        nuevo_item.extras = extras
    
    await db.commit()
    await db.refresh(carrito)
    
    # Retornar carrito actualizado
    return await get_carrito(current_user, db)


@router_carrito.put("/items/{item_id}", response_model=CarritoResponse)
async def update_carrito_item(
    item_id: int,
    cantidad: int = Query(..., ge=1, description="Nueva cantidad"),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualizar cantidad de un item del carrito (B-03)
    """
    # Buscar item
    result = await db.execute(
        select(CarritoItem)
        .join(Carrito)
        .where(
            CarritoItem.id == item_id,
            Carrito.user_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item no encontrado en el carrito"
        )
    
    # Validar stock
    result = await db.execute(select(Producto).where(Producto.id == item.producto_id))
    producto = result.scalar_one_or_none()
    
    if producto and producto.stock < cantidad:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stock insuficiente. Solo quedan {producto.stock} unidades"
        )
    
    item.cantidad = cantidad
    await db.commit()
    
    return await get_carrito(current_user, db)


@router_carrito.delete("/items/{item_id}", response_model=CarritoResponse)
async def remove_carrito_item(
    item_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Eliminar item del carrito (B-03)
    """
    result = await db.execute(
        select(CarritoItem)
        .join(Carrito)
        .where(
            CarritoItem.id == item_id,
            Carrito.user_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item no encontrado en el carrito"
        )
    
    await db.delete(item)
    await db.commit()
    
    return await get_carrito(current_user, db)


@router_carrito.delete("", response_model=Response)
async def clear_carrito(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Vaciar carrito completamente"""
    result = await db.execute(select(Carrito).where(Carrito.user_id == current_user.id))
    carrito = result.scalar_one_or_none()
    
    if carrito:
        await db.execute(
            delete(CarritoItem).where(CarritoItem.carrito_id == carrito.id)
        )
        await db.commit()
    
    return Response(status=200, message="Carrito vaciado exitosamente")


# ============================================
# ENDPOINTS DE PEDIDOS (B-02, B-04, E-04, E-05)
# ============================================

@router_pedidos.post("/validar-direccion", response_model=ValidacionDireccionResponse)
async def validar_direccion(
    direccion_data: ValidacionDireccionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Validar que la dirección esté dentro del radio de cobertura (E-05)
    
    Coordenadas de la pizzería (ejemplo):
    Latitud: -33.4489, Longitud: -70.6693 (Santiago, Chile)
    """
    # Coordenadas de la pizzería (configurar según ubicación real)
    pizzeria_lat = Decimal("-33.4489")
    pizzeria_lon = Decimal("-70.6693")
    
    # Calcular distancia
    distancia = calcular_distancia_km(
        pizzeria_lat,
        pizzeria_lon,
        direccion_data.latitud,
        direccion_data.longitud
    )
    
    # Validar cobertura
    dentro_cobertura = distancia <= Decimal(str(settings.RADIO_COBERTURA_KM))
    
    if not dentro_cobertura:
        return ValidacionDireccionResponse(
            valida=False,
            distancia_km=distancia,
            mensaje=f"La dirección está fuera del radio de cobertura ({settings.RADIO_COBERTURA_KM} km). Distancia: {distancia:.2f} km"
        )
    
    # Calcular ETA (E-04)
    eta = calcular_eta(distancia)
    
    return ValidacionDireccionResponse(
        valida=True,
        distancia_km=distancia,
        eta_minutos=eta,
        mensaje=f"Dirección válida. Tiempo estimado de entrega: {eta} minutos"
    )


@router_pedidos.get("/resumen", response_model=ResumenPedidoResponse)
async def get_resumen_pedido(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener resumen del pedido antes de confirmar (B-04)
    
    Muestra:
    - Items del carrito
    - Desglose de costos
    - ETA si hay dirección válida
    """
    # Obtener carrito
    carrito_response = await get_carrito(current_user, db)
    
    if not carrito_response["items"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El carrito está vacío"
        )
    
    # Calcular costos
    subtotal = carrito_response["total"]
    costo_envio = Decimal("2000")  # Costo fijo de envío
    impuestos = subtotal * Decimal("0.19")  # IVA 19%
    descuento = Decimal("0")
    total = subtotal + costo_envio + impuestos - descuento
    
    costos = CostosDetalle(
        subtotal=subtotal,
        costo_envio=costo_envio,
        impuestos=impuestos,
        descuento=descuento,
        total=total
    )
    
    # Detalle de entrega si existe en el perfil
    detalle_entrega = None
    if current_user.direccion and current_user.telefono:
        detalle_entrega = DetalleEntrega(
            direccion=current_user.direccion,
            telefono=current_user.telefono
        )
    
    return ResumenPedidoResponse(
        items=carrito_response["items"],
        costos=costos,
        detalle_entrega=detalle_entrega,
        eta_minutos=None  # Se calcula al validar dirección
    )


@router_pedidos.post("", response_model=PedidoResponse, status_code=status.HTTP_201_CREATED)
async def create_pedido(
    pedido_data: PedidoCreate,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Crear/confirmar pedido (B-04, E-02, E-04, E-05)
    
    Proceso:
    1. Validar carrito no vacío
    2. Validar dirección dentro de cobertura (E-05)
    3. Validar stock de productos (E-03)
    4. Calcular ETA (E-04)
    5. Crear pedido
    6. Reducir stock
    7. Vaciar carrito
    8. Encolar impresión (B-08)
    9. Programar email de confirmación (B-12)
    """
    # Obtener carrito
    result = await db.execute(select(Carrito).where(Carrito.user_id == current_user.id))
    carrito = result.scalar_one_or_none()
    
    if not carrito:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El carrito está vacío"
        )
    
    # Obtener items del carrito
    result = await db.execute(
        select(CarritoItem).where(CarritoItem.carrito_id == carrito.id)
    )
    items = result.scalars().all()
    
    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El carrito está vacío"
        )
    
    # Validar stock y crear snapshot de items
    items_snapshot = []
    for item in items:
        result = await db.execute(select(Producto).where(Producto.id == item.producto_id))
        producto = result.scalar_one_or_none()
        
        if not producto or not producto.disponible:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El producto {producto.nombre if producto else 'desconocido'} ya no está disponible"
            )
        
        if producto.stock < item.cantidad:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuficiente para {producto.nombre}. Solo quedan {producto.stock} unidades"
            )
        
        # Crear snapshot del item
        items_snapshot.append({
            "producto_id": producto.id,
            "nombre": producto.nombre,
            "cantidad": item.cantidad,
            "precio_unitario": float(item.precio_unitario),
            "notas": item.notas
        })
    
    # Calcular costos
    subtotal = sum(item.precio_unitario * item.cantidad for item in items)
    costo_envio = Decimal("2000")
    impuestos = subtotal * Decimal("0.19")
    descuento = Decimal("0")
    total = subtotal + costo_envio + impuestos - descuento
    
    # Calcular ETA si hay coordenadas (E-04, E-05)
    eta_minutos = None
    if pedido_data.detalle_entrega.latitud and pedido_data.detalle_entrega.longitud:
        pizzeria_lat = Decimal("-33.4489")
        pizzeria_lon = Decimal("-70.6693")
        
        distancia = calcular_distancia_km(
            pizzeria_lat,
            pizzeria_lon,
            pedido_data.detalle_entrega.latitud,
            pedido_data.detalle_entrega.longitud
        )
        
        if distancia > Decimal(str(settings.RADIO_COBERTURA_KM)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La dirección está fuera del radio de cobertura ({settings.RADIO_COBERTURA_KM} km)"
            )
        
        eta_minutos = calcular_eta(distancia)
    
    # Crear pedido
    nuevo_pedido = Pedido(
        user_id=current_user.id,
        estado="pendiente",
        subtotal=subtotal,
        costo_envio=costo_envio,
        impuestos=impuestos,
        descuento=descuento,
        total=total,
        direccion=pedido_data.detalle_entrega.direccion,
        telefono=pedido_data.detalle_entrega.telefono,
        instrucciones_especiales=pedido_data.detalle_entrega.instrucciones_especiales,
        eta_minutos=eta_minutos,
        latitud=pedido_data.detalle_entrega.latitud,
        longitud=pedido_data.detalle_entrega.longitud,
        items_json={"items": items_snapshot},
        metodo_pago=pedido_data.metodo_pago
    )
    
    db.add(nuevo_pedido)
    await db.flush()
    
    # Reducir stock (E-03)
    for item in items:
        result = await db.execute(select(Producto).where(Producto.id == item.producto_id))
        producto = result.scalar_one()
        producto.stock -= item.cantidad
        
        if producto.stock <= 0:
            producto.disponible = False
    
    # Encolar para impresión (B-08)
    cola_impresion = ColaImpresion(
        pedido_id=nuevo_pedido.id,
        estado="pendiente"
    )
    db.add(cola_impresion)
    
    # Programar email de confirmación (B-12)
    email_confirmacion = EmailConfirmacion(
        pedido_id=nuevo_pedido.id,
        email_destino=current_user.email,
        asunto=f"Confirmación de pedido #{nuevo_pedido.id} - Pizzería La Fornace",
        enviado=False
    )
    db.add(email_confirmacion)
    
    # Vaciar carrito
    for item in items:
        await db.delete(item)
    
    await db.commit()
    await db.refresh(nuevo_pedido)
    
    return nuevo_pedido


@router_pedidos.get("", response_model=List[PedidoResponse])
async def get_pedidos(
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    fecha_desde: Optional[datetime] = Query(None, description="Fecha inicio"),
    fecha_hasta: Optional[datetime] = Query(None, description="Fecha fin"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener historial de pedidos del usuario (B-02)
    
    Filtros:
    - Por estado
    - Por rango de fechas
    - Paginado
    """
    query = select(Pedido).where(Pedido.user_id == current_user.id)
    
    # Aplicar filtros
    if estado:
        query = query.where(Pedido.estado == estado)
    
    if fecha_desde:
        query = query.where(Pedido.fecha >= fecha_desde)
    
    if fecha_hasta:
        query = query.where(Pedido.fecha <= fecha_hasta)
    
    # Ordenar por más reciente
    query = query.order_by(desc(Pedido.fecha))
    
    # Aplicar paginación
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    pedidos = result.scalars().all()
    
    return pedidos


@router_pedidos.get("/{pedido_id}", response_model=PedidoResponse)
async def get_pedido(
    pedido_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener detalle de un pedido específico (B-02)
    """
    result = await db.execute(
        select(Pedido).where(
            Pedido.id == pedido_id,
            Pedido.user_id == current_user.id
        )
    )
    pedido = result.scalar_one_or_none()
    
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )
    
    return pedido
