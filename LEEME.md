# Conversor PDF a Markdown

Aplicación de escritorio para convertir PDFs a Markdown, con modo Obsidian
(frontmatter YAML + limpieza de formato).

---

## Cómo usarlo

1. Descomprimí el ZIP en cualquier carpeta.
2. Doble clic en **`iniciar.bat`**.

La primera vez tarda 1-2 minutos: instala todo lo necesario en una carpeta
`.venv` dentro del proyecto. Los siguientes arranques son inmediatos.

> **Requisito:** Python 3.10 o superior.
> Si no lo tenés, `iniciar.bat` te avisa y abre la página de descarga.
> Al instalarlo, marcá la casilla **"Add python.exe to PATH"**.

Nada se instala fuera de esta carpeta. Para desinstalar, borrala y listo.

---

## Convertir un PDF

1. Arrastrá los PDFs a la zona punteada, o usá **Browse Files...**
   (podés cargar varios a la vez; se procesan de a dos en paralelo).
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

## Los dos motores

| Motor | Para qué sirve | Tamaño |
|---|---|---|
| **Fast (pymupdf4llm)** | Informes, artículos, documentación. Rápido y preciso. | ~30 MB, ya instalado |
| **ML (marker-pdf)** | PDFs multi-columna, escaneados, con tablas densas. | ~4 GB, opcional |

El motor ML no viene por defecto para no obligar a nadie a descargar 4 GB.
Si lo necesitás, ejecutá **`instalar-motor-ml.bat`**.

Requiere Python 3.10–3.13: PyTorch, del que depende, todavía no publica
versiones para Python 3.14.

La app oculta el motor ML si no está instalado, así que no vas a ver opciones
que no funcionen.

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

## Si algo falla

| Síntoma | Solución |
|---|---|
| "No se encontró Python" | Instalá Python y marcá "Add python.exe to PATH". |
| Falla la instalación de dependencias | Revisá la conexión. Si tu Python es muy nuevo (3.14+), instalá 3.12, borrá `.venv` y reintentá. |
| La app no abre y no dice nada | Borrá la carpeta `.venv` y ejecutá `iniciar.bat` de nuevo. |
| Un PDF sale mal convertido | Probá el otro motor. Los escaneados necesitan el motor ML. |

---

## Repartir la app a otra gente

Hay dos formas, según si el destinatario tiene Python o no.

**A) ZIP del código fuente** (~50 KB). Sirve para quien tenga Python o
esté dispuesto a instalarlo. Comprimí estos archivos:

```
.gitignore  LEEME.md  iniciar.bat  instalar-motor-ml.bat
pdf2md_app.py  requirements.txt  requirements-ml.txt
icono.ico  construir-exe.bat  LEEME-exe.md
```

No incluyas `.venv`, `build` ni `dist`: se regeneran solos.

**B) Ejecutable `.exe`** (~200 MB). Funciona en cualquier Windows sin
instalar nada. Ejecutá **`construir-exe.bat`** y comprimí la carpeta
`dist\ConversorPDF` **completa** — el `.exe` necesita la carpeta
`_internal` que tiene al lado.

Reconstruilo cada vez que cambies `pdf2md_app.py`.

El `.exe` incluye solo el motor rápido: marker-pdf arrastra PyTorch y
varios GB de modelos, inviable de empaquetar.
