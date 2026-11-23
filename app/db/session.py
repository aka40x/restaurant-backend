"""Kết nối MySQL bằng SQLAlchemy."""
from sqlalchemy import create_engine
import ssl
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# engine: "đường ống" tới MySQL. pool_pre_ping giúp tự nối lại khi MySQL ngắt kết nối cũ.
# DB_SSL=true: kết nối MySQL qua TLS, kiểm tra chứng chỉ bằng bộ CA có sẵn của hệ điều hành.
_connect_args = {"ssl": ssl.create_default_context()} if settings.DB_SSL else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=280, connect_args=_connect_args)

# SessionLocal(): mỗi lần gọi tạo ra 1 phiên làm việc với DB
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Mọi model (bảng) đều kế thừa từ Base."""


def get_db():
    """Dependency cho FastAPI: mở session cho mỗi request và luôn đóng lại sau đó.

    Dùng trong router:  db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
