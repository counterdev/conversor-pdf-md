@echo off
chcp 65001 > nul
setlocal
title Construir ejecutable

cd /d "%~dp0"

set "VENV=.venv"
set "PY_EXE=%VENV%\Scripts\python.exe"
set "SALIDA=dist\ConversorPDF.exe"

echo.
echo  ══════════════════════════════════════════════════════
echo    Construir el ejecutable (.exe)
echo  ══════════════════════════════════════════════════════
echo.
echo  Genera UN SOLO archivo que funciona en cualquier PC
echo  con Windows, sin instalar Python ni nada más.
echo.
echo  Tarda 1-3 minutos. Vuelve a ejecutarlo cada vez que
echo  cambies pdf2md_app.py.
echo.

if not exist "%PY_EXE%" (
    echo  [X] No existe el entorno virtual.
    echo      Ejecuta primero iniciar.bat.
    echo.
    pause
    exit /b 1
)

rem PyInstaller solo hace falta para construir, no para usar la app
"%PY_EXE%" -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo  Instalando PyInstaller...
    "%PY_EXE%" -m pip install pyinstaller --quiet --disable-pip-version-check
    if errorlevel 1 goto :error
    echo.
)

echo  Construyendo...
echo.

rem La receta esta en ConversorPDF.spec: ahi se define el .exe unico
rem y se descarta el analisis de layout de PyMuPDF (~50 MB que la app no usa)
"%PY_EXE%" -m PyInstaller --noconfirm ConversorPDF.spec
if errorlevel 1 goto :error
if not exist "%SALIDA%" goto :error

echo.
echo  ══════════════════════════════════════════════════════
echo    Listo
echo  ══════════════════════════════════════════════════════
echo.
for %%F in ("%SALIDA%") do echo    %%~fF  (%%~zF bytes)
echo.
echo  Es un archivo único y autónomo: se puede subir, enviar
echo  o copiar tal cual. No necesita carpetas al lado.
echo.

choice /c SN /n /m "  ¿Abrir la carpeta ahora? (S/N): "
if not errorlevel 2 start "" "dist"

echo.
exit /b 0

:error
echo.
echo  [X] Falló la construcción.
echo      El detalle del error está más arriba.
echo.
pause
exit /b 1
