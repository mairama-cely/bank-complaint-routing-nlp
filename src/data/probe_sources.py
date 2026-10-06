"""T3 — HEAD request on the 21 archive URLs. No download.

Output: reports/source_probe.csv
Exit code 1 if any SELECTED export does not answer HTTP 200.
"""
from __future__ import annotations

import csv
import time

import requests

from common import load_config, p, stop

FIELDS = ["id", "period", "url", "selected", "http_status", "content_length_bytes",
          "content_length_mb", "last_modified", "content_type", "error"]


def head(url: str, timeout: int, retries: int):
    last_err = None
    for attempt in range(retries):
        try:
            return requests.head(url, timeout=timeout, allow_redirects=True), None
        except requests.RequestException as exc:
            last_err = f"{type(exc).__name__}: {exc}"
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return None, last_err


def main() -> int:
    cfg = load_config()
    sel_ids = set(cfg["selected_exports"])
    rows = []
    for e in cfg["exports"]:
        resp, err = head(e["url"], cfg["probe"]["timeout_s"], cfg["probe"]["max_retries"])
        cl = resp.headers.get("Content-Length") if resp is not None and resp.status_code == 200 else None
        rows.append({
            "id": e["id"],
            "period": e["period"],
            "url": e["url"],
            "selected": e["id"] in sel_ids,
            "http_status": resp.status_code if resp is not None else "NA",
            "content_length_bytes": int(cl) if cl else "NA",
            "content_length_mb": round(int(cl) / 1024**2, 1) if cl else "NA",
            "last_modified": resp.headers.get("Last-Modified", "NA") if resp is not None else "NA",
            "content_type": resp.headers.get("Content-Type", "NA") if resp is not None else "NA",
            "error": err or (resp.headers.get("x-deny-reason", "") if resp is not None else ""),
        })

    out = p(cfg, "reports") / "source_probe.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    print(f"{'id':>3} {'sel':>3} {'HTTP':>5} {'Mo':>9}  last_modified")
    for r in rows:
        print(f"{r['id']:>3} {'x' if r['selected'] else '':>3} {r['http_status']:>5} "
              f"{r['content_length_mb']:>9}  {r['last_modified']}  {r['error']}")

    sel = [r for r in rows if r["selected"]]
    no_cl = [r["id"] for r in rows if r["content_length_bytes"] == "NA" and r["http_status"] == 200]
    if no_cl:
        print(f"\n[ALERTE] Pas de Content-Length pour les exports {no_cl} : taille inconnue, non estimée.")
    known = [r["content_length_bytes"] for r in sel if r["content_length_bytes"] != "NA"]
    print(f"\nTaille connue des exports sélectionnés : {sum(known) / 1024**3:.2f} Go "
          f"({len(known)}/{len(sel)} tailles connues)")
    print(f"Rapport : {out}")

    bad = [r["id"] for r in sel if r["http_status"] != 200]
    if bad:
        stop(f"Exports sélectionnés sans réponse HTTP 200 : {bad}. Voir {out}", code=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
