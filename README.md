# Gestor de Inventario Inteligente (Atelier)

FastAPI + SQLite. Estructura:

- `app/` código del servidor (`main.py` rutas, `models.py` tablas, `seguridad.py` acceso, `color.py` análisis de ropa, `demo.py` datos de ejemplo)
- `app/static/` página web (`index.html`, `assets/css`, `assets/js`)
- `data/` base de datos e imágenes · `demo/` fotos de ejemplo · `tests/` pruebas

## Ejecutar
Windows: doble clic en `iniciar.bat` (o `Ejecutable/Iniciar_Gestor.bat`). Linux/Mac: `./iniciar.sh`. Abre http://127.0.0.1:8000

Administrador por defecto (archivo `.env`): `admin@tienda.com` / `Admin12345`. **Cámbialo antes de publicar.**
Los clientes se registran desde la pantalla de acceso («Crear cuenta»). El administrador los ve en la pestaña **Clientes**.

**Mis outfits:** desde «Probador con cámara» u «Outfits» se guarda una combinación (con el tamaño y altura de cada prenda); queda ligada a la cuenta y se conserva al cerrar sesión.

## Recuperar contraseña
Se envía un código de 6 dígitos al correo. Sin `SMTP_*` en `.env`, el código aparece en la consola del servidor
(con `MOSTRAR_CODIGO=1` también en pantalla; solo para demostraciones).

## Pruebas
`pip install pytest httpx` y luego `pytest`

## Publicar en la nube (Render)
1. Sube el contenido de la carpeta `Backend` a un repositorio de GitHub (la raíz del repo debe tener `Dockerfile`).
2. En render.com: New + > Blueprint (usa `render.yaml`) o New + > Web Service > Docker.
3. Variables de entorno: `ADMIN_EMAIL`, `ADMIN_PASSWORD` y `MOSTRAR_CODIGO` (1 solo para demos; para correos reales configura `SMTP_*`).
4. `datos_iniciales/` trae el catálogo (prendas e imágenes) y se copia sola la primera vez que arranca.

## Ejecutable de Windows (GitHub Actions)
Sube el proyecto a GitHub, abre la pestaña **Actions**, elige «Crear ejecutable de Windows» y pulsa **Run workflow**.
Al terminar, descarga el artefacto `GestorInventario-Windows`, descomprímelo y ejecuta `GestorInventario.exe`.
