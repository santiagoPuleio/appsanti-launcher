"""Panel de control para lanzar todos los programas de AppSanti."""
import csv
import json
import os
import re
import shutil
import sys
import subprocess
import threading
import tkinter as tk
import urllib.request
import zipfile
from datetime import datetime
from tkinter import ttk, messagebox

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "registro_uso.csv")
LOG_HEADERS = ["Programa", "Inicio", "Fin", "Duracion_seg", "Duracion"]

__version__ = "2.0.4"
GITHUB_REPO = "santiagoPuleio/appsanti-launcher"
ASSET_NAME = "AppSanti.exe"
MANIFEST_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/master/manifest.json"
LOCAL_MANIFEST_PATH = os.path.join(BASE_DIR, "manifest_local.json")

# Copia de referencia de manifest.json: se usa como punto de partida la primera vez
# que se abre el panel en una PC (para no forzar una descarga de algo que ya está instalado).
DEFAULT_MANIFEST = {
    "programas": [
        {
            "id": "calculadora_lomo",
            "nombre": "Calculadora de Lomo",
            "icono": "📏",
            "version": "1.0.0",
            "tipo": "archivo",
            "ruta": r"calculadoraLomo\dist\Lomera.exe",
            "release": "calculadora_lomo-v1.0.0",
            "asset": "Lomera.exe",
            "pestanas": ["Editorial", "CPS"],
        },
        {
            "id": "contador_caracteres",
            "nombre": "Contador de Caracteres",
            "icono": "🔢",
            "version": "1.0.0",
            "tipo": "archivo",
            "ruta": r"cont2.0\dist\contadorCaracteres_mod.exe",
            "release": "contador_caracteres-v1.0.0",
            "asset": "contadorCaracteres_mod.exe",
            "pestanas": ["Editorial"],
        },
        {
            "id": "generador_pdf",
            "nombre": "Generador PDF Bren/Meli",
            "icono": "🧾",
            "version": "1.0.0",
            "tipo": "archivo",
            "ruta": r"generadorMeliBren (1)\GeneradorPDFBrenMeli\dist\generarPDF\generarPDF.exe",
            "release": "generador_pdf-v1.0.0",
            "asset": "generarPDF.exe",
            "pestanas": ["Editorial", "CPS"],
        },
        {
            "id": "verificador_indices",
            "nombre": "Validador Indices (OpenArena)",
            "icono": "📄",
            "version": "1.0.0",
            "tipo": "carpeta",
            "ruta": r"programaIndices\validadorIndices\dist\verificador_indices",
            "ejecutable": "verificador_indices.exe",
            "release": "verificador_indices-v1.0.0",
            "asset": "verificador_indices.zip",
            "pestanas": ["Editorial"],
        },
        {
            "id": "validador_preplanta",
            "nombre": "ValidadorPrePlanta",
            "icono": "📐",
            "version": "1.0.0",
            "tipo": "carpeta",
            "ruta": r"validadorMeli\ValidadorPrePlanta\dist\margenes_pagina",
            "ejecutable": "margenes_pagina.exe",
            "release": "validador_preplanta-v1.0.0",
            "asset": "margenes_pagina.zip",
            "pestanas": ["Editorial"],
        },
        {
            "id": "validador_indices_mejorado",
            "nombre": "Validador de Pie v2",
            "icono": "📊",
            "version": "1.0.0",
            "tipo": "carpeta",
            "ruta": r"ValidarIndicesMejorado\dist\validador_superindices_word",
            "ejecutable": "validador_superindices_word.exe",
            "release": "validador_indices_mejorado-v1.0.0",
            "asset": "validador_indices_mejorado.zip",
            "pestanas": ["Editorial"],
        },
        {
            "id": "validador_pie",
            "nombre": "Validador de Pie",
            "icono": "👣",
            "version": "1.0.0",
            "tipo": "carpeta",
            "ruta": r"validarPie\dist\validador_superindices_word",
            "ejecutable": "validador_superindices_word.exe",
            "release": "validador_pie-v1.0.0",
            "asset": "validador_pie.zip",
            "pestanas": ["Editorial"],
        },
        {
            "id": "validador_preplanta_folios",
            "nombre": "ValidadorPrePlantavFolios",
            "icono": "📑",
            "version": "1.0.0",
            "tipo": "carpeta",
            "ruta": r"validadorpreplantaVFolios\validadorMeli\ValidadorPrePlanta\dist\margenes_pagina",
            "ejecutable": "margenes_pagina.exe",
            "release": "validador_preplanta_folios-v1.0.0",
            "asset": "margenes_pagina_folios.zip",
            "pestanas": ["CPS"],
        },
    ]
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


# --- Auto-actualización del launcher (AppSanti.exe) ---------------------------------


def buscar_actualizacion():
    """Busca, entre TODOS los releases, el de mayor versión con tag "vX.Y.Z" (el del launcher).

    No se puede usar /releases/latest: ese endpoint devuelve el release publicado
    más recientemente sin importar el tag, y este repo también aloja releases con
    tags propios para cada herramienta (ej. "calculadora_lomo-v1.0.0").
    """
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
    req = urllib.request.Request(url, headers={"User-Agent": "AppSanti-Launcher"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        releases = json.loads(resp.read().decode("utf-8"))

    candidatos = [r for r in releases if re.fullmatch(r"v\d+(\.\d+)*", r.get("tag_name", ""))]
    if not candidatos:
        return None
    mejor = max(candidatos, key=lambda r: _version_tuple(r["tag_name"]))

    tag = mejor["tag_name"]
    if _version_tuple(tag) <= _version_tuple(__version__):
        return None

    for asset in mejor.get("assets", []):
        if asset.get("name") == ASSET_NAME:
            return tag, asset.get("browser_download_url")
    return None


def descargar_a_archivo(url, destino, firma=None, reintentos=3):
    """Descarga a `destino`, verificando tamaño (Content-Length) y firma de archivo.

    Si la descarga queda incompleta o corrupta (proxy corporativo, antivirus, corte de red)
    reintenta antes de dejar el archivo en su lugar. Nunca deja un archivo a medio bajar.
    """
    ultimo_error = None
    for _intento in range(1, reintentos + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AppSanti-Launcher"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                largo_esperado = resp.headers.get("Content-Length")
                largo_esperado = int(largo_esperado) if largo_esperado is not None else None
                with open(destino, "wb") as f:
                    shutil.copyfileobj(resp, f, length=1024 * 1024)

            largo_real = os.path.getsize(destino)
            if largo_esperado is not None and largo_real != largo_esperado:
                raise ValueError(
                    f"Descarga incompleta: se esperaban {largo_esperado} bytes y llegaron {largo_real}."
                )

            if firma is not None:
                with open(destino, "rb") as f:
                    inicio = f.read(len(firma))
                if inicio != firma:
                    raise ValueError(
                        "El archivo descargado no tiene el formato esperado "
                        "(¿un proxy o antivirus lo interceptó?)."
                    )

            return
        except Exception as e:
            ultimo_error = e
            if os.path.isfile(destino):
                try:
                    os.remove(destino)
                except OSError:
                    pass

    raise RuntimeError(f"No se pudo descargar {url} después de {reintentos} intento(s): {ultimo_error}")


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


# --- Manifest de programas (Editorial / CPS) -----------------------------------------


def cargar_manifest_local():
    if os.path.isfile(LOCAL_MANIFEST_PATH):
        try:
            with open(LOCAL_MANIFEST_PATH, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            pass
    guardar_manifest_local(DEFAULT_MANIFEST)
    return json.loads(json.dumps(DEFAULT_MANIFEST))


def guardar_manifest_local(manifest):
    with open(LOCAL_MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def obtener_manifest_remoto():
    req = urllib.request.Request(MANIFEST_URL, headers={"User-Agent": "AppSanti-Launcher"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read().decode("utf-8"))


def comparar_programas(local, remoto):
    """Devuelve la lista de programas del manifest remoto que son nuevos o tienen otra versión."""
    locales_por_id = {p["id"]: p for p in local.get("programas", [])}
    cambios = []
    for programa in remoto.get("programas", []):
        actual = locales_por_id.get(programa["id"])
        if actual is None or actual.get("version") != programa.get("version"):
            cambios.append((actual, programa))
    return cambios


def ruta_absoluta_programa(programa):
    return os.path.join(BASE_DIR, programa["ruta"])


def ruta_ejecutable_programa(programa):
    base = ruta_absoluta_programa(programa)
    if programa["tipo"] == "carpeta":
        return os.path.join(base, programa["ejecutable"])
    return base


def instalar_programa(programa):
    """Descarga el asset del release del programa y lo instala en su ruta local.

    Verifica que la descarga esté completa y sea válida ANTES de tocar la instalación
    existente: si algo sale mal, el programa que ya funcionaba queda intacto.
    """
    url = f"https://github.com/{GITHUB_REPO}/releases/download/{programa['release']}/{programa['asset']}"
    destino_final = ruta_absoluta_programa(programa)

    if programa["tipo"] == "archivo":
        os.makedirs(os.path.dirname(destino_final), exist_ok=True)
        temp = destino_final + ".descarga"
        try:
            descargar_a_archivo(url, temp, firma=b"MZ")
            os.replace(temp, destino_final)
        finally:
            if os.path.isfile(temp):
                os.remove(temp)
    else:
        temp_zip = destino_final + ".zip.descarga"
        os.makedirs(os.path.dirname(destino_final), exist_ok=True)
        try:
            descargar_a_archivo(url, temp_zip, firma=b"PK")
            with zipfile.ZipFile(temp_zip) as zf:
                entrada_dañada = zf.testzip()
                if entrada_dañada is not None:
                    raise RuntimeError(f"El archivo descargado está corrupto (entrada dañada: {entrada_dañada}).")
                # Recién acá, con el zip ya verificado, se reemplaza la instalación existente.
                if os.path.isdir(destino_final):
                    shutil.rmtree(destino_final)
                os.makedirs(destino_final, exist_ok=True)
                zf.extractall(destino_final)
        finally:
            if os.path.isfile(temp_zip):
                os.remove(temp_zip)


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
        self.geometry("460x640")
        self.configure(bg=PALETTE["bg"])
        self.resizable(False, False)

        self.activos = {}
        self._next_id = 0
        self.status_var = tk.StringVar(value="Listo.")
        self.manifest = cargar_manifest_local()

        self._configurar_estilos()
        self._construir_header()
        self.programas_frame = tk.Frame(self, bg=PALETTE["bg"])
        self.programas_frame.pack(fill="x")
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

    def _pestanas_ordenadas(self):
        pestanas = []
        for programa in self.manifest.get("programas", []):
            for pestana in programa.get("pestanas", []):
                if pestana not in pestanas:
                    pestanas.append(pestana)
        return pestanas

    def _construir_programas(self):
        for widget in self.programas_frame.winfo_children():
            widget.destroy()

        notebook = ttk.Notebook(self.programas_frame)
        notebook.pack(fill="x", padx=16, pady=(14, 6))

        for pestana_nombre in self._pestanas_ordenadas():
            tab = tk.Frame(notebook, bg=PALETTE["bg"], height=250)
            tab.pack_propagate(False)
            notebook.add(tab, text=pestana_nombre)

            canvas = tk.Canvas(tab, bg=PALETTE["bg"], highlightthickness=0)
            scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
            inner = tk.Frame(canvas, bg=PALETTE["bg"])

            inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")
            inner.bind("<Configure>", lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")))
            canvas.bind("<Configure>", lambda e, c=canvas, i=inner_id: c.itemconfig(i, width=e.width))
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=8)
            scrollbar.pack(side="right", fill="y")

            def on_wheel(event, c=canvas):
                c.yview_scroll(-1 if event.delta > 0 else 1, "units")

            canvas.bind("<MouseWheel>", on_wheel)
            inner.bind("<MouseWheel>", on_wheel)

            for programa in self.manifest.get("programas", []):
                if pestana_nombre in programa.get("pestanas", []):
                    self._crear_card(inner, programa, on_wheel).pack(fill="x", pady=4, padx=(0, 4))

    def _crear_card(self, parent, programa, on_wheel):
        card = tk.Frame(
            parent,
            bg=PALETTE["card"],
            highlightthickness=1,
            highlightbackground=PALETTE["border"],
            cursor="hand2",
        )
        icono_lbl = tk.Label(card, text=programa.get("icono", "🧩"), font=("Segoe UI Emoji", 16), bg=PALETTE["card"])
        icono_lbl.pack(side="left", padx=(14, 10), pady=10)
        nombre_lbl = tk.Label(
            card, text=programa["nombre"], font=("Segoe UI", 10, "bold"), bg=PALETTE["card"], fg=PALETTE["text"], anchor="w"
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
            self.abrir_programa(programa)

        for w in widgets:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)
            w.bind("<MouseWheel>", on_wheel)

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

    def abrir_programa(self, programa):
        nombre = programa["nombre"]
        ruta = ruta_ejecutable_programa(programa)
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
            "ruta": ruta,
            "proc": proc,
            "inicio": datetime.now(),
            "item": item,
        }
        self.status_var.set(f"Abriendo: {nombre}")

    def _programa_en_uso(self, programa):
        ruta = ruta_ejecutable_programa(programa)
        return any(info["ruta"] == ruta for info in self.activos.values())

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

    # --- Auto-actualización del launcher ---

    def _chequear_actualizaciones(self):
        if not getattr(sys, "frozen", False):
            return
        threading.Thread(target=self._chequear_actualizaciones_worker, daemon=True).start()

    def _chequear_actualizaciones_worker(self):
        try:
            resultado = buscar_actualizacion()
        except Exception:
            resultado = None

        if resultado:
            tag, url = resultado
            if url:
                self.after(0, lambda: self.status_var.set(f"Descargando actualización {tag}..."))
                destino = os.path.join(BASE_DIR, "AppSanti_nuevo.exe")
                try:
                    descargar_a_archivo(url, destino, firma=b"MZ")
                except Exception:
                    self.after(0, lambda: self.status_var.set("No se pudo descargar la actualización."))
                else:
                    self.after(0, lambda: self._instalar_actualizacion(destino, tag))
                    return

        # Si no hubo actualización del launcher (o falló la descarga), revisamos programas.
        self._revisar_actualizaciones_programas()

    def _instalar_actualizacion(self, destino, tag):
        self.status_var.set(f"Actualización {tag} lista. Cerrando para instalarla...")
        messagebox.showinfo(
            "Actualización disponible",
            f"Se descargó la versión {tag}.\n\n"
            "El programa se va a cerrar y reabrir solo con la nueva versión.\n"
            "Si no se reabre en unos segundos, volvé a abrirlo manualmente: ya va a tener la actualización aplicada.",
        )
        aplicar_actualizacion_y_salir(destino)

    # --- Auto-actualización de los programas (manifest) ---

    def _revisar_actualizaciones_programas(self):
        try:
            remoto = obtener_manifest_remoto()
        except Exception:
            return
        cambios = comparar_programas(self.manifest, remoto)
        if not cambios:
            return
        self.after(0, lambda: self._preguntar_actualizar_programas(cambios, remoto))

    def _preguntar_actualizar_programas(self, cambios, remoto):
        lineas = []
        for actual, programa in cambios:
            if actual is None:
                lineas.append(f"• {programa['nombre']} (nuevo)")
            else:
                lineas.append(f"• {programa['nombre']} ({actual['version']} → {programa['version']})")

        respuesta = messagebox.askyesno(
            "Actualizaciones disponibles",
            "Hay actualizaciones disponibles para:\n\n" + "\n".join(lineas) + "\n\n¿Instalarlas ahora?",
        )
        if not respuesta:
            self.status_var.set("Actualizaciones de programas rechazadas.")
            return

        self.status_var.set("Instalando actualizaciones de programas...")
        programas_a_instalar = [programa for _actual, programa in cambios]
        threading.Thread(
            target=self._aplicar_actualizaciones_programas_worker,
            args=(programas_a_instalar, remoto),
            daemon=True,
        ).start()

    def _aplicar_actualizaciones_programas_worker(self, programas, remoto):
        instalados, omitidos, fallidos = [], [], []
        for programa in programas:
            if self._programa_en_uso(programa):
                omitidos.append(programa["nombre"])
                continue
            self.after(0, lambda n=programa["nombre"]: self.status_var.set(f"Descargando {n}..."))
            try:
                instalar_programa(programa)
            except Exception:
                fallidos.append(programa["nombre"])
            else:
                instalados.append(programa)

        self.after(0, lambda: self._finalizar_actualizaciones_programas(instalados, omitidos, fallidos, remoto))

    def _finalizar_actualizaciones_programas(self, instalados, omitidos, fallidos, remoto):
        if instalados:
            locales_por_id = {p["id"]: p for p in self.manifest.get("programas", [])}
            for programa in instalados:
                locales_por_id[programa["id"]] = programa
            # Preserva el orden del manifest remoto para que la UI se vea consistente.
            self.manifest["programas"] = [
                locales_por_id[p["id"]] for p in remoto.get("programas", []) if p["id"] in locales_por_id
            ]
            guardar_manifest_local(self.manifest)
            self._construir_programas()

        partes = []
        if instalados:
            partes.append(f"{len(instalados)} actualizado(s)")
        if omitidos:
            partes.append(f"{len(omitidos)} omitido(s) (en uso)")
        if fallidos:
            partes.append(f"{len(fallidos)} con error")
        self.status_var.set("Actualización de programas: " + ", ".join(partes) if partes else "Listo.")

        if omitidos or fallidos:
            detalle = ""
            if omitidos:
                detalle += "Omitidos (cerralos y volvé a intentar):\n" + "\n".join(omitidos) + "\n\n"
            if fallidos:
                detalle += "Con error al instalar:\n" + "\n".join(fallidos)
            messagebox.showwarning("Actualización de programas incompleta", detalle.strip())

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
