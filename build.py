#!/usr/bin/env python3
"""Génère le site Au Micro (dossier dist/) à partir des fichiers de data/.

Usage : python build.py            # base lue dans config.json
        BASE=/ python build.py     # pour un aperçu local (python -m http.server -d dist)
"""
import json, os, shutil, sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

RACINE = Path(__file__).parent
DIST = RACINE / "dist"
JOURS_SEM = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]
PERIODES = [("Matinale", "6 h – 10 h", "00:00", "10:00"),
            ("Mi-journée", "10 h – 14 h", "10:00", "14:00"),
            ("Fin d'après-midi et soirée", "après 14 h", "14:00", "24:00")]


def lire(p):
    return json.loads((RACINE / p).read_text(encoding="utf-8"))


def date_longue(d):
    j = date.fromisoformat(d)
    num = "1er" if j.day == 1 else str(j.day)
    return f"{JOURS_SEM[j.weekday()].capitalize()} {num} {MOIS[j.month-1]} {j.year}"


def date_courte(d):
    j = date.fromisoformat(d)
    num = "1er" if j.day == 1 else str(j.day)
    return f"{num} {MOIS[j.month-1]} {j.year}"


def teinte(s):
    h = 7
    for c in s:
        h = (h * 31 + ord(c)) % 360
    return h


def initiales(nom):
    # « François-Xavier Bellamy » → FB ; « Marine Le Pen » → ML
    mots = nom.split()
    return (mots[0][0] + (mots[1][0] if len(mots) > 1 else "")).upper()


def charger():
    cfg = lire("config.json")
    radios, emissions, personnes = lire("data/radios.json"), lire("data/emissions.json"), lire("data/personnalites.json")
    erreurs, passages = [], []
    for f in sorted((RACINE / "data/passages").glob("*.json")):
        d = f.stem
        try:
            date.fromisoformat(d)
        except ValueError:
            erreurs.append(f"{f.name} : le nom du fichier doit être une date AAAA-MM-JJ")
            continue
        for i, x in enumerate(json.loads(f.read_text(encoding="utf-8"))):
            ou = f"{f.name} #{i+1}"
            if x.get("emission") not in emissions:
                erreurs.append(f"{ou} : émission inconnue « {x.get('emission')} »")
                continue
            if x.get("personne") not in personnes:
                erreurs.append(f"{ou} : personnalité inconnue « {x.get('personne')} »")
                continue
            em = emissions[x["emission"]]
            if em["radio"] not in radios:
                erreurs.append(f"{ou} : radio inconnue « {em['radio']} »")
                continue
            passages.append({**x, "date": d, "em": em, "radio": radios[em["radio"]], "radio_id": em["radio"],
                             "animateur": x.get("animateur") or em.get("animateur"),
                             "nom": personnes[x["personne"]]["nom"]})
    if erreurs:
        print("Erreurs dans les données :", *erreurs, sep="\n  ")
        sys.exit(1)
    return cfg, radios, personnes, passages


def main():
    cfg, radios, personnes, passages = charger()
    base = os.environ.get("BASE", cfg["base"])
    env = Environment(loader=FileSystemLoader(RACINE / "templates"), autoescape=select_autoescape())
    env.globals.update(base=base, site=cfg, teinte=teinte, initiales=initiales,
                       date_longue=date_longue, date_courte=date_courte)

    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(RACINE / "static", DIST / "static")

    def ecrire(chemin, gabarit, **ctx):
        cible = DIST / chemin
        cible.parent.mkdir(parents=True, exist_ok=True)
        cible.write_text(env.get_template(gabarit).render(**ctx), encoding="utf-8")

    par_jour = defaultdict(list)
    for x in passages:
        par_jour[x["date"]].append(x)
    jours = sorted(par_jour)

    # Pages des jours
    for i, d in enumerate(jours):
        liste = sorted(par_jour[d], key=lambda x: x["heure"])
        periodes = []
        for nom, plage, de, a in PERIODES:
            lp = [x for x in liste if de <= x["heure"] < a]
            if lp:
                heures = sorted({x["heure"] for x in lp})
                periodes.append({"nom": nom, "plage": plage,
                                 "creneaux": [(h, [x for x in lp if x["heure"] == h]) for h in heures]})
        ctx = dict(jour=d, passages=liste, periodes=periodes, nb_radios=len({x["radio_id"] for x in liste}),
                   prec=jours[i-1] if i > 0 else None, suiv=jours[i+1] if i < len(jours)-1 else None,
                   jours=jours, page="jour")
        ecrire(f"{d[:4]}/{d[5:7]}/{d[8:]}/index.html", "jour.html", **ctx)
        if i == len(jours) - 1:
            ecrire("index.html", "jour.html", **ctx)

    # Personnalités
    par_perso = defaultdict(list)
    for x in passages:
        par_perso[x["personne"]].append(x)
    fiches = []
    for slug, p in personnes.items():
        l = sorted(par_perso.get(slug, []), key=lambda x: (x["date"], x["heure"]), reverse=True)
        if not l:
            continue
        f = {"slug": slug, **p, "passages": l, "dernier": l[0], "premier": l[-1],
             "radios": Counter(x["radio"]["nom"] for x in l).most_common()}
        fiches.append(f)
        ecrire(f"personnalites/{slug}/index.html", "personnalite.html", p=f, page="pers")
    fiches.sort(key=lambda f: (-len(f["passages"]), f["nom"].split()[-1]))
    ecrire("personnalites/index.html", "personnalites.html", fiches=fiches, page="pers")
    ecrire("404.html", "404.html", page="")
    print(f"Site généré : {len(jours)} jours, {len(fiches)} personnalités, {len(passages)} passages → {DIST}")


if __name__ == "__main__":
    main()
