from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "SnapGather API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Security
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_DAYS: int = 7

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # CORS — stored as a plain comma-separated string in .env, parsed here
    ALLOWED_ORIGINS_STR: str = "http://localhost:3000"

    # Frontend base URL
    FRONTEND_URL: str = "http://localhost:3000"

    # Upload limits
    MAX_UPLOAD_SIZE: int = 10_485_760
    MAX_PHOTOS_PER_GUEST: int = 15
    JPEG_COMPRESSION_QUALITY: int = 80

    # Storage buckets
    STORAGE_BUCKET_PHOTOS: str = "event-photos"
    STORAGE_BUCKET_QR: str = "qr-codes"

    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """
        Parse origins from the env string safely.
        Handles both formats people might use in .env:
          ALLOWED_ORIGINS_STR=http://localhost:3000
          ALLOWED_ORIGINS_STR=http://localhost:3000,https://myapp.vercel.app
        """
        raw = self.ALLOWED_ORIGINS_STR.strip()
        # Strip surrounding brackets/quotes if someone pasted JSON array format
        raw = raw.strip("[]").replace('"', "").replace("'", "")
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
