"""Carga las 10 prendas de ejemplo (carpeta demo/) la primera vez que se arranca con la BD vacía."""
import os

from .color import familia_de_paleta, procesar_imagen
from .models import DATA_DIR, Prenda, SesionBD

CARPETA_DEMO = os.path.join(os.path.dirname(__file__), "..", "demo")

# archivo, sku, nombre, categoría, precio MXN, tallas {XS,S,M,L}
PRENDAS = [
    ("393faa32dc874636a7ca50c4687d2d3b.jpg", "P00001", "Playera café con puntos", "superior", 329, (0, 0, 0, 0)),
    ("5e40a73ba96845399b60b8a7a99a2731.jpg", "S000001", "Suéter animal print", "superior", 549, (1, 2, 1, 0)),
    ("f1194771734f4dc999d3516f8e1da7a3.jpg", "P00002", "Playera a cuadros", "superior", 359, (0, 2, 2, 1)),
    ("367118abcc60425984f4ff6c29891713.jpg", "Pa000001", "Pantalón de mezclilla", "inferior", 699, (1, 3, 3, 2)),
    ("d1779d97a73d4a80b3275c4f8971cf36.jpg", "A000001", "Abrigo a cuadros", "exterior", 1299, (0, 1, 2, 1)),
    ("193191d04dbd4837945a9a83ca2d3ea5.jpg", "Pa000002", "Pantalón estrellas rojas", "inferior", 749, (1, 2, 2, 1)),
    ("829d2bf7437d4379808907f6c52182cf.jpg", "B000001", "Blusa tirantes", "superior", 289, (2, 3, 2, 1)),
    ("597f5f61a87c46fab229d80d84f74acc.jpg", "P000003", "Playera verde rayas", "superior", 319, (1, 2, 3, 2)),
    ("4b6e592ddcce40cda14a2382931c09db.jpg", "B000002", "Blusa naranja", "superior", 399, (1, 1, 2, 0)),
    ("56c66f5d0b424792925cb64c917ac769.jpg", "S000002", "Suéter amarillo", "exterior", 599, (0, 2, 1, 1)),
]


def sembrar_demo():
    with SesionBD() as bd:
        if bd.query(Prenda).first():
            return
        for archivo, sku, nombre, cat, precio, (xs, s, m, l) in PRENDAS:
            ruta = os.path.join(CARPETA_DEMO, archivo)
            if not os.path.exists(ruta):
                continue
            with open(ruta, "rb") as f:
                original = f.read()
            png, paleta, estampado = procesar_imagen(original)
            base = archivo.rsplit(".", 1)[0]
            destino = os.path.join(DATA_DIR, "uploads")
            with open(os.path.join(destino, f"{base}.png"), "wb") as f:
                f.write(png)
            with open(os.path.join(destino, f"{base}_orig.jpg"), "wb") as f:
                f.write(original)
            tallas = {"XS": xs, "S": s, "M": m, "L": l}
            bd.add(Prenda(sku=sku, nombre=nombre, categoria=cat, genero="mujer", precio=precio, tallas=tallas,
                          existencias=sum(tallas.values()), ruta_imagen=f"/uploads/{base}_orig.jpg",
                          ruta_recorte=f"/uploads/{base}.png", paleta=paleta,
                          familia=familia_de_paleta(paleta), estampado=estampado))
        bd.commit()
