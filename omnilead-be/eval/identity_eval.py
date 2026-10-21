"""Evaluasi identity resolution ambigu: presisi dan recall pada 50 lead dummy.

    uv run python eval/identity_eval.py

Populasi: 50 lead (25 nama depan, masing-masing dipakai dua orang berbeda
dengan perusahaan berbeda). Probe: 50 positif (orang yang sama, handle baru),
25 negatif nama sama tapi perusahaan baru, 25 negatif tidak terkait.
Usulan dianggap 'kuat' bila keyakinan >= 0.5 (di bawah itu tetap diusulkan
dengan label rendah, tidak pernah digabung otomatis).
"""

from datetime import datetime, timezone

from omnilead.identity import find_candidates
from omnilead.models import Lead

NOW = datetime.now(timezone.utc)
NAMES = ["Ani", "Budi", "Citra", "Dewi", "Eko", "Fajar", "Gita", "Hana", "Indra", "Joko",
         "Kiki", "Lina", "Maya", "Nando", "Oki", "Putri", "Rizky", "Sinta", "Tono", "Umar",
         "Vina", "Wawan", "Yuni", "Zaki", "Ayu"]
STRONG = 0.5


def lead(i: int, name: str, company: str | None, handles=()) -> Lead:
    return Lead(id=f"l{i}", name=name, company=company, handles=list(handles), created_at=NOW, updated_at=NOW)


def main() -> None:
    population = [lead(i, NAMES[i % 25], f"PT {NAMES[i % 25]}{i} Jaya") for i in range(50)]
    tp = fp = fn = 0
    top1_correct = 0
    neg_strong = 0

    for i, person in enumerate(population):  # positif
        probe = lead(900 + i, person.name, None, [f"instagram:{person.name.lower()}.{i}"])
        cands = find_candidates(probe, population, company_hint=person.company)
        strong = [c for c in cands if c.confidence >= STRONG]
        if cands and cands[0].lead.id == person.id:
            top1_correct += 1
        if strong and strong[0].lead.id == person.id:
            tp += 1
        else:
            fn += 1
        fp += sum(1 for c in strong if c.lead.id != person.id)

    for j in range(25):  # negatif: nama sama, perusahaan baru
        probe = lead(950 + j, NAMES[j], None, [f"instagram:{NAMES[j].lower()}_x"])
        strong = [c for c in find_candidates(probe, population, company_hint=f"CV Baru {j}") if c.confidence >= STRONG]
        neg_strong += len(strong)
    for j in range(25):  # negatif: tidak terkait
        probe = lead(980 + j, f"Zxy Qrs{j}", None, [f"instagram:zq{j}"])
        neg_strong += len([c for c in find_candidates(probe, population, company_hint=f"UD Lain {j}") if c.confidence >= STRONG])

    # Sulit: nama sama, tidak ada konteks perusahaan. Dua orang berbeda sama-sama kuat.
    ambiguous_two = 0
    for j in range(25):
        probe = lead(990 + j, NAMES[j], None, [f"instagram:{NAMES[j].lower()}.{j}"])
        strong = [c for c in find_candidates(probe, population) if c.confidence >= STRONG]
        ambiguous_two += len(strong) >= 2

    fp += neg_strong
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn)
    print("| Metrik | Hasil |\n|---|---|")
    print(f"| Probe positif (orang yang sama) | 50 |")
    print(f"| Top-1 benar (keyakinan apa pun) | {top1_correct}/50 |")
    print(f"| Usulan kuat (>=0.5) benar | {tp}/50 |")
    print(f"| Usulan kuat salah (false positive) | {fp} dari 100 probe |")
    print(f"| Presisi usulan kuat | {precision:.2f} |")
    print(f"| Recall usulan kuat | {recall:.2f} |")
    print(f"| Nama sama tanpa konteks perusahaan: usulan kuat ke 2 profil sekaligus | {ambiguous_two}/25 (manusia yang memilih) |")


if __name__ == "__main__":
    main()
