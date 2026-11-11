"""Contraseñas cifradas, sesiones, recuperación por código y límite de intentos."""
import hashlib
import hmac
import os
import re
import secrets
import smtplib
import time
from email.message import EmailMessage

DURACION_SESION = 8 * 3600       # segundos
DURACION_CODIGO = 10 * 60        # segundos
MAX_INTENTOS_CODIGO = 5
MAX_INTENTOS_ACCESO, SEGUNDOS_BLOQUEO = 5, 60
ITERACIONES_HASH = 200_000
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")

sesiones: dict[str, tuple[int, float]] = {}      # token -> (id_usuario, expira)
codigos_recuperacion: dict[str, tuple[str, float, int]] = {}  # correo -> (hash_codigo, expira, intentos)
intentos_fallidos: dict[str, tuple[int, float]] = {}  # clave -> (cantidad, bloqueado_hasta)


def correo_valido(correo):
    return bool(PATRON_CORREO.match(correo)) and len(correo) <= 120


def contrasena_segura(contrasena):
    """Mínimo 8 caracteres, con al menos una letra y un número."""
    return len(contrasena) >= 8 and any(c.isalpha() for c in contrasena) and any(c.isdigit() for c in contrasena)


def hash_contrasena(contrasena, sal=None):
    sal = sal or secrets.token_hex(16)
    resumen = hashlib.pbkdf2_hmac("sha256", contrasena.encode(), sal.encode(), ITERACIONES_HASH).hex()
    return f"{sal}${resumen}"


def verificar_contrasena(contrasena, hash_guardado):
    if "$" not in hash_guardado:
        return False
    sal = hash_guardado.split("$", 1)[0]
    return hmac.compare_digest(hash_contrasena(contrasena, sal), hash_guardado)


def crear_sesion(id_usuario):
    token = secrets.token_urlsafe(32)
    sesiones[token] = (id_usuario, time.time() + DURACION_SESION)
    return token


def usuario_de_token(token):
    dato = sesiones.get(token)
    if not dato or dato[1] < time.time():
        sesiones.pop(token, None)
        return None
    return dato[0]


def segundos_de_bloqueo(clave):
    cantidad, bloqueado_hasta = intentos_fallidos.get(clave, (0, 0))
    return max(0, int(bloqueado_hasta - time.time())) if cantidad >= MAX_INTENTOS_ACCESO else 0


def registrar_fallo(clave):
    cantidad, bloqueado_hasta = intentos_fallidos.get(clave, (0, 0))
    if bloqueado_hasta and bloqueado_hasta < time.time():
        cantidad = 0
    intentos_fallidos[clave] = (cantidad + 1, time.time() + SEGUNDOS_BLOQUEO)


def limpiar_fallos(clave):
    intentos_fallidos.pop(clave, None)


def generar_codigo(correo):
    codigo = f"{secrets.randbelow(10**6):06d}"
    codigos_recuperacion[correo] = (hash_contrasena(codigo, "recuperacion"), time.time() + DURACION_CODIGO, 0)
    return codigo


def validar_codigo(correo, codigo):
    dato = codigos_recuperacion.get(correo)
    if not dato or dato[1] < time.time() or dato[2] >= MAX_INTENTOS_CODIGO:
        codigos_recuperacion.pop(correo, None)
        return False
    if hmac.compare_digest(dato[0], hash_contrasena(codigo, "recuperacion")):
        codigos_recuperacion.pop(correo, None)
        return True
    codigos_recuperacion[correo] = (dato[0], dato[1], dato[2] + 1)
    return False


def enviar_codigo(correo_destino, codigo):
    """Envía el código por SMTP si está configurado; si no, lo imprime en la consola del servidor."""
    servidor = os.getenv("SMTP_HOST")
    if not servidor:
        print(f"[RECUPERACIÓN] Código para {correo_destino}: {codigo} (válido 10 min)")
        return "consola"
    mensaje = EmailMessage()
    mensaje["Subject"] = "Código para recuperar tu contraseña"
    mensaje["From"] = os.getenv("SMTP_FROM") or os.getenv("SMTP_USER") or correo_destino
    mensaje["To"] = correo_destino
    mensaje.set_content(f"Tu código de recuperación es {codigo}. Vence en 10 minutos.")
    try:
        with smtplib.SMTP(servidor, int(os.getenv("SMTP_PORT", "587")), timeout=10) as conexion:
            conexion.starttls()
            if os.getenv("SMTP_USER"):
                conexion.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD", ""))
            conexion.send_message(mensaje)
    except (OSError, smtplib.SMTPException) as error:
        print(f"[ERROR] No se pudo enviar el correo ({error}). Código para {correo_destino}: {codigo}")
        return "consola"
    return "correo"
