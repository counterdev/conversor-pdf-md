@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion
title Conversor PDF a Markdown

rem Trabajar siempre desde la carpeta del .bat, sin importar desde donde se ejecute
cd /d "%~dp0"

set "VENV=.venv"
set "PY_EXE=%VENV%\Scripts\python.exe"
set "PYW_EXE=%VENV%\Scripts\pythonw.exe"
set "STAMP=%VENV%\.deps-ok"

rem Si el entorno ya quedo listo de una ejecucion anterior, arrancar directo
if exist "%PY_EXE%" if exist "%STAMP%" goto :lanzar

echo.
echo  ══════════════════════════════════════════════════════
echo    Conversor PDF a Markdown — Primera instalación
echo  ══════════════════════════════════════════════════════
echo.
echo  Esto ocurre una sola vez. Los próximos arranques
echo  serán inmediatos.
echo.

rem ── [1/3] Buscar un Python compatible (3.10 o superior) ──────────────
echo  [1/3] Buscando Python...

set "BASE_PY="
for %%C in ("py -3" "python" "python3") do (
    if not defined BASE_PY (
        %%~C -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
        if !errorlevel! equ 0 set "BASE_PY=%%~C"
    )
)

if not defined BASE_PY goto :error_python

for /f "delims=" %%V in ('%BASE_PY% -c "import sys; print(sys.version.split()[0])"') do set "PY_VER=%%V"
echo        OK — Python %PY_VER%

rem ── [2/3] Crear el entorno virtual ───────────────────────────────────
echo  [2/3] Creando entorno virtual...

if not exist "%PY_EXE%" (
    %BASE_PY% -m venv "%VENV%"
    if errorlevel 1 goto :error_venv
)
echo        OK

rem ── [3/3] Instalar dependencias ──────────────────────────────────────
echo  [3/3] Instalando dependencias (puede tardar 1-2 minutos)...
echo.

"%PY_EXE%" -m pip install --upgrade pip --quiet --disable-pip-version-check
"%PY_EXE%" -m pip install -r requirements.txt --disable-pip-version-check
if errorlevel 1 goto :error_deps

echo. > "%STAMP%"
echo.
echo        OK — Instalación completa.
echo.

:lanzar
rem Comprobar que las dependencias respondan antes de abrir la ventana
"%PY_EXE%" -c "import pymupdf4llm, tkinterdnd2" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [!] Faltan dependencias. Reinstalando...
    echo.
    if exist "%STAMP%" del "%STAMP%" >nul 2>&1
    "%PY_EXE%" -m pip install -r requirements.txt --disable-pip-version-check
    if errorlevel 1 goto :error_deps
    echo. > "%STAMP%"
)

echo  Abriendo la aplicación...
start "" "%PYW_EXE%" "pdf2md_app.py"
exit /b 0


rem ── Errores ──────────────────────────────────────────────────────────

:error_python
echo.
echo  [X] No se encontró Python 3.10 o superior en este equipo.
echo.
echo      1. Descárgalo desde https://www.python.org/downloads/
echo      2. Durante la instalación, marca la casilla
echo         "Add python.exe to PATH"  (es fácil pasarla por alto)
echo      3. Vuelve a ejecutar este archivo.
echo.
echo      Se abrirá la página de descarga en tu navegador...
echo.
start "" "https://www.python.org/downloads/"
pause
exit /b 1

:error_venv
echo.
echo  [X] No se pudo crear el entorno virtual.
echo.
echo      Suele deberse a una instalación de Python incompleta
echo      o a permisos de escritura en esta carpeta.
echo.
echo      Prueba mover la carpeta a Documentos o al Escritorio
echo      y ejecutar de nuevo.
echo.
pause
exit /b 1

:error_deps
echo.
echo  [X] Falló la instalación de dependencias.
echo.
echo      Causas habituales:
echo        - Sin conexión a internet o proxy bloqueando pip.
echo        - Tu versión de Python es demasiado reciente y
echo          todavía no hay paquetes compilados para ella.
echo          En ese caso, instala Python 3.12 y borra la
echo          carpeta .venv antes de reintentar.
echo.
echo      El detalle del error está más arriba.
echo.
pause
exit /b 1
