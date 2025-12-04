"""
Servicio de Envío de Emails - Pizzería La Fornace
Implementa: B-12 (Confirmación pedidos), B-14 (Campañas masivas)
"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from datetime import datetime
import logging

from config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Servicio centralizado para envío de emails"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.email_from = settings.EMAIL_FROM or "noreply@lafornace.cl"
        self.enabled = bool(self.smtp_host and self.smtp_username and self.smtp_password)
    
    async def send_email(
        self,
        destinatario: str,
        asunto: str,
        contenido_html: str,
        contenido_texto: Optional[str] = None
    ) -> bool:
        """
        Enviar email individual
        
        Returns:
            bool: True si el envío fue exitoso, False en caso contrario
        """
        if not self.enabled:
            logger.warning(f"Email service not configured. Would send to: {destinatario}")
            # En modo desarrollo, simular envío exitoso
            logger.info(f"[SIMULATED EMAIL] To: {destinatario}, Subject: {asunto}")
            return True
        
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = asunto
            message["From"] = self.email_from
            message["To"] = destinatario
            
            # Agregar versión texto si existe
            if contenido_texto:
                text_part = MIMEText(contenido_texto, "plain", "utf-8")
                message.attach(text_part)
            
            # Agregar versión HTML
            html_part = MIMEText(contenido_html, "html", "utf-8")
            message.attach(html_part)
            
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_username,
                password=self.smtp_password,
                start_tls=True
            )
            
            logger.info(f"Email sent successfully to {destinatario}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {destinatario}: {str(e)}")
            return False
    
    async def send_bulk_email(
        self,
        destinatarios: List[str],
        asunto: str,
        contenido_html: str
    ) -> dict:
        """
        Enviar email a múltiples destinatarios
        
        Returns:
            dict: {"enviados": int, "fallidos": int, "total": int}
        """
        resultados = {"enviados": 0, "fallidos": 0, "total": len(destinatarios)}
        
        for destinatario in destinatarios:
            exito = await self.send_email(destinatario, asunto, contenido_html)
            if exito:
                resultados["enviados"] += 1
            else:
                resultados["fallidos"] += 1
        
        return resultados


# ============================================
# PLANTILLAS DE EMAIL
# ============================================

class EmailTemplates:
    """Plantillas HTML para diferentes tipos de emails"""
    
    @staticmethod
    def base_template(contenido: str, titulo: str = "Pizzería La Fornace") -> str:
        """Plantilla base para todos los emails"""
        return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titulo}</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background-color: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 20px 0;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #8B0000; padding: 20px; text-align: center;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 28px;">🍕 Pizzería La Fornace</h1>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 30px;">
                            {contenido}
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #333333; padding: 20px; text-align: center;">
                            <p style="color: #ffffff; margin: 0 0 10px 0; font-size: 14px;">Pizzería La Fornace · Solo entregamos calidad</p>
                            <p style="color: #888888; margin: 0; font-size: 12px;">© 2025 Todos los derechos reservados</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
    
    @staticmethod
    def confirmacion_pedido(
        pedido_id: int,
        total: float,
        direccion: str,
        eta_minutos: int,
        items: list,
        nombre_cliente: str = "Cliente"
    ) -> str:
        """
        Template para confirmación de pedido (B-12)
        """
        # Generar lista de items
        items_html = ""
        for item in items:
            nombre = item.get("nombre", "Producto")
            cantidad = item.get("cantidad", 1)
            precio = item.get("precio_unitario", 0)
            items_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">{nombre}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center;">{cantidad}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">${precio:,.0f}</td>
            </tr>
            """
        
        contenido = f"""
            <h2 style="color: #8B0000; margin-top: 0;">¡Gracias por tu pedido, {nombre_cliente}!</h2>
            
            <p style="font-size: 16px; color: #333;">Tu pedido ha sido confirmado exitosamente y está siendo procesado.</p>
            
            <div style="background-color: #f9f9f9; border-radius: 8px; padding: 20px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #333;">📋 Pedido #{pedido_id}</h3>
                
                <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 15px;">
                    <thead>
                        <tr style="background-color: #8B0000; color: white;">
                            <th style="padding: 10px; text-align: left;">Producto</th>
                            <th style="padding: 10px; text-align: center;">Cant.</th>
                            <th style="padding: 10px; text-align: right;">Precio</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>
                
                <p style="font-size: 20px; font-weight: bold; color: #8B0000; text-align: right; margin: 0;">
                    Total: ${total:,.0f}
                </p>
            </div>
            
            <div style="background-color: #e8f5e9; border-left: 4px solid #4CAF50; padding: 15px; margin: 20px 0;">
                <h4 style="margin: 0 0 10px 0; color: #2e7d32;">📍 Dirección de entrega</h4>
                <p style="margin: 0; color: #333;">{direccion}</p>
            </div>
            
            <div style="background-color: #fff3e0; border-left: 4px solid #FF9800; padding: 15px; margin: 20px 0;">
                <h4 style="margin: 0 0 10px 0; color: #e65100;">⏱️ Tiempo estimado de entrega</h4>
                <p style="margin: 0; color: #333; font-size: 18px; font-weight: bold;">{eta_minutos} minutos</p>
            </div>
            
            <p style="color: #666; font-size: 14px;">
                Si tienes alguna pregunta sobre tu pedido, no dudes en contactarnos.
            </p>
        """
        
        return EmailTemplates.base_template(contenido, f"Confirmación Pedido #{pedido_id}")
    
    @staticmethod
    def cambio_estado_pedido(
        pedido_id: int,
        estado: str,
        nombre_cliente: str = "Cliente"
    ) -> str:
        """Template para notificación de cambio de estado"""
        
        estados_info = {
            "confirmado": {
                "emoji": "✅",
                "titulo": "Pedido Confirmado",
                "mensaje": "Tu pedido ha sido confirmado y pronto comenzará su preparación.",
                "color": "#4CAF50"
            },
            "en_preparacion": {
                "emoji": "👨‍🍳",
                "titulo": "En Preparación",
                "mensaje": "¡Buenas noticias! Tu pedido está siendo preparado por nuestros chefs.",
                "color": "#FF9800"
            },
            "en_camino": {
                "emoji": "🛵",
                "titulo": "En Camino",
                "mensaje": "Tu pedido está en camino. ¡Prepárate para recibirlo!",
                "color": "#2196F3"
            },
            "entregado": {
                "emoji": "🎉",
                "titulo": "Entregado",
                "mensaje": "Tu pedido ha sido entregado. ¡Esperamos que lo disfrutes!",
                "color": "#4CAF50"
            }
        }
        
        info = estados_info.get(estado, {
            "emoji": "📦",
            "titulo": estado.replace("_", " ").title(),
            "mensaje": f"El estado de tu pedido ha cambiado a: {estado}",
            "color": "#666666"
        })
        
        contenido = f"""
            <div style="text-align: center; padding: 20px 0;">
                <span style="font-size: 64px;">{info['emoji']}</span>
                <h2 style="color: {info['color']}; margin: 20px 0 10px 0;">{info['titulo']}</h2>
                <p style="color: #666; font-size: 14px;">Pedido #{pedido_id}</p>
            </div>
            
            <p style="font-size: 16px; color: #333; text-align: center;">
                Hola {nombre_cliente},<br><br>
                {info['mensaje']}
            </p>
            
            <div style="text-align: center; margin-top: 30px;">
                <p style="color: #888; font-size: 12px;">
                    Puedes ver el estado de tu pedido en tu cuenta.
                </p>
            </div>
        """
        
        return EmailTemplates.base_template(contenido, f"Actualización Pedido #{pedido_id}")
    
    @staticmethod
    def promocion(
        asunto: str,
        mensaje: str,
        nombre_cliente: str = "Cliente"
    ) -> str:
        """Template para emails promocionales (B-14)"""
        
        contenido = f"""
            <div style="text-align: center; padding: 20px 0;">
                <span style="font-size: 64px;">🎁</span>
                <h2 style="color: #8B0000; margin: 20px 0;">¡Oferta Especial!</h2>
            </div>
            
            <p style="font-size: 16px; color: #333;">
                Hola {nombre_cliente},
            </p>
            
            <div style="background-color: #fff8e1; border: 2px dashed #FFC107; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
                <p style="font-size: 18px; color: #333; margin: 0;">
                    {mensaje}
                </p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="#" style="background-color: #8B0000; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Ver Ofertas
                </a>
            </div>
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            
            <p style="color: #888; font-size: 12px; text-align: center;">
                Recibiste este email porque estás suscrito a nuestras promociones.<br>
                <a href="#" style="color: #8B0000;">Cancelar suscripción</a>
            </p>
        """
        
        return EmailTemplates.base_template(contenido, asunto)
    
    @staticmethod
    def bienvenida(nombre_cliente: str, email: str) -> str:
        """Template para email de bienvenida al registrarse"""
        
        contenido = f"""
            <div style="text-align: center; padding: 20px 0;">
                <span style="font-size: 64px;">👋</span>
                <h2 style="color: #8B0000; margin: 20px 0;">¡Bienvenido a La Fornace!</h2>
            </div>
            
            <p style="font-size: 16px; color: #333;">
                Hola <strong>{nombre_cliente}</strong>,
            </p>
            
            <p style="font-size: 16px; color: #333;">
                Gracias por registrarte en Pizzería La Fornace. Ahora podrás disfrutar de:
            </p>
            
            <ul style="color: #333; font-size: 14px;">
                <li>Pedidos más rápidos con tu información guardada</li>
                <li>Historial completo de tus pedidos</li>
                <li>Promociones exclusivas para clientes registrados</li>
                <li>Seguimiento en tiempo real de tus entregas</li>
            </ul>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="#" style="background-color: #8B0000; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Ver el Menú
                </a>
            </div>
            
            <p style="color: #666; font-size: 14px;">
                Tu cuenta está asociada al email: <strong>{email}</strong>
            </p>
        """
        
        return EmailTemplates.base_template(contenido, "Bienvenido a Pizzería La Fornace")


# Instancia global del servicio
email_service = EmailService()
