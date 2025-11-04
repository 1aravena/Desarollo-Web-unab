"""
Router de Notificaciones y Campañas
Implementa: B-08, B-12, B-13, B-14
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Optional
from datetime import datetime
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

async def enviar_email(destinatario: str, asunto: str, contenido_html: str):
    """Enviar email usando SMTP"""
    message = MIMEMultipart("alternative")
    message["Subject"] = asunto
    message["From"] = settings.EMAIL_FROM
    message["To"] = destinatario
    
    html_part = MIMEText(contenido_html, "html")
    message.attach(html_part)
    
    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            start_tls=True
        )
        return True
    except Exception as e:
        print(f"Error enviando email: {e}")
        return False


async def generar_contenido_email_confirmacion(pedido: Pedido) -> str:
    """Generar contenido HTML del email de confirmación"""
    return f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>¡Gracias por tu pedido!</h2>
            <p>Hola,</p>
            <p>Tu pedido #{pedido.id} ha sido confirmado exitosamente.</p>
            
            <h3>Detalles del pedido:</h3>
            <ul>
                <li><strong>Número de pedido:</strong> #{pedido.id}</li>
                <li><strong>Total:</strong> ${pedido.total:,.0f}</li>
                <li><strong>Dirección de entrega:</strong> {pedido.direccion}</li>
                <li><strong>Tiempo estimado:</strong> {pedido.eta_minutos} minutos</li>
            </ul>
            
            <p>Recibirás tu pedido pronto.</p>
            
            <p>Saludos,<br>
            <strong>Pizzería La Fornace</strong></p>
        </body>
    </html>
    """


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
    
    # Generar contenido del email
    contenido = await generar_contenido_email_confirmacion(pedido)
    
    # Enviar email en segundo plano
    async def enviar_email_task():
        exito = await enviar_email(
            email_data.email_destino,
            email_confirmacion.asunto,
            contenido
        )
        
        if exito:
            email_confirmacion.enviado = True
            email_confirmacion.fecha_envio = datetime.utcnow()
        else:
            email_confirmacion.reintentos += 1
            email_confirmacion.error_mensaje = "Error al enviar email"
        
        await db.commit()
    
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
    # Verificar que el pedido pertenece al usuario
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
    
    # Filtrar por preferencias de canal
    clientes_filtrados = []
    for cliente in clientes:
        result = await db.execute(
            select(PreferenciaPromo).where(PreferenciaPromo.cliente_id == cliente.id)
        )
        preferencias = result.scalar_one_or_none()
        
        if preferencias:
            if campania.canal == "email" and preferencias.email_opt_in:
                clientes_filtrados.append(cliente)
            elif campania.canal == "sms" and preferencias.sms_opt_in:
                clientes_filtrados.append(cliente)
            elif campania.canal == "whatsapp" and preferencias.whatsapp_opt_in:
                clientes_filtrados.append(cliente)
    
    # Enviar notificaciones en segundo plano
    async def enviar_notificaciones_task():
        for cliente in clientes_filtrados:
            if campania.canal == "email":
                await enviar_email(
                    cliente.email,
                    f"Promoción - {campania.nombre}",
                    campania.mensaje
                )
        
        campania.estado = "enviada"
        campania.fecha_envio = datetime.utcnow()
        campania.cliente_count = len(clientes_filtrados)
        await db.commit()
    
    background_tasks.add_task(enviar_notificaciones_task)
    
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
