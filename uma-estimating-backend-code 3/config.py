from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/uma_estimating"

    # JWT
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # Google OAuth
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: str = "http://localhost:3000/auth/google/callback"

    # App
    app_name: str = "UMA Estimating Platform"
    debug: bool = False
    environment: str = "development"

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
