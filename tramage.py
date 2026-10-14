"""Tramage : allège une image à la manière de solar.lowtechmagazine.com.

Glisser des images (ou un dossier) dans la fenêtre, ou sur l'icône de l'appli
(l'exe sous Windows, le Dock sous macOS).
Chaque image est réduite à 800 px maximum, passée en niveaux de gris, tramée
avec une matrice de Bayer 8x8, puis enregistrée en PNG à palette, à côté de
l'original, sous le nom <nom>_<N>tons.png.

Mêmes réglages que le script du site (lowtechmag/solar_v2,
utils/dither_images.py, qui s'appuie sur hitherdither). L'algorithme est
réécrit ici avec Pillow seul pour garder l'exe léger.
"""

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, font, ttk

from PIL import Image, ImageChops, ImageOps
from tkinterdnd2 import DND_FILES, TkinterDnD

MAX_SIZE = (800, 800)
THRESHOLD = 96  # amplitude du motif de Bayer, règle aussi le contraste
BAYER_ORDER = 8

PALETTES = {
    3: (0, 125, 250),
    6: (25, 75, 125, 175, 225, 250),
    11: tuple(range(0, 251, 25)),
}

TONE_LABELS = {
    3: "3 tons : le plus léger, motif très visible",
    6: "6 tons : le réglage du site",
    11: "11 tons : plus fin, plus lourd",
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tif", ".tiff", ".bmp"}
OUTPUT_SUFFIXES = tuple(f"_{n}tons.png" for n in PALETTES)


def bayer_index(n):
    """Matrice d'indices de Bayer n x n (n puissance de 2)."""
    if n == 2:
        return [[0, 2], [3, 1]]
    s = bayer_index(n // 2)
    top = [[4 * v for v in row] + [4 * v + 2 for v in row] for row in s]
    bottom = [[4 * v + 3 for v in row] + [4 * v + 1 for v in row] for row in s]
    return top + bottom


# Décalage ajouté à chaque pixel selon sa position, comme hitherdither :
# (1 + I) / (1 + n²) * seuil.
BAYER_ROWS = [
    bytes(round((1 + v) / (1 + BAYER_ORDER**2) * THRESHOLD) for v in row)
    for row in bayer_index(BAYER_ORDER)
]


def output_path(src, tones):
    stem, _ = os.path.splitext(src)
    return f"{stem}_{tones}tons.png"


def load_rgb(src):
    """Ouvre l'image redressée (EXIF), réduite, transparence aplatie sur blanc."""
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        has_alpha = im.mode in ("RGBA", "LA") or "transparency" in im.info
        im = im.convert("RGBA" if has_alpha else "RGB")
    im.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
    if has_alpha:
        bg = Image.new("RGBA", im.size, "white")
        bg.alpha_composite(im)
        im = bg
    return im.convert("RGB")


def dither(rgb, tones):
    palette = PALETTES[tones]
    # Moyenne des trois canaux : c'est le gris le plus proche au sens de la
    # distance RGB qu'utilise hitherdither.
    gray = rgb.convert("L", matrix=(1 / 3, 1 / 3, 1 / 3, 0))

    w, h = gray.size
    reps = w // BAYER_ORDER + 1
    pattern = b"".join(
        (BAYER_ROWS[y % BAYER_ORDER] * reps)[:w] for y in range(h)
    )
    shifted = ImageChops.add(gray, Image.frombytes("L", (w, h), pattern))

    nearest = [
        min(range(len(palette)), key=lambda i: abs(palette[i] - v))
        for v in range(256)
    ]
    out = Image.frombytes("P", (w, h), shifted.point(nearest).tobytes())
    # Palette de N entrées exactement : Pillow écrit alors un PNG 2 ou 4 bits.
    out.putpalette([c for v in palette for c in (v, v, v)])
    return out


def process_file(src, tones):
    """Trame une image. Renvoie (chemin de sortie, poids avant, poids après)."""
    dst = output_path(src, tones)
    dither(load_rgb(src), tones).save(dst, optimize=True)
    return dst, os.path.getsize(src), os.path.getsize(dst)


def human_size(n):
    if n < 1024:
        return f"{n} o"
    if n < 1024**2:
        return f"{n / 1024:.0f} Ko"
    return f"{n / 1024**2:.1f} Mo".replace(".", ",")


def open_file(path):
    if sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.run(["open", path])


def expand_paths(paths):
    """Remplace les dossiers par les images qu'ils contiennent (sans les sous-dossiers)."""
    files = []
    for p in paths:
        if os.path.isdir(p):
            files += sorted(
                os.path.join(p, f)
                for f in os.listdir(p)
                if os.path.splitext(f)[1].lower() in IMAGE_EXTS
                and not f.endswith(OUTPUT_SUFFIXES)
            )
        else:
            files.append(p)
    return files


class App:
    def __init__(self, root):
        self.root = root
        self.jobs = queue.Queue()
        self.results = queue.Queue()
        self.outputs = []  # chemin de sortie de chaque ligne du journal

        root.title("Tramage")
        root.geometry("520x460")
        root.minsize(420, 380)

        # Police et taille système de chaque OS (Segoe UI 9 sous Windows,
        # SF 13 sous macOS) : les tailles ci-dessous sont relatives.
        default = font.nametofont("TkDefaultFont").actual()
        family, size = default["family"], abs(default["size"])

        frame = ttk.Frame(root, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Nombre de tons", font=(family, size + 1, "bold")).pack(
            anchor="w"
        )
        self.tones = tk.IntVar(value=6)
        for n in PALETTES:
            ttk.Radiobutton(
                frame, text=TONE_LABELS[n], variable=self.tones, value=n
            ).pack(anchor="w", pady=1)

        self.zone = tk.Label(
            frame,
            text="Glissez vos images ici\n(ou cliquez pour les choisir)",
            font=(family, size + 3),
            bg="#f1f1ee",
            fg="#444",
            relief="groove",
            bd=2,
            height=5,
            cursor="hand2",
        )
        self.zone.pack(fill="x", pady=(14, 10))
        self.zone.drop_target_register(DND_FILES)
        self.zone.dnd_bind("<<Drop>>", self.on_drop)
        self.zone.dnd_bind("<<DropEnter>>", lambda e: self.highlight(True))
        self.zone.dnd_bind("<<DropLeave>>", lambda e: self.highlight(False))
        self.zone.bind("<Button-1>", self.on_click)

        self.log = tk.Listbox(frame, font=(family, size), activestyle="none")
        self.log.pack(fill="both", expand=True)
        self.log.bind("<Double-Button-1>", self.open_selected)

        ttk.Label(
            frame,
            text="Le PNG est enregistré à côté de l'original. "
            "Double-clic sur une ligne pour l'ouvrir.",
            foreground="#666",
        ).pack(anchor="w", pady=(6, 0))

        threading.Thread(target=self.worker, daemon=True).start()
        root.after(100, self.poll_results)

    def highlight(self, on):
        self.zone.configure(bg="#dde8f5" if on else "#f1f1ee")
        return "copy"

    def on_drop(self, event):
        self.highlight(False)
        self.enqueue(self.root.tk.splitlist(event.data))
        return "copy"

    def on_click(self, _event):
        paths = filedialog.askopenfilenames(
            title="Choisir des images",
            filetypes=[("Images", " ".join(f"*{e}" for e in sorted(IMAGE_EXTS)))],
        )
        self.enqueue(paths)

    def enqueue(self, paths):
        tones = self.tones.get()
        for p in expand_paths(paths):
            self.jobs.put((p, tones))

    def worker(self):
        while True:
            src, tones = self.jobs.get()
            try:
                self.results.put((src, process_file(src, tones), None))
            except Exception as e:
                self.results.put((src, None, e))

    def poll_results(self):
        while not self.results.empty():
            src, result, error = self.results.get()
            name = os.path.basename(src)
            if error is None:
                dst, before, after = result
                ratio = before / after if after else 0
                line = (
                    f"✓ {name} → {os.path.basename(dst)} : "
                    f"{human_size(before)} → {human_size(after)} (÷{ratio:.0f})"
                )
                self.outputs.append(dst)
            else:
                line = f"✗ {name} : {error}"
                self.outputs.append(None)
            self.log.insert("end", line)
            self.log.see("end")
        self.root.after(100, self.poll_results)

    def open_selected(self, _event):
        sel = self.log.curselection()
        if sel and self.outputs[sel[0]]:
            open_file(self.outputs[sel[0]])


def main():
    try:
        # Texte net sur les écrans à mise à l'échelle (125 %, 150 %…).
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    root = TkinterDnD.Tk()
    app = App(root)
    # Fichiers glissés sur l'icône de l'exe : traités avec le réglage choisi
    # dans la fenêtre (6 tons au lancement).
    if len(sys.argv) > 1:
        app.enqueue(sys.argv[1:])
    if sys.platform == "darwin":
        # macOS ne passe pas par sys.argv : les fichiers déposés sur l'icône
        # du Dock arrivent par cet événement, au lancement comme ensuite.
        root.createcommand("::tk::mac::OpenDocument", lambda *p: app.enqueue(p))
    root.mainloop()


if __name__ == "__main__":
    main()
