"""Panel de control para lanzar todos los programas de AppSanti."""
import csv
import json
import os
import sys
import subprocess
import threading
import tkinter as tk
import urllib.request
from datetime import datetime
from tkinter import ttk, messagebox

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "registro_uso.csv")
LOG_HEADERS = ["Programa", "Inicio", "Fin", "Duracion_seg", "Duracion"]

__version__ = "1.0.2"
GITHUB_REPO = "santiagoPuleio/appsanti-launcher"
ASSET_NAME = "AppSanti.exe"

CALCULADORA_LOMO = ("Calculadora de Lomo", "📏", r"calculadoraLomo\dist\Lomera.exe")
CONTADOR_CARACTERES = ("Contador de Caracteres", "🔢", r"cont2.0\dist\contadorCaracteres_mod.exe")
GENERADOR_PDF = ("Generador PDF Bren/Meli", "🧾", r"generadorMeliBren (1)\GeneradorPDFBrenMeli\dist\generarPDF\generarPDF.exe")
VERIFICADOR_INDICES = ("Verificador de Índices PDF", "📄", r"programaIndices\validadorIndices\dist\verificador_indices\verificador_indices.exe")
VALIDADOR_PREPLANTA = ("ValidadorPrePlanta", "📐", r"validadorMeli\ValidadorPrePlanta\dist\margenes_pagina\margenes_pagina.exe")
VALIDADOR_INDICES_MEJORADO = ("Validador de Índices Mejorado", "📊", r"ValidarIndicesMejorado\dist\validador_superindices_word\validador_superindices_word.exe")
VALIDADOR_PIE = ("Validador de Pie", "👣", r"validarPie\dist\validador_superindices_word\validador_superindices_word.exe")
VALIDADOR_PREPLANTA_FOLIOS = (
    "ValidadorPrePlantavFolios",
    "📑",
    r"validadorpreplantaVFolios\validadorMeli\ValidadorPrePlanta\dist\margenes_pagina\margenes_pagina.exe",
)

PESTANAS = {
    "Editorial": [
        CALCULADORA_LOMO,
        CONTADOR_CARACTERES,
        GENERADOR_PDF,
        VERIFICADOR_INDICES,
        VALIDADOR_PREPLANTA,
        VALIDADOR_INDICES_MEJORADO,
        VALIDADOR_PIE,
    ],
    "CPS": [
        CALCULADORA_LOMO,
        GENERADOR_PDF,
        VALIDADOR_PREPLANTA_FOLIOS,
    ],
}

PALETTE = {
    "bg": "#eef1f8",
    "header": "#4C63D2",
    "header_text": "#ffffff",
    "card": "#ffffff",
    "card_hover": "#e8edff",
    "border": "#dde3f0",
    "text": "#1c2333",
    "subtext": "#6b7280",
    "accent": "#4C63D2",
}


def format_duration(seconds):
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def registrar_uso(nombre, inicio_dt, fin_dt):
    nuevo = not os.path.isfile(LOG_PATH)
    duracion_seg = (fin_dt - inicio_dt).total_seconds()
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if nuevo:
            writer.writerow(LOG_HEADERS)
        writer.writerow(
            [
                nombre,
                inicio_dt.strftime("%Y-%m-%d %H:%M:%S"),
                fin_dt.strftime("%Y-%m-%d %H:%M:%S"),
                f"{duracion_seg:.0f}",
                format_duration(duracion_seg),
            ]
        )


def leer_log():
    if not os.path.isfile(LOG_PATH):
        return []
    with open(LOG_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _version_tuple(version):
    partes = []
    for p in version.lstrip("vV").split("."):
        try:
            partes.append(int(p))
        except ValueError:
            partes.append(0)
    return tuple(partes)


def buscar_actualizacion():
    """Consulta el último release público en GitHub. Devuelve (tag, url_descarga) o None."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "AppSanti-Launcher"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    tag = data.get("tag_name", "")
    if not tag or _version_tuple(tag) <= _version_tuple(__version__):
        return None

    for asset in data.get("assets", []):
        if asset.get("name") == ASSET_NAME:
            return tag, asset.get("browser_download_url")
    return None


def descargar_actualizacion(url, destino):
    req = urllib.request.Request(url, headers={"User-Agent": "AppSanti-Launcher"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(destino, "wb") as f:
        f.write(resp.read())


def aplicar_actualizacion_y_salir(exe_nuevo):
    """Reemplaza el .exe en uso por el nuevo una vez que este proceso termina, y lo reabre."""
    exe_actual = os.path.abspath(sys.executable)
    pid = os.getpid()
    bat_path = os.path.join(BASE_DIR, "_actualizar_appsanti.bat")
    contenido_bat = (
        "@echo off\r\n"
        ":espera\r\n"
        f'tasklist /fi "PID eq {pid}" 2>nul | find "{pid}" >nul\r\n'
        "if not errorlevel 1 (\r\n"
        "  timeout /t 1 /nobreak >nul\r\n"
        "  goto espera\r\n"
        ")\r\n"
        f'move /y "{exe_nuevo}" "{exe_actual}" >nul\r\n'
        f'start "" "{exe_actual}"\r\n'
        'del "%~f0"\r\n'
    )
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(contenido_bat)
    subprocess.Popen(["cmd", "/c", bat_path], creationflags=subprocess.CREATE_NO_WINDOW)
    os._exit(0)


class HistorialWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Historial de uso")
        self.geometry("560x440")
        self.configure(bg=PALETTE["bg"])

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)

        sesiones_frame = ttk.Frame(notebook)
        totales_frame = ttk.Frame(notebook)
        notebook.add(sesiones_frame, text="Sesiones")
        notebook.add(totales_frame, text="Totales por programa")

        self._construir_sesiones(sesiones_frame)
        self._construir_totales(totales_frame)

    def _construir_sesiones(self, parent):
        rows = leer_log()
        if not rows:
            ttk.Label(parent, text="Todavía no hay registros de uso.").pack(pady=30)
            return
        cols = ("Programa", "Inicio", "Fin", "Duracion")
        tree = ttk.Treeview(parent, columns=cols, show="headings")
        widths = {"Programa": 190, "Inicio": 130, "Fin": 130, "Duracion": 80}
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=widths[c], anchor="center" if c == "Duracion" else "w")
        for r in reversed(rows):
            tree.insert("", "end", values=(r["Programa"], r["Inicio"], r["Fin"], r["Duracion"]))
        tree.pack(fill="both", expand=True)

    def _construir_totales(self, parent):
        rows = leer_log()
        if not rows:
            ttk.Label(parent, text="Todavía no hay registros de uso.").pack(pady=30)
            return
        totales, conteo = {}, {}
        for r in rows:
            totales[r["Programa"]] = totales.get(r["Programa"], 0) + float(r["Duracion_seg"])
            conteo[r["Programa"]] = conteo.get(r["Programa"], 0) + 1
        cols = ("Programa", "Usos", "Tiempo total")
        tree = ttk.Treeview(parent, columns=cols, show="headings")
        tree.heading("Programa", text="Programa")
        tree.heading("Usos", text="Usos")
        tree.heading("Tiempo total", text="Tiempo total")
        tree.column("Programa", width=260, anchor="w")
        tree.column("Usos", width=80, anchor="center")
        tree.column("Tiempo total", width=120, anchor="center")
        for nombre, seg in sorted(totales.items(), key=lambda x: -x[1]):
            tree.insert("", "end", values=(nombre, conteo[nombre], format_duration(seg)))
        tree.pack(fill="both", expand=True)


class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AppSanti - Panel de Control")
        self.geometry("460x780")
        self.configure(bg=PALETTE["bg"])
        self.resizable(False, False)

        self.activos = {}
        self._next_id = 0
        self.status_var = tk.StringVar(value="Listo.")

        self._configurar_estilos()
        self._construir_header()
        self._construir_programas()
        self._construir_activos()
        self._construir_footer()
        self._centrar()

        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)
        self.after(1000, self._tick)
        self.after(1500, self._chequear_actualizaciones)

    def _configurar_estilos(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("TNotebook", background=PALETTE["bg"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            font=("Segoe UI", 10, "bold"),
            padding=(18, 9),
            background=PALETTE["card"],
            foreground=PALETTE["subtext"],
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", PALETTE["accent"])],
            foreground=[("selected", "#ffffff")],
        )

        style.configure("Treeview", font=("Segoe UI", 9), rowheight=24, background=PALETTE["card"], fieldbackground=PALETTE["card"])
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

        style.configure(
            "Accent.TButton",
            font=("Segoe UI", 9, "bold"),
            padding=(12, 6),
            background=PALETTE["accent"],
            foreground="#ffffff",
            borderwidth=0,
        )
        style.map("Accent.TButton", background=[("active", "#3d51b0")])

    def _centrar(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"+{x}+{y}")

    def _construir_header(self):
        header = tk.Frame(self, bg=PALETTE["header"], height=80)
        header.pack(fill="x")
        tk.Label(
            header,
            text="AppSanti",
            font=("Segoe UI", 18, "bold"),
            bg=PALETTE["header"],
            fg=PALETTE["header_text"],
        ).pack(anchor="w", padx=20, pady=(14, 0))
        tk.Label(
            header,
            text="Elegí el programa que querés abrir",
            font=("Segoe UI", 9),
            bg=PALETTE["header"],
            fg="#dbe2ff",
        ).pack(anchor="w", padx=20, pady=(0, 12))

    def _construir_programas(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="x", padx=16, pady=(14, 6))

        for pestana_nombre, herramientas in PESTANAS.items():
            tab = tk.Frame(notebook, bg=PALETTE["bg"], height=420)
            tab.pack_propagate(False)
            notebook.add(tab, text=pestana_nombre)

            inner = tk.Frame(tab, bg=PALETTE["bg"])
            inner.pack(fill="both", expand=True, padx=4, pady=8)
            for nombre, icono, ruta in herramientas:
                self._crear_card(inner, nombre, icono, ruta).pack(fill="x", pady=4)

    def _crear_card(self, parent, nombre, icono, ruta):
        card = tk.Frame(
            parent,
            bg=PALETTE["card"],
            highlightthickness=1,
            highlightbackground=PALETTE["border"],
            cursor="hand2",
        )
        icono_lbl = tk.Label(card, text=icono, font=("Segoe UI Emoji", 16), bg=PALETTE["card"])
        icono_lbl.pack(side="left", padx=(14, 10), pady=10)
        nombre_lbl = tk.Label(
            card, text=nombre, font=("Segoe UI", 10, "bold"), bg=PALETTE["card"], fg=PALETTE["text"], anchor="w"
        )
        nombre_lbl.pack(side="left", fill="x", expand=True, pady=10)
        flecha_lbl = tk.Label(card, text="▶", font=("Segoe UI", 10), bg=PALETTE["card"], fg=PALETTE["accent"])
        flecha_lbl.pack(side="right", padx=14)

        widgets = [card, icono_lbl, nombre_lbl, flecha_lbl]

        def on_enter(_e):
            for w in widgets:
                w.configure(bg=PALETTE["card_hover"])

        def on_leave(_e):
            for w in widgets:
                w.configure(bg=PALETTE["card"])

        def on_click(_e):
            self.abrir_programa(nombre, ruta)

        for w in widgets:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)

        return card

    def _construir_activos(self):
        frame = tk.Frame(self, bg=PALETTE["bg"])
        frame.pack(fill="both", expand=True, padx=16, pady=(6, 0))

        tk.Label(
            frame, text="En uso ahora", font=("Segoe UI", 10, "bold"), bg=PALETTE["bg"], fg=PALETTE["text"]
        ).pack(anchor="w", pady=(4, 4))

        self.tree_activos = ttk.Treeview(
            frame, columns=("programa", "tiempo"), show="headings", height=4
        )
        self.tree_activos.heading("programa", text="Programa")
        self.tree_activos.heading("tiempo", text="Tiempo abierto")
        self.tree_activos.column("programa", width=300)
        self.tree_activos.column("tiempo", width=110, anchor="center")
        self.tree_activos.pack(fill="x")

    def _construir_footer(self):
        footer = tk.Frame(self, bg=PALETTE["bg"])
        footer.pack(fill="x", padx=16, pady=10, side="bottom")

        ttk.Button(footer, text="Ver historial de uso", command=self._abrir_historial).pack(side="right")
        tk.Label(
            footer, textvariable=self.status_var, font=("Segoe UI", 8), bg=PALETTE["bg"], fg=PALETTE["subtext"]
        ).pack(side="left")
        tk.Label(
            footer, text=f"v{__version__}", font=("Segoe UI", 8), bg=PALETTE["bg"], fg=PALETTE["subtext"]
        ).pack(side="left", padx=(8, 0))

    def _abrir_historial(self):
        HistorialWindow(self)

    def abrir_programa(self, nombre, ruta_relativa):
        ruta = os.path.join(BASE_DIR, ruta_relativa)
        if not os.path.isfile(ruta):
            messagebox.showerror("No encontrado", f"No se encontró el ejecutable de '{nombre}':\n{ruta}")
            return
        try:
            proc = subprocess.Popen([ruta], cwd=os.path.dirname(ruta))
        except OSError as e:
            messagebox.showerror("Error al abrir", f"No se pudo abrir '{nombre}':\n{e}")
            return

        self._next_id += 1
        item = self.tree_activos.insert("", "end", values=(nombre, "0:00"))
        self.activos[self._next_id] = {
            "nombre": nombre,
            "proc": proc,
            "inicio": datetime.now(),
            "item": item,
        }
        self.status_var.set(f"Abriendo: {nombre}")

    def _tick(self):
        for key, info in list(self.activos.items()):
            if info["proc"].poll() is not None:
                fin = datetime.now()
                registrar_uso(info["nombre"], info["inicio"], fin)
                self.tree_activos.delete(info["item"])
                duracion = format_duration((fin - info["inicio"]).total_seconds())
                self.status_var.set(f"Cerrado: {info['nombre']} ({duracion})")
                del self.activos[key]
            else:
                elapsed = (datetime.now() - info["inicio"]).total_seconds()
                self.tree_activos.item(info["item"], values=(info["nombre"], format_duration(elapsed)))
        self.after(1000, self._tick)

    def _chequear_actualizaciones(self):
        if not getattr(sys, "frozen", False):
            return
        threading.Thread(target=self._chequear_actualizaciones_worker, daemon=True).start()

    def _chequear_actualizaciones_worker(self):
        try:
            resultado = buscar_actualizacion()
        except Exception:
            return
        if not resultado:
            return
        tag, url = resultado
        if not url:
            return

        self.after(0, lambda: self.status_var.set(f"Descargando actualización {tag}..."))
        destino = os.path.join(BASE_DIR, "AppSanti_nuevo.exe")
        try:
            descargar_actualizacion(url, destino)
        except Exception:
            self.after(0, lambda: self.status_var.set("No se pudo descargar la actualización."))
            return

        self.after(0, lambda: self._instalar_actualizacion(destino, tag))

    def _instalar_actualizacion(self, destino, tag):
        self.status_var.set(f"Actualización {tag} lista. Cerrando para instalarla...")
        messagebox.showinfo(
            "Actualización disponible",
            f"Se descargó la versión {tag}.\n\n"
            "El programa se va a cerrar y reabrir solo con la nueva versión.\n"
            "Si no se reabre en unos segundos, volvé a abrirlo manualmente: ya va a tener la actualización aplicada.",
        )
        aplicar_actualizacion_y_salir(destino)

    def _al_cerrar(self):
        if self.activos:
            respuesta = messagebox.askyesno(
                "Programas abiertos",
                "Hay programas todavía abiertos. Si cerrás el panel ahora, no se registrará "
                "el tiempo de uso de esas sesiones. ¿Cerrar igual?",
            )
            if not respuesta:
                return
        self.destroy()


def main():
    Launcher().mainloop()


if __name__ == "__main__":
    main()
