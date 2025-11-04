"""
Configuración de la aplicación FastAPI
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Configuración global de la aplicación"""
    
    # Database
    DATABASE_URL: str
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    # CORS
    ALLOWED_ORIGINS: str
    
    # Email
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    EMAIL_FROM: str
    
    # Transbank (Pasarela de pago)
    TRANSBANK_API_URL: str
    TRANSBANK_COMMERCE_CODE: str
    TRANSBANK_API_KEY: str
    
    # Storage
    STORAGE_TYPE: str
    STORAGE_PATH: str
    
    # App
    APP_NAME: str
    APP_VERSION: str
    DEBUG: bool
    RADIO_COBERTURA_KM: float
    
    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
