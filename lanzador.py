"""Arranca el servidor y abre el navegador. Es el punto de entrada del ejecutable de Windows."""
import os
import sys
import threading
import webbrowser

import uvicorn

# Que la carpeta "data" (base de datos e imágenes) quede junto al .exe y no en una carpeta temporal
carpeta_base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
os.chdir(carpeta_base)

from app.main import app  # se importa después del chdir

if __name__ == "__main__":
    threading.Timer(2, lambda: webbrowser.open("http://127.0.0.1:8000")).start()
    uvicorn.run(app, host="127.0.0.1", port=8000)
