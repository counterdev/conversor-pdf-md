# Conversor PDF a Markdown

Convierte PDFs a Markdown, con modo Obsidian (frontmatter YAML + limpieza
de formato).

---

## Cómo usarlo

Doble clic en **`ConversorPDF.exe`**.

No hay que instalar nada: ni Python, ni librerías, ni permisos de
administrador. La carpeta `_internal` que está al lado tiene que
acompañar siempre al ejecutable, así que movelos juntos.

> Windows puede mostrar un aviso de "Windows protegió tu PC" la primera
> vez, porque el ejecutable no tiene firma digital. Hacé clic en
> **Más información → Ejecutar de todas formas**.

---

## Convertir un PDF

1. Arrastrá los PDFs a la zona punteada, o usá **Browse Files...**
   (podés cargar varios; se procesan de a dos en paralelo).
2. Elegí dónde guardar, el **formato** y si querés el **modo Obsidian**.
3. **Iniciar Conversión**.

El resultado lleva el mismo nombre del PDF. Si ya existe un archivo con
ese nombre, se guarda como `nombre_1` — nunca se sobrescribe nada.

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

Y limpia el cuerpo: colapsa líneas en blanco repetidas y normaliza el
formato. Desactivalo si querés el Markdown crudo.

---

## Qué PDFs maneja bien

Informes, artículos, documentación, libros — todo lo que tenga texto real.

Los PDFs **escaneados** (páginas que en realidad son fotos) no se pueden
convertir con esta versión: no hay texto que extraer. Para esos hace falta
el motor ML, que se instala desde el código fuente con
`instalar-motor-ml.bat`.
