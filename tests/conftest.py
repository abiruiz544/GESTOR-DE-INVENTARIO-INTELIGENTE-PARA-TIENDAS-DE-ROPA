import io
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ.update(DATA_DIR=_tmp, DATABASE_URL=f"sqlite:///{_tmp}/test.db", ADMIN_EMAIL="admin@tienda.com",
                  ADMIN_PASSWORD="Admin12345", SEMBRAR_DEMO="0", MOSTRAR_CODIGO="1")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def cliente():
    return TestClient(app)


@pytest.fixture(scope="session")
def token(cliente):
    r = cliente.post("/api/auth/login", json={"email": "admin@tienda.com", "password": "Admin12345"})
    return {"Authorization": "Bearer " + r.json()["token"]}


def foto_prenda(color=(200, 30, 30)):
    """Camiseta roja sobre fondo blanco, para probar que el fondo se ignora."""
    im = Image.new("RGB", (300, 400), "white")
    ImageDraw.Draw(im).rectangle([70, 60, 230, 340], fill=color)
    b = io.BytesIO()
    im.save(b, "JPEG")
    return b.getvalue()
