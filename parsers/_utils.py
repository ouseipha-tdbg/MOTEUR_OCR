import hashlib
import re
from datetime import datetime

# Année sur 2 OU 4 chiffres (factures : 27/02/26), séparateurs . / - uniquement
# (l'espace créait des faux positifs sur les nombres OCR éclatés)
DATE_RE = re.compile(r"\b(\d{1,2})[./\-](\d{1,2})[./\-](\d{2}|\d{4})\b")
NIP_RE = re.compile(r"\b(\d{13})\b")
MONTANT_TOKEN_RE = re.compile(r"\b\d{1,3}(?:[.,\s]\d{3})+\b|\b\d{4,8}\b")


def find_after(lines: list[str], keys: list[str]) -> str:
    """Cherche la valeur après un label — même ligne (après : ou espace) ou ligne suivante."""
    for i, l in enumerate(lines):
        low = l.lower()
        for k in keys:
            if k in low:
                # après ":"
                if ":" in l:
                    v = l.split(":", 1)[1].strip()
                    if v and v.lower() != k:
                        return v
                # après le label sur la même ligne
                idx = low.find(k)
                after = l[idx + len(k):].strip(" :.-—\t")
                if after and len(after) > 1:
                    return after
                # ligne suivante
                if i + 1 < len(lines):
                    nxt = lines[i + 1].strip()
                    if nxt:
                        return nxt
    return ""


def find_dates(joined: str) -> list[str]:
    """Dates validées (jour<=31, mois<=12), année 2 chiffres normalisée en 20xx."""
    out = []
    for d, m, y in DATE_RE.findall(joined):
        if not (1 <= int(d) <= 31 and 1 <= int(m) <= 12):
            continue
        if len(y) == 2:
            y = "20" + y
        if not (2000 <= int(y) <= 2099):
            continue
        out.append(f"{int(d):02d}/{int(m):02d}/{y}")
    return out


def date_key(s: str) -> tuple:
    """Clé de tri pour date DD/MM/YYYY."""
    d, m, y = s.split("/")
    return (int(y), int(m), int(d))


def fuzzy_client(joined: str, target: str = "ZAMAPAY") -> str:
    """Détecte le nom client malgré le bruit OCR (ZAHAPAY, ZANAPAY, ZAMAPRY...).
    Tolère 1-2 caractères substitués via difflib."""
    import difflib
    for tok in re.findall(r"\b[A-Z]{5,10}\b", joined.upper()):
        if difflib.SequenceMatcher(None, tok, target).ratio() >= 0.72:
            # suffixe éventuel (SA, SARL) collé après dans le texte
            m = re.search(re.escape(tok) + r"\s+(SA(?:RL)?)\b", joined.upper())
            return f"{target} {m.group(1)}" if m else target
    return ""


def parse_montant(s: str) -> int:
    """'17.110' / '122 858' / '122,858' -> int."""
    digits = re.sub(r"\D", "", s)
    return int(digits) if digits else 0


def montant_near(lines: list[str], keys: list[str], window: int = 14) -> str:
    """Montant associé à un label ('total a payer'...) malgré l'OCR éclaté.

    Heuristiques (photos de factures rotées / tableaux) :
    - fenêtre de lignes autour du label (l'ordre spatial est perdu)
    - exclusion des tokens adjacents à une date (codes d'impression '27/02/26 143078')
    - canonicalisation des lectures tête-bêche ('858221' = '122858' lu à l'envers),
      en gardant la variante la plus tardive dans le document (corps de facture)
    - score = fréquence dans tout le doc, départage par valeur max
    """
    def _tokens(s):
        # retire les dates avant tokenisation (sinon l'année compte comme montant)
        s = DATE_RE.sub(" ", s)
        out = []
        for t in MONTANT_TOKEN_RE.findall(s):
            v = parse_montant(t)
            if 2000 <= v <= 2099:  # année isolée (période '2/2026'...)
                continue
            out.append(t)
        return out

    def _is_date_line(s):
        return bool(DATE_RE.search(s))

    # occurrences de chaque montant dans tout le doc (dernière position gardée)
    last_pos, freq = {}, {}
    for idx, l in enumerate(lines):
        for tok in _tokens(l):
            v = parse_montant(tok)
            if not (100 <= v <= 99_999_999):
                continue
            last_pos[v] = idx
            freq[v] = freq.get(v, 0) + 1

    # fusion des lectures inversées (rotation 180°) vers la variante la plus tardive
    def canon(v):
        rv = int(str(v)[::-1]) if str(v)[-1] != "0" else v
        if rv != v and rv in last_pos:
            return v if last_pos[v] >= last_pos[rv] else rv
        return v

    keys_compact = [k.replace(" ", "") for k in keys]

    # priorité : montant sur la MÊME ligne que le label (haute précision)
    same_line = []
    for l in lines:
        low = l.lower()
        if any(k in low for k in keys) or any(k in low.replace(" ", "") for k in keys_compact):
            same_line += [parse_montant(t) for t in _tokens(l)]
    same_line = [v for v in same_line if 100 <= v <= 99_999_999]
    if same_line:
        return str(max(same_line))

    candidates = {}
    for i, l in enumerate(lines):
        low = l.lower()
        low_compact = low.replace(" ", "")
        # match aussi les labels collés par l'OCR ('TOTALTTC', 'NETAPAYER')
        if not (any(k in low for k in keys) or any(k in low_compact for k in keys_compact)):
            continue
        for j in range(max(0, i - window), min(len(lines), i + window + 1)):
            if _is_date_line(lines[j]) or (j > 0 and _is_date_line(lines[j - 1])):
                continue  # code d'impression collé à une date
            for tok in _tokens(lines[j]):
                v = parse_montant(tok)
                if 100 <= v <= 99_999_999:
                    c = canon(v)
                    score = freq.get(v, 0) + (freq.get(int(str(v)[::-1]), 0) if str(v)[-1] != "0" else 0)
                    candidates[c] = max(candidates.get(c, 0), score)

    if not candidates:
        return ""
    best = max(candidates.items(), key=lambda kv: (kv[1], kv[0]))
    return str(best[0])


def yam_id(seed: str) -> str:
    if not seed.strip():
        seed = datetime.utcnow().isoformat()
    d = hashlib.sha1(seed.encode()).hexdigest()
    return f"YAM-{int(d[:8], 16) % 1_000_000:06d}"


def mrz_date(s: str, past: bool = True) -> str:
    """YYMMDD -> DD/MM/YYYY. past=True pour date naissance, False pour expiration."""
    if len(s) != 6 or not s.isdigit():
        return ""
    yy, mm, dd = int(s[:2]), s[2:4], s[4:6]
    year = 2000 + yy if (past and yy <= 30) or (not past and yy < 80) else 1900 + yy
    return f"{dd}/{mm}/{year}"


def parse_mrz_id(mrz_lines: list[str]) -> dict:
    """Parse MRZ TD1 (carte identité, 3 lignes de 30 chars)."""
    out = {}
    if len(mrz_lines) < 3:
        return out
    l1, l2, l3 = mrz_lines[0], mrz_lines[1], mrz_lines[2]

    # Ligne 1: I<{country3}{doc_number9}<check<optional<
    if len(l1) >= 15 and l1[0] in ("I", "A", "C"):
        out["nationalite"] = l1[2:5].replace("<", "")
        out["mrz_doc_number"] = l1[5:14].replace("<", "")

    # Ligne 2: {birth6}{check1}{sex1}{expiry6}{check1}{nationality3}<...
    if len(l2) >= 15:
        birth = l2[0:6]
        sex = l2[7] if len(l2) > 7 else ""
        expiry = l2[8:14]
        out["date_naissance_mrz"] = mrz_date(birth, past=True)
        out["date_expiration_mrz"] = mrz_date(expiry, past=False)
        if sex in ("M", "F"):
            out["sexe_mrz"] = sex

    # Ligne 3 : format standard {NOM}<<{PRENOM1}<{PRENOM2}<...
    # OCR peut manquer un `<` → on split sur toute séquence de `<`
    import re as _re
    tokens = [t for t in _re.split(r"<+", l3.strip("<")) if t]
    if tokens:
        out["nom_mrz"] = tokens[0].strip()
        if len(tokens) > 1:
            out["prenoms_mrz"] = " ".join(tokens[1:]).strip()

    return out


def extract_mrz_lines(lines: list[str]) -> list[str]:
    """Détecte les lignes MRZ (>= 25 chars, majuscules/chiffres/<)."""
    mrz = []
    for l in lines:
        clean = l.replace(" ", "").upper()
        if len(clean) >= 25 and re.match(r"^[A-Z0-9<]+$", clean):
            mrz.append(clean)
    return mrz
