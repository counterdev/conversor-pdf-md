@echo off
chcp 65001 > nul
setlocal
title Construir ejecutable

cd /d "%~dp0"

set "VENV=.venv"
set "PY_EXE=%VENV%\Scripts\python.exe"
set "SALIDA=dist\ConversorPDF"

echo.
echo  ══════════════════════════════════════════════════════
echo    Construir el ejecutable (.exe)
echo  ══════════════════════════════════════════════════════
echo.
echo  Genera una versión que funciona en cualquier PC con
echo  Windows, sin necesidad de instalar Python.
echo.
echo  Tarda 1-3 minutos. Volvé a ejecutarlo cada vez que
echo  cambies pdf2md_app.py.
echo.

if not exist "%PY_EXE%" (
    echo  [X] No existe el entorno virtual.
    echo      Ejecutá primero iniciar.bat.
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

"%PY_EXE%" -m PyInstaller ^
    --noconfirm ^
    --windowed ^
    --name ConversorPDF ^
    --icon icono.ico ^
    --collect-all pymupdf ^
    --collect-all pymupdf4llm ^
    --collect-all tkinterdnd2 ^
    --exclude-module marker ^
    --exclude-module torch ^
    --exclude-module PyInstaller ^
    pdf2md_app.py

if errorlevel 1 goto :error
if not exist "%SALIDA%\ConversorPDF.exe" goto :error

rem El LEEME viaja junto al ejecutable
if exist "LEEME-exe.md" copy /y "LEEME-exe.md" "%SALIDA%\LEEME.md" >nul

echo.
echo  ══════════════════════════════════════════════════════
echo    Listo
echo  ══════════════════════════════════════════════════════
echo.
echo  El ejecutable quedó en:
echo    %SALIDA%\ConversorPDF.exe
echo.
echo  Para repartirlo, comprimí la carpeta COMPLETA
echo    %SALIDA%
echo  (el .exe necesita la carpeta _internal que está al lado).
echo.

choice /c SN /n /m "  ¿Abrir la carpeta ahora? (S/N): "
if not errorlevel 2 start "" "%SALIDA%"

echo.
exit /b 0

:error
echo.
echo  [X] Falló la construcción.
echo      El detalle del error está más arriba.
echo.
pause
exit /b 1
