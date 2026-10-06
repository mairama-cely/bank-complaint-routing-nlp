"""Phase 3a — Company-name masking (variant `company_masked`).

Lexicon built from the TRAIN split only (Company column), applied unchanged to val and test.
  - full names : normalised Company values (legal suffixes removed) of companies with >= min_company_complaints
  - single tokens from those names, kept only if >= single_token_min_concentration of the train documents
    containing the token are complaints against a company whose normalised name contains that token,
    and only if the token appears in the names of at most single_token_max_companies retained companies
No hand-written alias list (user decision 2026-10-05): brands absent from the Company column stay visible.
Matches are case-insensitive, token-level (words separated by whitespace only), with an optional
possessive "'s" or a plural "s" glued to the last word.

Outputs: data/processed/company_masked.parquet (complaint_id, split, service, text_company_masked),
         reports/phase3a/*.csv, reports/phase3a_company_mask.md
The frozen Phase 2b files are read only (sha256 checked), never modified.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))
from common import ROOT, load_config, read_json, stop, write_json  # noqa: E402
from profile_report import md_table  # noqa: E402

WORD = re.compile(r"[a-z0-9]+")
GENERIC_TAIL = {"financial", "bank", "services", "service", "corporation", "national", "association", "usa", "us"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(8 * 1024**2), b""):
            h.update(b)
    return h.hexdigest()


def normalise(name: str, suffixes: set) -> str:
    toks = WORD.findall(str(name).lower().replace("&", " "))
    while toks and (toks[-1] in suffixes or (len(toks) >= 2 and toks[-2:] == ["n", "a"])):
        if toks[-2:] == ["n", "a"]:
            toks = toks[:-2]
            continue
        toks.pop()
    toks = [t for t in toks if t not in {"the", "dba"}]
    return " ".join(toks)


def make_masker(patterns: list[str], tok: str):
    """Token-level matcher (linear time; a regex alternation of hundreds of names is too slow on ~100k texts).
    Returns (mask_function, hits_counter). Shared with Phase 3c (external test set) so the lexicon is applied
    identically."""
    index: dict[str, list[tuple[str, ...]]] = {}
    for p in patterns:
        t = tuple(p.split())
        index.setdefault(t[0], []).append(t)
    for v in index.values():
        v.sort(key=len, reverse=True)
    tok_rx = re.compile(r"[A-Za-z0-9]+")
    collapse = re.compile(r"(" + re.escape(tok) + r")(?:\s*\1)+")
    hits = Counter()

    def mask(text: str) -> str:
        ms = list(tok_rx.finditer(text))
        low = [m.group().lower() for m in ms]
        spans, i = [], 0
        while i < len(ms):
            matched = None
            cands = list(index.get(low[i], []))
            if low[i].endswith("s"):                       # plural glued to a one-word name, e.g. "paypals"
                cands += [p for p in index.get(low[i][:-1], []) if len(p) == 1]
            for cand_p in cands:
                n = len(cand_p)
                if i + n > len(ms):
                    continue
                ok = True
                for j in range(n):
                    w = low[i + j]
                    last = j == n - 1
                    if not (w == cand_p[j] or (last and w == cand_p[j] + "s")):
                        ok = False
                        break
                    if j and not text[ms[i + j - 1].end():ms[i + j].start()].isspace():
                        ok = False
                        break
                if ok:
                    matched = (i, i + n)
                    break
            if matched:
                a, b = matched
                end = ms[b - 1].end()
                if b < len(ms) and low[b] == "s" and text[end:ms[b].start()] == "'":   # possessive 's
                    end, b = ms[b].end(), b + 1
                spans.append((ms[a].start(), end))
                hits[" ".join(low[a:b])] += 1
                i = b
            else:
                i += 1
        if not spans:
            return text
        out, prev = [], 0
        for a, e in spans:
            out.append(text[prev:a]); out.append(f" {tok} "); prev = e
        out.append(text[prev:])
        return re.sub(r"\s+", " ", collapse.sub(r"\1", "".join(out))).strip()

    return mask, hits


def main() -> int:
    cfg = load_config()
    p3 = cfg.get("phase3")
    if not p3:
        stop("Section phase3 absente de config.yaml.")
    cm = p3["company_mask"]
    if cm["lexicon_source"] != "train":
        stop("company_mask.lexicon_source doit valoir 'train'.")
    tok = cm["token"]
    suffixes = set(cm["legal_suffixes"])

    proc = ROOT / "data" / "processed"
    manifest = read_json(proc / "MANIFEST.json")
    if manifest is None:
        stop("data/processed/MANIFEST.json absent : Phase 2b non exécutée.")
    if sha256(proc / "complaints_clean.parquet") != manifest["all"]["sha256"]:
        stop("complaints_clean.parquet ne correspond pas au sha256 du manifeste (jeu modifié depuis la 2b).")
    print("[1/5] Vérification sha256 et chargement…", flush=True)
    df = pd.read_parquet(proc / "complaints_clean.parquet", columns=["complaint_id", "service", "split", "text_clean"])

    # company column: real name resolved from Phase 1 metadata
    cols = read_json(ROOT / cfg["paths"]["interim"] / "columns.json")
    norm_cols = list(cols["original_to_normalized"].values())
    if "company" not in norm_cols:
        stop(f"Colonne 'company' introuvable. Colonnes réelles : {norm_cols}")
    cid = cols["keys"]["complaint_id"]
    nar_pq = (ROOT / cfg["paths"]["interim"] / "complaints_with_narrative.parquet").as_posix()
    comp = duckdb.connect().execute(
        f'SELECT CAST("{cid}" AS VARCHAR) AS complaint_id, "company" FROM read_parquet(\'{nar_pq}\')').df()
    df = df.merge(comp, on="complaint_id", how="left", validate="one_to_one")
    n_missing = int(df["company"].isna().sum())
    if n_missing:
        stop(f"{n_missing} réclamations sans valeur Company après jointure.")
    df["company_norm"] = df["company"].map(lambda c: normalise(c, suffixes))

    # --- lexicon from TRAIN only
    print("[2/5] Construction du lexique (train)…", flush=True)
    tr = df[df["split"] == "train"]
    vc = tr["company_norm"].value_counts()
    kept = vc[vc >= cm["min_company_complaints"]]
    kept = kept[kept.index != ""]
    # multi-word names are masked as phrases; single words (incl. one-word company names) must pass the
    # concentration test below, so that a common word used as a company name is not masked everywhere
    phrases = set()
    for c in kept.index:
        toks = c.split()
        while len(toks) >= 2:                       # e.g. "capital one financial" -> also "capital one"
            phrases.add(" ".join(toks))
            if toks[-1] not in GENERIC_TAIL:
                break
            toks = toks[:-1]

    cand = {t for c in kept.index for t in c.split() if len(t) >= cm["single_token_min_len"] and not t.isdigit()}
    n_companies = Counter(t for c in kept.index for t in set(c.split()) if t in cand)
    doc_tokens = tr["text_clean"].str.lower().map(lambda t: set(WORD.findall(t)) & cand)
    comp_tokens = tr["company_norm"].map(lambda c: set(c.split()))
    n_docs, n_match = Counter(), Counter()
    for dt, ct in zip(doc_tokens, comp_tokens):
        for t in dt:
            n_docs[t] += 1
            if t in ct:
                n_match[t] += 1
    single = pd.DataFrame({"token": list(cand)})
    single["n_docs"] = single["token"].map(n_docs).fillna(0).astype(int)
    single["n_docs_company_match"] = single["token"].map(n_match).fillna(0).astype(int)
    single["concentration"] = (single["n_docs_company_match"] / single["n_docs"].where(single["n_docs"] > 0)).round(3)
    single["n_company_names"] = single["token"].map(n_companies).astype(int)
    single["selected"] = ((single["n_docs"] >= cm["single_token_min_docs"])
                          & (single["concentration"] >= cm["single_token_min_concentration"])
                          & (single["n_company_names"] <= cm["single_token_max_companies"]))
    single = single.sort_values(["selected", "n_docs"], ascending=[False, False])
    sel_tokens = set(single.loc[single["selected"], "token"])
    patterns = sorted(phrases | sel_tokens, key=lambda p: (-len(p), p))
    if not patterns:
        stop("Lexique vide : vérifier les seuils de company_mask.")
    mask, hits = make_masker(patterns, tok)

    print(f"[3/5] Masquage des {len(df):,} narratifs ({len(patterns)} motifs)…", flush=True)
    df["text_company_masked"] = df["text_clean"].map(mask)
    df["n_company_tokens"] = df["text_company_masked"].str.count(re.escape(tok))

    out = proc / "company_masked.parquet"
    df[["complaint_id", "split", "service", "text_company_masked", "n_company_tokens"]].to_parquet(out, index=False)
    manifest_p3 = {"file": out.name, "rows": int(len(df)), "sha256": sha256(out),
                   "_created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "_source_sha256": manifest["all"]["sha256"], "_config": cm,
                   "_n_patterns": len(patterns)}
    write_json(proc / "MANIFEST_company_masked.json", manifest_p3)

    # --- measurements
    print("[4/5] Mesures de couverture…", flush=True)
    rep = ROOT / "reports" / "phase3a"; rep.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"pattern": patterns}).to_csv(rep / "lexicon_patterns.csv", index=False)
    single.to_csv(rep / "single_token_candidates.csv", index=False)
    cov = (df.assign(masked=df["n_company_tokens"] > 0)
             .groupby(["split", "service"])["masked"].mean().mul(100).round(2).unstack("split")
             [["train", "val", "test"]].reset_index())
    cov.to_csv(rep / "coverage_by_split_service.csv", index=False)
    top_hits = pd.DataFrame(hits.most_common(30), columns=["matched_text", "n_occurrences"])
    top_hits.to_csv(rep / "top_matches.csv", index=False)

    top15_path = ROOT / "reports" / "phase2c" / "top15_discriminant_words.csv"
    before_after = pd.DataFrame()
    if top15_path.exists():
        print("[5/5] Fréquences avant / après des mots discriminants de la 2c…", flush=True)
        words = sorted({w for c in pd.read_csv(top15_path, index_col=0).columns
                        for w in pd.read_csv(top15_path, index_col=0)[c].dropna() if not str(w).startswith("[")})
        tr2 = df[df["split"] == "train"]
        low_b, low_a = tr2["text_clean"].str.lower(), tr2["text_company_masked"].str.lower()
        rows = []
        for w in words:
            r = re.compile(r"\b" + re.escape(w) + r"\b")
            b, a = int(low_b.str.count(r).sum()), int(low_a.str.count(r).sum())
            rows.append({"word": w, "train_count_before": b, "train_count_after": a,
                         "pct_removed": round(100 * (b - a) / b, 1) if b else None})
        before_after = pd.DataFrame(rows).sort_values("pct_removed", ascending=False)
        before_after.to_csv(rep / "top15_words_before_after.csv", index=False)

    lines = [
        "# Masquage des noms d'entreprises — Phase 3a", "",
        f"Généré le {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC par `src/features/build_company_mask.py`. "
        "Lexique construit sur le **jeu d'entraînement uniquement**, appliqué tel quel à la validation et au test.", "",
        f"- Entreprises distinctes (nom normalisé) dans train : {tr['company_norm'].nunique():,} ; retenues "
        f"(≥ {cm['min_company_complaints']} réclamations) : {len(kept):,}.",
        f"- Motifs du lexique : {len(patterns):,} (noms complets : {len(phrases):,} ; mots isolés retenus : "
        f"{len(sel_tokens):,} sur {len(cand):,} candidats).", "",
        "## 1. Part des narratifs contenant au moins un `[COMPANY]` (%)", "", md_table(cov), "",
        "## 2. 30 correspondances les plus fréquentes (tous jeux)", "", md_table(top_hits), "",
        "## 3. Mots isolés candidats (retenus en tête, puis rejetés)", "",
        f"Critère : ≥ {cm['single_token_min_docs']} documents train et concentration ≥ "
        f"{cm['single_token_min_concentration']} (part des documents contenant le mot dont l'entreprise visée contient ce mot) "
        f"et mot présent dans les noms de ≤ {cm['single_token_max_companies']} entreprises retenues (`n_company_names`). "
        "Liste complète : `reports/phase3a/single_token_candidates.csv`.", "",
        md_table(single, max_rows=120), "",
        "## 4. Mots les plus discriminants de la 2c : fréquence avant / après masquage (train)", "",
        "Un `pct_removed` proche de 100 indique un mot masqué ; proche de 0, un mot non capté par le lexique.", "",
        md_table(before_after, max_rows=200) if not before_after.empty else "_top15_discriminant_words.csv introuvable_", "",
        "## 5. Limites", "",
        "- Les marques absentes de la colonne Company (ex. une application détenue par une société au nom différent) "
        "ne sont pas captées.",
        "- Un mot isolé rejeté (concentration insuffisante ou présent dans trop de noms) reste visible dans le texte, "
        "même s'il désigne parfois l'entreprise.",
        "- Aucune liste d'alias écrite à la main (décision du 2026-10-05) : les formes courtes ou commerciales absentes "
        "de la colonne Company restent visibles (voir section 4, mots à `pct_removed` = 0).",
        "- Un mot retenu peut aussi être un mot courant dans certains textes : la part de faux positifs d'un mot est "
        "au plus 1 − concentration (section 3).",
    ]
    (ROOT / "reports" / "phase3a_company_mask.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Motifs : {len(patterns):,} ; fichier : {out}")
    print(f"Rapport : {ROOT / 'reports' / 'phase3a_company_mask.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
