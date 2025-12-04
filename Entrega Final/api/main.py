"""
============================================================================
API Principal - Pizzeria La Fornace
============================================================================
Framework: FastAPI (Python 3.11+)
Base de Datos: PostgreSQL con SQLAlchemy (async)
Autenticacion: JWT con OAuth2 Bearer

Este archivo es el punto de entrada de la API REST que implementa
todas las historias de usuario del sistema de pedidos online.

Historias Implementadas:
------------------------
Enablers (E-01 a E-08): Infraestructura tecnica
    - E-01: Registro con validacion de email
    - E-02: Pasarela de pago con boleta digital
    - E-03: Gestion de stock en tiempo real
    - E-04: Calculo de ETA (tiempo estimado de entrega)
    - E-05: Validacion de cobertura geografica
    - E-06: Login con credenciales cifradas (bcrypt)
    - E-07: Roles y permisos diferenciados (RBAC)
    - E-08: Recuperacion de contrasena segura

Business (B-01 a B-14): Valor de negocio
    - B-01: Edicion de datos de contacto
    - B-02: Historial de pedidos
    - B-03: Carrito de compras con personalizacion
    - B-04: Resumen y confirmacion de pedido
    - B-05: Anulacion de pedidos con reembolso
    - B-06: CRUD de productos (admin)
    - B-07: Visualizacion del menu
    - B-08: Impresion automatica para cocina
    - B-09: Reportes de ventas
    - B-10: Ranking de productos
    - B-11: Exportacion a PDF
    - B-12: Email de confirmacion
    - B-13: Preferencias promocionales
    - B-14: Campanias segmentadas

Autor: Equipo de Desarrollo
Curso: Desarrollo Web y Movil - UNAB
Fecha: Diciembre 2025
============================================================================
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from config import settings
from database import init_db, AsyncSessionLocal
from models import Usuario
from auth import get_password_hash
from sqlalchemy import select
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
    
    # Crear usuario administrador por defecto si no existe
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Usuario).where(Usuario.email == "admin@lafornace.cl"))
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            print("Creando usuario administrador por defecto...")
            hashed_password = get_password_hash("admin123")
            new_admin = Usuario(
                email="admin@lafornace.cl",
                nombre="Administrador Sistema",
                telefono="+56912345678",
                direccion="Oficina Central",
                hashed_password=hashed_password,
                rol="administrador",
                email_verificado=True,
                activo=True
            )
            db.add(new_admin)
            await db.commit()
            print("Usuario administrador creado: admin@lafornace.cl / admin123")
        
        # Crear usuario cocinero por defecto si no existe
        result = await db.execute(select(Usuario).where(Usuario.email == "cocinero@lafornace.cl"))
        cocinero_user = result.scalar_one_or_none()
        
        if not cocinero_user:
            print("Creando usuario cocinero por defecto...")
            hashed_password = get_password_hash("cocina123")
            new_cocinero = Usuario(
                email="cocinero@lafornace.cl",
                nombre="Chef Mario",
                telefono="+56987654321",
                direccion="Cocina La Fornace",
                hashed_password=hashed_password,
                rol="cocinero",
                email_verificado=True,
                activo=True
            )
            db.add(new_cocinero)
            await db.commit()
            print("Usuario cocinero creado: cocinero@lafornace.cl / cocina123")
    
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# REGISTRAR ROUTERS
# ============================================================================
# Cada router agrupa endpoints relacionados a una funcionalidad especifica.
# Esta organizacion modular facilita el mantenimiento y testing del codigo.

# Router de Autenticacion y Usuarios (E-01, E-06, E-07, E-08, B-01)
app.include_router(auth.router)

# Router de Productos y Menu (B-06, B-07, E-03)
app.include_router(productos.router)

# Router de Carrito (B-03) y Pedidos (B-02, B-04, E-04, E-05)
app.include_router(carrito_pedidos.router_carrito)
app.include_router(carrito_pedidos.router_pedidos)

# Router de Anulaciones (B-05)
app.include_router(anulaciones.router)

# Router de Reportes (B-09, B-10, B-11)
app.include_router(reportes.router)

# Routers de Notificaciones y Campanias (B-08, B-12, B-13, B-14)
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
