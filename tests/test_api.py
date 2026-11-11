import json

from tests.conftest import foto_prenda


def alta(cliente, token, sku="T1", cat="superior"):
    return cliente.post("/api/admin/prendas", headers=token, files={"file": ("a.jpg", foto_prenda(), "image/jpeg")},
                        data={"name": "Playera roja", "sku": sku, "category": cat, "gender": "mujer", "price": "299",
                              "sizes": json.dumps({"XS": 1, "S": 2, "M": 3, "L": 4})})


ADMIN = {"email": "admin@tienda.com", "password": "Admin12345"}


def test_login_correcto_e_incorrecto(cliente):
    assert cliente.post("/api/auth/login", json={**ADMIN, "password": "mal"}).status_code == 401
    respuesta = cliente.post("/api/auth/login", json=ADMIN)
    assert respuesta.status_code == 200 and respuesta.json()["role"] == "Administrador"


def test_admin_requiere_sesion(cliente):
    assert cliente.get("/api/admin/prendas").status_code == 401
    assert cliente.post("/api/admin/prendas").status_code in (401, 422)
    assert cliente.get("/api/tienda/prendas").status_code == 401  # la tienda también exige sesión


def test_registro_login_y_permisos_de_cliente(cliente, token):
    datos = {"name": "Ana Pérez", "email": "ANA@correo.com", "password": "Clave1234"}
    assert cliente.post("/api/auth/register", json={**datos, "password": "corta"}).status_code == 400
    assert cliente.post("/api/auth/register", json={**datos, "email": "no-es-correo"}).status_code == 400
    assert cliente.post("/api/auth/register", json=datos).status_code == 200
    assert cliente.post("/api/auth/register", json=datos).status_code == 400  # correo repetido
    sesion = cliente.post("/api/auth/login", json={"email": "ana@correo.com", "password": "Clave1234"}).json()
    assert sesion["role"] == "Cliente"
    cabecera = {"Authorization": "Bearer " + sesion["token"]}
    assert cliente.get("/api/tienda/prendas", headers=cabecera).status_code == 200
    assert cliente.get("/api/admin/prendas", headers=cabecera).status_code == 403
    assert cliente.get("/api/admin/clientes", headers=cabecera).status_code == 403
    lista = cliente.get("/api/admin/clientes", headers=token).json()
    assert [c["email"] for c in lista] == ["ana@correo.com"]
    assert "password" not in lista[0] and "contrasena_hash" not in lista[0]


def test_alta_edicion_baja_y_stock(cliente, token):
    r = alta(cliente, token)
    assert r.status_code == 200 and r.json()["stock"] == 10
    pid = r.json()["id"]
    assert alta(cliente, token).status_code == 400  # SKU repetido
    r = cliente.put(f"/api/admin/prendas/{pid}", headers=token, json={"price": 350, "sizes": {"S": 1}})
    assert r.json()["price"] == 350 and r.json()["stock"] == 1
    assert cliente.delete(f"/api/admin/prendas/{pid}", headers=token).status_code == 200


def test_vista_cliente_publica_y_evaluacion(cliente, token):
    a = alta(cliente, token, "C1", "superior").json()
    b = alta(cliente, token, "C2", "inferior").json()
    lista = cliente.get("/api/tienda/prendas", headers=token).json()
    assert {a["id"], b["id"]} <= {g["id"] for g in lista}
    r = cliente.get(f"/api/tienda/evaluar?ids={a['id']},{b['id']}", headers=token).json()
    assert r["verdict"] in ("Excelente", "Buena", "Regular", "Mala") and 0 <= r["score"] <= 100
    assert cliente.get(f"/api/tienda/prendas/{a['id']}/outfits", headers=token).status_code == 200


def test_recuperar_contrasena(cliente):
    cliente.post("/api/auth/register", json={"name": "Luis", "email": "luis@correo.com", "password": "Clave1234"})
    codigo = cliente.post("/api/auth/forgot", json={"email": "luis@correo.com"}).json()["demo_code"]
    base = {"email": "luis@correo.com", "new_password": "Nueva5678"}
    assert cliente.post("/api/auth/reset", json={**base, "code": "000000"}).status_code == 400
    assert cliente.post("/api/auth/reset", json={**base, "code": codigo, "new_password": "corta"}).status_code == 400
    assert cliente.post("/api/auth/reset", json={**base, "code": codigo}).status_code == 200
    assert cliente.post("/api/auth/login", json={"email": "luis@correo.com", "password": "Nueva5678"}).status_code == 200


def test_bloqueo_por_intentos(cliente):
    for _ in range(5):
        cliente.post("/api/auth/login", json={"email": "otro@correo.com", "password": "x"})
    assert cliente.post("/api/auth/login", json={"email": "otro@correo.com", "password": "x"}).status_code == 429


def test_cabeceras_de_seguridad(cliente):
    assert cliente.get("/api/salud").headers["x-content-type-options"] == "nosniff"


def test_genero_filtra_la_tienda(cliente, token):
    h = cliente.post("/api/admin/prendas", headers=token, files={"file": ("a.jpg", foto_prenda(), "image/jpeg")},
                     data={"name": "Camisa", "sku": "H1", "category": "superior", "gender": "hombre", "price": "400",
                           "sizes": json.dumps({"M": 1})}).json()
    ids_mujer = {g["id"] for g in cliente.get("/api/tienda/prendas?genero=mujer", headers=token).json()}
    ids_hombre = {g["id"] for g in cliente.get("/api/tienda/prendas?genero=hombre", headers=token).json()}
    assert h["id"] in ids_hombre and h["id"] not in ids_mujer


def test_mis_outfits_se_guardan_por_usuario(cliente, token):
    superior = alta(cliente, token, "O1", "superior").json()
    inferior = alta(cliente, token, "O2", "inferior").json()
    cliente.post("/api/auth/register", json={"name": "Eva", "email": "eva@correo.com", "password": "Clave1234"})
    cliente.post("/api/auth/register", json={"name": "Raúl", "email": "raul@correo.com", "password": "Clave1234"})

    def entrar(correo):
        sesion = cliente.post("/api/auth/login", json={"email": correo, "password": "Clave1234"}).json()
        return {"Authorization": "Bearer " + sesion["token"]}

    eva = entrar("eva@correo.com")
    cuerpo = {"name": "Look de oficina", "items": {"superior": superior["id"], "inferior": inferior["id"]},
              "adjustments": {"superior": {"s": 1.2, "y": 0.05}}}
    assert cliente.post("/api/mis-outfits", headers=eva, json={**cuerpo, "items": {"superior": superior["id"]}}).status_code == 400
    guardado = cliente.post("/api/mis-outfits", headers=eva, json=cuerpo).json()
    assert guardado["adjustments"]["superior"]["s"] == 1.2
    # cerrar sesión y volver a entrar: el outfit sigue ahí
    assert [o["name"] for o in cliente.get("/api/mis-outfits", headers=entrar("eva@correo.com")).json()] == ["Look de oficina"]
    # otro usuario no lo ve ni lo puede borrar
    raul = entrar("raul@correo.com")
    assert cliente.get("/api/mis-outfits", headers=raul).json() == []
    assert cliente.delete(f"/api/mis-outfits/{guardado['id']}", headers=raul).status_code == 404
    assert cliente.delete(f"/api/mis-outfits/{guardado['id']}", headers=eva).status_code == 200
