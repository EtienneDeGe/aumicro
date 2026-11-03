"""Télécharge des vignettes Wikimedia Commons dans outils/apercus/ pour les examiner."""
import sys, urllib.parse, urllib.request, pathlib
d = pathlib.Path("outils/apercus"); d.mkdir(parents=True, exist_ok=True)
for i, f in enumerate(sys.argv[1:]):
    u = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(f.replace(" ", "_")) + "?width=600"
    data = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "AuMicro/1.0 (https://etiennedege.github.io/aumicro/)"}), timeout=60).read()
    (d / f"apercu-{i}.jpg").write_bytes(data); print(f, len(data))
