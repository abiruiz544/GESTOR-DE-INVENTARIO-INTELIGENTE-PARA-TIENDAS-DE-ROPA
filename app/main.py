import json
import os
import secrets
import uuid
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import seguridad as seg
from .color import comparar, familia_de_paleta, procesar_imagen, sugerir_outfits, veredicto
from .models import (CATEGORIAS, DATA_DIR, GENEROS, ROL_ADMIN, ROL_CLIENTE, TALLAS, OutfitGuardado, Prenda, SesionBD, Usuario,
                     motor_bd, preparar_base_de_datos)

TAMANO_MAXIMO_IMAGEN = 10 * 1024 * 1024
RUTA_UPLOADS = os.path.join(DATA_DIR, "uploads")
CARPETA_ESTATICA = os.path.join(os.path.dirname(__file__), "static")

preparar_base_de_datos()
# Sin /docs ni /openapi.json: no se publica el mapa de la API
app = FastAPI(title="Gestor de Inventario Inteligente", version="4.0.0", docs_url=None, redoc_url=None, openapi_url=None)

POLITICA_CONTENIDO = ("default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; "
                      "style-src 'self' 'unsafe-inline'; "
                      "script-src 'self' https://cdn.jsdelivr.net 'wasm-unsafe-eval'; "
                      "connect-src 'self' https://cdn.jsdelivr.net https://storage.googleapis.com; "
                      "worker-src 'self' blob:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")


@app.middleware("http")
async def cabeceras_seguridad(request: Request, call_next):
    respuesta = await call_next(request)
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    respuesta.headers["X-Frame-Options"] = "DENY"
    respuesta.headers["Referrer-Policy"] = "same-origin"
    respuesta.headers["Permissions-Policy"] = "camera=(self)"
    respuesta.headers["Content-Security-Policy"] = POLITICA_CONTENIDO
    if request.url.path.startswith("/api/"):
        respuesta.headers["Cache-Control"] = "no-store"  # las respuestas con datos personales no se guardan en caché
    return respuesta


def obtener_bd():
    with SesionBD() as bd:
        yield bd


def sembrar_admin():
    """Crea el administrador inicial con correo y contraseña tomados del entorno (.env)."""
    with SesionBD() as bd:
        if bd.query(Usuario).filter_by(rol=ROL_ADMIN).first():
            return
        correo = os.getenv("ADMIN_EMAIL", "admin@tienda.com").strip().lower()
        contrasena = os.getenv("ADMIN_PASSWORD")
        if not contrasena:
            contrasena = secrets.token_urlsafe(9)
            print(f"[AVISO] ADMIN_PASSWORD no definida. Contraseña temporal para '{correo}': {contrasena}")
        bd.add(Usuario(nombre="Administrador", correo=correo, contrasena_hash=seg.hash_contrasena(contrasena), rol=ROL_ADMIN))
        bd.commit()


def usuario_actual(authorization: str = Header(""), bd: Session = Depends(obtener_bd)):
    """Cualquier persona con sesión iniciada (cliente o administrador)."""
    id_usuario = seg.usuario_de_token(authorization.replace("Bearer ", ""))
    usuario = bd.get(Usuario, id_usuario) if id_usuario else None
    if not usuario:
        raise HTTPException(401, "Sesión no válida")
    return usuario


def admin_actual(usuario: Usuario = Depends(usuario_actual)):
    """Solo el administrador: los clientes reciben 403 en las rutas /api/admin."""
    if usuario.rol != ROL_ADMIN:
        raise HTTPException(403, "Acceso solo para administración")
    return usuario


def a_dict(p: Prenda):
    return {
        "id": p.id, "sku": p.sku, "name": p.nombre, "category": p.categoria, "gender": p.genero or "mujer", "price": p.precio,
        "sizes": {t: (p.tallas or {}).get(t, 0) for t in TALLAS}, "stock": p.existencias,
        "image": p.ruta_recorte or p.ruta_imagen, "original": p.ruta_imagen, "palette": p.paleta,
        "family": p.familia, "pattern": p.estampado, "created": p.fecha_registro.isoformat(),
    }


def normalizar_tallas(crudo):
    try:
        datos = crudo if isinstance(crudo, dict) else json.loads(crudo or "{}")
        return {t: max(0, int(datos.get(t, 0))) for t in TALLAS}
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(400, "Tallas inválidas")


# ------------------------------------------------------------------ Autenticación
class Registro(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=1, max_length=128)


class Login(BaseModel):
    email: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=128)


class Olvido(BaseModel):
    email: str = Field(min_length=1, max_length=120)


class Reinicio(BaseModel):
    email: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=1, max_length=128)


def clave_de_intentos(request: Request, correo: str):
    direccion_ip = request.client.host if request.client else "?"
    return f"{direccion_ip}|{correo}"


MENSAJE_CONTRASENA = "La contraseña debe tener al menos 8 caracteres, con letras y números"


@app.post("/api/auth/register")
def registrar_cliente(datos: Registro, request: Request, bd: Session = Depends(obtener_bd)):
    correo = datos.email.strip().lower()
    if not seg.correo_valido(correo):
        raise HTTPException(400, "Correo no válido")
    if not seg.contrasena_segura(datos.password):
        raise HTTPException(400, MENSAJE_CONTRASENA)
    clave = "registro|" + (request.client.host if request.client else "?")
    espera = seg.segundos_de_bloqueo(clave)
    if espera:
        raise HTTPException(429, f"Demasiados intentos. Espera {espera} s")
    if bd.query(Usuario).filter_by(correo=correo).first():
        seg.registrar_fallo(clave)
        raise HTTPException(400, "Ya existe una cuenta con ese correo")
    bd.add(Usuario(nombre=datos.name.strip(), correo=correo, contrasena_hash=seg.hash_contrasena(datos.password), rol=ROL_CLIENTE))
    bd.commit()
    return {"ok": True, "message": "Cuenta creada. Ahora inicia sesión."}


@app.post("/api/auth/login")
def iniciar_sesion(datos: Login, request: Request, bd: Session = Depends(obtener_bd)):
    correo = datos.email.strip().lower()
    clave = clave_de_intentos(request, correo)
    espera = seg.segundos_de_bloqueo(clave)
    if espera:
        raise HTTPException(429, f"Demasiados intentos. Espera {espera} s e inténtalo de nuevo")
    usuario = bd.query(Usuario).filter_by(correo=correo).first()
    if not usuario or not seg.verificar_contrasena(datos.password, usuario.contrasena_hash):
        seg.registrar_fallo(clave)
        raise HTTPException(401, "Correo o contraseña incorrectos")
    seg.limpiar_fallos(clave)
    return {"token": seg.crear_sesion(usuario.id), "name": usuario.nombre, "role": usuario.rol}


@app.post("/api/auth/logout")
def cerrar_sesion(authorization: str = Header("")):
    seg.sesiones.pop(authorization.replace("Bearer ", ""), None)
    return {"ok": True}


@app.post("/api/auth/forgot")
def olvide_contrasena(datos: Olvido, request: Request, bd: Session = Depends(obtener_bd)):
    correo = datos.email.strip().lower()
    clave = "olvido|" + clave_de_intentos(request, correo)
    if seg.segundos_de_bloqueo(clave):
        raise HTTPException(429, "Demasiadas solicitudes. Espera un minuto")
    seg.registrar_fallo(clave)
    # Misma respuesta exista o no la cuenta, para no revelar qué correos están registrados
    respuesta = {"ok": True, "message": "Si el correo está registrado, se generó un código de 6 dígitos (vigencia: 10 min)."}
    if bd.query(Usuario).filter_by(correo=correo).first():
        codigo = seg.generar_codigo(correo)
        respuesta["channel"] = seg.enviar_codigo(correo, codigo)
        if os.getenv("MOSTRAR_CODIGO") == "1":  # solo para demostraciones en clase
            respuesta["demo_code"] = codigo
    return respuesta


@app.post("/api/auth/reset")
def restablecer_contrasena(datos: Reinicio, bd: Session = Depends(obtener_bd)):
    correo = datos.email.strip().lower()
    if not seg.contrasena_segura(datos.new_password):
        raise HTTPException(400, MENSAJE_CONTRASENA)
    usuario = bd.query(Usuario).filter_by(correo=correo).first()
    if not usuario or not seg.validar_codigo(correo, datos.code):
        raise HTTPException(400, "Código inválido o vencido")
    usuario.contrasena_hash = seg.hash_contrasena(datos.new_password)
    bd.commit()
    return {"ok": True, "message": "Contraseña actualizada. Ya puedes iniciar sesión."}


# ------------------------------------------------------------ Vista cliente (requiere sesión)
@app.get("/api/tienda/prendas")
def tienda_listar(q: str = "", categoria: str = "todas", genero: str = "todos", bd: Session = Depends(obtener_bd), _=Depends(usuario_actual)):
    consulta = bd.query(Prenda)
    if q:
        consulta = consulta.filter(Prenda.nombre.ilike(f"%{q}%"))
    if categoria in CATEGORIAS:
        consulta = consulta.filter(Prenda.categoria == categoria)
    if genero in ("mujer", "hombre"):  # lo unisex aparece en ambos
        consulta = consulta.filter(Prenda.genero.in_([genero, "unisex"]))
    return [a_dict(p) for p in consulta.order_by(Prenda.fecha_registro.desc())]


@app.get("/api/tienda/prendas/{id_prenda}/outfits")
def tienda_outfits(id_prenda: int, refresh: bool = False, bd: Session = Depends(obtener_bd), _=Depends(usuario_actual)):
    base = bd.get(Prenda, id_prenda)
    if not base:
        raise HTTPException(404, "No existe")
    return [{"type": s["tipo"], "affinity": s["afinidad"], "verdict": s["veredicto"], "garment": a_dict(s["prenda"])}
            for s in sugerir_outfits(base, bd.query(Prenda).all(), refresh)]


def evaluar_prendas(prendas):
    """Califica un outfit de 2 o 3 prendas (promedio de los pares de prendas)."""
    if len(prendas) < 2:
        return {"score": None, "verdict": "Elige al menos 2 prendas", "tips": []}
    pares = [(a, b) for i, a in enumerate(prendas) for b in prendas[i + 1:]]
    resultados = [(comparar(a.paleta, b.paleta, a.estampado, b.estampado), a, b) for a, b in pares]
    puntaje = round(sum(r[0][0] for r in resultados) / len(resultados))
    consejos = []
    if any(a.estampado and b.estampado for a, b in pares):
        consejos.append("Dos prendas estampadas compiten: cambia una por un color liso.")
    peor = min(resultados, key=lambda r: r[0][0])
    if puntaje < 72:
        consejos.append(f"Lo que más choca: {peor[1].nombre} + {peor[2].nombre} ({peor[0][1]}).")
    if puntaje >= 85:
        consejos.append("Paleta equilibrada: los colores se complementan.")
    return {"score": puntaje, "verdict": veredicto(puntaje), "tips": consejos}


@app.get("/api/tienda/evaluar")
def tienda_evaluar(ids: str, bd: Session = Depends(obtener_bd), _=Depends(usuario_actual)):
    try:
        lista = [int(i) for i in ids.split(",") if i][:3]
    except ValueError:
        raise HTTPException(400, "ids inválidos")
    return evaluar_prendas([p for p in (bd.get(Prenda, i) for i in lista) if p])


# ------------------------------------------------------------------ Mis outfits (por usuario)
MAX_OUTFITS_POR_USUARIO = 100


class GuardarOutfit(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    items: dict[str, int]                                   # categoría -> id de la prenda
    adjustments: Optional[dict[str, dict[str, float]]] = None  # categoría -> {"s": tamaño, "y": altura}


def limpiar_ajustes(crudo):
    """Deja solo valores válidos: tamaño entre 0.7 y 1.6, altura entre -0.2 y 0.2."""
    limpios = {}
    for categoria in CATEGORIAS:
        dato = (crudo or {}).get(categoria) or {}
        limpios[categoria] = {"s": round(min(1.6, max(0.7, dato.get("s", 1.0))), 2),
                              "y": round(min(0.2, max(-0.2, dato.get("y", 0.0))), 2)}
    return limpios


def outfit_a_dict(outfit, bd):
    prendas = {cat: bd.get(Prenda, id_prenda) for cat, id_prenda in (outfit.prendas or {}).items()}
    return {"id": outfit.id, "name": outfit.nombre, "score": outfit.puntaje, "verdict": veredicto(outfit.puntaje),
            "adjustments": outfit.ajustes or {}, "created": outfit.fecha_registro.isoformat(),
            "items": {cat: (a_dict(p) if p else None) for cat, p in prendas.items()}}  # None = la prenda ya no existe


@app.get("/api/mis-outfits")
def listar_mis_outfits(bd: Session = Depends(obtener_bd), usuario: Usuario = Depends(usuario_actual)):
    outfits = bd.query(OutfitGuardado).filter_by(usuario_id=usuario.id).order_by(OutfitGuardado.fecha_registro.desc()).all()
    return [outfit_a_dict(o, bd) for o in outfits]


@app.post("/api/mis-outfits")
def guardar_mi_outfit(datos: GuardarOutfit, bd: Session = Depends(obtener_bd), usuario: Usuario = Depends(usuario_actual)):
    if bd.query(OutfitGuardado).filter_by(usuario_id=usuario.id).count() >= MAX_OUTFITS_POR_USUARIO:
        raise HTTPException(400, f"Máximo {MAX_OUTFITS_POR_USUARIO} outfits guardados")
    prendas = {}
    for categoria, id_prenda in datos.items.items():
        prenda = bd.get(Prenda, id_prenda)
        if categoria not in CATEGORIAS or not prenda or prenda.categoria != categoria:
            raise HTTPException(400, "Prenda o categoría inválida")
        prendas[categoria] = prenda
    if len(prendas) < 2:
        raise HTTPException(400, "Un outfit necesita al menos 2 prendas")
    puntaje = evaluar_prendas(list(prendas.values()))["score"]
    outfit = OutfitGuardado(usuario_id=usuario.id, nombre=datos.name.strip(), prendas={c: p.id for c, p in prendas.items()},
                            ajustes=limpiar_ajustes(datos.adjustments), puntaje=puntaje)
    bd.add(outfit)
    bd.commit()
    bd.refresh(outfit)
    return outfit_a_dict(outfit, bd)


@app.delete("/api/mis-outfits/{id_outfit}")
def borrar_mi_outfit(id_outfit: int, bd: Session = Depends(obtener_bd), usuario: Usuario = Depends(usuario_actual)):
    outfit = bd.get(OutfitGuardado, id_outfit)
    if not outfit or outfit.usuario_id != usuario.id:  # nadie puede borrar outfits de otra persona
        raise HTTPException(404, "No existe")
    bd.delete(outfit)
    bd.commit()
    return {"ok": True}


# --------------------------------------------------------- Vista administrador
class Edicion(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    category: Optional[str] = None
    gender: Optional[str] = None
    price: Optional[float] = Field(None, ge=0, le=1_000_000)
    sizes: Optional[dict[str, int]] = None


@app.get("/api/admin/prendas")
def admin_listar(q: str = "", bd: Session = Depends(obtener_bd), _=Depends(admin_actual)):
    consulta = bd.query(Prenda)
    if q:
        consulta = consulta.filter(Prenda.nombre.ilike(f"%{q}%") | Prenda.sku.ilike(f"%{q}%"))
    return [a_dict(p) for p in consulta.order_by(Prenda.id)]


def guardar_prenda(bd, nombre, sku, categoria, genero, precio, tallas, bytes_imagen):
    try:
        png, paleta, estampado = procesar_imagen(bytes_imagen)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    base = uuid.uuid4().hex
    with open(os.path.join(RUTA_UPLOADS, f"{base}.png"), "wb") as f:
        f.write(png)
    with open(os.path.join(RUTA_UPLOADS, f"{base}_orig.jpg"), "wb") as f:
        f.write(bytes_imagen)
    p = Prenda(sku=sku, nombre=nombre, categoria=categoria, genero=genero, precio=precio, tallas=tallas,
               existencias=sum(tallas.values()), ruta_imagen=f"/uploads/{base}_orig.jpg",
               ruta_recorte=f"/uploads/{base}.png", paleta=paleta, familia=familia_de_paleta(paleta),
               estampado=estampado)
    bd.add(p)
    bd.commit()
    bd.refresh(p)
    return p


@app.post("/api/admin/prendas")
async def admin_crear(
    name: str = Form(..., min_length=1, max_length=120), sku: str = Form(..., min_length=1, max_length=40),
    category: str = Form("superior"), gender: str = Form("mujer"), price: float = Form(0, ge=0, le=1_000_000), sizes: str = Form("{}"),
    file: UploadFile = File(...), bd: Session = Depends(obtener_bd), _=Depends(admin_actual),
):
    if category not in CATEGORIAS:
        raise HTTPException(400, "Categoría inválida")
    if gender not in GENEROS:
        raise HTTPException(400, "Género inválido")
    datos = await file.read()
    if len(datos) > TAMANO_MAXIMO_IMAGEN:
        raise HTTPException(400, "La imagen supera los 10 MB")
    if bd.query(Prenda).filter_by(sku=sku).first():
        raise HTTPException(400, "Ya existe una prenda con ese SKU")
    return a_dict(guardar_prenda(bd, name, sku, category, gender, price, normalizar_tallas(sizes), datos))


@app.put("/api/admin/prendas/{id_prenda}")
def admin_editar(id_prenda: int, datos: Edicion, bd: Session = Depends(obtener_bd), _=Depends(admin_actual)):
    p = bd.get(Prenda, id_prenda)
    if not p:
        raise HTTPException(404, "No existe")
    if datos.name is not None:
        p.nombre = datos.name
    if datos.category is not None:
        if datos.category not in CATEGORIAS:
            raise HTTPException(400, "Categoría inválida")
        p.categoria = datos.category
    if datos.gender is not None:
        if datos.gender not in GENEROS:
            raise HTTPException(400, "Género inválido")
        p.genero = datos.gender
    if datos.price is not None:
        p.precio = datos.price
    if datos.sizes is not None:
        p.tallas = normalizar_tallas(datos.sizes)
        p.existencias = sum(p.tallas.values())
    bd.commit()
    return a_dict(p)


@app.delete("/api/admin/prendas/{id_prenda}")
def admin_baja(id_prenda: int, bd: Session = Depends(obtener_bd), _=Depends(admin_actual)):
    p = bd.get(Prenda, id_prenda)
    if not p:
        raise HTTPException(404, "No existe")
    for ruta in (p.ruta_imagen, p.ruta_recorte):
        if ruta:
            try:
                os.remove(os.path.join(RUTA_UPLOADS, os.path.basename(ruta)))
            except OSError:
                pass
    bd.delete(p)
    bd.commit()
    return {"ok": True}


@app.get("/api/admin/dashboard")
def admin_panel(bd: Session = Depends(obtener_bd), _=Depends(admin_actual)):
    prendas = bd.query(Prenda).all()
    por_cat = {c: sum(1 for p in prendas if p.categoria == c) for c in CATEGORIAS}
    por_fam = {f: sum(1 for p in prendas if p.familia == f) for f in ("Cálido", "Frío", "Neutro")}
    return {
        "total": len(prendas), "units": sum(p.existencias for p in prendas),
        "value": round(sum(p.precio * p.existencias for p in prendas), 2),
        "out_of_stock": [a_dict(p) for p in prendas if p.existencias == 0],
        "categories": por_cat, "families": por_fam,
        "dominant": [c["hex"] for c in sorted((c for p in prendas for c in p.paleta), key=lambda c: -c["pct"])[:8]],
    }


@app.get("/api/admin/bd")
def admin_ver_bd(bd: Session = Depends(obtener_bd), _=Depends(admin_actual)):
    """Vista de la tabla `prendas` tal como está guardada en la base de datos."""
    filas = bd.query(Prenda).order_by(Prenda.id).all()
    return {"table": "prendas", "rows": [
        {"id": p.id, "sku": p.sku, "nombre": p.nombre, "categoria": p.categoria, "genero": p.genero or "mujer", "precio": p.precio,
         "tallas": p.tallas, "existencias": p.existencias, "familia": p.familia, "estampado": p.estampado,
         "colores": [f'{c["nombre"]} {c["hex"]} {c["pct"]}%' for c in p.paleta],
         "recorte": p.ruta_recorte, "fecha_registro": p.fecha_registro.isoformat()} for p in filas]}


@app.get("/api/admin/clientes")
def admin_listar_clientes(bd: Session = Depends(obtener_bd), _=Depends(admin_actual)):
    """Clientes registrados: nombre, correo y fecha de registro."""
    clientes = bd.query(Usuario).filter_by(rol=ROL_CLIENTE).order_by(Usuario.fecha_registro.desc()).all()
    return [{"id": c.id, "name": c.nombre, "email": c.correo, "created": c.fecha_registro.isoformat()} for c in clientes]


@app.get("/api/salud")
def salud():
    return {"status": "ok"}


# ---------------------------------------------------------------------- Arranque
sembrar_admin()
if os.getenv("SEMBRAR_DEMO", "1") == "1":
    from .demo import sembrar_demo
    sembrar_demo()

app.mount("/uploads", StaticFiles(directory=RUTA_UPLOADS), name="uploads")
app.mount("/assets", StaticFiles(directory=os.path.join(CARPETA_ESTATICA, "assets")), name="assets")


@app.get("/")
def pagina_principal():
    return FileResponse(os.path.join(CARPETA_ESTATICA, "index.html"))
