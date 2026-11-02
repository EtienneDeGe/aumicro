#!/usr/bin/env python3
"""Collecte quotidienne des invités politiques.

1. Lit les flux podcast des émissions (data/sources.json) : chaque épisode donne l'invité et le lien d'écoute.
2. Garde uniquement les personnalités politiques françaises (vérification sur Wikidata), avec photo libre.
3. Cherche la vidéo de l'interview sur les chaînes YouTube des radios.
4. Écrit les passages dans data/passages/AAAA-MM-JJ.json et un résumé dans resume.md (corps de la proposition à valider).

Usage : python collecte.py [--jours 3] [--depuis AAAA-MM-JJ] [--essai]
Seule la bibliothèque standard de Python est utilisée.
"""
import argparse, difflib, html, json, re, sys, time, unicodedata, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RACINE = Path(__file__).parent
PARIS = ZoneInfo("Europe/Paris")
UA = {"User-Agent": "AuMicro/1.0 (https://etiennedege.github.io/aumicro/; recensement des invites politiques)",
      "Accept-Language": "fr-FR,fr"}
CACHE_F = RACINE / "data/cache_wikidata.json"


# ---------- utilitaires ----------
def lire(p):
    return json.loads((RACINE / p).read_text(encoding="utf-8"))


def ecrire(p, o):
    (RACINE / p).write_text(json.dumps(o, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get(url, essais=3):
    for i in range(essais):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read()
        except Exception as e:
            if i == essais - 1:
                raise
            time.sleep(2 * (i + 1))


def sans_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", sans_accents(s).lower()).strip()


def slugifier(s):
    return re.sub(r"[^a-z0-9]+", "-", sans_accents(s).lower()).strip("-")


def texte(h):
    h = re.sub(r"<[^>]+>", " ", h or "")
    return " ".join(html.unescape(h).split())


# ---------- extraction des noms ----------
MAJ = r"A-ZÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸ"
MOT = rf"[{MAJ}][a-zà-ÿ'’]+(?:-[{MAJ}]?[a-zà-ÿ'’]+)*"
PARTICULE = r"(?:de |du |des |d'|d’|de la |Le |La |Mc|Mac|Ben |Ould |Van |von |El |Al-)"
NOM_RE = re.compile(rf"\b({MOT}(?:\s+{PARTICULE}?{MOT}){{1,3}})")
PROFESSIONS = {"Journaliste", "Magistrat", "Magistrate", "Historien", "Historienne", "Écrivain", "Ecrivain", "Écrivaine", "Acteur",
               "Actrice", "Philosophe", "Essayiste", "Économiste", "Sociologue", "Politologue", "Avocat", "Avocate", "Professeur",
               "Professeure", "Réalisateur", "Réalisatrice", "Chanteur", "Chanteuse", "Comédien", "Comédienne", "Romancier", "Romancière"}
MOTS_VIDES = {"Invité", "Invitée", "Invités", "Grand", "Grande", "Entretien", "Interview", "Podcast", "Replay",
              "Le", "La", "Les", "Un", "Une", "Avec", "Chaque", "Ecoutez", "Écoutez", "Retrouvez", "Sur", "Pour",
              "Face", "France", "Inter", "Sud", "Radio", "Europe", "Assemblée", "Sénat", "Parti", "République", "Matin"}


AVANT_ANIMATEUR = re.compile(r"(?:questions d[e'’]|au micro d[e'’]|présentée? par|animée? par|avec|interrogée? par|face à)\s*$", re.I)


def candidats(t):
    """Noms propres trouvés dans le texte, ceux de la forme « Nom, fonction » en premier."""
    vus, prioritaires, autres = set(), [], []
    for m in NOM_RE.finditer(t):
        mots = m.group(1).strip().split()
        while mots and (mots[0] in MOTS_VIDES or mots[0][0].islower()):
            mots = mots[1:]
        while mots and mots[-1] in PROFESSIONS:
            mots = mots[:-1]
        if len(mots) < 2:
            continue
        nom = " ".join(mots)
        debut = t.find(nom, m.start())
        avant = t[max(0, debut - 30):debut]
        if nom in vus or (AVANT_ANIMATEUR.search(avant) and not avant.rstrip().endswith(":")):
            continue
        vus.add(nom)
        (prioritaires if t[debut + len(nom):debut + len(nom) + 1] == "," else autres).append((nom, debut))
    return prioritaires + autres


FIN_FONCTION = re.compile(r"(?:^|,? )(?:rapporte|pointe|nie|débattent|appelle|alerte|estime|assure|regrette|confie|annonce|déclare|"
                          r"explique|dénonce|juge|affirme|plaide|souligne|considère|publie|défend|met en garde|s['’]inquiète|"
                          r"répond|est l['’]invit|est l|était|a salué|a |revient|réagit|invitée? |au micro|sur RTL|sur RMC|sur Europe|"
                          r"était|s['’]exprime|pour |qui |dans |face à|ce (?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)|"
                          r"était|et auteur|auteur d)|[.;:!?]")


FONCTION_POLITIQUE = re.compile(
    r"d[ée]put[ée]|eurodéput|ministre|s[ée]nat(?:eur|rice)|président(?:e)? du sénat|\bmaire\b|adjointe? au maire|\bpartis?\b|porte-parole|"
    r"candidat|conseill(?:er|ère) (?:régional|départemental|municipal|de paris|d['’]arrondissement)|\bélue?s?\b|"
    r"secrétaire (?:national|général|d['’]état)|premier secrétaire|coordinat(?:eur|rice) national|haute?-commissaire|"
    r"président(?:e)? (?:délégué(?:e)? )?du groupe (?!ment)(?!(?:e\b|carrefour|renault|lvmh|bpce|la poste|sncf|total))|"
    r"président(?:e)? (?:des (?:républicains|députés|sénateurs)|de la région|du conseil (?:régional|départemental|de paris|général)|"
    r"de région|du parti|du rassemblement|de l['’]assemblée|de l['’]union des droites)|"
    r"homme politique|femme politique|personnalité politique|responsable politique|homme d['’]état|femme d['’]état|"
    r"\bLFI\b|\bRN\b|\bPS\b|\bLR\b|\bPCF\b|EELV|écologistes?\b|insoumis|communiste|socialiste|républicains|reconquête|"
    r"renaissance|modem|horizons|place publique|debout la france|nouvelle énergie|gouvernement|chef de file|co-président|"
    r"vice-président(?:e)? (?:du|de la|de l['’]|des) ?(?:rn|rassemblement|républicains|parti|région|conseil|assemblée|sénat|groupe|lfi)|"
    r"(?<!ancien )président(?:e)? de la république|président(?:e)? du conseil constitutionnel|militant", re.I)


PERIMETRE_ELARGI = (
    # institutions publiques
    r"gouverneur|banque de france|banque centrale|cour des comptes|préfet|préfète|défenseure? des droits|conseil constitutionnel|"
    r"conseil d['’]état|conseil économique|haute autorité|autorité de|arcom|cnil|ambassadeur|ambassadrice|procureur|procureure|"
    r"chef d['’]état-major|commissaire européen|commission européenne|médiateur|inspecteur général|directeur général de la|directrice générale de la|"
    r"président(?:e)? de (?:la |l['’])?(?:cour|commission|agence|caisse|assemblée|haute|autorité|cnil|insee|ofce|sncf|ratp|france travail|"
    r"france universités|conférence|association des maires|régions de france|départements de france)|"
    # syndicats et patronat
    r"syndica|\bcgt\b|cfdt|force ouvrière|\bfo\b|unsa|cfe-cgc|cftc|solidaires|\bfsu\b|snes|medef|cpme|u2p|fnsea|"
    r"confédération|confédéral|union étudiante|\bunef\b|\bfage\b|voix lycéenne|\bfidl\b|patronat|patronale|"
    # think tanks et associations
    r"fondation (?:jean[- ]jaurès|jaurès|robert schuman|res publica|ifrap|pour l['’]innovation politique|gabriel péri|copernic|abbé pierre)|"
    r"fondapol|institut montaigne|terra nova|think tank|association|\bong\b|collectif|fédération|amnesty|secours populaire|"
    r"secours catholique|emmaüs|ligue des droits|\bldh\b|licra|sos racisme|\bcrif\b|unicef|croix-rouge|restos du cœur|"
    r"médecins sans frontières|président(?:e)? de l['’]université|france universités|les lycéens|voix lycéenne|"
    r"organisation (?:syndicale|lycéenne|étudiante)|syndicat lycéen|union syndicale lycéenne")
DANS_PERIMETRE = re.compile(FONCTION_POLITIQUE.pattern + "|" + PERIMETRE_ELARGI, re.I)


def fonction_apres(t, nom):
    i = t.find(nom)
    if i < 0:
        return None
    reste = t[i + len(nom):]
    if not reste.startswith(","):
        return None
    reste = reste[1:].strip()
    m = FIN_FONCTION.search(reste)
    f = (reste[:m.start()] if m else reste[:140]).strip(" ,").replace("«", "").replace("»", "").replace('"', "")
    f = " ".join(f.split())
    if f.count("(") > f.count(")"):
        f = f[:f.rfind("(")].strip(" ,")
    if 4 <= len(f) <= 160:
        return f[0].upper() + f[1:]
    return None


def animateur(t):
    m = re.search(r"(?:répond(?:ent)? aux questions d[e'’] ?|au micro d[e'’] ?)" + rf"({MOT}(?:\s+{PARTICULE}?{MOT}){{1,2}})", t)
    if m:
        return m.group(1)
    m = re.search(rf"^({MOT}(?:\s+{PARTICULE}?{MOT}){{1,2}}) reçoit", t)
    return m.group(1) if m else None


# ---------- Wikidata ----------
class Wikidata:
    API = "https://www.wikidata.org/w/api.php"

    def __init__(self):
        self.cache = json.loads(CACHE_F.read_text(encoding="utf-8")) if CACHE_F.exists() else {}
        self.modifie = False

    def api(self, **p):
        p.update(format="json")
        for essai in range(5):
            time.sleep(0.4)
            r = json.loads(get(self.API + "?" + urllib.parse.urlencode(p)))
            if "error" not in r:
                return r
            print("  ! Wikidata :", r["error"].get("info", "")[:120])
            time.sleep(3 * (essai + 1))
        raise RuntimeError(r["error"].get("info", "erreur Wikidata"))

    MANDATS = re.compile(r"ministre|député|sénat|maire|président de la république|secrétaire d['’]état|porte-parole du gouvernement|"
                         r"conseill(?:er|ère) (?:régional|départemental|municipal|de paris)|président du conseil|parlement européen|"
                         r"président de région|chef du gouvernement|haut-commissaire", re.I)

    def mandat_politique(self, positions):
        """Vrai si l'une des fonctions occupées (P39) est un mandat ou une fonction gouvernementale."""
        positions = [p for p in positions if p]
        if not positions:
            return False
        inconnues = [p for p in positions if ("pos:" + p) not in self.cache]
        for i in range(0, len(inconnues), 40):
            lot = inconnues[i:i + 40]
            ents = self.api(action="wbgetentities", ids="|".join(lot), props="labels", languages="fr|en")["entities"]
            for p in lot:
                lab = ents.get(p, {}).get("labels", {})
                self.cache["pos:" + p] = (lab.get("fr") or lab.get("en") or {}).get("value", "")
                self.modifie = True
        return any(self.MANDATS.search(self.cache["pos:" + p]) for p in positions)

    def personne(self, nom):
        """Fiche Wikidata d'une personne française vivante portant ce nom, ou None.

        Renvoie {qid, nom, description, photo_fichier, politique, fonction_publique}."""
        cle = "v2:" + norm(nom)
        if cle in self.cache:
            return self.cache[cle]
        res = None
        try:
            hits = self.api(action="wbsearchentities", search=nom, language="fr", uselang="fr", type="item", limit=5)["search"]
            ids = [h["id"] for h in hits if norm(h.get("label", "")) == norm(nom) or norm(h.get("match", {}).get("text", "")) == norm(nom)]
            if ids:
                ents = self.api(action="wbgetentities", ids="|".join(ids), props="claims|labels|descriptions", languages="fr")["entities"]
                candidats_wd = []
                for qid in ids:
                    e = ents[qid]
                    c = e.get("claims", {})
                    val = lambda p: [x["mainsnak"].get("datavalue", {}).get("value") for x in c.get(p, [])]
                    ids_de = lambda p: {v.get("id") for v in val(p) if isinstance(v, dict)}
                    if "Q5" not in ids_de("P31") or "Q142" not in ids_de("P27") or c.get("P570"):
                        continue
                    politique = "Q82955" in ids_de("P106") or bool(c.get("P102")) or self.mandat_politique(ids_de("P39"))
                    candidats_wd.append({"qid": qid, "nom": e.get("labels", {}).get("fr", {}).get("value", nom),
                                         "description": e.get("descriptions", {}).get("fr", {}).get("value"),
                                         "photo_fichier": (val("P18") or [None])[0],
                                         "politique": politique, "fonction_publique": bool(c.get("P39"))})
                # en cas d'homonymes, la personnalité politique d'abord
                candidats_wd.sort(key=lambda x: (not x["politique"], not x["fonction_publique"]))
                res = candidats_wd[0] if candidats_wd else None
        except Exception as ex:
            print(f"  ! Wikidata indisponible pour {nom} : {ex}")
            return None  # pas de mise en cache en cas d'erreur
        self.cache[cle] = res
        self.modifie = True
        return res

    def photo(self, fichier):
        """URL d'une vignette Wikimedia Commons et crédit (auteur, licence)."""
        if not fichier:
            return None, None
        url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(fichier.replace(" ", "_")) + "?width=240"
        credit = None
        try:
            r = json.loads(get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
                {"action": "query", "titles": "File:" + fichier, "prop": "imageinfo", "iiprop": "extmetadata", "format": "json"})))
            meta = next(iter(r["query"]["pages"].values()))["imageinfo"][0]["extmetadata"]
            auteur = texte(meta.get("Artist", {}).get("value", ""))[:80]
            licence = meta.get("LicenseShortName", {}).get("value", "")
            credit = ", ".join(x for x in (auteur, licence, "Wikimedia Commons") if x)
        except Exception:
            credit = "Wikimedia Commons"
        return url, credit

    def sauver(self):
        if self.modifie:
            CACHE_F.write_text(json.dumps(self.cache, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


# ---------- choix de l'invité ----------
def decider(noms, ep, lien_slug, anims, exclus, inclus, wd):
    """Choisit l'invité d'un épisode parmi les noms cités.

    1. Le premier nom présenté sous la forme « Nom, fonction » (ou présent dans l'adresse de l'épisode) est l'invité :
       on le retient si sa fonction entre dans le périmètre (politique, institutions, syndicats et patronat,
       think tanks et associations), sinon il est « hors périmètre » (expert, chef d'entreprise, artiste…).
    2. Sans fonction écrite, on s'appuie sur Wikidata : personnalité politique ou titulaire d'une fonction publique,
       à condition que son nom figure dans le titre ou l'adresse de l'épisode (sinon elle n'est peut-être que citée).
    """
    titre = norm(ep["titre"])
    sans_fonction = []
    for nom, _ in noms:
        if norm(nom) in exclus or norm(nom) in anims:
            continue
        f = fonction_apres(ep["desc"], nom) or fonction_apres(ep["titre"], nom)
        dans_lien = slugifier(nom) in lien_slug
        if f or dans_lien:
            w = wd.personne(nom)
            if norm(nom) in inclus or (f and DANS_PERIMETRE.search(f)) or (not f and w and w["politique"]):
                return {"verdict": "retenu", "nom": nom, "fonction": f, "wd": w}
            if f and w and w["politique"]:
                # fonction écrite non politique mais homonyme politique sur Wikidata : à vérifier
                return {"verdict": "prudence", "nom": w["nom"], "fonction": f}
            return {"verdict": "hors-champ", "nom": w["nom"] if w else nom, "fonction": f or (w or {}).get("description")}
        sans_fonction.append(nom)
    # sans fonction écrite : d'abord une personnalité politique nommée dans le titre, sinon mise en attente
    attente = None
    for nom in sorted(sans_fonction, key=lambda n: norm(n) not in titre):
        w = wd.personne(nom)
        if not w:
            continue
        if norm(nom) in inclus or (w["politique"] and norm(nom) in titre):
            return {"verdict": "retenu", "nom": nom, "fonction": None, "wd": w}
        if w["politique"] and not attente:
            attente = {"verdict": "prudence", "nom": w["nom"], "fonction": None}
    return attente or {"verdict": "aucun"}


# ---------- flux podcast ----------
def url_flux(src):
    if src.get("flux"):
        return src["flux"]
    page = get(src["page"]).decode("utf-8", "replace")
    m = re.search(r'https://radiofrance-podcast\.net/podcast09/[\w-]+\.xml', page)
    if not m:
        raise RuntimeError("flux introuvable sur " + src["page"])
    return m.group(0)


def episodes(src):
    racine = ET.fromstring(get(url_flux(src)))
    lien_chaine = (racine.findtext("channel/link") or "").strip()
    for it in racine.iter("item"):
        try:
            quand = parsedate_to_datetime(it.findtext("pubDate")).astimezone(PARIS)
        except Exception:
            continue
        enc = it.find("enclosure")
        audio = enc.get("url") if enc is not None else None
        lien = (it.findtext("link") or "").strip()
        if src.get("replay") == "lien" and lien and lien.rstrip("/") != lien_chaine.rstrip("/"):
            ecouter = lien
        else:
            ecouter = audio or lien or None
        yield {"date": quand.date(), "titre": texte(it.findtext("title")), "desc": texte(it.findtext("description")),
               "ecouter": ecouter, "lien": lien}


# ---------- YouTube ----------
YT_NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


def videos(chaine):
    r = ET.fromstring(get("https://www.youtube.com/feeds/videos.xml?channel_id=" + chaine))
    for e in r.findall("a:entry", YT_NS):
        yield {"titre": e.findtext("a:title", namespaces=YT_NS) or "",
               "date": datetime.fromisoformat(e.findtext("a:published", namespaces=YT_NS)).astimezone(PARIS).date(),
               "url": "https://www.youtube.com/watch?v=" + e.findtext("yt:videoId", namespaces=YT_NS)}


# ---------- programme principal ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jours", type=int, default=3, help="nombre de jours à remonter (défaut 3)")
    ap.add_argument("--depuis", help="date de début AAAA-MM-JJ (prioritaire sur --jours)")
    ap.add_argument("--essai", action="store_true", help="affiche le résultat sans rien écrire")
    a = ap.parse_args()
    aujourdhui = datetime.now(PARIS).date()
    debut = date.fromisoformat(a.depuis) if a.depuis else aujourdhui - timedelta(days=a.jours - 1)

    sources, emissions = lire("data/sources.json"), lire("data/emissions.json")
    personnes = lire("data/personnalites.json")
    exclus = {norm(n) for n in lire("data/exclus.json")["noms"]} if (RACINE / "data/exclus.json").exists() else set()
    forcer = {(p["date"], p["emission"]): p for p in lire("data/forcer.json")["passages"]} if (RACINE / "data/forcer.json").exists() else {}
    alias = {norm(k): v for k, v in lire("data/alias.json")["noms"].items()} if (RACINE / "data/alias.json").exists() else {}
    inclus = {norm(n) for n in lire("data/inclus.json")["noms"]} if (RACINE / "data/inclus.json").exists() else set()
    par_qid = {p.get("wikidata"): s for s, p in personnes.items() if p.get("wikidata")}
    wd = Wikidata()
    nouveaux, completes, ecartes, prudence, hors_champ, erreurs = [], [], [], [], [], []
    jours_modifies = {}

    def jour(d):
        k = d.isoformat()
        if k not in jours_modifies:
            f = RACINE / f"data/passages/{k}.json"
            jours_modifies[k] = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
        return jours_modifies[k]

    # 1. Podcasts
    for src in sources["podcasts"]:
        em_id = src["emission"]
        em = emissions[em_id]
        print(f"\n== {em['nom']} ({em['radio']})")
        try:
            eps = [e for e in episodes(src) if debut <= e["date"] <= aujourdhui]
        except Exception as ex:
            erreurs.append(f"{em['nom']} : flux illisible ({ex})")
            print("  ! flux illisible :", ex)
            continue
        for ep in eps:
            # émissions dont le flux mélange semaine et week-end
            em_id = src.get("week-end", src["emission"]) if ep["date"].weekday() >= 5 else src["emission"]
            em = emissions[em_id]
            trouve = None
            anims = {norm(a) for a in re.split(r" et |, ", em.get("animateur") or "") if a}
            anim_ep = animateur(ep["desc"])
            if anim_ep:
                anims.add(norm(anim_ep))
            noms = [(alias.get(norm(n), n), p) for n, p in candidats(ep["desc"]) + candidats(ep["titre"])]
            lien_slug = slugifier(ep.get("lien") or "")
            # nom de l'invité écrit dans l'adresse (ex. « …le-8h30-franceinfo-de-prisca-thevenot_8241112.html »)
            m = re.search(r"-de-([a-z]+(?:-[a-z]+){1,3})(?:_\d+|\.html|/?$)", (ep.get("lien") or "").lower())
            if m and not any(slugifier(n) == m.group(1) for n, _ in noms):
                noms.insert(0, (" ".join(w.capitalize() for w in m.group(1).split("-")), -1))
            # l'invité dont le nom figure dans l'adresse de l'épisode passe en premier
            noms.sort(key=lambda n: slugifier(n[0]) not in lien_slug)
            impose = forcer.get((ep["date"].isoformat(), em_id))
            if impose:
                choix = {"verdict": "retenu", "nom": impose["nom"],
                         "fonction": impose.get("fonction") or fonction_apres(ep["desc"], impose["nom"]),
                         "wd": None if impose.get("sans_wikidata") else wd.personne(impose["nom"])}
            else:
                choix = decider(noms, ep, lien_slug, anims, exclus, inclus, wd)
            if choix["verdict"] == "aucun":
                ecartes.append(f"{ep['date']} · {em['nom']} : « {ep['titre'][:90]} »")
                print(f"  - {ep['date']} aucun invité retenu : {ep['titre'][:80]}")
                continue
            if choix["verdict"] == "hors-champ":
                hors_champ.append(f"{ep['date']} · {em['nom']} : {choix['nom']} — {choix['fonction'] or 'fonction non précisée'}")
                print(f"  - {ep['date']} hors périmètre : {choix['nom']} — {choix['fonction']}")
                continue
            if choix["verdict"] == "prudence":
                prudence.append(f"{ep['date']} · {em['nom']} : {choix['nom']} ({choix['fonction'] or 'fonction non précisée'}) — « {ep['titre'][:80]} »")
                print(f"  ? {ep['date']} prudence : {choix['nom']}")
                continue
            trouve, fonction_ep = choix["wd"], choix["fonction"]
            # personnalité : existante ou nouvelle
            if trouve:
                slug = par_qid.get(trouve["qid"])
                if not slug:
                    slug = slugifier(trouve["nom"])
                    if slug in personnes and personnes[slug].get("wikidata") not in (None, trouve["qid"]):
                        slug = f"{slug}-{trouve['qid'].lower()}"
                    p = personnes.setdefault(slug, {"nom": trouve["nom"], "photo": None, "credit_photo": None})
                    p["wikidata"] = trouve["qid"]
                    if not p.get("photo") and trouve.get("photo_fichier"):
                        p["photo"], p["credit_photo"] = wd.photo(trouve["photo_fichier"])
                    par_qid[trouve["qid"]] = slug
                nom_affiche = trouve["nom"]
            else:  # personnalité absente de Wikidata (responsable syndical, associatif…)
                nom_affiche = choix["nom"]
                slug = slugifier(nom_affiche)
                # coquille dans le résumé (« Fickenstein » pour « Finchelstein ») : rattacher à la fiche existante
                proches = difflib.get_close_matches(norm(nom_affiche), [norm(p["nom"]) for p in personnes.values()], n=1, cutoff=0.82)
                if slug not in personnes and proches:
                    slug = next(k for k, p in personnes.items() if norm(p["nom"]) == proches[0])
                    nom_affiche = personnes[slug]["nom"]
                personnes.setdefault(slug, {"nom": nom_affiche, "photo": None, "credit_photo": None, "wikidata": None})
                trouve = {"nom": nom_affiche, "description": None}
            fonction = fonction_ep or (trouve.get("description") or "").capitalize() or None
            liste = jour(ep["date"])
            existant = next((x for x in liste if x["emission"] == em_id and x["personne"] == slug), None)
            if existant:
                if not existant.get("ecouter") and ep["ecouter"]:
                    existant["ecouter"] = ep["ecouter"]
                    existant["statut"] = "confirme"
                    completes.append(f"{ep['date']} · {em['nom']} · {trouve['nom']} : lien d'écoute ajouté")
                continue
            x = {"heure": em.get("heure", "00:00"), "emission": em_id, "personne": slug, "fonction": fonction,
                 "ecouter": ep["ecouter"], "voir": None, "statut": "confirme"}
            anim = animateur(ep["desc"])
            if anim and anim != em.get("animateur") and norm(anim) != norm(trouve["nom"]):
                x["animateur"] = anim
            liste.append(x)
            nouveaux.append((ep["date"], em, trouve["nom"], fonction, ep["ecouter"]))
            print(f"  + {ep['date']} {trouve['nom']} — {fonction}")

    # 2. Vidéos YouTube pour les passages récents sans vidéo
    cache_videos = {}
    for d in [debut + timedelta(days=i) for i in range((aujourdhui - debut).days + 1)]:
        for x in jour(d):
            if x.get("voir"):
                continue
            radio = emissions[x["emission"]]["radio"]
            nom = personnes[x["personne"]]["nom"]
            nom_famille = norm(nom.split(" ", 1)[-1])
            for ch in sources["youtube"].get(radio, []):
                if ch not in cache_videos:
                    try:
                        cache_videos[ch] = list(videos(ch))
                    except Exception as ex:
                        erreurs.append(f"YouTube {ch} : {ex}")
                        cache_videos[ch] = []
                v = next((v for v in cache_videos[ch] if d <= v["date"] <= d + timedelta(days=1)
                          and f" {nom_famille} " in f" {norm(v['titre'])} "), None)
                if v:
                    x["voir"] = v["url"]
                    completes.append(f"{d} · {nom} : vidéo « {v['titre'][:80]} »")
                    break

    # 3. Écriture
    for k in list(jours_modifies):
        if not jours_modifies[k]:
            del jours_modifies[k]
    if a.essai:
        print("\n(essai : rien n'est écrit)")
    else:
        for k, liste in jours_modifies.items():
            liste.sort(key=lambda x: (x["heure"], x["emission"]))
            ecrire(f"data/passages/{k}.json", liste)
        ecrire("data/personnalites.json", dict(sorted(personnes.items())))
        wd.sauver()

    r = [f"## Collecte du {aujourdhui.strftime('%d/%m/%Y')}", ""]
    if nouveaux:
        r += [f"### {len(nouveaux)} nouveau{'x' if len(nouveaux) > 1 else ''} passage{'s' if len(nouveaux) > 1 else ''}", ""]
        r += [f"- **{d.strftime('%d/%m')}** · {em['heure'] if 'heure' in em else ''} · {em['nom']} : **{nom}** — {f or '_fonction à compléter_'}"
              + (f" ([écouter]({e}))" if e else "") for d, em, nom, f, e in sorted(nouveaux, key=lambda n: (n[0], n[1].get('heure', '')))]
        r.append("")
    if completes:
        r += ["### Compléments", ""] + [f"- {c}" for c in completes] + [""]
    if prudence:
        r += ["### Écartés par prudence (à ajouter à la main si ce sont bien des invités politiques)", ""]
        r += [f"- {p}" for p in prudence] + [""]
    if hors_champ:
        r += ["<details><summary>Invités hors périmètre (experts, entreprises, culture…)</summary>", ""]
        r += [f"- {h}" for h in hors_champ] + ["", "</details>", ""]
    if ecartes:
        r += ["<details><summary>Épisodes sans invité identifié</summary>", ""]
        r += [f"- {e}" for e in ecartes] + ["", "</details>", ""]
    if erreurs:
        r += ["### Problèmes rencontrés", ""] + [f"- {e}" for e in erreurs] + [""]
    if not (nouveaux or completes):
        r.append("Rien de nouveau.")
    (RACINE / "resume.md").write_text("\n".join(r) + "\n", encoding="utf-8")
    print("\n" + "\n".join(r))


if __name__ == "__main__":
    main()
