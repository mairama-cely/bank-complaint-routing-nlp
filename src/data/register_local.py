"""T4/T5 (adapted) — Register the CSV files downloaded and extracted manually into data/raw/.

Replaces download.py + extract.py: the original CFPB zip archives were not kept, so the
manifest records the sha256 of the local CSV files (not of the zips served by the CFPB).

Outputs: data/raw/MANIFEST.json, reports/local_inventory.csv
Stops if a SELECTED export is missing or if a file does not look like the expected CSV.
"""
from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from tqdm import tqdm

from common import load_config, p, read_json, stop, write_json


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f, tqdm(total=path.stat().st_size, unit="B", unit_scale=True,
                                    desc=f"sha256 {path.name[:32]}", leave=False) as bar:
        for block in iter(lambda: f.read(8 * 1024**2), b""):
            h.update(block)
            bar.update(len(block))
    return h.hexdigest()


def sniff(path: Path) -> tuple[str, str]:
    """Return (detected_format, first_line). CSV = first line contains commas and no JSON/zip signature."""
    head = path.open("rb").read(65536).lstrip(b"\xef\xbb\xbf")
    first = head.split(b"\n", 1)[0].decode("utf-8", errors="replace").strip()
    if head[:4] == b"PK\x03\x04":
        return "zip", first
    if head.lstrip()[:1] in (b"{", b"["):
        return "json", first
    if "," in first:
        return "csv", first
    return "autre", first


def main() -> int:
    cfg = load_config()
    raw, reports = p(cfg, "raw"), p(cfg, "reports")
    manifest_path = raw / "MANIFEST.json"
    manifest = read_json(manifest_path, default={})
    selected = set(cfg["selected_exports"])

    expected = {e["csv"]: e for e in cfg["exports"]}
    present = {f.name for f in raw.glob("*.csv")}
    unknown = sorted(present - set(expected))
    if unknown:
        print(f"[ALERTE] CSV présents dans data/raw mais absents de config.yaml (ignorés) : {unknown}")

    missing_sel = [e["id"] for e in cfg["exports"] if e["id"] in selected and e["csv"] not in present]
    if missing_sel:
        stop(f"Exports sélectionnés absents de data/raw : {missing_sel}")

    rows, headers = [], {}
    for e in cfg["exports"]:
        f = raw / e["csv"]
        if not f.exists():
            rows.append({"id": e["id"], "selected": e["id"] in selected, "file": e["csv"], "present": False,
                         "size_mb": "NA", "detected_format": "NA", "n_header_fields": "NA", "sha256": "NA"})
            continue
        fmt, first = sniff(f)
        st = f.stat()
        entry = manifest.get(str(e["id"]))
        if entry and entry.get("bytes") == st.st_size and entry.get("mtime_ns") == st.st_mtime_ns:
            digest = entry["sha256"]                     # unchanged file: no re-hash
        else:
            digest = sha256(f)
            if entry and digest != entry["sha256"]:      # added 2026-10-05: never accept a silent content change
                stop(f"Contenu de {e['csv']} modifié depuis son enregistrement (sha256 {entry['sha256'][:12]}… "
                     f"→ {digest[:12]}…). Retélécharger le fichier depuis l'archive CFPB avant de continuer.")
        manifest[str(e["id"])] = {
            "id": e["id"],
            "filename": e["csv"],
            "bytes": st.st_size,
            "mtime_ns": st.st_mtime_ns,
            "sha256": digest,
            "registered_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_url": e["url"],
            "acquisition": "téléchargement manuel du zip CFPB puis extraction par l'utilisatrice ; zip non conservé",
        }
        write_json(manifest_path, manifest)
        headers[e["id"]] = first
        rows.append({"id": e["id"], "selected": e["id"] in selected, "file": e["csv"], "present": True,
                     "size_mb": round(st.st_size / 1024**2, 1), "detected_format": fmt,
                     "n_header_fields": len(next(csv.reader([first]))), "sha256": digest})
        print(f"[ok] export {e['id']:>2}  {rows[-1]['size_mb']:>8} Mo  {fmt}")

    out = reports / "local_inventory.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    total = sum(r["size_mb"] for r in rows if r["present"])
    sel_total = sum(r["size_mb"] for r in rows if r["present"] and r["selected"])
    print(f"\nFichiers présents : {sum(r['present'] for r in rows)}/21 — {total / 1024:.2f} Go "
          f"(sélection : {sel_total / 1024:.2f} Go)")
    print(f"Inventaire : {out}\nManifeste : {manifest_path}")

    bad = [r for r in rows if r["present"] and r["selected"] and r["detected_format"] != "csv"]
    if bad:
        stop("Fichiers sélectionnés non reconnus comme CSV :\n" +
             "\n".join(f"  export {r['id']}: {r['file']} → {r['detected_format']}" for r in bad))
    distinct = {h for i, h in headers.items()}
    if len(distinct) > 1:
        print(f"[ALERTE] {len(distinct)} en-têtes différents parmi les fichiers présents — "
              "build_interim.py s'arrêtera si l'écart touche la sélection.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
