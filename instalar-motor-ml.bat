@echo off
chcp 65001 > nul
setlocal
title Instalar motor ML (marker-pdf)

cd /d "%~dp0"

set "VENV=.venv"
set "PY_EXE=%VENV%\Scripts\python.exe"

echo.
echo  ══════════════════════════════════════════════════════
echo    Motor ML opcional — marker-pdf
echo  ══════════════════════════════════════════════════════
echo.
echo  Sirve para PDFs complejos: multi-columna, escaneados
echo  o con tablas densas.
echo.
echo  Ojo con el tamaño:
echo    - La instalación descarga PyTorch (~2.5 GB).
echo    - La primera conversión descarga los modelos (~1.5 GB).
echo.
echo  El motor rápido ya instalado cubre informes, artículos
echo  y documentación normal. Esto es solo un extra.
echo.

choice /c SN /n /m "  ¿Continuar? (S/N): "
if errorlevel 2 goto :cancelado

echo.

if not exist "%PY_EXE%" (
    echo  [X] No existe el entorno virtual.
    echo      Ejecuta primero iniciar.bat.
    echo.
    pause
    exit /b 1
)

rem PyTorch todavía no publica versiones para Python 3.14
"%PY_EXE%" -c "import sys; sys.exit(0 if sys.version_info < (3,14) else 1)" >nul 2>&1
if errorlevel 1 (
    echo  [X] Tu entorno usa Python 3.14, y PyTorch — del que
    echo      depende marker-pdf — todavía no publica versiones
    echo      compatibles.
    echo.
    echo      Para usar el motor ML: instala Python 3.12, borra
    echo      la carpeta .venv y vuelve a ejecutar iniciar.bat.
    echo.
    pause
    exit /b 1
)

echo  Instalando (esto puede tardar varios minutos)...
echo.
"%PY_EXE%" -m pip install -r requirements-ml.txt --disable-pip-version-check
if errorlevel 1 goto :error

echo.
echo  OK — Motor ML instalado.
echo  Abre la app con iniciar.bat: aparecerá como segunda
echo  opción en "Motor de conversión".
echo.
pause
exit /b 0

:cancelado
echo.
echo  Cancelado. No se instaló nada.
echo.
pause
exit /b 0

:error
echo.
echo  [X] Falló la instalación.
echo      Revisa el detalle del error más arriba.
echo.
pause
exit /b 1
