# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['python_multipart']
hiddenimports += collect_submodules('uvicorn')

a = Analysis(
    ['lanzador.py'],
    datas=[('app/static', 'app/static'), ('demo', 'demo'), ('datos_iniciales', 'datos_iniciales'), ('.env', '.')],
    hiddenimports=hiddenimports,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='GestorInventario', console=True, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name='GestorInventario', upx=False)
