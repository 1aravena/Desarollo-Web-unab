"""
Router de Productos y Menú
Implementa: B-06, B-07, E-03
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional

from database import get_db
from models import Producto, Categoria, Tamanio, Extra, Usuario
from schemas import (
    ProductoCreate, ProductoUpdate, ProductoResponse,
    CategoriaCreate, CategoriaResponse,
    TamanioResponse, ExtraResponse,
    MenuQueryInput, Response
)
from auth import get_current_user, require_admin

router = APIRouter(prefix="/api/v1/productos", tags=["Productos"])


# ============================================
# ENDPOINTS DE CATEGORÍAS
# ============================================

@router.get("/categorias", response_model=List[CategoriaResponse])
async def get_categorias(
    db: AsyncSession = Depends(get_db)
):
    """Obtener todas las categorías activas"""
    result = await db.execute(
        select(Categoria).where(Categoria.activo == True).order_by(Categoria.nombre)
    )
    categorias = result.scalars().all()
    return categorias


@router.post("/categorias", response_model=CategoriaResponse, status_code=status.HTTP_201_CREATED)
async def create_categoria(
    categoria_data: CategoriaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """Crear nueva categoría (B-06 - Solo administradores)"""
    # Verificar que no exista una categoría con el mismo nombre
    result = await db.execute(
        select(Categoria).where(Categoria.nombre == categoria_data.nombre)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una categoría con ese nombre"
        )
    
    nueva_categoria = Categoria(**categoria_data.model_dump())
    db.add(nueva_categoria)
    await db.commit()
    await db.refresh(nueva_categoria)
    
    return nueva_categoria


# ============================================
# ENDPOINTS DE PRODUCTOS (CRUD - B-06)
# ============================================

@router.post("", response_model=ProductoResponse, status_code=status.HTTP_201_CREATED)
async def create_producto(
    producto_data: ProductoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Crear nuevo producto (B-06 - Solo administradores)
    
    Validaciones:
    - Categoría debe existir
    - Precio debe ser positivo
    - Stock inicial (E-03)
    """
    # Verificar que la categoría existe
    result = await db.execute(select(Categoria).where(Categoria.id == producto_data.categoria_id))
    categoria = result.scalar_one_or_none()
    
    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada"
        )
    
    nuevo_producto = Producto(**producto_data.model_dump())
    db.add(nuevo_producto)
    await db.commit()
    await db.refresh(nuevo_producto)
    
    return nuevo_producto


@router.get("", response_model=List[ProductoResponse])
async def get_productos(
    categoria_id: Optional[int] = Query(None, description="Filtrar por categoría"),
    busqueda: Optional[str] = Query(None, description="Buscar en nombre o descripción"),
    solo_disponibles: bool = Query(True, description="Solo productos disponibles"),
    solo_activos: bool = Query(True, description="Solo productos activos"),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener listado de productos (B-07 - Menú)
    
    Filtros:
    - Por categoría
    - Por búsqueda de texto
    - Solo disponibles
    - Solo activos
    """
    query = select(Producto).options(selectinload(Producto.categoria))
    
    # Aplicar filtros
    conditions = []
    
    if categoria_id:
        conditions.append(Producto.categoria_id == categoria_id)
    
    if solo_disponibles:
        conditions.append(Producto.disponible == True)
        conditions.append(Producto.stock > 0)  # E-03: Control de stock
    
    if solo_activos:
        conditions.append(Producto.activo == True)
    
    if busqueda:
        search_pattern = f"%{busqueda}%"
        conditions.append(
            or_(
                Producto.nombre.ilike(search_pattern),
                Producto.descripcion.ilike(search_pattern)
            )
        )
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(Producto.nombre)
    
    result = await db.execute(query)
    productos = result.scalars().all()
    
    return productos


@router.get("/{producto_id}", response_model=ProductoResponse)
async def get_producto(
    producto_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtener detalle de un producto (B-07)"""
    result = await db.execute(select(Producto).options(selectinload(Producto.categoria)).where(Producto.id == producto_id))
    producto = result.scalar_one_or_none()
    
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )
    
    return producto


@router.put("/{producto_id}", response_model=ProductoResponse)
async def update_producto(
    producto_id: int,
    producto_update: ProductoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Actualizar producto (B-06 - Solo administradores)
    
    Permite actualizar cualquier campo del producto
    """
    result = await db.execute(select(Producto).options(selectinload(Producto.categoria)).where(Producto.id == producto_id))
    producto = result.scalar_one_or_none()
    
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )
    
    # Actualizar solo los campos proporcionados
    update_data = producto_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(producto, field, value)
    
    await db.commit()
    await db.refresh(producto)
    
    return producto


@router.delete("/{producto_id}", response_model=Response)
async def delete_producto(
    producto_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Eliminar (desactivar) producto (B-06 - Solo administradores)
    
    No se elimina de la BD, solo se marca como inactivo
    """
    result = await db.execute(select(Producto).where(Producto.id == producto_id))
    producto = result.scalar_one_or_none()
    
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )
    
    producto.activo = False
    producto.disponible = False
    
    await db.commit()
    
    return Response(
        status=200,
        message=f"Producto '{producto.nombre}' desactivado exitosamente"
    )


@router.patch("/{producto_id}/stock", response_model=ProductoResponse)
async def update_stock(
    producto_id: int,
    cantidad: int = Query(..., description="Nueva cantidad de stock"),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Actualizar stock de producto (E-03 - Control de stock)
    
    Actualiza la disponibilidad automáticamente según el stock
    """
    result = await db.execute(select(Producto).options(selectinload(Producto.categoria)).where(Producto.id == producto_id))
    producto = result.scalar_one_or_none()
    
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )
    
    producto.stock = cantidad
    producto.disponible = cantidad > 0
    
    await db.commit()
    await db.refresh(producto)
    
    return producto


# ============================================
# ENDPOINTS DE TAMAÑOS
# ============================================

@router.get("/tamanios/list", response_model=List[TamanioResponse])
async def get_tamanios(
    db: AsyncSession = Depends(get_db)
):
    """Obtener todos los tamaños disponibles"""
    result = await db.execute(
        select(Tamanio).where(Tamanio.activo == True).order_by(Tamanio.precio_adicional)
    )
    tamanios = result.scalars().all()
    return tamanios


# ============================================
# ENDPOINTS DE EXTRAS
# ============================================

@router.get("/extras/list", response_model=List[ExtraResponse])
async def get_extras(
    db: AsyncSession = Depends(get_db)
):
    """Obtener todos los extras disponibles"""
    result = await db.execute(
        select(Extra).where(Extra.activo == True, Extra.disponible == True).order_by(Extra.nombre)
    )
    extras = result.scalars().all()
    return extras


# ============================================
# ENDPOINT DE MENÚ COMPLETO (B-07)
# ============================================

@router.get("/menu/completo")
async def get_menu_completo(
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener menú completo con categorías, productos, tamaños y extras (B-07)
    
    Respuesta optimizada para mostrar el menú en la interfaz
    """
    # Obtener categorías con sus productos
    result_categorias = await db.execute(
        select(Categoria).where(Categoria.activo == True).order_by(Categoria.nombre)
    )
    categorias = result_categorias.scalars().all()
    
    # Obtener todos los productos activos y disponibles
    result_productos = await db.execute(
        select(Producto).options(selectinload(Producto.categoria)).where(
            Producto.activo == True,
            Producto.disponible == True,
            Producto.stock > 0
        ).order_by(Producto.categoria_id, Producto.nombre)
    )
    productos = result_productos.scalars().all()
    
    # Obtener tamaños
    result_tamanios = await db.execute(
        select(Tamanio).where(Tamanio.activo == True).order_by(Tamanio.precio_adicional)
    )
    tamanios = result_tamanios.scalars().all()
    
    # Obtener extras
    result_extras = await db.execute(
        select(Extra).where(Extra.activo == True, Extra.disponible == True).order_by(Extra.nombre)
    )
    extras = result_extras.scalars().all()
    
    # Organizar productos por categoría
    menu_por_categoria = []
    for categoria in categorias:
        productos_categoria = [p for p in productos if p.categoria_id == categoria.id]
        
        if productos_categoria:  # Solo incluir categorías con productos
            menu_por_categoria.append({
                "categoria": CategoriaResponse.model_validate(categoria),
                "productos": [ProductoResponse.model_validate(p) for p in productos_categoria]
            })
    
    return {
        "categorias_con_productos": menu_por_categoria,
        "tamanios": [TamanioResponse.model_validate(t) for t in tamanios],
        "extras": [ExtraResponse.model_validate(e) for e in extras]
    }
