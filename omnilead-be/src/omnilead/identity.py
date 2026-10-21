"""Identity resolution untuk kasus AMBIGU.

Kecocokan pasti (HP/email/handle sama persis) ditangani `IngestService` dan
digabung otomatis. Di sini hanya kemiripan: nama dan konteks. Hasilnya tidak
pernah digabung diam-diam; selalu berupa USULAN merge dengan bukti dan skor
keyakinan yang harus disetujui manusia.
"""

import re
from dataclasses import dataclass, field

from omnilead.models import Lead

THRESHOLD = 0.35
_COMPANY_NOISE = re.compile(r"\b(pt|cv|ud|tbk)\b\.?", re.I)


def _tokens(name: str | None) -> list[str]:
    return [t for t in re.findall(r"[a-z]+", (name or "").lower()) if len(t) >= 3]


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
