# Tramage

Allège des images à la manière du site solaire de
[Low-tech Magazine](https://solar.lowtechmagazine.com/about/the-solar-website/) :
réduction à 800 px, niveaux de gris, tramage de Bayer 8×8, PNG à palette.
Une photo de quelques centaines de Ko tombe à quelques dizaines.

Glisser des images (ou un dossier) dans la fenêtre, choisir 3, 6 ou 11 tons.
Le résultat est enregistré à côté de l'original : `photo_6tons.png`.

## Télécharger

- **Windows** : compiler avec `build.ps1` → `dist\Tramage.exe`.
- **macOS** : onglet *Actions* → dernier run « Build macOS » → *Artifacts* :
  `Tramage-mac-AppleSilicon` (M1, M2…) ou `Tramage-mac-Intel`.

L'appli n'est pas signée par Apple. Au premier lancement, macOS la bloque :
ouvrir **Réglages Système → Confidentialité et sécurité**, puis cliquer sur
**Ouvrir quand même** en bas de la page.

## Compiler

```bash
powershell -ExecutionPolicy Bypass -File build.ps1   # Windows
./build_mac.sh                                       # macOS, Python 3.12 de python.org
```

## Crédits

Réglages (palettes, seuil, taille) repris du script de tramage du site,
[lowtechmag/solar_v2](https://github.com/lowtechmag/solar_v2). Algorithme de
Bayer réécrit avec Pillow d'après [hitherdither](https://github.com/hbldh/hitherdither).
