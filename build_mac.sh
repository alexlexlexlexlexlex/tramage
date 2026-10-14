#!/bin/bash
# Construit dist/Tramage.app. À lancer sur un Mac : l'appli sort pour
# l'architecture de ce Mac (Apple Silicon ou Intel).
# Il faut Python 3.12 de python.org (son Tk est celui que tkinterdnd2 attend).
set -euo pipefail
cd "$(dirname "$0")"

PY=${PYTHON:-python3.12}
[ -d venv-mac ] || "$PY" -m venv venv-mac
./venv-mac/bin/python -m pip install -q --disable-pip-version-check pillow tkinterdnd2 pyinstaller

./venv-mac/bin/pyinstaller --noconfirm Tramage.spec

echo "OK : $(pwd)/dist/Tramage.app"
