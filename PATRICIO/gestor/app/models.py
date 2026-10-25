import datetime as dt
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine("sqlite:///./gestor.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    pw_hash = Column(String)
    role = Column(String, default="Administradora")

class Garment(Base):
    __tablename__ = "garments"
    id = Column(Integer, primary_key=True)
    sku = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    stock = Column(Integer, default=0)
    image = Column(String)
    palette = Column(JSON)      # [{h,s,v,pct,hex}] x3 (HSV: h 0-360, s/v 0-1)
    family = Column(String)     # Cálido | Frío | Neutro
    created = Column(DateTime, default=dt.datetime.utcnow)
