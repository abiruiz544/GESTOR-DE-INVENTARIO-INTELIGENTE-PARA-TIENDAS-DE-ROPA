from app.color import armonia, comparar, procesar_imagen, veredicto
from tests.conftest import foto_prenda


def test_fondo_blanco_no_entra_en_la_paleta():
    _, paleta, _ = procesar_imagen(foto_prenda())
    assert paleta[0]["nombre"] == "Rojo" and paleta[0]["pct"] > 90
    assert all(c["nombre"] != "Blanco" for c in paleta)


def test_recorte_tiene_transparencia():
    from io import BytesIO
    from PIL import Image
    png, _, _ = procesar_imagen(foto_prenda())
    assert Image.open(BytesIO(png)).mode == "RGBA"


def test_armonias():
    azul = {"h": 220, "s": .7, "v": .6, "pct": 100}
    naranja = {"h": 35, "s": .8, "v": .9, "pct": 100}
    negro = {"h": 0, "s": 0, "v": .05, "pct": 100}
    assert armonia(azul, naranja)[0] == "Complementaria"
    assert armonia(azul, negro)[0] == "Neutro + color"


def test_estampados_se_penalizan_y_veredictos():
    a = [{"h": 10, "s": .6, "v": .6, "pct": 100}]
    assert comparar(a, a, True, True)[0] < comparar(a, a)[0]
    assert veredicto(90) == "Excelente" and veredicto(40) == "Mala"
