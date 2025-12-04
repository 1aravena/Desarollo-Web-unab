"""
Router de Anulaciones y Reembolsos
Implementa: B-05, E-02
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from database import get_db
from models import Pedido, SolicitudAnulacion, Reembolso, Usuario
from schemas import AnulacionInput, AnulacionResponse, ReembolsoResponse, Response
from auth import get_current_user

router = APIRouter(prefix="/api/v1/anulaciones", tags=["Anulaciones"])


@router.post("", response_model=AnulacionResponse, status_code=status.HTTP_201_CREATED)
async def solicitar_anulacion(
    anulacion_data: AnulacionInput,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Solicitar anulación de pedido (B-05)
    
    Condiciones:
    - El pedido debe pertenecer al usuario
    - El pedido no debe estar ya cancelado
    - El pedido no debe haber iniciado preparación
    - Motivo justificado (mínimo 10 caracteres)
    """
    # Buscar pedido
    result = await db.execute(
        select(Pedido).where(
            Pedido.id == anulacion_data.pedido_id,
            Pedido.user_id == current_user.id
        )
    )
    pedido = result.scalar_one_or_none()
    
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )
    
    # Verificar que no esté ya cancelado
    if pedido.estado == "cancelado":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pedido ya está cancelado"
        )
    
    # Verificar que no haya iniciado preparación
    if pedido.estado in ["preparando", "enviado", "entregado"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede anular el pedido porque ya está en estado: {pedido.estado}"
        )
    
    # Verificar que no exista ya una solicitud de anulación
    result = await db.execute(
        select(SolicitudAnulacion).where(SolicitudAnulacion.pedido_id == pedido.id)
    )
    existing_anulacion = result.scalar_one_or_none()
    
    if existing_anulacion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una solicitud de anulación para este pedido"
        )
    
    # Verificar ventana de tiempo (ejemplo: máximo 10 minutos después de confirmar)
    tiempo_transcurrido = datetime.utcnow() - pedido.fecha
    if tiempo_transcurrido > timedelta(minutes=10):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tiempo límite para anular el pedido ha expirado (10 minutos)"
        )
    
    # Crear solicitud de anulación
    nueva_anulacion = SolicitudAnulacion(
        pedido_id=pedido.id,
        motivo=anulacion_data.motivo,
        estado="pendiente",
        monto_reembolso=pedido.total
    )
    
    db.add(nueva_anulacion)
    await db.flush()
    
    # Actualizar estado del pedido
    pedido.estado = "cancelado"
    
    # Crear registro de reembolso
    reembolso = Reembolso(
        anulacion_id=nueva_anulacion.id,
        monto=pedido.total,
        metodo_pago=pedido.metodo_pago or "transferencia",
        estado="pendiente"
    )
    
    db.add(reembolso)
    
    await db.commit()
    await db.refresh(nueva_anulacion)
    
    # TODO: Notificar al administrador
    # TODO: Procesar reembolso automático si aplica
    
    return nueva_anulacion


@router.get("/{pedido_id}", response_model=AnulacionResponse)
async def get_anulacion_by_pedido(
    pedido_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener detalles de anulación por pedido
    """
    # Verificar que el pedido pertenezca al usuario
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
    
    # Buscar anulación
    result = await db.execute(
        select(SolicitudAnulacion).where(SolicitudAnulacion.pedido_id == pedido_id)
    )
    anulacion = result.scalar_one_or_none()
    
    if not anulacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe solicitud de anulación para este pedido"
        )
    
    return anulacion


@router.get("/{pedido_id}/reembolso", response_model=ReembolsoResponse)
async def get_reembolso(
    pedido_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener estado del reembolso
    """
    # Verificar que el pedido pertenezca al usuario
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
    
    # Buscar anulación y reembolso
    result = await db.execute(
        select(Reembolso)
        .join(SolicitudAnulacion)
        .where(SolicitudAnulacion.pedido_id == pedido_id)
    )
    reembolso = result.scalar_one_or_none()
    
    if not reembolso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe reembolso para este pedido"
        )
    
    return reembolso


@router.get("/pedido/{pedido_id}/puede-anular", response_model=dict)
async def puede_anular_pedido(
    pedido_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verificar si un pedido puede ser anulado (B-05)
    
    Útil para mostrar/ocultar botón de anulación en la interfaz
    """
    # Buscar pedido
    result = await db.execute(
        select(Pedido).where(
            Pedido.id == pedido_id,
            Pedido.user_id == current_user.id
        )
    )
    pedido = result.scalar_one_or_none()
    
    if not pedido:
        return {
            "puede_anular": False,
            "razon": "Pedido no encontrado"
        }
    
    # Verificar condiciones
    if pedido.estado == "cancelado":
        return {
            "puede_anular": False,
            "razon": "El pedido ya está cancelado"
        }
    
    if pedido.estado in ["preparando", "enviado", "entregado"]:
        return {
            "puede_anular": False,
            "razon": f"El pedido ya está en estado: {pedido.estado}"
        }
    
    # Verificar ventana de tiempo
    tiempo_transcurrido = datetime.utcnow() - pedido.fecha
    if tiempo_transcurrido > timedelta(minutes=10):
        return {
            "puede_anular": False,
            "razon": "El tiempo límite para anular ha expirado (10 minutos)"
        }
    
    # Verificar si ya existe solicitud
    result = await db.execute(
        select(SolicitudAnulacion).where(SolicitudAnulacion.pedido_id == pedido.id)
    )
    if result.scalar_one_or_none():
        return {
            "puede_anular": False,
            "razon": "Ya existe una solicitud de anulación"
        }
    
    return {
        "puede_anular": True,
        "razon": None,
        "tiempo_restante_minutos": int(10 - (tiempo_transcurrido.total_seconds() / 60))
    }
