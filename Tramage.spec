# -*- mode: python ; coding: utf-8 -*-
# Spec PyInstaller commun : dist/Tramage.exe (un seul fichier) sous Windows,
# dist/Tramage.app sous macOS. À lancer via build.ps1 ou build_mac.sh :
# PyInstaller ne compile que pour l'OS (et l'architecture) qui le fait tourner.
import glob
import os
import platform
import sys

import tkinterdnd2

# tkinterdnd2 livre la bibliothèque native tkdnd de six plateformes et n'a pas
# de hook PyInstaller. On n'embarque que celle de la machine de build, rangée
# là où TkinterDnD._require() ira la chercher.
system = platform.system()
machine = (
    os.environ.get("PROCESSOR_ARCHITECTURE", platform.machine())
    if system == "Windows"
    else platform.machine()
)
tkdnd_dir = {
    ("Darwin", "arm64"): "osx-arm64",
    ("Darwin", "x86_64"): "osx-x64",
    ("Windows", "AMD64"): "win-x64",
    ("Windows", "ARM64"): "win-arm64",
    ("Windows", "x86"): "win-x86",
}[(system, machine)]
binaries, datas = [], []
# Variante "-tcl9" en plus, si le Python de build embarque Tcl/Tk 9.
for d in (tkdnd_dir, tkdnd_dir + "-tcl9"):
    src = os.path.join(os.path.dirname(tkinterdnd2.__file__), "tkdnd", d)
    for f in glob.glob(os.path.join(src, "*")):
        kind = binaries if f.endswith((".dll", ".dylib")) else datas
        kind.append((f, f"tkinterdnd2/tkdnd/{d}"))

a = Analysis(["tramage.py"], binaries=binaries, datas=datas)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    exe = EXE(
        pyz, a.scripts, [], exclude_binaries=True, name="Tramage", console=False
    )
    coll = COLLECT(exe, a.binaries, a.datas, name="Tramage")
    app = BUNDLE(
        coll,
        name="Tramage.app",
        bundle_identifier="local.tramage",
        info_plist={
            "NSHighResolutionCapable": True,
            # Autorise le dépôt d'images et de dossiers sur l'icône du Dock.
            "CFBundleDocumentTypes": [
                {
                    "CFBundleTypeName": "Image",
                    "CFBundleTypeRole": "Viewer",
                    "LSHandlerRank": "Alternate",
                    "LSItemContentTypes": ["public.image", "public.folder"],
                }
            ],
        },
    )
else:
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [], name="Tramage", console=False
    )
