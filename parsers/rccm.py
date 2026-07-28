"""Parser RCCM — Immatriculation entreprise Burkina Faso.
Champs basés sur exemple réel (P0 - Immatriculation Principale) :
    Nom + Prénoms du dirigeant
    Date/Lieu naissance, Sexe, Nationalité
    NIP (13 chiffres), Téléphone
    Adresse (BP + Secteur)
    Nom commercial (VEENEMS FID)
    N° RCCM (BF-OUA-01-2025-A10-09917)
    IFU (00275371W)
    Activités, Chiffre d'affaires
    Date d'immatriculation
    N° CEFORE
"""
import re
from ._utils import find_after, find_dates, yam_id

# RCCM burkinabé : BF-OUA-01-2025-A10-09917
RCCM_NUM_RE = re.compile(r"(BF[-\s]?[A-Z]{2,4}[-\s]?\d{2}[-\s]?\d{4}[-\s]?[A-Z]?\d{1,3}[-\s]?\d{4,6})", re.I)
# IFU : 8 chiffres + lettre
IFU_RE = re.compile(r"\b(\d{7,10}[A-Z])\b")
NIP_RE = re.compile(r"\b(\d{8})\s*[/\-]?\s*(\d{8})\b")   # NIP double (79223325/51862251)
TEL_RE = re.compile(r"\b(\d{8})\b")
BP_RE = re.compile(r"BP\s*(\d{2,5})", re.I)
CA_RE = re.compile(r"(?:chiffre.*affaires?|CA)[^\d]{0,30}(\d[\d\s.,]{3,15})\s*(?:FCFA|CFA)?", re.I)
CEFORE_RE = re.compile(r"CEFORE\s*[:\-]?\s*([A-Z]{2,4}\d{2,4}\s*/\s*\d{3,6})", re.I)


def parse_rccm(lines: list[str]) -> dict:
    joined = " ".join(lines)
    low = joined.lower()

    out = {
        "nom": find_after(lines, ["nom"]),
        "prenoms": find_after(lines, ["prenoms", "prénoms", "prenom"]),
        "date_naissance": "",
        "lieu_naissance": find_after(lines, ["lieu"]),
        "sexe": "",
        "nationalite": find_after(lines, ["nationalite", "nationalité"]),
        "situation_matrimoniale": find_after(lines, ["situation matrimoniale", "matrimoniale"]),
        "adresse": find_after(lines, ["adresse domicile", "adresse"]),
        "telephone": "",
        "nip": "",
        "nom_commercial": find_after(lines, ["nom commercial"]),
        "enseigne": find_after(lines, ["enseigne"]),
        "secteur_activite": find_after(lines, ["secteur"]),
        "numero_rccm": "",
        "ifu": "",
        "activites_principales": find_after(lines, ["principale", "activites principales", "activités"]),
        "date_immatriculation": "",
        "chiffre_affaires": "",
        "nombre_permanents": find_after(lines, ["permanents", "nombre de permanents"]),
        "numero_cefore": "",
    }

    # RCCM number (BF-OUA-01-2025-A10-09917)
    m = RCCM_NUM_RE.search(joined)
    if m:
        out["numero_rccm"] = re.sub(r"\s+", "-", m.group(1)).replace("--", "-").strip("-")

    # IFU (avec lettre finale)
    m = IFU_RE.search(joined)
    if m: out["ifu"] = m.group(1)

    # NIP (79223325/51862251 ou juste 8 chiffres)
    m = NIP_RE.search(joined)
    if m:
        out["nip"] = f"{m.group(1)}/{m.group(2)}"
    else:
        # fallback : 1er groupe de 8 chiffres après "NIP" ou "N° Identification"
        m = re.search(r"(?:nip|n[°o]?\s*ident)[^\d]{0,10}(\d{8})", low)
        if m: out["nip"] = m.group(1)

    # Sexe
    m = re.search(r"sexe\s*:?\s*(masculin|f[eé]minin|m|f)", low)
    if m:
        v = m.group(1).lower()
        out["sexe"] = "M" if v.startswith("m") else "F"

    # Téléphone (8 chiffres)
    for m in TEL_RE.finditer(joined):
        v = m.group(1)
        # exclure NIP (partie de 8 chiffres)
        if v not in out["nip"]:
            out["telephone"] = v
            break

    # Chiffre d'affaires
    m = CA_RE.search(joined)
    if m: out["chiffre_affaires"] = re.sub(r"\s+", "", m.group(1)) + " FCFA"

    # CEFORE
    m = CEFORE_RE.search(joined)
    if m: out["numero_cefore"] = re.sub(r"\s+", "", m.group(1))

    # Dates : naissance = 1ère, immatriculation = plus récente
    dates = find_dates(joined)
    if dates and not out["date_naissance"]:
        out["date_naissance"] = dates[0]
    if len(dates) >= 2:
        out["date_immatriculation"] = dates[-1]

    out["yam_id"] = yam_id(
        out["numero_rccm"] or out["ifu"] or f"{out['nom']}{out['prenoms']}"
    )
    return out
