# Au Micro

Les invités politiques des grandes radios françaises, jour par jour, avec les liens vers le direct et les replays.

## Organisation

- `data/radios.json` : les radios (nom, lien du direct)
- `data/emissions.json` : les émissions, rattachées à une radio
- `data/personnalites.json` : les personnalités (nom, photo, crédit photo)
- `data/passages/AAAA-MM-JJ.json` : les passages d'un jour (heure, émission, personnalité, fonction ce jour-là, replay, statut `annonce` ou `confirme`)
- `templates/` et `static/` : l'apparence du site
- `build.py` : génère le site dans `dist/` et vérifie la cohérence des données

## Aperçu local

```
pip install -r requirements.txt
BASE=/ python build.py
python -m http.server -d dist
```

Chaque modification de la branche `main` met le site à jour automatiquement (GitHub Actions → GitHub Pages).
