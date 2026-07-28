"""Parser facture générique + routage auto vers ONEA/SONABEL.

Si le texte OCR contient les marqueurs ONEA ou SONABEL, on délègue au parser
spécialisé (beaucoup plus fiable) et on fusionne les champs génériques.
"""
import re
from ._utils import find_after, find_dates, date_key, yam_id, montant_near

# numéro de facture : exige au moins un chiffre (évite de capturer "N°Police" etc.)
FACTURE_NUM_RE = re.compile(
    r"(?:facture|invoice)\s*(?:n[°o]?\s*[:\-]?\s*)?((?=[A-Z0-9\-/]*\d)[A-Z0-9\-/]{3,20})", re.I
)
TVA_RE = re.compile(r"tva\s*[:\-]?\s*(\d+(?:[.,]\d+)?)\s*%", re.I)
DEVISE_RE = re.compile(r"\b(FCFA|XOF|EUR|USD)\b|(€|\$)", re.I)  # \b évite 'erreur' -> EUR

_ONEA_MARKERS = ("onea", "l'eau et de l'assainissement", "assainissement")
_SONABEL_MARKERS = ("sonabel", "electricite du burkina", "électricité du burkina")


def parse_facture(lines: list[str]) -> dict:
    joined = " ".join(lines)
    low = joined.lower()

    # --- routage auto vers parser spécialisé ---
    if any(k in low for k in _SONABEL_MARKERS):
        from .sonabel import parse_sonabel
        out = parse_sonabel(lines)
        out["doc_type_detecte"] = "sonabel"
        out["yam_id"] = yam_id(out.get("numero_police") or out.get("numero_abonne") or joined[:50])
        return out
    if any(k in low for k in _ONEA_MARKERS):
        from .onea import parse_onea
        out = parse_onea(lines)
        out["doc_type_detecte"] = "onea"
        out["yam_id"] = yam_id(out.get("numero_contrat") or out.get("numero_abonne") or joined[:50])
        return out

    # --- facture générique ---
    out = {
        "numero_facture": "",
        "date_facture": "",
        "date_limite": "",
        "fournisseur": find_after(lines, ["fournisseur", "emetteur", "émetteur", "vendeur"]),
        "client": find_after(lines, ["client", "acheteur", "destinataire"]),
        "montant_ht": montant_near(lines, ["montant ht", "total ht", "sous-total"], window=3),
        "tva": "",
        "montant_ttc": montant_near(
            lines, ["total a payer", "total à payer", "net a payer", "net à payer",
                    "montant ttc", "total ttc"]
        ),
        "devise": "",
    }

    m = FACTURE_NUM_RE.search(joined)
    if m: out["numero_facture"] = m.group(1)

    m = TVA_RE.search(joined)
    if m: out["tva"] = m.group(1) + "%"

    dates = find_dates(joined)
    if dates:
        out["date_facture"] = dates[0]
        out["date_limite"] = max(dates, key=date_key)

    m = DEVISE_RE.search(joined)
    if m:
        sym = {"€": "EUR", "$": "USD"}
        out["devise"] = sym.get(m.group(2), (m.group(1) or "").upper())

    out["yam_id"] = yam_id(out["numero_facture"] or f"{out['fournisseur']}{out['date_facture']}")
    return out
