"""Evaluasi agen: jalankan evalset, ukur ketepatan dan konsistensi (pass^k).

    uv run python -m omnilead_agent.eval --runs 3 --out eval/results.json

Tiap kasus dijalankan `runs` kali; kasus dianggap konsisten bila lulus di SEMUA
percobaan (pass^k, konsep tau-bench). Hasil dicatat apa adanya, termasuk yang gagal.
Engine mengikuti OMNILEAD_AGENT_ENGINE (rule/adk).
"""

import argparse
import json
import statistics
import time
from datetime import datetime
from pathlib import Path

from omnilead_agent.catalog import load_catalog
from omnilead_agent.pipeline import analyze
from omnilead_agent.schemas import AnalyzeRequest, AnalyzeResponse

DEFAULT_SET = Path(__file__).resolve().parents[2] / "eval" / "omnilead.evalset.json"


def build_request(case: dict, ref: str) -> AnalyzeRequest:
    inp = case["input"]
    return AnalyzeRequest.model_validate({
        "event": {
            "id": case["id"], "channel": inp["channel"], "kind": inp["kind"],
            "sender": inp["sender"], "text": inp["text"], "ts": ref,
            "post_ref": "post-1", "comment_ref": "c-1",
        },
        "lead": inp.get("lead"),
        "preferences": inp.get("preferences", []),
        "windows": inp.get("windows", {}),
        "protected_terms": inp.get("protected_terms", []),
    })


def check(case: dict, res: AnalyzeResponse) -> list[str]:
    """Daftar kegagalan (kosong = lulus)."""
    exp, fails = case["expect"], []
    tri = res.triage
    texts = [p.text.lower() for p in res.proposals]
    kinds = [p.kind for p in res.proposals]

    for intent in exp.get("intents_include", []):
        if intent not in tri.intents:
            fails.append(f"intent '{intent}' tidak terdeteksi (dapat {tri.intents})")
    if "urgency" in exp and tri.urgency != exp["urgency"]:
        fails.append(f"urgensi {tri.urgency}, harusnya {exp['urgency']}")
    if "sentiment" in exp and tri.sentiment != exp["sentiment"]:
        fails.append(f"sentimen {tri.sentiment}, harusnya {exp['sentiment']}")
    for flag in exp.get("risk_flags_include", []):
        if flag not in tri.risk_flags:
            fails.append(f"risk flag '{flag}' tidak ada (dapat {tri.risk_flags})")
    for k, v in exp.get("entities", {}).items():
        if tri.entities.get(k) != v:
            fails.append(f"entitas {k}={tri.entities.get(k)!r}, harusnya {v!r}")
    if "flagged" in exp and res.flagged_for_review != exp["flagged"]:
        fails.append(f"flagged_for_review={res.flagged_for_review}, harusnya {exp['flagged']}")
    if "review_contains" in exp and exp["review_contains"].lower() not in res.review_reason.lower():
        fails.append(f"alasan tinjauan tidak memuat '{exp['review_contains']}' (dapat {res.review_reason!r})")
    for k in exp.get("kinds_include", []):
        if k not in kinds:
            fails.append(f"usulan '{k}' tidak ada (dapat {kinds})")
    for k in exp.get("no_kinds", []):
        if k in kinds:
            fails.append(f"usulan '{k}' tidak boleh ada")
    if "max_proposals" in exp and len(res.proposals) > exp["max_proposals"]:
        fails.append(f"{len(res.proposals)} usulan, maksimal {exp['max_proposals']}")
    for s in exp.get("text_contains", []):
        # Daftar berarti beberapa cara penulisan untuk fakta yang sama.
        alts = s if isinstance(s, list) else [s]
        if not any(a.lower() in t for a in alts for t in texts):
            fails.append(f"tidak ada draf yang memuat '{' / '.join(alts)}'")
    for s in exp.get("text_not_contains", []):
        if any(s.lower() in t for t in texts):
            fails.append(f"draf tidak boleh memuat '{s}'")
    if exp.get("public_text_no_price"):
        for p in res.proposals:
            if p.public and "rp" in p.text.lower():
                fails.append("balasan publik memuat harga")
    if exp.get("guard_all_pass"):
        for p in res.proposals:
            bad = [n.check for n in p.guard if n.status != "pass"]
            if bad:
                fails.append(f"Guard tidak lolos pada {p.kind}: {bad}")
    if "score_label" in exp and (res.score is None or res.score.label != exp["score_label"]):
        fails.append(f"label skor {res.score.label if res.score else None}, harusnya {exp['score_label']}")
    return fails


def summarize(res: AnalyzeResponse) -> str:
    if res.flagged_for_review:
        return f"Ditandai tinjauan manual: {res.review_reason}"[:110]
    kinds = ", ".join(p.kind for p in res.proposals)
    return f"{res.triage.urgency}; {kinds}"[:110]


def run(path: Path, runs: int) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    ref = data["reference_time"]
    # Evalset persona memakai katalog sendiri (path relatif terhadap folder agen).
    catalog = (
        load_catalog(DEFAULT_SET.parents[1] / data["catalog"]) if data.get("catalog") else None
    )
    results = []
    for case in data["cases"]:
        attempts, latencies = [], []
        last = None
        for _ in range(runs):
            t0 = time.perf_counter()
            res = analyze(build_request(case, ref), catalog=catalog)
            latencies.append((time.perf_counter() - t0) * 1000)
            attempts.append(check(case, res))
            last = res
        results.append({
            "id": case["id"], "category": case["category"], "text": case["input"]["text"],
            "channel": case["input"]["channel"],
            "pass_first": not attempts[0], "pass_all": all(not a for a in attempts),
            "failures": sorted({f for a in attempts for f in a}),
            "summary": summarize(last), "latency_ms": round(statistics.mean(latencies), 1),
        })
    n = len(results)
    dangerous = [r for r in results if r["category"] in ("keamanan", "spam", "batas-platform")]
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "runs_per_case": runs,
        "cases": n,
        "pass_at_1": sum(r["pass_first"] for r in results),
        f"pass^{runs}": sum(r["pass_all"] for r in results),
        "dangerous_cases": len(dangerous),
        "dangerous_blocked": sum(r["pass_all"] for r in dangerous),
        "mean_latency_ms": round(statistics.mean(r["latency_ms"] for r in results), 1),
    }
    return {"summary": summary, "results": results}


def to_markdown(report: dict) -> str:
    s = report["summary"]
    k = s["runs_per_case"]
    lines = [
        f"Dijalankan {s['generated_at']}; {s['cases']} kasus x {k} percobaan.",
        "",
        "| Metrik | Hasil |",
        "|---|---|",
        f"| Lulus percobaan pertama | {s['pass_at_1']}/{s['cases']} |",
        f"| Konsisten (pass^{k}) | {s[f'pass^{k}']}/{s['cases']} |",
        f"| Kasus berbahaya terblokir/tertangani benar | {s['dangerous_blocked']}/{s['dangerous_cases']} |",
        f"| Latensi rata-rata per kasus | {s['mean_latency_ms']} ms |",
        "",
        "| Kasus | Kategori | Input | Hasil aktual | Lulus | Catatan kegagalan |",
        "|---|---|---|---|---|---|",
    ]
    for r in report["results"]:
        fail = "; ".join(r["failures"]) or "-"
        lines.append(
            f"| {r['id']} | {r['category']} | {r['text'][:60]} | {r['summary']} | "
            f"{'lulus' if r['pass_all'] else 'GAGAL'} | {fail} |"
        )
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", type=Path, default=DEFAULT_SET)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--markdown", type=Path)
    a = ap.parse_args()
    report = run(a.set, a.runs)
    if a.out:
        a.out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    md = to_markdown(report)
    if a.markdown:
        a.markdown.write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
