import io, colorsys, random
import cv2, numpy as np
from PIL import Image
from sklearn.cluster import KMeans

def analyze(data: bytes):
    """Redimensiona, convierte a HSV y aplica K-Means (K=3). Devuelve 3 colores ordenados por presencia."""
    im = Image.open(io.BytesIO(data)).convert("RGB"); im.thumbnail((100, 100))
    hsv = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2HSV).reshape(-1, 3).astype(float)
    h, s, v = hsv[:, 0] * 2, hsv[:, 1] / 255, hsv[:, 2] / 255      # OpenCV: H 0-179
    rad = np.radians(h)
    X = np.c_[s * np.cos(rad), s * np.sin(rad), v]                  # el matiz es circular: se proyecta a un cono
    km = KMeans(3, n_init=10, random_state=42).fit(X)
    out = []
    for k in range(3):
        m = km.labels_ == k
        if not m.any(): continue
        hh = float(np.degrees(np.arctan2(np.sin(rad[m]).mean(), np.cos(rad[m]).mean())) % 360)
        c = dict(h=round(hh, 1), s=round(float(s[m].mean()), 3), v=round(float(v[m].mean()), 3), pct=round(float(m.mean()) * 100, 1))
        r, g, b = colorsys.hsv_to_rgb(hh / 360, c["s"], c["v"])
        c["hex"] = "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))
        out.append(c)
    return sorted(out, key=lambda c: -c["pct"])

def neutral(c): return c["s"] < .18 or c["v"] < .2
def color_family(c): return "Neutro" if neutral(c) else ("Cálido" if c["h"] < 70 or c["h"] >= 300 else "Frío")

def family(palette):
    votes = {}
    for c in palette: votes[color_family(c)] = votes.get(color_family(c), 0) + c["pct"]
    return max(votes, key=votes.get)

def hue_dist(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)

def harmony(a, b):
    """Armonías de Itten por distancia angular en Hue. Devuelve (tipo, afinidad %)."""
    if neutral(a) or neutral(b):
        return ("Monocromática", 72 if neutral(a) and neutral(b) else 60)
    d = hue_dist(a["h"], b["h"])
    opts = [("Complementaria", 98 - abs(d - 180) * 1.2 if abs(d - 180) <= 30 else 0),
            ("Análoga", 96 - d * 0.9 if 10 < d <= 45 else 0),
            ("Monocromática", 98 - d * 2 - abs(a["v"] - b["v"]) * 10 if d <= 10 else 0)]
    return max(opts, key=lambda o: o[1])

def recommend(base, others, refresh=False):
    base_c = next((c for c in base.palette if not neutral(c)), base.palette[0])
    res = []
    for g in others:
        if g.id == base.id or g.stock <= 0: continue
        t, p = max((harmony(base_c, c) for c in g.palette), key=lambda x: x[1])
        if p >= 50: res.append(dict(garment=g, type=t, affinity=round(p + (random.uniform(-6, 6) if refresh else 0))))
    res.sort(key=lambda r: -r["affinity"])
    return res[:6]
