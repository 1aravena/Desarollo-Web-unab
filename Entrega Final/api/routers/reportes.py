"""
Router de Reportes y Exportación
Implementa: B-09, B-10, B-11
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response as FastAPIResponse
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.units import inch

from database import get_db
from models import Pedido, Producto, RankingProducto, PDFExport, Usuario
from schemas import (
    ReporteQueryInput, ReporteVentasResponse,
    RankingQueryInput, RankingProductoResponse,
    PDFExportInput, PDFExportResponse, ProductoSimpleResponse,
    Response
)
from auth import get_current_user, require_admin
from config import settings

router = APIRouter(prefix="/api/v1/reportes", tags=["Reportes"])


@router.post("/ventas", response_model=ReporteVentasResponse)
async def generar_reporte_ventas(
    reporte_data: ReporteQueryInput,
    current_user: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Generar reporte de ventas por período (B-09)
    
    Métricas:
    - Ventas totales
    - Cantidad de pedidos
    - Ticket promedio
    - Top productos vendidos
    """
    # Obtener pedidos del período
    result = await db.execute(
        select(Pedido).where(
            Pedido.fecha >= reporte_data.fecha_inicio,
            Pedido.fecha <= reporte_data.fecha_fin,
            Pedido.estado.in_(["confirmado", "preparando", "enviado", "entregado"])
        )
    )
    pedidos = result.scalars().all()
    
    if not pedidos:
        return ReporteVentasResponse(
            fecha_inicio=reporte_data.fecha_inicio,
            fecha_fin=reporte_data.fecha_fin,
            ventas_totales=Decimal("0"),
            cantidad_pedidos=0,
            ticket_promedio=Decimal("0"),
            productos_mas_vendidos=[]
        )
    
    # Calcular métricas
    ventas_totales = sum(p.total for p in pedidos)
    cantidad_pedidos = len(pedidos)
    ticket_promedio = ventas_totales / cantidad_pedidos if cantidad_pedidos > 0 else Decimal("0")
    
    # Calcular productos más vendidos
    productos_vendidos = {}
    for pedido in pedidos:
        if pedido.items_json and "items" in pedido.items_json:
            for item in pedido.items_json["items"]:
                producto_id = item.get("producto_id")
                cantidad = item.get("cantidad", 0)
                nombre = item.get("nombre", "Desconocido")
                
                if producto_id not in productos_vendidos:
                    productos_vendidos[producto_id] = {
                        "producto_id": producto_id,
                        "nombre": nombre,
                        "cantidad_total": 0,
                        "ingresos": Decimal("0")
                    }
                
                productos_vendidos[producto_id]["cantidad_total"] += cantidad
                productos_vendidos[producto_id]["ingresos"] += Decimal(str(item.get("precio_unitario", 0))) * cantidad
    
    # Ordenar por cantidad vendida
    productos_mas_vendidos = sorted(
        productos_vendidos.values(),
        key=lambda x: x["cantidad_total"],
        reverse=True
    )[:10]  # Top 10
    
    return ReporteVentasResponse(
        fecha_inicio=reporte_data.fecha_inicio,
        fecha_fin=reporte_data.fecha_fin,
        ventas_totales=ventas_totales,
        cantidad_pedidos=cantidad_pedidos,
        ticket_promedio=ticket_promedio,
        productos_mas_vendidos=productos_mas_vendidos
    )


@router.get("/ranking-productos", response_model=List[RankingProductoResponse])
async def get_ranking_productos(
    fecha_inicio: Optional[datetime] = Query(None),
    fecha_fin: Optional[datetime] = Query(None),
    top_n: int = Query(10, ge=1, le=100),
    current_user: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener ranking de pizzas más vendidas (B-10)
    
    Si no se especifican fechas, usa el último mes
    """
    # Establecer fechas por defecto si no se proporcionan
    if not fecha_fin:
        fecha_fin = datetime.utcnow()
    
    if not fecha_inicio:
        fecha_inicio = fecha_fin - timedelta(days=30)
    
    # Obtener pedidos del período
    result = await db.execute(
        select(Pedido).where(
            Pedido.fecha >= fecha_inicio,
            Pedido.fecha <= fecha_fin,
            Pedido.estado.in_(["confirmado", "preparando", "enviado", "entregado"])
        )
    )
    pedidos = result.scalars().all()
    
    # Calcular ranking
    productos_ranking = {}
    for pedido in pedidos:
        if pedido.items_json and "items" in pedido.items_json:
            for item in pedido.items_json["items"]:
                producto_id = item.get("producto_id")
                cantidad = item.get("cantidad", 0)
                
                if producto_id not in productos_ranking:
                    productos_ranking[producto_id] = {
                        "producto_id": producto_id,
                        "cantidad_vendida": 0,
                        "ingreso_total": Decimal("0")
                    }
                
                productos_ranking[producto_id]["cantidad_vendida"] += cantidad
                productos_ranking[producto_id]["ingreso_total"] += Decimal(str(item.get("precio_unitario", 0))) * cantidad
    
    # Ordenar por cantidad vendida
    ranking_ordenado = sorted(
        productos_ranking.values(),
        key=lambda x: x["cantidad_vendida"],
        reverse=True
    )[:top_n]
    
    # Obtener información completa de productos
    resultado = []
    for idx, item in enumerate(ranking_ordenado, start=1):
        result = await db.execute(
            select(Producto).where(Producto.id == item["producto_id"])
        )
        producto = result.scalar_one_or_none()
        
        if producto:
            resultado.append(RankingProductoResponse(
                posicion=idx,
                producto=ProductoSimpleResponse.model_validate(producto),
                cantidad_vendida=item["cantidad_vendida"],
                ingreso_total=item["ingreso_total"]
            ))
    
    return resultado


@router.post("/exportar-pdf", response_model=PDFExportResponse)
async def exportar_reporte_pdf(
    export_data: PDFExportInput,
    current_user: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Exportar reporte a PDF (B-11)
    
    Tipos soportados:
    - reporte_ventas
    - ranking
    - pedido
    """
    # Crear directorio de exportación si no existe
    export_dir = os.path.join(settings.STORAGE_PATH, "pdf_exports")
    os.makedirs(export_dir, exist_ok=True)
    
    # Generar nombre de archivo único
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"{export_data.tipo}_{timestamp}.pdf"
    ruta_archivo = os.path.join(export_dir, nombre_archivo)
    
    # Crear PDF según tipo
    if export_data.tipo == "reporte_ventas":
        await generar_pdf_reporte_ventas(ruta_archivo, export_data.metadata, db)
    elif export_data.tipo == "ranking":
        await generar_pdf_ranking(ruta_archivo, export_data.metadata, db)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de reporte no soportado: {export_data.tipo}"
        )
    
    # Obtener tamaño del archivo
    tamano_bytes = os.path.getsize(ruta_archivo)
    
    # Registrar exportación
    pdf_export = PDFExport(
        tipo=export_data.tipo,
        nombre_archivo=nombre_archivo,
        ruta_archivo=ruta_archivo,
        tamano_bytes=tamano_bytes,
        metadata_json=export_data.metadata,
        fecha_expiracion=datetime.utcnow() + timedelta(days=7)  # Expira en 7 días
    )
    
    db.add(pdf_export)
    await db.commit()
    await db.refresh(pdf_export)
    
    return PDFExportResponse(
        id=pdf_export.id,
        nombre_archivo=nombre_archivo,
        ruta_descarga=f"/api/v1/reportes/descargar-pdf/{pdf_export.id}",
        tamano_bytes=tamano_bytes,
        fecha_generacion=pdf_export.fecha_generacion
    )


@router.get("/descargar-pdf/{pdf_id}")
async def descargar_pdf(
    pdf_id: int,
    current_user: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Descargar PDF exportado (B-11)
    """
    result = await db.execute(select(PDFExport).where(PDFExport.id == pdf_id))
    pdf_export = result.scalar_one_or_none()
    
    if not pdf_export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF no encontrado"
        )
    
    # Verificar si ha expirado
    if pdf_export.fecha_expiracion and pdf_export.fecha_expiracion < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="El PDF ha expirado"
        )
    
    # Verificar que el archivo existe
    if not os.path.exists(pdf_export.ruta_archivo):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo no encontrado"
        )
    
    return FileResponse(
        path=pdf_export.ruta_archivo,
        filename=pdf_export.nombre_archivo,
        media_type="application/pdf"
    )


# ============================================
# UTILIDADES DE GENERACIÓN DE PDF
# ============================================

async def generar_pdf_reporte_ventas(ruta: str, metadata: dict, db: AsyncSession):
    """Generar PDF de reporte de ventas"""
    doc = SimpleDocTemplate(ruta, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Título
    title = Paragraph("<b>Reporte de Ventas - Pizzería La Fornace</b>", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 0.5 * inch))
    
    # Obtener datos del reporte
    if metadata:
        fecha_inicio = datetime.fromisoformat(metadata.get("fecha_inicio"))
        fecha_fin = datetime.fromisoformat(metadata.get("fecha_fin"))
        
        # Información del período
        info = f"Período: {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}"
        story.append(Paragraph(info, styles['Normal']))
        story.append(Spacer(1, 0.3 * inch))
        
        # Tabla de métricas
        data = [
            ['Métrica', 'Valor'],
            ['Ventas Totales', f"${metadata.get('ventas_totales', 0):,.0f}"],
            ['Cantidad de Pedidos', str(metadata.get('cantidad_pedidos', 0))],
            ['Ticket Promedio', f"${metadata.get('ticket_promedio', 0):,.0f}"]
        ]
        
        table = Table(data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    doc.build(story)


async def generar_pdf_ranking(ruta: str, metadata: dict, db: AsyncSession):
    """Generar PDF de ranking de productos"""
    doc = SimpleDocTemplate(ruta, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Título
    title = Paragraph("<b>Ranking de Productos Más Vendidos</b>", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 0.5 * inch))
    
    # Tabla de ranking
    if metadata and "ranking" in metadata:
        data = [['Posición', 'Producto', 'Cantidad Vendida', 'Ingresos']]
        
        for item in metadata["ranking"]:
            data.append([
                str(item.get('posicion', '')),
                item.get('producto_nombre', ''),
                str(item.get('cantidad_vendida', 0)),
                f"${item.get('ingreso_total', 0):,.0f}"
            ])
        
        table = Table(data, colWidths=[1*inch, 3*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    doc.build(story)
