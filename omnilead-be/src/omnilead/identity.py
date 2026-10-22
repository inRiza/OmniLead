"""Identity resolution untuk kasus AMBIGU.

Kecocokan pasti (HP/email/handle sama persis) ditangani `IngestService` dan
digabung otomatis. Di sini hanya kemiripan: nama dan konteks. Hasilnya tidak
pernah digabung diam-diam; selalu berupa USULAN merge dengan bukti dan skor
keyakinan yang harus disetujui manusia.
"""

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from omnilead.models import Lead

THRESHOLD = 0.35
_COMPANY_NOISE = re.compile(r"\b(pt|cv|ud|tbk)\b\.?", re.I)
GMAIL_DOMAINS = {"gmail.com", "googlemail.com"}
PLUS_DOMAINS = {"outlook.com", "hotmail.com", "live.com", "icloud.com", "me.com", "proton.me", "protonmail.com"}
FREE_DOMAINS = GMAIL_DOMAINS | PLUS_DOMAINS | {"yahoo.com", "yahoo.co.id", "ymail.com", "aol.com", "mail.com"}


def canon_email(raw: str | None) -> str | None:
    if not raw or "@" not in raw:
        return None
    local, _, domain = raw.strip().lower().rpartition("@")
    if not local or not domain:
        return None
    if domain in GMAIL_DOMAINS:
        local, domain = local.split("+", 1)[0].replace(".", ""), "gmail.com"
    elif domain in PLUS_DOMAINS:
        local = local.split("+", 1)[0]
    return f"{local}@{domain}"


def email_domain(raw: str | None) -> str | None:
    email = canon_email(raw)
    if not email:
        return None
    domain = email.rpartition("@")[2]
    return None if domain in FREE_DOMAINS else domain


def identity_keys(lead: Lead) -> set[str]:
    keys = {f"phone:{p}" for p in lead.phones if p}
    keys |= {f"email:{e}" for e in (canon_email(x) for x in lead.emails) if e}
    keys |= {f"handle:{h}" for h in lead.handles if h}
    return keys


HONORIFICS = {"kak", "kakak", "ka", "kk", "bu", "ibu", "pak", "bapak", "mbak", "mba", "mas", "bang", "abang",
              "sis", "gan", "om", "tante", "dek", "adik", "bunda", "ayah", "teh", "aa", "kang", "uni", "uda",
              "dr", "ir", "hj", "h"}


def _tokens(name: str | None) -> list[str]:
    return [t for t in re.findall(r"[a-z]+", (name or "").lower()) if len(t) >= 3 and t not in HONORIFICS]


def _similar(a: str, b: str, ratio: float) -> bool:
    return a == b or SequenceMatcher(None, a, b).ratio() >= ratio


def _strip_dummy(name: str | None) -> str:
    return re.sub(r"\(dummy\)", "", name or "", flags=re.I)


def norm_company(company: str | None) -> str:
    text = _COMPANY_NOISE.sub(" ", (company or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


@dataclass
class Candidate:
    lead: Lead
    confidence: float
    evidence: list[str] = field(default_factory=list)


def score_pair(
    new: Lead, existing: Lead, company_hint: str | None = None
) -> Candidate | None:
    """Skor kemiripan 0..0.95 antara profil baru dan profil yang sudah ada."""
    evidence: list[str] = []
    score = 0.0

    a, b = _tokens(_strip_dummy(new.name)), _tokens(_strip_dummy(existing.name))
    if a and b:
        if set(a) == set(b):
            score += 0.5
            evidence.append(f"Nama sama: {existing.name}")
        elif a[0] == b[0]:
            score += 0.35
            evidence.append(f"Nama depan sama: {a[0].title()}")
        elif len(a) == len(b) and all(_similar(x, y, 0.8) for x, y in zip(a, b)):
            score += 0.4
            evidence.append(f"Nama mirip: {existing.name}")
        elif _similar(a[0], b[0], 0.8):
            score += 0.25
            evidence.append(f"Nama depan mirip: {a[0].title()} dan {b[0].title()}")

    domains_new = {d for d in (email_domain(e) for e in new.emails) if d}
    domains_old = {d for d in (email_domain(e) for e in existing.emails) if d}
    shared = domains_new & domains_old
    if shared:
        score += 0.3
        evidence.append(f"Domain email kantor sama: {sorted(shared)[0]}")

    cmp_new = norm_company(company_hint or new.company)
    cmp_old = norm_company(existing.company)
    if cmp_new and cmp_old:
        if cmp_new == cmp_old:
            score += 0.4
            evidence.append(f"Perusahaan sama: {existing.company}")
        else:
            # Nama mirip tapi perusahaan berbeda: kemungkinan orang lain.
            score -= 0.2
            evidence.append(
                f"Perusahaan berbeda ({company_hint or new.company} vs {existing.company})"
            )

    handle_names = _tokens(" ".join(h.split(":", 1)[-1] for h in new.handles))
    if b and any(b[0] in h for h in handle_names):
        score += 0.1
        evidence.append("Handle memuat nama yang sama")

    score = min(score, 0.95)
    if score < THRESHOLD:
        return None
    return Candidate(lead=existing, confidence=round(score, 2), evidence=evidence)


def find_candidates(
    new: Lead, others: list[Lead], company_hint: str | None = None
) -> list[Candidate]:
    out = [
        c
        for other in others
        if other.id != new.id and (c := score_pair(new, other, company_hint))
    ]
    out.sort(key=lambda c: -c.confidence)
    return out[:3]
