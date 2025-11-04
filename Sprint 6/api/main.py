"""
API Principal de Pizzería La Fornace
FastAPI Application - Sprint 6

Implementa todas las historias de usuario:
- Enabler Stories: E-01 a E-08
- Business Stories: B-01 a B-14
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from config import settings
from database import init_db
from routers import (
    auth,
    productos,
    carrito_pedidos,
    anulaciones,
    reportes,
    notificaciones
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eventos de inicio y cierre de la aplicación"""
    # Startup
    print("Iniciando API de Pizzería La Fornace...")
    print(f"Version: {settings.APP_VERSION}")
    print(f"Debug: {settings.DEBUG}")
    
    # Inicializar base de datos
    await init_db()
    print("Base de datos inicializada")
    
    yield
    
    # Shutdown
    print("Cerrando API...")


# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    API RESTful para el sistema de pedidos de Pizzería La Fornace.
    
    ## Funcionalidades principales:
    
    ### Autenticación y Usuarios
    * **E-01**: Registro de clientes con validación de email
    * **E-06**: Login con credenciales cifradas
    * **E-07**: Asignación de roles y permisos (RBAC)
    * **E-08**: Recuperación de contraseña
    * **B-01**: Gestión de perfil y contacto
    
    ### Productos y Menú
    * **B-06**: CRUD de productos (administrador)
    * **B-07**: Visualización de menú con imágenes
    * **E-03**: Control de stock en tiempo real
    
    ### Carrito y Pedidos
    * **B-03**: Carrito de compras con personalización
    * **B-04**: Resumen y confirmación de pedido
    * **B-02**: Historial de pedidos
    * **E-04**: Cálculo de ETA (tiempo estimado)
    * **E-05**: Validación de cobertura geográfica
    
    ### Pagos y Anulaciones
    * **E-02**: Integración con pasarela de pago
    * **B-05**: Anulación de pedidos con reembolso
    
    ### Reportes y Analytics
    * **B-09**: Reportes de ventas por período
    * **B-10**: Ranking de productos más vendidos
    * **B-11**: Exportación a PDF
    
    ### Notificaciones y Campañas
    * **B-08**: Impresión automática para cocina
    * **B-12**: Email de confirmación
    * **B-13**: Gestión de preferencias promocionales
    * **B-14**: Campañas segmentadas
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configurar CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=settings.allowed_origins_list,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# ============================================
# REGISTRAR ROUTERS
# ============================================

# Autenticación y usuarios
app.include_router(auth.router)

# Productos y menú
app.include_router(productos.router)

# Carrito y pedidos
app.include_router(carrito_pedidos.router_carrito)
app.include_router(carrito_pedidos.router_pedidos)

# Anulaciones
app.include_router(anulaciones.router)

# Reportes
app.include_router(reportes.router)

# Notificaciones y campañas
app.include_router(notificaciones.router_impresion)
app.include_router(notificaciones.router_notificaciones)
app.include_router(notificaciones.router_campanias)


# ============================================
# ENDPOINTS RAÍZ
# ============================================

@app.get("/", tags=["Root"])
async def root():
    """Endpoint raíz de la API"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION
    }


@app.get("/api/v1/info", tags=["Info"])
async def api_info():
    """Información de la API y cobertura de historias de usuario"""
    return {
        "nombre": "API Pizzería La Fornace",
        "version": settings.APP_VERSION,
        "descripcion": "API RESTful completa para sistema de pedidos online",
        "historias_implementadas": {
            "enabler_stories": [
                "E-01: Registro con validación de email",
                "E-02: Pasarela de pago con boleta digital",
                "E-03: Gestión de stock en tiempo real",
                "E-04: Estimación de tiempo de entrega (ETA)",
                "E-05: Validación de cobertura geográfica",
                "E-06: Login con credenciales cifradas",
                "E-07: Roles y permisos (RBAC)",
                "E-08: Recuperación de contraseña"
            ],
            "business_stories": [
                "B-01: Gestión de perfil y contacto",
                "B-02: Historial de pedidos",
                "B-03: Carrito de compras",
                "B-04: Resumen y confirmación",
                "B-05: Anulación con reembolso",
                "B-06: CRUD de productos",
                "B-07: Menú con imágenes",
                "B-08: Impresión automática cocina",
                "B-09: Reportes de ventas",
                "B-10: Ranking de productos",
                "B-11: Exportación a PDF",
                "B-12: Email de confirmación",
                "B-13: Preferencias promocionales",
                "B-14: Campañas segmentadas"
            ]
        },
        "arquitectura": {
            "patron": "Macroservicios en 3 capas",
            "framework": "FastAPI",
            "base_datos": "PostgreSQL",
            "orm": "SQLAlchemy (async)",
            "autenticacion": "JWT (OAuth2)",
            "validacion": "Pydantic v2"
        },
        "endpoints_principales": {
            "auth": "/api/v1/auth",
            "productos": "/api/v1/productos",
            "carrito": "/api/v1/carrito",
            "pedidos": "/api/v1/pedidos",
            "anulaciones": "/api/v1/anulaciones",
            "reportes": "/api/v1/reportes",
            "notificaciones": "/api/v1/notificaciones",
            "campanias": "/api/v1/campanias"
        }
    }


# ============================================
# MANEJO DE ERRORES GLOBAL
# ============================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "status": 404,
            "message": "Recurso no encontrado",
            "path": str(request.url)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "status": 500,
            "message": "Error interno del servidor",
            "detail": str(exc) if settings.DEBUG else "Contacte al administrador"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
