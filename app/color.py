"""Motor de color: segmenta la prenda (ignora el fondo), extrae su paleta y puntúa combinaciones."""
import colorsys
import io
import random

import cv2
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

LADO_TRABAJO = 400          # px; suficiente para segmentar y rápido
LADO_MAXIMO_GUARDADO = 900  # px; recorte que se guarda para catálogo y probador


# ---------------------------------------------------------------- Segmentación
def segmentar(rgb):
    """Devuelve una máscara booleana (True = prenda) del tamaño de `rgb`.

    1) Estima el color de fondo con el borde de la foto.
    2) Marca como fondo lo parecido a ese color que esté conectado con el borde.
    3) Refina con GrabCut para recuperar bordes y descartar sombras.
    """
    alto, ancho = rgb.shape[:2]
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    borde = np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])
    fondo = np.median(borde, axis=0)
    distancia = np.linalg.norm(lab - fondo, axis=2)

    candidato = (distancia < 14).astype(np.uint8)
    _, etiquetas = cv2.connectedComponents(candidato)
    en_borde = set(np.unique(np.concatenate(
        [etiquetas[0], etiquetas[-1], etiquetas[:, 0], etiquetas[:, -1]]))) - {0}
    es_fondo = np.isin(etiquetas, list(en_borde)) & (candidato == 1)

    gc = np.where(es_fondo, cv2.GC_PR_BGD, cv2.GC_PR_FGD).astype(np.uint8)
    gc[distancia > 30] = cv2.GC_FGD
    gc[es_fondo & (distancia < 6)] = cv2.GC_BGD
    try:
        bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
        cv2.grabCut(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), gc, None, bgd, fgd, 3,
                    cv2.GC_INIT_WITH_MASK)
        mascara = (gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)
    except cv2.error:
        mascara = ~es_fondo

    mascara = cv2.morphologyEx(mascara.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, comp, stats, _ = cv2.connectedComponentsWithStats(mascara)
    if n > 1:  # conserva solo las manchas relevantes (la prenda) y quita ruido
        mayor = stats[1:, cv2.CC_STAT_AREA].max()
        grandes = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= 0.05 * mayor]
        mascara = np.isin(comp, grandes).astype(np.uint8)
    # rellena huecos internos (botones, puntos blancos del estampado)
    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    relleno = np.zeros_like(mascara)
    cv2.drawContours(relleno, contornos, -1, 1, cv2.FILLED)
    mascara = relleno.astype(bool)
    if not 0.03 < mascara.mean() < 0.97:  # segmentación dudosa: usa toda la imagen
        mascara = np.ones((alto, ancho), bool)
    return mascara


def procesar_imagen(bytes_imagen):
    """Devuelve (png_recortado, paleta, estampado). Lanza ValueError si no es una imagen."""
    try:
        img = Image.open(io.BytesIO(bytes_imagen))
        img.load()
    except Exception as exc:
        raise ValueError("No se pudo leer la imagen") from exc
    img = img.convert("RGB")
    img.thumbnail((LADO_MAXIMO_GUARDADO, LADO_MAXIMO_GUARDADO))
    rgb = np.array(img)

    chica = img.copy()
    chica.thumbnail((LADO_TRABAJO, LADO_TRABAJO))
    rgb_chica = np.array(chica)
    mascara_chica = segmentar(rgb_chica)

    paleta = extraer_paleta(rgb_chica, mascara_chica)
    estampado = detectar_estampado(rgb_chica, mascara_chica, paleta)

    mascara = cv2.resize(mascara_chica.astype(np.uint8), (rgb.shape[1], rgb.shape[0]),
                         interpolation=cv2.INTER_LINEAR).astype(bool)
    alfa = cv2.GaussianBlur((mascara * 255).astype(np.uint8), (3, 3), 0)
    ys, xs = np.where(mascara)
    rgba = np.dstack([rgb, alfa])[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    salida = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(salida, "PNG", optimize=True)
    return salida.getvalue(), paleta, estampado


# --------------------------------------------------------------------- Paleta
def nombre_color(c):
    h, s, v = c["h"], c["s"], c["v"]
    if v < 0.2:
        return "Negro"
    if s < 0.12:
        return "Blanco" if v > 0.85 else ("Gris claro" if v > 0.6 else "Gris")
    if 15 <= h < 50 and s < 0.45 and v > 0.6:
        return "Beige"
    if 10 <= h < 45 and v < 0.6:
        return "Café"
    if 50 <= h < 90 and v < 0.6:
        return "Verde olivo"
    for tope, nombre in [(15, "Rojo"), (35, "Naranja"), (65, "Amarillo"), (160, "Verde"),
                         (200, "Turquesa"), (255, "Azul"), (290, "Morado"), (335, "Rosa"), (361, "Rojo")]:
        if h < tope:
            return nombre + (" oscuro" if v < 0.4 and nombre != "Rojo" else "")
    return "Rojo"


def extraer_paleta(rgb, mascara):
    """Hasta 3 colores dominantes calculados SOLO con los píxeles de la prenda."""
    pix = rgb[mascara]
    if len(pix) > 6000:
        pix = pix[np.random.default_rng(42).choice(len(pix), 6000, replace=False)]
    k = int(min(3, len(np.unique(pix, axis=0))))
    lab = cv2.cvtColor(pix.reshape(-1, 1, 3), cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(float)
    modelo = KMeans(n_clusters=k, n_init=5, random_state=42).fit(lab)
    paleta = []
    for g in range(k):
        grupo = modelo.labels_ == g
        r, gg, b = (float(x) for x in pix[grupo].mean(axis=0) / 255)
        h, s, v = colorsys.rgb_to_hsv(r, gg, b)
        c = {"h": round(h * 360, 1), "s": round(s, 3), "v": round(v, 3),
             "pct": round(float(grupo.mean()) * 100, 1),
             "hex": "#%02x%02x%02x" % (int(r * 255), int(gg * 255), int(b * 255))}
        c["nombre"] = nombre_color(c)
        paleta.append(c)
    paleta.sort(key=lambda c: -c["pct"])
    return [c for c in paleta if c["pct"] >= 4] or paleta[:1]


def detectar_estampado(rgb, mascara, paleta):
    """True si la prenda tiene rayas, cuadros o puntos (mucho borde interno)."""
    bordes = cv2.Canny(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), 60, 140) > 0
    interior = cv2.erode(mascara.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    densidad = bordes[interior].mean() if interior.any() else 0
    return bool(densidad > 0.07 and len(paleta) >= 2)


# ----------------------------------------------------------------- Armonía
def es_neutro(c):
    return c["s"] < 0.18 or c["v"] < 0.2


def es_neutro_suave(c):
    """Beige, café, azul marino y mezclilla se comportan como neutros en moda."""
    if es_neutro(c):
        return True
    h, s, v = c["h"], c["s"], c["v"]
    return (10 <= h < 50 and s < 0.5) or (190 <= h < 250 and (v < 0.4 or s < 0.5))


def familia_de_color(c):
    if es_neutro(c):
        return "Neutro"
    return "Cálido" if c["h"] < 70 or c["h"] >= 300 else "Frío"


def familia_de_paleta(paleta):
    puntos = {}
    for c in paleta:
        puntos[familia_de_color(c)] = puntos.get(familia_de_color(c), 0) + c["pct"]
    return max(puntos, key=puntos.get)


def distancia_matiz(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def armonia(a, b):
    """(tipo, puntaje 0-100) entre dos colores."""
    if es_neutro(a) and es_neutro(b):
        return "Neutros", 80 if abs(a["v"] - b["v"]) > 0.25 else 66
    if es_neutro(a) or es_neutro(b):
        return "Neutro + color", 84
    d = distancia_matiz(a["h"], b["h"])
    dv = abs(a["v"] - b["v"])
    if d <= 12:
        return "Monocromática", max(60, 92 - dv * 25) if dv > 0.12 else 70
    if d <= 45:
        return "Análoga", 90 - d * 0.35
    if abs(d - 180) <= 25:
        return "Complementaria", 93 - abs(d - 180) * 0.5
    if abs(d - 120) <= 20:
        return "Triádica", 70
    if es_neutro_suave(a) or es_neutro_suave(b):
        return "Base neutra suave", 76
    return "Contraste fuerte", 38


def comparar(paleta_a, paleta_b, estampado_a=False, estampado_b=False):
    """Puntúa dos prendas con sus paletas ponderadas por área (regla 60-30-10)."""
    total = suma = 0.0
    tipos = {}
    for ca in paleta_a:
        for cb in paleta_b:
            peso = ca["pct"] * cb["pct"]
            tipo, p = armonia(ca, cb)
            suma += peso * p
            total += peso
            tipos[tipo] = tipos.get(tipo, 0) + peso
    puntaje = suma / total if total else 0
    if estampado_a and estampado_b:
        puntaje -= 14  # dos estampados compiten entre sí
    return round(max(0, min(100, puntaje))), max(tipos, key=tipos.get)


def veredicto(puntaje):
    if puntaje >= 85:
        return "Excelente"
    if puntaje >= 72:
        return "Buena"
    if puntaje >= 58:
        return "Regular"
    return "Mala"


COMPLEMENTARIAS = {"superior": ["inferior", "exterior"], "inferior": ["superior", "exterior"],
                   "exterior": ["superior", "inferior"]}


def genero_compatible(a, b):
    return a == b or "unisex" in (a, b)


def sugerir_outfits(base, todas, variar=False, por_categoria=2):
    """Mejores prendas con stock para completar el outfit, máximo `por_categoria` por categoría."""
    candidatas = []
    for otra in todas:
        if otra.id == base.id or otra.existencias <= 0 or otra.categoria not in COMPLEMENTARIAS.get(base.categoria, []) \
                or not genero_compatible(getattr(base, "genero", "mujer"), getattr(otra, "genero", "mujer")):
            continue
        p, tipo = comparar(base.paleta, otra.paleta, base.estampado, otra.estampado)
        if variar:
            p = max(0, min(100, p + random.uniform(-5, 5)))
        candidatas.append({"prenda": otra, "tipo": tipo, "afinidad": round(p), "veredicto": veredicto(round(p))})
    candidatas.sort(key=lambda r: -r["afinidad"])
    salida, cuenta = [], {}
    for r in candidatas:
        c = r["prenda"].categoria
        if r["afinidad"] >= 58 and cuenta.get(c, 0) < por_categoria:
            salida.append(r)
            cuenta[c] = cuenta.get(c, 0) + 1
    return salida
