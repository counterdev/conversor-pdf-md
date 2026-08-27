# Conversor PDF a Markdown

Aplicación de escritorio para Windows que convierte PDFs a **Markdown** o
**texto plano**, con modo Obsidian (frontmatter YAML + limpieza de formato).

Arrastrás los archivos, elegís el formato y listo.

---

## Descargar

**[⬇ Descargar ConversorPDF.exe](https://github.com/counterdev/conversor-pdf-md/releases/latest)**

Un solo archivo de 59 MB. Doble clic y funciona: sin instalar Python, sin
librerías, sin permisos de administrador. No necesita carpetas al lado.

El primer arranque tarda unos segundos porque el programa se descomprime en
una carpeta temporal. Los siguientes son más rápidos.

> **Windows protegió tu PC**
> Puede aparecer la primera vez, porque el ejecutable no tiene firma digital.
> Hacé clic en **Más información → Ejecutar de todas formas**.

---

## Cómo se usa

1. Arrastrá los PDFs a la zona punteada, o usá **Browse Files...**
   Podés cargar varios a la vez: se procesan de a dos en paralelo.
2. Elegí el **motor de conversión**.
3. Elegí dónde guardar, el **formato** y si querés el **modo Obsidian**.
4. **Iniciar Conversión**.

El resultado lleva el mismo nombre del PDF. Si ya existe un archivo con ese
nombre, se guarda como `nombre_1` — nunca se sobrescribe nada.

Para sacar archivos de la cola: seleccionalos y apretá `Supr`.

---

## Los dos formatos

| Formato | Qué genera |
|---|---|
| **Markdown (.md)** | Conserva títulos, negritas, listas y tablas. Es el formato por defecto. |
| **Texto plano (.txt)** | El mismo contenido sin marcas: los títulos quedan como líneas sueltas, las listas mantienen su guión y las tablas pasan a columnas separadas por tabulación. |

El **modo Obsidian** solo aplica a `.md`, así que se desactiva solo cuando
elegís `.txt`.

En los `.md`, el texto que venía resaltado en el PDF se guarda como
`==texto==`, la sintaxis nativa de resaltado de Obsidian. En los `.txt` el
resaltado se quita y queda el texto limpio.

---

## Modo Obsidian

Activado por defecto. Agrega al inicio del `.md`:

```yaml
---
title: "Nombre del documento"
source: documento.pdf
created: 2026-08-27 14:30
tags: [pdf-import]
engine: Fast (pymupdf4llm)
---
```

Y limpia el cuerpo: colapsa líneas en blanco repetidas y normaliza el formato.
Desactivalo si querés el Markdown crudo del motor.

---

## Los dos motores

| Motor | Para qué sirve | Tamaño |
|---|---|---|
| **Fast (pymupdf4llm)** | Informes, artículos, documentación. Rápido y preciso. | ~30 MB, incluido |
| **ML (marker-pdf)** | PDFs multi-columna, escaneados, con tablas densas. | ~4 GB, opcional |

El `.exe` incluye solo el motor rápido, que cubre todo PDF con texto real.

Los PDFs **escaneados** (páginas que en realidad son fotos) necesitan el motor
ML, que no viene por defecto para no obligar a nadie a descargar 4 GB. Se
instala desde el código fuente con `instalar-motor-ml.bat`, y requiere
Python 3.10–3.13: PyTorch, del que depende, todavía no publica versiones
para Python 3.14.

La app oculta el motor ML si no está instalado, así que no vas a ver opciones
que no funcionen.

---

## Desde el código fuente

Si preferís correrlo con Python en vez de usar el `.exe`:

1. Descargá el ZIP del repo (**Code → Download ZIP**) y descomprimilo.
2. Doble clic en **`iniciar.bat`**.

La primera vez tarda 1-2 minutos: crea un entorno virtual e instala las
dependencias dentro de la carpeta del proyecto. Los siguientes arranques son
inmediatos.

Requiere **Python 3.10 o superior**. Si no lo tenés, `iniciar.bat` te avisa y
abre la página de descarga. Al instalarlo, marcá la casilla
**"Add python.exe to PATH"**.

Nada se instala fuera de la carpeta. Para desinstalar, borrala y listo.

### Construir el ejecutable

```
construir-exe.bat
```

Genera `dist\ConversorPDF.exe`, un archivo único y autónomo. La receta de
empaquetado está en [`ConversorPDF.spec`](ConversorPDF.spec), que además
descarta el analizador de layout de PyMuPDF: son ~50 MB en modelos ONNX que
la app no usa, porque fija `use_layout(False)`.

Reconstruilo cada vez que cambies `pdf2md_app.py`.

---

## Si algo falla

| Síntoma | Solución |
|---|---|
| El `.exe` no abre y no dice nada | Esperá unos segundos: el primer arranque descomprime el programa. |
| "No se encontró Python" (código fuente) | Instalá Python y marcá "Add python.exe to PATH". |
| Falla la instalación de dependencias | Revisá la conexión. Si tu Python es muy nuevo (3.14+), instalá 3.12, borrá `.venv` y reintentá. |
| La app no abre desde `iniciar.bat` | Borrá la carpeta `.venv` y ejecutalo de nuevo. |
| Un PDF sale mal convertido | Probá el otro motor. Los escaneados necesitan el motor ML. |

---

## Cómo está hecho

Python + Tkinter, en un único archivo: [`pdf2md_app.py`](pdf2md_app.py).

- **Motores**: [pymupdf4llm](https://github.com/pymupdf/RAG) (rápido) y
  [marker-pdf](https://github.com/datalab-to/marker) (ML, opcional).
- **Arrastrar y soltar**: [tkinterdnd2](https://github.com/pmgagne/tkinterdnd2).
- **Empaquetado**: [PyInstaller](https://pyinstaller.org).

Las conversiones corren en un `ThreadPoolExecutor` de dos hilos, con la UI
informando progreso por una cola de mensajes.
