"""
================================================================================
Router de Autenticacion y Usuarios - Pizzeria La Fornace
================================================================================

Este router maneja toda la logica de autenticacion y gestion de usuarios.
Es el punto de entrada para registro, login, perfil y recuperacion de password.

Endpoints Implementados:
------------------------
POST   /register              - Registro de nuevos usuarios (E-01)
POST   /login                 - Inicio de sesion con JWT (E-06)
GET    /me                    - Obtener perfil actual (B-01)
PUT    /me                    - Actualizar perfil (B-01)
PUT    /me/contacto           - Actualizar datos de contacto (B-01)
POST   /password-recovery/*   - Flujo de recuperacion (E-08)
POST   /verify-email/{token}  - Verificacion de email (E-01)

Seguridad:
----------
- Passwords hasheados con bcrypt
- Tokens JWT con expiracion (30 min por defecto)
- Proteccion contra enumeracion de usuarios
- Tokens de recuperacion de un solo uso

Historias de Usuario:
---------------------
E-01: Registro de Cliente
E-06: Login con Credenciales
E-07: RBAC (roles validados en dependencias)
E-08: Recuperacion de Password
B-01: Gestion de Perfil/Contacto

Dependencias:
-------------
- auth.py: Funciones de hashing y JWT
- models.py: Entidad Usuario
- schemas.py: DTOs de entrada/salida
================================================================================
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import secrets
from datetime import datetime, timedelta

from database import get_db
from models import Usuario, PreferenciaPromo
from schemas import (
    UsuarioCreate, UsuarioResponse, UsuarioUpdate, ContactoUpdateInput,
    TokenResponse, RecuperacionPasswordRequest, RecuperacionPasswordReset,
    UsuarioLogin, Response
)
from auth import (
    get_password_hash, verify_password, create_access_token,
    create_recovery_token, verify_recovery_token, get_current_user
)

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])


@router.post("/register", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UsuarioCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Registrar nuevo usuario (E-01)
    
    Validaciones:
    - Email único y con formato válido
    - Password con mínimo 8 caracteres
    - Genera token de verificación de email
    """
    # Verificar si el email ya existe
    result = await db.execute(select(Usuario).where(Usuario.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # Crear usuario
    hashed_password = get_password_hash(user_data.password)
    verification_token = secrets.token_urlsafe(32)
    
    new_user = Usuario(
        email=user_data.email,
        nombre=user_data.nombre,
        telefono=user_data.telefono,
        direccion=user_data.direccion,
        hashed_password=hashed_password,
        token_verificacion=verification_token,
        rol="cliente"
    )
    
    db.add(new_user)
    await db.flush()
    
    # Crear preferencias promocionales por defecto (B-13)
    preferencias = PreferenciaPromo(
        cliente_id=new_user.id,
        email_opt_in=True,
        sms_opt_in=False,
        whatsapp_opt_in=False
    )
    db.add(preferencias)
    
    await db.commit()
    await db.refresh(new_user)
    
    # TODO: Enviar email de verificación
    
    return new_user


@router.post("/login", response_model=TokenResponse)
async def login(
    user_data: UsuarioLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Iniciar sesión con credenciales (E-06)
    
    Validaciones:
    - Verificar password con hash
    - Bloqueo tras intentos fallidos (implementar)
    - Generar JWT token
    """
    # Buscar usuario por email
    result = await db.execute(select(Usuario).where(Usuario.email == user_data.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o password incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo. Contacte al administrador"
        )
    
    # Crear token de acceso
    access_token = create_access_token(data={"sub": user.email})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UsuarioResponse.model_validate(user)
    )


@router.get("/me", response_model=UsuarioResponse)
async def get_current_user_profile(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener perfil del usuario actual (B-01)
    """
    return current_user


@router.put("/me", response_model=UsuarioResponse)
async def update_profile(
    user_update: UsuarioUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualizar perfil del usuario (B-01)
    
    Permite actualizar:
    - Nombre
    - Teléfono
    - Dirección
    """
    if user_update.nombre is not None:
        current_user.nombre = user_update.nombre
    if user_update.telefono is not None:
        current_user.telefono = user_update.telefono
    if user_update.direccion is not None:
        current_user.direccion = user_update.direccion
    
    current_user.fecha_actualizacion = datetime.utcnow()
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.put("/me/contacto", response_model=UsuarioResponse)
async def update_contact_info(
    contacto_update: ContactoUpdateInput,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualizar datos de contacto específicamente (B-01)
    
    Validaciones:
    - Email único si se modifica
    - Formato válido de datos
    """
    if contacto_update.email is not None:
        # Verificar que el nuevo email no esté en uso
        result = await db.execute(
            select(Usuario).where(
                Usuario.email == contacto_update.email,
                Usuario.id != current_user.id
            )
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está en uso por otro usuario"
            )
        
        current_user.email = contacto_update.email
        current_user.email_verificado = False  # Requerir nueva verificación
    
    if contacto_update.telefono is not None:
        current_user.telefono = contacto_update.telefono
    
    if contacto_update.direccion is not None:
        current_user.direccion = contacto_update.direccion
    
    current_user.fecha_actualizacion = datetime.utcnow()
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.post("/password-recovery/request", response_model=Response)
async def request_password_recovery(
    request_data: RecuperacionPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Solicitar recuperación de password (E-08)
    
    Genera token único con expiración y envía email
    """
    # Buscar usuario
    result = await db.execute(select(Usuario).where(Usuario.email == request_data.email))
    user = result.scalar_one_or_none()
    
    # Siempre responder con éxito para evitar enumeración de usuarios
    if not user:
        return Response(
            status=200,
            message="Si el email existe, recibirás instrucciones para recuperar tu password"
        )
    
    # Generar token de recuperación
    recovery_token = create_recovery_token(user.email)
    
    # Guardar token en BD con expiración
    user.token_recuperacion = recovery_token
    user.token_expiracion = datetime.utcnow() + timedelta(hours=1)
    
    await db.commit()
    
    # TODO: Enviar email con enlace de recuperación
    # URL: https://domain.com/reset-password?token={recovery_token}
    
    return Response(
        status=200,
        message="Si el email existe, recibirás instrucciones para recuperar tu password"
    )


@router.post("/password-recovery/reset", response_model=Response)
async def reset_password(
    reset_data: RecuperacionPasswordReset,
    db: AsyncSession = Depends(get_db)
):
    """
    Resetear password con token (E-08)
    
    Validaciones:
    - Token válido y no expirado
    - Token no reutilizado
    """
    # Verificar token
    email = verify_recovery_token(reset_data.token)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o expirado"
        )
    
    # Buscar usuario
    result = await db.execute(select(Usuario).where(Usuario.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Verificar que el token coincida y no haya expirado
    if user.token_recuperacion != reset_data.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido"
        )
    
    if user.token_expiracion and user.token_expiracion < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token expirado. Solicita un nuevo enlace de recuperación"
        )
    
    # Actualizar password
    user.hashed_password = get_password_hash(reset_data.nueva_password)
    user.token_recuperacion = None
    user.token_expiracion = None
    
    await db.commit()
    
    return Response(
        status=200,
        message="Password actualizado exitosamente"
    )


@router.post("/verify-email/{token}", response_model=Response)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Verificar email con token (E-01)
    """
    result = await db.execute(select(Usuario).where(Usuario.token_verificacion == token))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de verificación inválido"
        )
    
    user.email_verificado = True
    user.token_verificacion = None
    
    await db.commit()
    
    return Response(
        status=200,
        message="Email verificado exitosamente"
    )
