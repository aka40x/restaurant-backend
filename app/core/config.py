"""Đọc cấu hình từ file .env (hoặc biến môi trường).

Muốn thêm cấu hình mới: thêm 1 dòng vào class Settings + thêm vào .env.example.
"""
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "Quản lý nhà hàng API"

    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3307
    DB_USER: str = "app_user"
    DB_PASSWORD: str = "app_password"
    DB_NAME: str = "app_db"
    
    # ---- Đăng nhập (JWT) ----
    # SECRET_KEY dùng để ký token. Tạo chuỗi ngẫu nhiên: python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY: str = "doi-chuoi-nay-trong-file-env"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Chuỗi các origin cách nhau bằng dấu phẩy, hoặc "*"
    CORS_ORIGINS: str = "*"

    @property
    def database_url(self) -> str:
        # mysql+pymysql://user:password@host:port/database
        return (
            f"mysql+pymysql://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
