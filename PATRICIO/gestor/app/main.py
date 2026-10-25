import os, uuid, secrets, hashlib
from typing import Optional
from fastapi import FastAPI, Depends, UploadFile, File, Form, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .models import Base, engine, SessionLocal, User, Garment
from .color import analyze, family, recommend

Base.metadata.create_all(engine)
os.makedirs("uploads", exist_ok=True)
app = FastAPI(title="Gestor de Inventario Inteligente")
TOKENS: dict[str, int] = {}          # sesiones en memoria (suficiente para la demo)

def hash_pw(p): return hashlib.pbkdf2_hmac("sha256", p.encode(), b"atelier-norte", 100_000).hex()
with SessionLocal() as db:
    if not db.query(User).first():
        db.add(User(email="admin@atelier.es", pw_hash=hash_pw("admin123"))); db.commit()

def get_db():
    with SessionLocal() as db: yield db

def user(authorization: str = Header(""), db: Session = Depends(get_db)):
    uid = TOKENS.get(authorization.replace("Bearer ", ""))
    if not uid: raise HTTPException(401, "Sesión no válida")
    return db.get(User, uid)

class Login(BaseModel): email: str; password: str
class Edit(BaseModel): name: Optional[str] = None; stock: Optional[int] = None

def out(g): return dict(id=g.id, sku=g.sku, name=g.name, stock=g.stock, image=g.image, palette=g.palette, family=g.family, created=g.created.isoformat())

@app.post("/api/auth/login")
def login(b: Login, db: Session = Depends(get_db)):
    u = db.query(User).filter_by(email=b.email.strip().lower()).first()
    if not u or u.pw_hash != hash_pw(b.password): raise HTTPException(401, "Correo o contraseña incorrectos")
    t = secrets.token_hex(24); TOKENS[t] = u.id
    return {"token": t, "email": u.email, "role": u.role}

@app.post("/api/auth/logout")
def logout(authorization: str = Header("")): TOKENS.pop(authorization.replace("Bearer ", ""), None); return {"ok": True}

@app.get("/api/garments")
def list_garments(q: str = "", fam: str = "Todos", db: Session = Depends(get_db), _=Depends(user)):
    qs = db.query(Garment)
    if q: qs = qs.filter((Garment.name.ilike(f"%{q}%")) | (Garment.sku.ilike(f"%{q}%")))
    if fam != "Todos": qs = qs.filter(Garment.family == fam)
    return [out(g) for g in qs.order_by(Garment.created.desc())]

@app.post("/api/garments")
async def create(name: str = Form(...), sku: str = Form(...), stock: int = Form(0), file: UploadFile = File(...), db: Session = Depends(get_db), _=Depends(user)):
    if file.content_type not in ("image/jpeg", "image/png"): raise HTTPException(400, "Solo se aceptan archivos JPG o PNG")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024: raise HTTPException(400, "La imagen supera los 10 MB")
    if db.query(Garment).filter_by(sku=sku).first(): raise HTTPException(400, "Ya existe una prenda con ese SKU")
    try: palette = analyze(data)
    except Exception: raise HTTPException(400, "No se pudo leer la imagen")
    fn = f"{uuid.uuid4().hex}.{'png' if file.content_type == 'image/png' else 'jpg'}"
    open(f"uploads/{fn}", "wb").write(data)
    g = Garment(sku=sku, name=name, stock=stock, image=f"/uploads/{fn}", palette=palette, family=family(palette))
    db.add(g); db.commit(); db.refresh(g); return out(g)

@app.put("/api/garments/{gid}")
def edit(gid: int, b: Edit, db: Session = Depends(get_db), _=Depends(user)):
    g = db.get(Garment, gid) or HTTPException(404, "No existe")
    if isinstance(g, HTTPException): raise g
    if b.name is not None: g.name = b.name
    if b.stock is not None: g.stock = max(0, b.stock)
    db.commit(); return out(g)

@app.delete("/api/garments/{gid}")
def delete(gid: int, db: Session = Depends(get_db), _=Depends(user)):
    g = db.get(Garment, gid)
    if not g: raise HTTPException(404, "No existe")
    db.delete(g); db.commit(); return {"ok": True}

@app.get("/api/garments/{gid}/recommendations")
def recs(gid: int, refresh: bool = False, db: Session = Depends(get_db), _=Depends(user)):
    g = db.get(Garment, gid)
    if not g: raise HTTPException(404, "No existe")
    return [dict(type=r["type"], affinity=r["affinity"], garment=out(r["garment"])) for r in recommend(g, db.query(Garment).all(), refresh)]

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db), _=Depends(user)):
    gs = db.query(Garment).all()
    fams = {"Cálido": 0, "Frío": 0, "Neutro": 0}
    for g in gs: fams[g.family] += 1
    combos = sum(len(recommend(g, gs)) for g in gs) // 2
    top = sorted((c for g in gs for c in g.palette), key=lambda c: -c["pct"])[:6]
    return dict(total=len(gs), colors=len(gs) * 3, combos=combos, families=fams, dominant=[c["hex"] for c in top],
                latest=[out(g) for g in sorted(gs, key=lambda g: g.created, reverse=True)[:3]])

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
@app.get("/")
def index(): return FileResponse("app/static/index.html")
