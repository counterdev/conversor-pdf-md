# -*- mode: python ; coding: utf-8 -*-
"""Receta de empaquetado del Conversor PDF a Markdown.

Genera un unico .exe autonomo. Se usa desde construir-exe.bat.
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

BASE = Path(SPECPATH)

datas, binaries, hiddenimports = [], [], []
for paquete in ("pymupdf", "pymupdf4llm", "tkinterdnd2"):
    d, b, h = collect_all(paquete)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    [str(BASE / "pdf2md_app.py")],
    pathex=[str(BASE)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    # marker-pdf y PyTorch no se empaquetan: son varios GB y el .exe
    # solo lleva el motor rapido
    excludes=["marker", "torch", "PyInstaller"],
    noarchive=False,
)


def es_layout(destino: str) -> bool:
    """Identifica el analisis de layout de PyMuPDF (modelos ONNX incluidos)."""
    ruta = destino.replace("\\", "/")
    return ruta.startswith("pymupdf/layout/") or ruta == "pymupdf/layout"


def es_modulo_layout(nombre: str) -> bool:
    return nombre == "pymupdf.layout" or nombre.startswith("pymupdf.layout.")


# El analisis de layout pesa ~50 MB en modelos ONNX y la app no lo usa:
# fija use_layout(False), y pymupdf4llm cae solo en ese modo cuando el
# modulo no esta presente.
a.datas = [entrada for entrada in a.datas if not es_layout(entrada[0])]
a.pure = [entrada for entrada in a.pure if not es_modulo_layout(entrada[0])]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ConversorPDF",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(BASE / "icono.ico"),
)
