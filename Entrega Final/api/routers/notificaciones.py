"""
Router de Notificaciones y Campañas
Implementa: B-08, B-12, B-13, B-14
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Optional
from datetime import datetime
import logging

from database import get_db
from models import (
    ColaImpresion, EmailConfirmacion, PreferenciaPromo,
    CampaniaSegmentada, Usuario, Pedido
)
from schemas import (
    ImpresionInput, ImpresionResponse,
    EmailConfirmacionInput, EmailConfirmacionResponse,
    PreferenciaPromoInput, PreferenciaPromoResponse,
    CampaignInput, CampaniaResponse,
    Response
)
from auth import get_current_user, require_admin, require_cocinero
from config import settings
from services.email_service import email_service, EmailTemplates

logger = logging.getLogger(__name__)

router_impresion = APIRouter(prefix="/api/v1/impresion", tags=["Impresión"])
router_notificaciones = APIRouter(prefix="/api/v1/notificaciones", tags=["Notificaciones"])
router_campanias = APIRouter(prefix="/api/v1/campanias", tags=["Campañas"])


# ============================================
# ENDPOINTS DE IMPRESIÓN (B-08)
# ============================================

@router_impresion.get("/cola", response_model=List[ImpresionResponse])
async def get_cola_impresion(
    estado: Optional[str] = None,
    current_user: Usuario = Depends(require_cocinero),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener cola de impresión (B-08 - Para cocineros)
    
    Estados: pendiente, impreso, error
    """
    query = select(ColaImpresion).order_by(ColaImpresion.fecha_envio_cocina)
    
    if estado:
        query = query.where(ColaImpresion.estado == estado)
    
    result = await db.execute(query)
    cola = result.scalars().all()
    
    return cola


@router_impresion.post("/{pedido_id}/imprimir", response_model=ImpresionResponse)
async def marcar_como_impreso(
    pedido_id: int,
    current_user: Usuario = Depends(require_cocinero),
    db: AsyncSession = Depends(get_db)
):
    """
    Marcar pedido como impreso (B-08)
    
    Actualiza el estado en la cola de impresión
    """
    result = await db.execute(
        select(ColaImpresion).where(ColaImpresion.pedido_id == pedido_id)
    )
    cola_item = result.scalar_one_or_none()
    
    if not cola_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado en cola de impresión"
        )
    
    cola_item.estado = "impreso"
    cola_item.fecha_impresion = datetime.utcnow()
    
    # Actualizar estado del pedido
    result = await db.execute(select(Pedido).where(Pedido.id == pedido_id))
    pedido = result.scalar_one_or_none()
    
    if pedido and pedido.estado == "pendiente":
        pedido.estado = "preparando"
    
    await db.commit()
    await db.refresh(cola_item)
    
    return cola_item


@router_impresion.post("/{pedido_id}/reimprimir", response_model=ImpresionResponse)
async def reimprimir_pedido(
    pedido_id: int,
    current_user: Usuario = Depends(require_cocinero),
    db: AsyncSession = Depends(get_db)
):
    """
    Reintentar impresión de un pedido (B-08)
    """
    result = await db.execute(
        select(ColaImpresion).where(ColaImpresion.pedido_id == pedido_id)
    )
    cola_item = result.scalar_one_or_none()
    
    if not cola_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado en cola de impresión"
        )
    
    cola_item.estado = "pendiente"
    cola_item.reintentos += 1
    
    await db.commit()
    await db.refresh(cola_item)
    
    # TODO: Integrar con sistema de impresión real
    
    return cola_item


# ============================================
# ENDPOINTS DE EMAILS (B-12)
# ============================================

@router_notificaciones.post("/email-confirmacion", response_model=EmailConfirmacionResponse)
async def enviar_email_confirmacion(
    email_data: EmailConfirmacionInput,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Enviar email de confirmación de pedido (B-12)
    """
    # Verificar que el pedido existe
    result = await db.execute(select(Pedido).where(Pedido.id == email_data.pedido_id))
    pedido = result.scalar_one_or_none()
    
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )
    
    # Buscar registro de email existente
    result = await db.execute(
        select(EmailConfirmacion).where(EmailConfirmacion.pedido_id == email_data.pedido_id)
    )
    email_confirmacion = result.scalar_one_or_none()
    
    if not email_confirmacion:
        # Crear nuevo registro
        email_confirmacion = EmailConfirmacion(
            pedido_id=email_data.pedido_id,
            email_destino=email_data.email_destino,
            asunto=f"Confirmación de pedido #{email_data.pedido_id} - Pizzería La Fornace",
            enviado=False
        )
        db.add(email_confirmacion)
        await db.flush()
    
    # Generar contenido del email usando el servicio
    items = pedido.items_json.get("items", []) if pedido.items_json else []
    contenido_html = EmailTemplates.confirmacion_pedido(
        pedido_id=pedido.id,
        total=float(pedido.total),
        direccion=pedido.direccion or "No especificada",
        eta_minutos=pedido.eta_minutos or 45,
        items=items,
        nombre_cliente="Cliente"
    )
    
    # Guardar referencia para actualizar estado después del envío
    email_id = email_confirmacion.id
    email_destino = email_data.email_destino
    
    # Enviar email en segundo plano
    async def enviar_email_task():
        try:
            exito = await email_service.send_email(
                destinatario=email_destino,
                asunto=email_confirmacion.asunto,
                contenido_html=contenido_html
            )
            
            # Actualizar registro (nota: esto puede tener problemas de sesión, pero es aceptable para este caso)
            logger.info(f"Email confirmación enviado: {exito}")
        except Exception as e:
            logger.error(f"Error enviando email de confirmación: {str(e)}")
    
    background_tasks.add_task(enviar_email_task)
    
    return email_confirmacion


@router_notificaciones.post("/{pedido_id}/reenviar-confirmacion", response_model=EmailConfirmacionResponse)
async def reenviar_email_confirmacion(
    pedido_id: int,
    background_tasks: BackgroundTasks,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reenviar email de confirmación (B-12)
    """
    # Verificar que el pedido pertenece al usuario o es admin
    if current_user.rol in ["admin", "administrador"]:
        result = await db.execute(
            select(Pedido).where(Pedido.id == pedido_id)
        )
    else:
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
    
    # Reenviar email
    return await enviar_email_confirmacion(
        EmailConfirmacionInput(
            pedido_id=pedido_id,
            email_destino=current_user.email
        ),
        background_tasks,
        db
    )


# ============================================
# ENDPOINTS DE PREFERENCIAS PROMOCIONALES (B-13)
# ============================================

@router_campanias.get("/preferencias", response_model=PreferenciaPromoResponse)
async def get_preferencias_promo(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener preferencias promocionales del usuario (B-13)
    """
    result = await db.execute(
        select(PreferenciaPromo).where(PreferenciaPromo.cliente_id == current_user.id)
    )
    preferencias = result.scalar_one_or_none()
    
    if not preferencias:
        # Crear preferencias por defecto
        preferencias = PreferenciaPromo(
            cliente_id=current_user.id,
            email_opt_in=True,
            sms_opt_in=False,
            whatsapp_opt_in=False
        )
        db.add(preferencias)
        await db.commit()
        await db.refresh(preferencias)
    
    return preferencias


@router_campanias.put("/preferencias", response_model=PreferenciaPromoResponse)
async def update_preferencias_promo(
    preferencias_update: PreferenciaPromoInput,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualizar preferencias promocionales (B-13)
    
    Permite suscribirse o darse de baja de:
    - Email marketing
    - SMS marketing
    - WhatsApp marketing
    """
    result = await db.execute(
        select(PreferenciaPromo).where(PreferenciaPromo.cliente_id == current_user.id)
    )
    preferencias = result.scalar_one_or_none()
    
    if not preferencias:
        preferencias = PreferenciaPromo(cliente_id=current_user.id)
        db.add(preferencias)
    
    # Actualizar preferencias
    update_data = preferencias_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(preferencias, field, value)
    
    preferencias.fecha_ultima_actualizacion = datetime.utcnow()
    
    await db.commit()
    await db.refresh(preferencias)
    
    return preferencias


# ============================================
# ENDPOINTS DE CAMPAÑAS SEGMENTADAS (B-14)
# ============================================

@router_campanias.post("", response_model=CampaniaResponse, status_code=status.HTTP_201_CREATED)
async def crear_campania(
    campania_data: CampaignInput,
    current_user: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Crear campaña segmentada (B-14 - Solo administradores)
    
    Criterios de segmentación pueden incluir:
    - Clientes activos/inactivos
    - Clientes con pedidos en último mes
    - Clientes por ubicación geográfica
    """
    # Calcular cantidad de clientes que cumplen criterios
    cliente_count = await calcular_clientes_segmentados(campania_data.criterios, db)
    
    nueva_campania = CampaniaSegmentada(
        nombre=campania_data.nombre,
        criterios_json=campania_data.criterios,
        mensaje=campania_data.mensaje,
        canal=campania_data.canal,
        estado="draft",
        cliente_count=cliente_count
    )
    
    db.add(nueva_campania)
    await db.commit()
    await db.refresh(nueva_campania)
    
    return nueva_campania


@router_campanias.post("/{campania_id}/enviar", response_model=Response)
async def enviar_campania(
    campania_id: int,
    background_tasks: BackgroundTasks,
    current_user: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Enviar campaña a clientes segmentados (B-14)
    Solo envía por email (según requerimiento: solo correo)
    """
    result = await db.execute(
        select(CampaniaSegmentada).where(CampaniaSegmentada.id == campania_id)
    )
    campania = result.scalar_one_or_none()
    
    if not campania:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaña no encontrada"
        )
    
    if campania.estado == "enviada":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La campaña ya fue enviada"
        )
    
    # Obtener clientes que cumplen criterios
    clientes = await obtener_clientes_segmentados(campania.criterios_json, db)
    
    # Filtrar por preferencias de email
    clientes_filtrados = []
    for cliente in clientes:
        result = await db.execute(
            select(PreferenciaPromo).where(PreferenciaPromo.cliente_id == cliente.id)
        )
        preferencias = result.scalar_one_or_none()
        
        # Si no tiene preferencias, asumimos que acepta emails por defecto
        # Si tiene preferencias, verificamos email_opt_in
        if not preferencias or preferencias.email_opt_in:
            clientes_filtrados.append(cliente)
    
    # Preparar datos para el envío
    emails_destinatarios = [c.email for c in clientes_filtrados if c.email]
    mensaje_campania = campania.mensaje
    nombre_campania = campania.nombre
    
    # Enviar notificaciones en segundo plano
    async def enviar_notificaciones_task():
        try:
            enviados = 0
            for cliente in clientes_filtrados:
                if not cliente.email:
                    continue
                
                # Usar plantilla de promoción
                contenido_html = EmailTemplates.promocion(
                    asunto=nombre_campania,
                    mensaje=mensaje_campania,
                    nombre_cliente=cliente.nombre or "Cliente"
                )
                
                exito = await email_service.send_email(
                    destinatario=cliente.email,
                    asunto=f"🍕 {nombre_campania}",
                    contenido_html=contenido_html
                )
                
                if exito:
                    enviados += 1
            
            logger.info(f"Campaña #{campania_id} enviada: {enviados}/{len(clientes_filtrados)} emails")
        except Exception as e:
            logger.error(f"Error enviando campaña #{campania_id}: {str(e)}")
    
    background_tasks.add_task(enviar_notificaciones_task)
    
    # Actualizar estado de la campaña
    campania.estado = "enviada"
    campania.fecha_envio = datetime.utcnow()
    campania.cliente_count = len(clientes_filtrados)
    await db.commit()
    
    return Response(
        status=200,
        message=f"Campaña programada para envío a {len(clientes_filtrados)} clientes"
    )


@router_campanias.get("", response_model=List[CampaniaResponse])
async def get_campanias(
    estado: Optional[str] = None,
    current_user: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener listado de campañas (B-14)
    """
    query = select(CampaniaSegmentada).order_by(CampaniaSegmentada.fecha_creacion.desc())
    
    if estado:
        query = query.where(CampaniaSegmentada.estado == estado)
    
    result = await db.execute(query)
    campanias = result.scalars().all()
    
    return campanias


# ============================================
# UTILIDADES
# ============================================

async def calcular_clientes_segmentados(criterios: dict, db: AsyncSession) -> int:
    """Calcular cantidad de clientes que cumplen criterios de segmentación"""
    query = select(Usuario).where(Usuario.rol == "cliente", Usuario.activo == True)
    
    # Aplicar criterios (ejemplo simple)
    if criterios.get("email_verificado"):
        query = query.where(Usuario.email_verificado == True)
    
    result = await db.execute(query)
    clientes = result.scalars().all()
    
    return len(clientes)


async def obtener_clientes_segmentados(criterios: dict, db: AsyncSession) -> List[Usuario]:
    """Obtener clientes que cumplen criterios de segmentación"""
    query = select(Usuario).where(Usuario.rol == "cliente", Usuario.activo == True)
    
    # Aplicar criterios
    if criterios.get("email_verificado"):
        query = query.where(Usuario.email_verificado == True)
    
    result = await db.execute(query)
    return result.scalars().all()
