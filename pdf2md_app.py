"""
PDF to Markdown Converter — Desktop Application
================================================
Convierte PDFs normales y complejos a Markdown.
Motor rápido: pymupdf4llm | Motor ML: marker-pdf (opcional)
"""

import os
import sys
import queue
import threading
import traceback
import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Any, Callable

from tkinterdnd2 import TkinterDnD

warnings.filterwarnings("ignore", message="Unsupported Windows version")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def format_size(n_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n_bytes < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:.1f} TB"


# ---------------------------------------------------------------------------
# Obsidian Post-Processor
# ---------------------------------------------------------------------------

class ObsidianPostProcessor:
    """Limpia y enriquece el Markdown para Obsidian."""

    @staticmethod
    def process(md_text: str, source_pdf: Path, engine_name: str) -> str:
        frontmatter = ObsidianPostProcessor._build_frontmatter(source_pdf, engine_name)
        body = ObsidianPostProcessor._clean_body(md_text)
        return f"{frontmatter}\n\n{body}"

    @staticmethod
    def _build_frontmatter(source_pdf: Path, engine_name: str) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        return "\n".join([
            "---",
            f'title: "{source_pdf.stem}"',
            f"source: {source_pdf.name}",
            f"created: {now}",
            f'tags: [pdf-import]',
            f"engine: {engine_name}",
            "---",
        ])

    @staticmethod
    def _clean_body(md_text: str) -> str:
        lines = md_text.splitlines()
        cleaned: list[str] = []
        prev_blank = False

        for line in lines:
            stripped = line.rstrip()

            # Collapse multiple blank lines into one
            is_blank = stripped == ""
            if is_blank and prev_blank:
                continue
            prev_blank = is_blank

            cleaned.append(stripped)

        # Strip leading/trailing blank lines
        while cleaned and cleaned[0] == "":
            cleaned.pop(0)
        while cleaned and cleaned[-1] == "":
            cleaned.pop()

        return "\n".join(cleaned)


# ---------------------------------------------------------------------------
# Conversion Engine Layer (Strategy Pattern)
# ---------------------------------------------------------------------------

class ConversionEngine(ABC):
    @property
    @abstractmethod
    def engine_id(self) -> str: ...

    @property
    @abstractmethod
    def display_name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool: ...

    @abstractmethod
    def convert(self, pdf_path: Path) -> str: ...


class PyMuPDF4LLMEngine(ConversionEngine):
    engine_id = "pymupdf4llm"
    display_name = "Fast (pymupdf4llm)"
    description = "PDFs normales: informes, artículos, documentación. Rápido y preciso."

    @classmethod
    def is_available(cls) -> bool:
        try:
            import pymupdf4llm  # noqa: F401
            return True
        except Exception:
            return False

    def convert(self, pdf_path: Path) -> str:
        import pymupdf4llm
        pymupdf4llm.use_layout(False)
        return pymupdf4llm.to_markdown(str(pdf_path), write_images=False)


class MarkerPDFEngine(ConversionEngine):
    engine_id = "marker"
    display_name = "ML (marker-pdf)"
    description = "PDFs complejos: multi-columna, escaneados, tablas densas. Usa modelos de ML."

    @classmethod
    def is_available(cls) -> bool:
        try:
            import marker  # noqa: F401
            return True
        except Exception:
            return False

    def convert(self, pdf_path: Path) -> str:
        self._fix_accelerate_meta_device()

        try:
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
        except ImportError as e:
            raise RuntimeError(
                "marker-pdf no está instalado correctamente. "
                "Ejecutá: pip install marker-pdf"
            ) from e

        try:
            converter = PdfConverter(artifact_dict=create_model_dict())
            rendered = converter(str(pdf_path))
            return rendered.markdown
        except Exception as e:
            msg = str(e)
            if "ConnectTimeout" in msg or "IncompleteRead" in msg or "Max retries" in msg:
                raise RuntimeError(
                    "No se pudieron descargar los modelos ML. "
                    "Verificá tu conexión a internet e intentá de nuevo.\n\n"
                    "Los modelos se descargan una sola vez (~1.5GB).\n"
                    f"Error original: {msg[:200]}"
                ) from e
            raise

    @staticmethod
    def _fix_accelerate_meta_device():
        """Reemplaza init_empty_weights de accelerate para usar CPU en vez de meta.

        accelerate crea modelos vacíos en dispositivo 'meta' para ahorrar memoria
        durante la carga. Luego intenta .to() para moverlos a CPU/GPU, pero
        PyTorch >= 2.2 rechaza .to() desde 'meta' y exige .to_empty().

        En vez de parchear PyTorch, reemplazamos la función de accelerate para
        que cree los modelos directamente en CPU, evitando el problema de raíz.
        """
        import contextlib

        import torch
        import torch.nn as nn

        if getattr(MarkerPDFEngine, '_meta_fixed', False):
            return

        # Buscar init_empty_weights en las ubicaciones conocidas de accelerate
        _orig_func = None
        _target_module = None
        for mod_path in ["accelerate.utils", "accelerate.utils.modeling"]:
            try:
                mod = __import__(mod_path, fromlist=["init_empty_weights"])
                if hasattr(mod, "init_empty_weights"):
                    _orig_func = mod.init_empty_weights
                    _target_module = mod
                    break
            except ImportError:
                continue

        if _orig_func is None:
            return  # accelerate no encontrado, no hay nada que parchear

        @contextlib.contextmanager
        def _cpu_init_empty_weights(include_buffers=None):
            old_register_parameter = nn.Module.register_parameter
            if include_buffers:
                old_register_buffer = nn.Module.register_buffer

            def register_empty_parameter(module, name, param):
                old_register_parameter(module, name, param)
                if param is not None:
                    param_cls = type(param)
                    module._parameters[name] = param_cls(
                        module._parameters[name].to(torch.device("cpu"))
                    )

            def register_empty_buffer(module, name, buffer, persistent=True):
                old_register_buffer(module, name, buffer, persistent=persistent)
                if buffer is not None:
                    module._buffers[name] = module._buffers[name].to(
                        torch.device("cpu")
                    )

            try:
                nn.Module.register_parameter = register_empty_parameter
                if include_buffers:
                    nn.Module.register_buffer = register_empty_buffer
                yield
            finally:
                nn.Module.register_parameter = old_register_parameter
                if include_buffers:
                    nn.Module.register_buffer = old_register_buffer

        _target_module.init_empty_weights = _cpu_init_empty_weights
        MarkerPDFEngine._meta_fixed = True


def get_available_engines() -> dict[str, ConversionEngine]:
    engines: dict[str, ConversionEngine] = {}
    for cls in (PyMuPDF4LLMEngine, MarkerPDFEngine):
        if cls.is_available():
            engines[cls.engine_id] = cls()
    return engines


# ---------------------------------------------------------------------------
# Conversion Job
# ---------------------------------------------------------------------------

@dataclass
class ConversionJob:
    pdf_path: Path
    engine_id: str
    output_dir: Path | None = None
    obsidian_mode: bool = False
    status: str = "Waiting..."
    result: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Conversion Manager (Background Threading)
# ---------------------------------------------------------------------------

class ConversionManager:
    def __init__(self, max_workers: int = 2):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._message_queue: queue.Queue = queue.Queue()
        self._cancel_event = threading.Event()
        self._futures: list[Future] = []
        self._total = 0
        self._completed = 0

    @property
    def messages(self) -> queue.Queue:
        return self._message_queue

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    @property
    def total(self) -> int:
        return self._total

    @property
    def completed(self) -> int:
        return self._completed

    def start(self, jobs: list[ConversionJob], engine: ConversionEngine) -> None:
        self._cancel_event.clear()
        self._total = len(jobs)
        self._completed = 0
        self._futures.clear()

        for job in jobs:
            if self._cancel_event.is_set():
                break
            future = self._executor.submit(self._convert_job, job, engine)
            self._futures.append(future)

    def _convert_job(self, job: ConversionJob, engine: ConversionEngine) -> None:
        if self._cancel_event.is_set():
            job.status = "Cancelled"
            self._message_queue.put(("cancelled", job))
            return

        try:
            job.status = "Converting..."
            self._message_queue.put(("progress", job))

            md_text = engine.convert(job.pdf_path)
            job.result = md_text
            job.status = "Done"
            self._completed += 1
            self._message_queue.put(("done", job))

        except Exception as exc:
            job.status = f"Error: {exc}"
            job.error = traceback.format_exc()
            self._completed += 1
            self._message_queue.put(("error", job, exc))

    def cancel(self) -> None:
        self._cancel_event.set()

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


# ---------------------------------------------------------------------------
# UI — Drop Target Frame
# ---------------------------------------------------------------------------

class DropTargetFrame(ttk.Frame):
    def __init__(self, parent: ttk.Frame, on_files_dropped: Callable[[list[Path]], None]):
        super().__init__(parent)
        self._on_files_dropped = on_files_dropped

        self._canvas: tk.Canvas | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, borderwidth=2, relief="groove")
        outer.pack(fill="both", expand=True, padx=4, pady=(4, 2))

        canvas = tk.Canvas(
            outer, height=90, bg="#f0f4f8", highlightthickness=0
        )
        canvas.pack(fill="both", expand=True)
        self._canvas = canvas

        self._text_id = canvas.create_text(
            450, 45,
            text="Soltá tus archivos PDF acá\n— o —\nHacé clic en Browse...",
            font=("Segoe UI", 11), fill="#5b6b7c", justify="center"
        )

        canvas.drop_target_register("DND_Files")
        canvas.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event) -> None:
        raw_paths = self._parse_drop_data(event.data)
        pdf_paths = [Path(p) for p in raw_paths if Path(p).suffix.lower() == ".pdf"]
        if pdf_paths:
            self._on_files_dropped(pdf_paths)

    @staticmethod
    def _parse_drop_data(data: str) -> list[str]:
        paths: list[str] = []
        current: list[str] = []
        i = 0
        while i < len(data):
            ch = data[i]
            if ch == "{":
                j = data.index("}", i + 1) if "}" in data[i + 1:] else len(data)
                current.append(data[i + 1:j])
                i = j + 1
            elif ch == " ":
                if current:
                    paths.append("".join(current))
                    current = []
                i += 1
            else:
                current.append(ch)
                i += 1
        if current:
            paths.append("".join(current))
        return [p.strip().strip('"') for p in paths if p.strip()]


# ---------------------------------------------------------------------------
# UI — File Queue Frame
# ---------------------------------------------------------------------------

class FileQueueFrame(ttk.LabelFrame):
    def __init__(self, parent: ttk.Frame):
        super().__init__(parent, text="Archivos", padding=4)
        self._jobs: list[ConversionJob] = []
        self._on_queue_changed: Callable[[], None] | None = None

        self._tree: ttk.Treeview | None = None
        self._count_label: ttk.Label | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 2))

        self._count_label = ttk.Label(toolbar, text="0 archivos en cola")
        self._count_label.pack(side="left")

        columns = ("#", "filename", "status")
        self._tree = ttk.Treeview(
            self, columns=columns, show="headings",
            selectmode="extended", height=6
        )
        self._tree.heading("#", text="#")
        self._tree.heading("filename", text="Nombre")
        self._tree.heading("status", text="Estado")

        self._tree.column("#", width=40, anchor="center", stretch=False)
        self._tree.column("filename", width=380, anchor="w")
        self._tree.column("status", width=120, anchor="w")

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._tree.bind("<Delete>", self._on_delete_key)

    def set_on_queue_changed(self, callback: Callable[[], None]) -> None:
        self._on_queue_changed = callback

    def add_files(self, paths: list[Path]) -> None:
        for p in paths:
            job = ConversionJob(pdf_path=p, engine_id="pymupdf4llm")
            self._jobs.append(job)
            self._tree.insert(
                "", "end",
                values=(len(self._jobs), p.name, "Waiting..."),
                iid=str(id(job))
            )
        self._update_count()
        if self._on_queue_changed:
            self._on_queue_changed()

    def remove_selected(self) -> None:
        selected = self._tree.selection()
        for iid in selected:
            job = self._find_job_by_iid(iid)
            if job and job.status not in ("Converting...",):
                self._jobs.remove(job)
                self._tree.delete(iid)
        self._renumber()
        self._update_count()
        if self._on_queue_changed:
            self._on_queue_changed()

    def clear_completed(self) -> None:
        to_remove = [j for j in self._jobs if j.status not in ("Waiting...", "Converting...")]
        for job in to_remove:
            for iid in self._tree.get_children():
                if self._tree.item(iid)["values"][1] == job.pdf_path.name:
                    self._tree.delete(iid)
                    break
            self._jobs.remove(job)
        self._renumber()
        self._update_count()

    def clear_all(self) -> None:
        to_remove = [j for j in self._jobs if j.status != "Converting..."]
        for job in to_remove:
            for iid in self._tree.get_children():
                if self._tree.item(iid)["values"][1] == job.pdf_path.name:
                    self._tree.delete(iid)
                    break
            self._jobs.remove(job)
        self._renumber()
        self._update_count()
        if self._on_queue_changed:
            self._on_queue_changed()

    def get_pending_jobs(self) -> list[ConversionJob]:
        return [j for j in self._jobs if j.status == "Waiting..."]

    def get_all_jobs(self) -> list[ConversionJob]:
        return list(self._jobs)

    def update_job_status(self, job: ConversionJob) -> None:
        for iid, values in [(i, self._tree.item(i)["values"]) for i in self._tree.get_children()]:
            if values[1] == job.pdf_path.name:
                self._tree.set(iid, "status", job.status)
                self._renumber()
                break

    def _renumber(self) -> None:
        for idx, iid in enumerate(self._tree.get_children(), start=1):
            values = list(self._tree.item(iid)["values"])
            values[0] = idx
            self._tree.item(iid, values=values)

    def _find_job_by_iid(self, iid: str) -> ConversionJob | None:
        filename = self._tree.item(iid)["values"][1]
        for j in self._jobs:
            if j.pdf_path.name == filename:
                return j
        return None

    def _on_delete_key(self, _event) -> None:
        self.remove_selected()

    def _update_count(self) -> None:
        if self._count_label:
            n = len(self._jobs)
            self._count_label.configure(text=f"{n} archivo{'s' if n != 1 else ''} en cola")


# ---------------------------------------------------------------------------
# UI — Engine Selector Frame
# ---------------------------------------------------------------------------

class EngineSelectorFrame(ttk.LabelFrame):
    def __init__(self, parent: ttk.Frame):
        super().__init__(parent, text="Motor de Conversión", padding=4)
        self._var = tk.StringVar(value="pymupdf4llm")
        self._on_change: Callable[[str], None] | None = None

        self._rb_fast: ttk.Radiobutton | None = None
        self._rb_ml: ttk.Radiobutton | None = None
        self._desc_label: ttk.Label | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        fast_avail = PyMuPDF4LLMEngine.is_available()
        ml_avail = MarkerPDFEngine.is_available()

        self._rb_fast = ttk.Radiobutton(
            self, text=PyMuPDF4LLMEngine.display_name,
            variable=self._var, value="pymupdf4llm",
            command=self._on_select
        )
        self._rb_fast.pack(anchor="w")
        if not fast_avail:
            self._rb_fast.configure(state="disabled")

        ml_text = MarkerPDFEngine.display_name
        if not ml_avail:
            ml_text += "  [No instalado — pip install marker-pdf]"

        self._rb_ml = ttk.Radiobutton(
            self, text=ml_text, variable=self._var,
            value="marker", command=self._on_select
        )
        self._rb_ml.pack(anchor="w")
        if not ml_avail:
            self._rb_ml.configure(state="disabled")

        self._desc_label = ttk.Label(
            self,
            text=PyMuPDF4LLMEngine.description,
            font=("Segoe UI", 9), foreground="#6b7c8b"
        )
        self._desc_label.pack(anchor="w", padx=(20, 0), pady=(2, 0))

    def _on_select(self) -> None:
        descriptions = {
            "pymupdf4llm": PyMuPDF4LLMEngine.description,
            "marker": MarkerPDFEngine.description,
        }
        if self._desc_label:
            self._desc_label.configure(text=descriptions.get(self._var.get(), ""))
        if self._on_change:
            self._on_change(self._var.get())

    def set_on_change(self, callback: Callable[[str], None]) -> None:
        self._on_change = callback

    def get_selected(self) -> str:
        return self._var.get()

    def enable(self) -> None:
        if PyMuPDF4LLMEngine.is_available():
            self._rb_fast.configure(state="normal")
        if MarkerPDFEngine.is_available():
            self._rb_ml.configure(state="normal")

    def disable(self) -> None:
        self._rb_fast.configure(state="disabled")
        self._rb_ml.configure(state="disabled")


# ---------------------------------------------------------------------------
# UI — Output Selector Frame
# ---------------------------------------------------------------------------

class OutputSelectorFrame(ttk.LabelFrame):
    def __init__(self, parent: ttk.Frame):
        super().__init__(parent, text="Salida y Formato", padding=4)
        self._var = tk.StringVar(value="same")
        self._obsidian_var = tk.BooleanVar(value=True)

        self._custom_entry: ttk.Entry | None = None
        self._browse_btn: ttk.Button | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        rb_same = ttk.Radiobutton(
            self, text="Misma carpeta que el PDF de origen",
            variable=self._var, value="same", command=self._on_toggle
        )
        rb_same.pack(anchor="w")

        custom_frame = ttk.Frame(self)
        custom_frame.pack(anchor="w", fill="x", pady=(2, 0))

        rb_custom = ttk.Radiobutton(
            custom_frame, text="Carpeta personalizada:",
            variable=self._var, value="custom", command=self._on_toggle
        )
        rb_custom.pack(side="left")

        self._custom_entry = ttk.Entry(custom_frame, width=40, state="disabled")
        self._custom_entry.pack(side="left", padx=(6, 4))

        self._browse_btn = ttk.Button(
            custom_frame, text="Browse...",
            command=self._browse, state="disabled"
        )
        self._browse_btn.pack(side="left")

        # Obsidian toggle
        sep = ttk.Separator(self, orient="horizontal")
        sep.pack(fill="x", pady=(8, 4))

        obsidian_cb = ttk.Checkbutton(
            self,
            text="Modo Obsidian (frontmatter YAML + tags + formato limpio)",
            variable=self._obsidian_var,
        )
        obsidian_cb.pack(anchor="w")

    def _on_toggle(self) -> None:
        state = "normal" if self._var.get() == "custom" else "disabled"
        if self._custom_entry:
            self._custom_entry.configure(state=state)
        if self._browse_btn:
            self._browse_btn.configure(state=state)

    def _browse(self) -> None:
        path = filedialog.askdirectory(title="Seleccioná carpeta de salida")
        if path and self._custom_entry:
            self._custom_entry.delete(0, "end")
            self._custom_entry.insert(0, path)

    def get_output_dir(self, source_pdf: Path) -> Path:
        if self._var.get() == "custom" and self._custom_entry:
            custom = self._custom_entry.get().strip()
            if custom:
                return Path(custom)
        return source_pdf.parent

    def get_obsidian_mode(self) -> bool:
        return self._obsidian_var.get()

    def enable(self) -> None:
        children = self.winfo_children()
        self._traverse_enable(children, True)

    def disable(self) -> None:
        children = self.winfo_children()
        self._traverse_enable(children, False)

    @staticmethod
    def _traverse_enable(widgets: tuple, state: bool) -> None:
        for w in widgets:
            try:
                if isinstance(w, (ttk.Radiobutton, ttk.Entry, ttk.Button, ttk.Checkbutton)):
                    w.configure(state="normal" if state else "disabled")
                children = w.winfo_children()
                if children:
                    OutputSelectorFrame._traverse_enable(children, state)
            except tk.TclError:
                pass


# ---------------------------------------------------------------------------
# UI — Progress Frame
# ---------------------------------------------------------------------------

class ProgressFrame(ttk.Frame):
    def __init__(self, parent: ttk.Frame):
        super().__init__(parent)
        self._on_cancel: Callable[[], None] | None = None

        self._progress: ttk.Progressbar | None = None
        self._label: ttk.Label | None = None
        self._cancel_btn: ttk.Button | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        self._progress = ttk.Progressbar(self, mode="determinate", maximum=100)
        self._progress.pack(fill="x", padx=4, pady=(4, 2))

        controls = ttk.Frame(self)
        controls.pack(fill="x", padx=4)

        self._label = ttk.Label(controls, text="Listo para convertir.", font=("Segoe UI", 9))
        self._label.pack(side="left")

        self._cancel_btn = ttk.Button(controls, text="Cancelar", command=self._on_cancel_click)
        self._cancel_btn.pack(side="right")

    def set_on_cancel(self, callback: Callable[[], None]) -> None:
        self._on_cancel = callback

    def _on_cancel_click(self) -> None:
        if self._on_cancel:
            self._on_cancel()

    def reset(self) -> None:
        if self._progress:
            self._progress["value"] = 0
        self.set_label("Iniciando conversión...")

    def set_progress(self, completed: int, total: int) -> None:
        if self._progress:
            self._progress["value"] = (completed / total * 100) if total else 0

    def set_label(self, text: str) -> None:
        if self._label:
            self._label.configure(text=text)


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()

        self.title("PDF to Markdown Converter")
        self.minsize(900, 650)
        self.geometry("920x700")

        self._style = ttk.Style()
        self._setup_theme()

        self._manager: ConversionManager | None = None
        self._poll_id: str | None = None
        self._engine: ConversionEngine | None = None

        self._drop_frame: DropTargetFrame | None = None
        self._queue_frame: FileQueueFrame | None = None
        self._engine_frame: EngineSelectorFrame | None = None
        self._output_frame: OutputSelectorFrame | None = None
        self._progress_frame: ProgressFrame | None = None
        self._status_bar: ttk.Label | None = None
        self._start_btn: ttk.Button | None = None

        self._build_ui()

    def _setup_theme(self) -> None:
        try:
            available = self._style.theme_names()
            if "vista" in available:
                self._style.theme_use("vista")
            elif "winnative" in available:
                self._style.theme_use("winnative")
        except tk.TclError:
            pass

    # -- Build UI ----------------------------------------------------------

    def _build_ui(self) -> None:
        # Top bar with Browse / Clear
        top_bar = ttk.Frame(self)
        top_bar.pack(fill="x", padx=8, pady=(8, 0))

        browse_btn = ttk.Button(top_bar, text="Browse Files...", command=self._browse_files)
        browse_btn.pack(side="left", padx=(0, 6))

        clear_btn = ttk.Button(top_bar, text="Clear Queue", command=self._clear_queue)
        clear_btn.pack(side="left")

        # Drop zone
        self._drop_frame = DropTargetFrame(self, on_files_dropped=self._add_files)
        self._drop_frame.pack(fill="x", padx=8, pady=(6, 0))

        # File queue
        self._queue_frame = FileQueueFrame(self)
        self._queue_frame.pack(fill="both", expand=True, padx=8, pady=(6, 0))
        self._queue_frame.set_on_queue_changed(self._on_queue_update)

        # Engine + Output row
        options_row = ttk.Frame(self)
        options_row.pack(fill="x", padx=8, pady=(6, 0))

        self._engine_frame = EngineSelectorFrame(options_row)
        self._engine_frame.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._engine_frame.set_on_change(self._on_engine_change)

        self._output_frame = OutputSelectorFrame(options_row)
        self._output_frame.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # Progress
        self._progress_frame = ProgressFrame(self)
        self._progress_frame.pack(fill="x", padx=8, pady=(6, 0))
        self._progress_frame.set_on_cancel(self._cancel_conversion)

        # Action buttons
        action_bar = ttk.Frame(self)
        action_bar.pack(fill="x", padx=8, pady=(6, 4))

        self._start_btn = ttk.Button(
            action_bar, text="Iniciar Conversión",
            command=self._start_conversion
        )
        self._start_btn.pack(side="left")

        # Status bar
        self._status_bar = ttk.Label(
            self, text="Listo. Cargá archivos PDF para comenzar.",
            font=("Segoe UI", 9), anchor="w",
            relief="sunken", padding=(6, 3)
        )
        self._status_bar.pack(fill="x", side="bottom")

    # -- Event Handlers ----------------------------------------------------

    def _browse_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Seleccioná archivos PDF",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        if paths:
            self._add_files([Path(p) for p in paths])

    def _add_files(self, paths: list[Path]) -> None:
        if self._queue_frame:
            self._queue_frame.add_files(paths)
            self._set_status(f"{len(paths)} archivo(s) agregado(s).")

    def _clear_queue(self) -> None:
        if self._queue_frame:
            self._queue_frame.clear_all()
            self._set_status("Cola vaciada.")

    def _on_queue_update(self) -> None:
        if self._queue_frame and self._start_btn:
            pending = self._queue_frame.get_pending_jobs()
            self._start_btn.configure(
                state="normal" if pending else "disabled"
            )

    def _on_engine_change(self, engine_id: str) -> None:
        pass  # descriptiva se actualiza sola en el frame

    # -- Conversion Flow ---------------------------------------------------

    def _start_conversion(self) -> None:
        if not self._queue_frame:
            return

        engine_id = self._engine_frame.get_selected() if self._engine_frame else "pymupdf4llm"
        engines = get_available_engines()

        if engine_id not in engines:
            messagebox.showerror(
                "Motor no disponible",
                f"El motor '{engine_id}' no está instalado.\n\n"
                "Instalalo con: pip install marker-pdf\n"
                "O seleccioná el motor rápido (pymupdf4llm)."
            )
            return

        self._engine = engines[engine_id]
        jobs = self._queue_frame.get_pending_jobs()

        if not jobs:
            messagebox.showinfo("Sin archivos", "No hay archivos PDF en cola para convertir.")
            return

        # Assign engine + output + obsidian mode
        obsidian_mode = self._output_frame.get_obsidian_mode() if self._output_frame else True
        for job in jobs:
            job.engine_id = engine_id
            job.obsidian_mode = obsidian_mode
            if self._output_frame:
                job.output_dir = self._output_frame.get_output_dir(job.pdf_path)

        self._disable_inputs()
        self._progress_frame.reset()

        self._manager = ConversionManager(max_workers=2)
        self._manager.start(jobs, self._engine)
        self._poll_progress()

        self._set_status(f"Convirtiendo {len(jobs)} archivo(s) con {self._engine.display_name}...")

    def _poll_progress(self) -> None:
        if not self._manager:
            return

        msg_queue = self._manager.messages
        try:
            while True:
                msg = msg_queue.get_nowait()
                msg_type = msg[0]
                job: ConversionJob = msg[1]

                if self._queue_frame:
                    self._queue_frame.update_job_status(job)

                if msg_type == "done":
                    self._write_output(job)
                elif msg_type == "error":
                    exc = msg[2] if len(msg) > 2 else None
                    self._set_status(f"Error en {job.pdf_path.name}: {job.status}")

        except queue.Empty:
            pass

        completed = self._manager.completed
        total = self._manager.total
        self._progress_frame.set_progress(completed, total)
        self._progress_frame.set_label(
            f"Completado: {completed} de {total} archivo(s)"
        )

        # Check if all done
        all_queued = self._queue_frame.get_pending_jobs() if self._queue_frame else []
        still_working = [j for j in (self._queue_frame.get_all_jobs() if self._queue_frame else [])
                         if j.status == "Converting..."]

        if not still_working and completed >= total:
            self._finish_conversion()
            return

        self._poll_id = self.after(150, self._poll_progress)

    def _write_output(self, job: ConversionJob) -> None:
        if not job.result:
            return

        output_dir = job.output_dir or job.pdf_path.parent
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return

        stem = job.pdf_path.stem
        out_path = output_dir / f"{stem}.md"

        # Handle collisions
        counter = 1
        while out_path.exists():
            out_path = output_dir / f"{stem}_{counter}.md"
            counter += 1

        # Apply Obsidian post-processing if enabled
        content = job.result
        if job.obsidian_mode:
            engine = self._engine
            engine_name = engine.display_name if engine else "pymupdf4llm"
            content = ObsidianPostProcessor.process(job.result, job.pdf_path, engine_name)

        try:
            out_path.write_text(content, encoding="utf-8")
        except OSError as exc:
            job.status = f"Error al escribir: {exc}"
            if self._queue_frame:
                self._queue_frame.update_job_status(job)

    def _finish_conversion(self) -> None:
        if self._poll_id:
            self.after_cancel(self._poll_id)
            self._poll_id = None

        self._enable_inputs()

        if self._manager and self._manager.is_cancelled:
            self._set_status("Conversión cancelada por el usuario.")
            self._progress_frame.set_label("Cancelado.")
        else:
            total = self._manager.total if self._manager else 0
            self._set_status(f"Conversión completada. {total} archivo(s) procesado(s).")
            self._progress_frame.set_label(f"¡Listo! {total} archivo(s) convertido(s).")

        # Optional notification
        try:
            self.bell()
        except tk.TclError:
            pass

    def _cancel_conversion(self) -> None:
        if self._manager:
            self._manager.cancel()
            self._progress_frame.set_label("Cancelando...")
            self._set_status("Cancelando conversión...")

    # -- UI State Management ------------------------------------------------

    def _disable_inputs(self) -> None:
        if self._start_btn:
            self._start_btn.configure(state="disabled")
        if self._engine_frame:
            self._engine_frame.disable()
        if self._output_frame:
            self._output_frame.disable()

    def _enable_inputs(self) -> None:
        if self._start_btn:
            self._start_btn.configure(state="normal")
        if self._engine_frame:
            self._engine_frame.enable()
        if self._output_frame:
            self._output_frame.enable()

    def _set_status(self, text: str) -> None:
        if self._status_bar:
            self._status_bar.configure(text=text)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    if not PyMuPDF4LLMEngine.is_available():
        messagebox.showerror(
            "Dependencia Faltante",
            "pymupdf4llm no está instalado.\n\n"
            "Ejecutá: pip install pymupdf4llm\n\n"
            "La aplicación se cerrará."
        )
        sys.exit(1)

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
