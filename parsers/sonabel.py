"""Parser SONABEL — identification client uniquement (KYC/KYB).

Zone cible : "Nom et adresse de l'abonné" + N° police / abonné / compteur.
"""
import re
from ._utils import fuzzy_client

POLICE_RE = re.compile(r"\b(\d{6})\s*([A-Z])\b")
# TI parfois lu TIO/T1 ; O<->0 fréquent dans les chiffres
ABONNE_RE = re.compile(r"\b(T[I1][O0]?\s*[\dO]{8,10})\s*[/\-]?\s*(\d?)\b", re.I)
COMPTEUR_RE = re.compile(r"\b(2\d{8,9})\s*[/\-]?\s*(\d?)\b")
# Adresse cadastrale BF : SECT 11 LOT 02 PLE 44 (tolérant)
PARCELLE_RE = re.compile(
    r"(S\w{2,5}[\.\s]*\d{1,3}[\.\s]*L[O0]T[\.\s]*\d{1,3}[\.\s]*(?:PLE|PARCELLE|PARC|P)[\.\s]*\d{1,4})",
    re.I
)
PARCELLE_DEGRADEE_RE = re.compile(r"([A-Z0-9]{0,12})PLE\s*(\d{1,4})\b", re.I)


def parse_sonabel(lines: list[str]) -> dict:
    joined = " ".join(lines)

    out = {
        "fournisseur": "SONABEL",
        "client": "",
        "numero_police": "",
        "numero_abonne": "",
        "compteur": "",
        "parcelle": "",
    }

    m = POLICE_RE.search(joined)
    if m: out["numero_police"] = f"{m.group(1)} {m.group(2)}"

    m = ABONNE_RE.search(joined)
    if m:
        raw = re.sub(r"[\s/]", "", m.group(1)).upper()
        digits = re.sub(r"O", "0", raw[2:] if raw[:2] in ("TI", "T1") else raw)
        base = "TI" + digits
        out["numero_abonne"] = f"{base}/{m.group(2)}" if m.group(2) else base

    m = COMPTEUR_RE.search(joined)
    if m:
        out["compteur"] = f"{m.group(1)}/{m.group(2)}" if m.group(2) else m.group(1)

    # Client : fuzzy ZAMAPAY (tolère ZAHAPAY, ZAmAPAY... bruit OCR)
    out["client"] = fuzzy_client(joined)

    m = PARCELLE_RE.search(joined)
    if m:
        raw = m.group(1)
        nums = re.findall(r"\d+", raw)
        if len(nums) == 3:
            out["parcelle"] = f"SECT {nums[0]} LOT {nums[1]} PLE {nums[2]}"
        else:
            out["parcelle"] = re.sub(r"\s+", " ", raw).upper()
    else:
        m = PARCELLE_DEGRADEE_RE.search(joined)
        if m and (any(c.isdigit() for c in m.group(1)) or m.group(1).upper().startswith("S")):
            out["parcelle"] = f"{m.group(1)}PLE{m.group(2)}".upper() + " (partiel)"

    return out
