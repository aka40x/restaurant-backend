# Moi nguoi tu sua YOUR_PASSWORD thanh mat khau MySQL tren may minh.
# Sau khi sua xong, chay 1 lan:  git update-index --skip-worktree backend/database.py
# de Git bo qua thay doi nay (tranh lo mat khau khi commit).
DATABASE_URL = "mysql+pymysql://root:YOUR_PASSWORD@localhost/restaurant_db"

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
