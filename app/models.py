import datetime
import os
import shutil

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, create_engine, inspect
from sqlalchemy.orm import declarative_base, sessionmaker


def cargar_variables_de_entorno():
    """Lee el archivo .env de la raíz del proyecto (sin dependencias extra)."""
    ruta_env = os.path.join(os.path.dirname(__file__), "..", ".env")
    if not os.path.exists(ruta_env):
        return
    with open(ruta_env, encoding="utf-8-sig") as archivo:
        for linea in archivo:
            linea = linea.split(" #")[0].strip()
            if "=" in linea and not linea.startswith("#"):
                nombre_variable, valor = linea.split("=", 1)
                os.environ.setdefault(nombre_variable.strip(), valor.strip())


cargar_variables_de_entorno()

DATA_DIR = os.getenv("DATA_DIR", "data")
os.makedirs(os.path.join(DATA_DIR, "uploads"), exist_ok=True)

# Primera vez (o servidor nuevo en la nube): copia el catálogo inicial (prendas e imágenes, sin cuentas de usuario)
RUTA_BD = os.path.join(DATA_DIR, "inventario.db")
CARPETA_INICIAL = os.path.join(os.path.dirname(__file__), "..", "datos_iniciales")
if not os.path.exists(RUTA_BD) and os.path.isdir(CARPETA_INICIAL) and not os.getenv("DATABASE_URL"):
    shutil.copytree(CARPETA_INICIAL, DATA_DIR, dirs_exist_ok=True)

motor_bd = create_engine(
    os.getenv("DATABASE_URL", "sqlite:///" + os.path.abspath(RUTA_BD)),  # ruta absoluta: sirve en Windows, Linux y discos de la nube
    connect_args={"check_same_thread": False},
)
SesionBD = sessionmaker(bind=motor_bd, autoflush=False)
BaseModelo = declarative_base()

TALLAS = ["XS", "S", "M", "L"]  # Extra pequeña, Chica, Mediana, Grande
CATEGORIAS = ["superior", "inferior", "exterior"]
GENEROS = ["mujer", "hombre", "unisex"]
ROL_ADMIN = "Administrador"
ROL_CLIENTE = "Cliente"


class Usuario(BaseModelo):
    """Cuenta de acceso: el administrador y los clientes registrados."""
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    correo = Column(String, unique=True, index=True, nullable=False)
    contrasena_hash = Column(String, nullable=False)  # formato "sal$hash" (PBKDF2-SHA256); nunca se guarda la contraseña real
    rol = Column(String, default=ROL_CLIENTE, index=True)
    fecha_registro = Column(DateTime, default=datetime.datetime.utcnow)


class Prenda(BaseModelo):
    __tablename__ = "prendas"
    id = Column(Integer, primary_key=True)
    sku = Column(String, unique=True, index=True)
    nombre = Column(String, index=True)
    categoria = Column(String, index=True, default="superior")
    genero = Column(String, index=True, default="mujer")
    precio = Column(Float, default=0.0)
    tallas = Column(JSON, default=dict)        # {"XS": 2, "S": 3, "M": 0, "L": 1}
    existencias = Column(Integer, default=0)   # suma de tallas (se recalcula)
    ruta_imagen = Column(String)               # foto original
    ruta_recorte = Column(String)              # PNG sin fondo (catálogo y probador)
    paleta = Column(JSON)
    familia = Column(String, index=True)
    estampado = Column(Boolean, default=False)
    fecha_registro = Column(DateTime, default=datetime.datetime.utcnow)


class OutfitGuardado(BaseModelo):
    """Combinación de prendas que un usuario guardó en «Mis outfits»."""
    __tablename__ = "outfits_guardados"
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, index=True, nullable=False)  # dueño del outfit
    nombre = Column(String, nullable=False)
    prendas = Column(JSON, default=dict)   # {"superior": id_prenda, "inferior": id_prenda, "exterior": id_prenda}
    ajustes = Column(JSON, default=dict)   # {"superior": {"s": 1.0, "y": 0.0}, ...} tamaño y altura en el probador
    puntaje = Column(Integer, default=0)
    fecha_registro = Column(DateTime, default=datetime.datetime.utcnow)


def preparar_base_de_datos():
    """Crea las tablas. Si la tabla `usuarios` es de la versión anterior (sin correo), se recrea:
    solo contenía al administrador, que se vuelve a crear desde el archivo .env. Las prendas no se tocan."""
    inspector = inspect(motor_bd)
    if "usuarios" in inspector.get_table_names():
        columnas = {columna["name"] for columna in inspector.get_columns("usuarios")}
        if "correo" not in columnas:
            Usuario.__table__.drop(motor_bd)
    BaseModelo.metadata.create_all(motor_bd)
