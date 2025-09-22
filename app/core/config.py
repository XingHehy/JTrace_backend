import yaml
from pydantic import BaseModel
from functools import lru_cache
from pathlib import Path


class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    debug: bool = False
    log_level: str = "info"


class MySQLSettings(BaseModel):
    url: str


class RedisSettings(BaseModel):
    url: str


class JWTSettings(BaseModel):
    secret_key: str
    algorithm: str = "HS256"
    access_token_expires_minutes: int = 60 * 24


class UploadAccessSignatureSettings(BaseModel):
    enabled: bool = True
    secret_key: str
    expires_minutes: int = 60
    algorithm: str = "HS256"


class UploadSettings(BaseModel):
    base_dir: str = "uploads"
    max_file_size: int = 52428800  # 50MB
    allowed_image_types: list[str] = ["image/jpeg", "image/png", "image/gif", "image/webp", "image/jpg"]
    allowed_video_types: list[str] = ["video/mp4", "video/avi", "video/mov", "video/mkv", "video/webm"]
    access_signature: UploadAccessSignatureSettings
    directory_strategy: str = "date_user"  # date_user | user_date | simple
    create_thumbnails: bool = True


class AppSettings(BaseModel):
    server: ServerSettings
    mysql: MySQLSettings
    redis: RedisSettings
    jwt: JWTSettings
    upload: UploadSettings


@lru_cache
def load_settings() -> AppSettings:
    candidates = [
        Path("config.yaml"),
        Path(__file__).resolve().parents[3] / "config.yaml",
        Path(__file__).resolve().parents[2] / "config.yaml",
    ]
    for p in candidates:
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return AppSettings(**data)
    raise FileNotFoundError("config.yaml not found. Place it at project root.")
