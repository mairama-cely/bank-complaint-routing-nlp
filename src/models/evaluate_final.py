"""Phase 3c-ii — Final evaluation: 2026 test set (used once) and 2025 external set.

Test lock: reports/phase3c/TEST_LOCK.json records the sha256 of the evaluated models. A re-run with the SAME
models is allowed (deterministic, recorded as a re-run); a run with DIFFERENT models is refused, so that no model
can be re-tuned after looking at the test set.

Per variant (as_is, company_masked) and per dataset (test_2026, external_2025): macro-F1 with 95 % bootstrap CI,
accuracy, top-2 accuracy, per-service precision / recall / F1, confusion matrix; paired bootstrap of the
as_is - company_masked macro-F1 gap; calibration (ECE, Brier, reliability table) ; error analysis on the reference
variant (most confused pairs with examples, high-confidence errors = label-noise candidates, monthly macro-F1 on 2025).
Predictions (val, test, external) are saved for Phase 5.

Outputs: reports/phase3c/*.csv, reports/figures/phase3c_*.png, data/processed/predictions/*.parquet,
         reports/phase3c_evaluation.md
"""
from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import precision_recall_fscore_support  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))
from common import ROOT, load_config, read_json, stop, write_json  # noqa: E402
from profile_report import md_table  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(8 * 1024**2), b""):
            h.update(b)
    return h.hexdigest()


def macro_f1_int(yt: np.ndarray, yp: np.ndarray, k: int) -> float:
    cm = np.bincount(yt * k + yp, minlength=k * k).reshape(k, k).astype(float)
    tp = np.diag(cm)
    with np.errstate(divide="ignore", invalid="ignore"):
        p = np.where(cm.sum(0) > 0, tp / cm.sum(0), 0.0)
        r = np.where(cm.sum(1) > 0, tp / cm.sum(1), 0.0)
        f = np.where(p + r > 0, 2 * p * r / (p + r), 0.0)
    return float(f.mean())


def bootstrap_ci(yt, yp, k, n, rng, yp2=None):
    m = len(yt)
    vals, diffs = np.empty(n), np.empty(n)
    for b in range(n):
        idx = rng.integers(0, m, m)
        vals[b] = macro_f1_int(yt[idx], yp[idx], k)
        if yp2 is not None:
            diffs[b] = vals[b] - macro_f1_int(yt[idx], yp2[idx], k)
    ci = (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))
    dci = (float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))) if yp2 is not None else None
    return ci, dci


def calibration(proba: np.ndarray, yt: np.ndarray, bins: int):
    conf = proba.max(1); pred = proba.argmax(1); correct = (pred == yt).astype(float)
    edges = np.linspace(0, 1, bins + 1)
    rows, ece = [], 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (conf > lo) & (conf <= hi) if lo > 0 else (conf >= lo) & (conf <= hi)
        if sel.sum() == 0:
            continue
        acc, cf = correct[sel].mean(), conf[sel].mean()
        ece += abs(acc - cf) * sel.sum() / len(yt)
        rows.append({"bin": f"{lo:.2f}-{hi:.2f}", "n": int(sel.sum()), "mean_confidence": round(cf, 4),
                     "accuracy": round(acc, 4), "gap": round(acc - cf, 4)})
    onehot = np.zeros_like(proba); onehot[np.arange(len(yt)), yt] = 1
    brier = float(((proba - onehot) ** 2).sum(1).mean())
    return float(ece), brier, pd.DataFrame(rows)


def main() -> int:
    cfg = load_config()
    p3 = cfg.get("phase3", {}); ev = p3.get("evaluation")
    if not ev:
        stop("phase3.evaluation absent de config.yaml.")
    proc, models_dir = ROOT / "data" / "processed", ROOT / "models"
    rep = ROOT / "reports" / "phase3c"; rep.mkdir(parents=True, exist_ok=True)
    fig_dir = ROOT / cfg["paths"]["figures"]; fig_dir.mkdir(parents=True, exist_ok=True)
    pred_dir = proc / "predictions"; pred_dir.mkdir(exist_ok=True)

    # --- integrity checks
    print("[1/6] Contrôles d'intégrité (sha256 des données et des modèles)…", flush=True)
    man, mman, eman = (read_json(proc / n) for n in ("MANIFEST.json", "MANIFEST_company_masked.json",
                                                      "MANIFEST_external.json"))
    mm = read_json(models_dir / "MANIFEST_models.json")
    if None in (man, mman, eman, mm):
        stop("Un manifeste est absent (2b, 3a, 3c-i ou modèles).")
    for name in ("val", "test"):
        if sha256(proc / f"{name}.parquet") != man[name]["sha256"]:
            stop(f"{name}.parquet ne correspond pas à son sha256.")
    if sha256(proc / mman["file"]) != mman["sha256"]:
        stop("company_masked.parquet ne correspond pas à son sha256.")
    if sha256(proc / eman["file"]) != eman["sha256"]:
        stop(f"{eman['file']} ne correspond pas à son sha256.")
    variants = ["as_is", "company_masked"]
    model_sha = {}
    for v in variants:
        if sha256(models_dir / mm[v]["file"]) != mm[v]["sha256"]:
            stop(f"Modèle {mm[v]['file']} modifié depuis la Phase 3b.")
        model_sha[v] = mm[v]["sha256"]

    # --- test lock
    lock_path = rep / "TEST_LOCK.json"
    lock = read_json(lock_path)
    rerun = False
    if lock is not None:
        if lock["model_sha256"] != model_sha:
            stop("Le test a déjà été évalué avec d'autres modèles (reports/phase3c/TEST_LOCK.json). "
                 "Réévaluer avec de nouveaux modèles reviendrait à les ajuster sur le test : refusé.")
        rerun = True
        print("      Réexécution avec les mêmes modèles (autorisée, consignée).", flush=True)

    # --- data
    print("[2/6] Chargement de val, test et du jeu externe…", flush=True)
    masked = pd.read_parquet(proc / mman["file"], columns=["complaint_id", "text_company_masked"])
    def load(name):
        d = pd.read_parquet(proc / f"{name}.parquet", columns=["complaint_id", "service", "text_clean"])
        return d.merge(masked, on="complaint_id", how="left", validate="one_to_one")
    data = {"val_2026": load("val"), "test_2026": load("test"),
            f"external_{eman['label']}": pd.read_parquet(
                proc / eman["file"], columns=["complaint_id", "service", "received_month", "text_clean",
                                              "text_company_masked"])}
    ext_key = f"external_{eman['label']}"
    models = {v: joblib.load(models_dir / mm[v]["file"]) for v in variants}
    classes = np.array(models[variants[0]].classes_)
    if any(list(models[v].classes_) != list(classes) for v in variants):
        stop("Les deux modèles n'ont pas les mêmes classes.")
    k = len(classes); cidx = {c: i for i, c in enumerate(classes)}
    for ds, d in data.items():
        unknown = set(d["service"]) - set(classes)
        if unknown:
            stop(f"{ds} contient des services inconnus des modèles : {sorted(unknown)}")

    # --- predictions
    print("[3/6] Prédictions…", flush=True)
    P = {}
    for v in variants:
        col = mm[v]["text_column"]
        for ds, d in data.items():
            proba = models[v].predict_proba(d[col])
            P[(v, ds)] = proba
            out = pd.DataFrame(proba, columns=[f"p_{c}" for c in classes])
            out.insert(0, "complaint_id", d["complaint_id"].to_numpy())
            out.insert(1, "service_true", d["service"].to_numpy())
            out.insert(2, "service_pred", classes[proba.argmax(1)])
            out.insert(3, "confidence", proba.max(1))
            out.to_parquet(pred_dir / f"{ds}_{v}.parquet", index=False)

    # --- metrics
    print(f"[4/6] Métriques et intervalles bootstrap ({ev['bootstrap_resamples']} tirages)…", flush=True)
    rng = np.random.default_rng(p3["random_state"])
    metric_rows, per_class, cms, gaps = [], [], {}, []
    for ds in ("test_2026", ext_key):
        yt = data[ds]["service"].map(cidx).to_numpy()
        preds = {v: P[(v, ds)].argmax(1) for v in variants}
        for v in variants:
            proba = P[(v, ds)]; yp = preds[v]
            other = [x for x in variants if x != v][0]
            ci, dci = bootstrap_ci(yt, yp, k, ev["bootstrap_resamples"], rng,
                                   yp2=preds[other] if v == "as_is" else None)
            top2 = np.argsort(-proba, 1)[:, :2]
            metric_rows.append({"dataset": ds, "variant": v, "n": len(yt),
                                "macro_f1": round(macro_f1_int(yt, yp, k), 4),
                                "macro_f1_ci95": f"[{ci[0]:.4f} ; {ci[1]:.4f}]",
                                "accuracy": round(float((yp == yt).mean()), 4),
                                "top2_accuracy": round(float((top2 == yt[:, None]).any(1).mean()), 4)})
            if dci is not None:
                gaps.append({"dataset": ds, "gap_as_is_minus_masked": round(macro_f1_int(yt, preds["as_is"], k)
                                                                           - macro_f1_int(yt, preds["company_masked"], k), 4),
                             "gap_ci95": f"[{dci[0]:.4f} ; {dci[1]:.4f}]"})
            p, r, f, s = precision_recall_fscore_support(yt, yp, labels=range(k), zero_division=0)
            for i, c in enumerate(classes):
                per_class.append({"dataset": ds, "variant": v, "service": c, "precision": round(p[i], 4),
                                  "recall": round(r[i], 4), "f1": round(f[i], 4), "support": int(s[i])})
            cm = pd.DataFrame(np.bincount(yt * k + yp, minlength=k * k).reshape(k, k), index=classes, columns=classes)
            cms[(ds, v)] = cm
            cm.to_csv(rep / f"confusion_{ds}_{v}.csv")
    metrics = pd.DataFrame(metric_rows); metrics.to_csv(rep / "metrics.csv", index=False)
    pc = pd.DataFrame(per_class); pc.to_csv(rep / "per_service.csv", index=False)
    gaps_df = pd.DataFrame(gaps); gaps_df.to_csv(rep / "variant_gap.csv", index=False)

    # --- calibration
    print("[5/6] Calibrage…", flush=True)
    cal_rows, rel = [], {}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, ds in zip(axes, ("test_2026", ext_key)):
        yt = data[ds]["service"].map(cidx).to_numpy()
        ax.plot([0, 1], [0, 1], "--", color="grey", linewidth=1)
        for v in variants:
            ece, brier, table = calibration(P[(v, ds)], yt, ev["calibration_bins"])
            cal_rows.append({"dataset": ds, "variant": v, "ece": round(ece, 4), "brier": round(brier, 4)})
            table.to_csv(rep / f"reliability_{ds}_{v}.csv", index=False)
            rel[(ds, v)] = table
            ax.plot(table["mean_confidence"], table["accuracy"], marker="o", label=v)
        ax.set_title(ds); ax.set_xlabel("Confiance moyenne (classe prédite)"); ax.set_ylabel("Exactitude observée")
        ax.legend()
    fig.suptitle("Courbes de fiabilité"); fig.tight_layout()
    fig.savefig(fig_dir / "phase3c_reliability.png", dpi=150); plt.close(fig)
    cal = pd.DataFrame(cal_rows); cal.to_csv(rep / "calibration.csv", index=False)

    # --- error analysis (reference variant, test 2026)
    print("[6/6] Analyse d'erreurs (variante de référence) et rapport…", flush=True)
    ref = ev["reference_variant"]
    d = data["test_2026"].copy()
    proba = P[(ref, "test_2026")]
    d["pred"] = classes[proba.argmax(1)]; d["confidence"] = proba.max(1)
    err = d[d["pred"] != d["service"]]
    pairs = (err.groupby(["service", "pred"]).size().sort_values(ascending=False)
             .reset_index(name="n_errors").head(6))
    pairs["share_of_true_service_pct"] = [round(100 * n / (d["service"] == s).sum(), 2)
                                          for s, n in zip(pairs["service"], pairs["n_errors"])]
    pairs.to_csv(rep / "top_confused_pairs.csv", index=False)
    ex_rows = []
    for _, pr in pairs.iterrows():
        sub = err[(err["service"] == pr["service"]) & (err["pred"] == pr["pred"])].sort_values("complaint_id")
        for _, r in sub.head(ev["examples_per_pair"]).iterrows():
            ex_rows.append({"true": r["service"], "pred": r["pred"], "complaint_id": r["complaint_id"],
                            "confidence": round(r["confidence"], 3), "text_300": r[mm[ref]["text_column"]][:300]})
    examples = pd.DataFrame(ex_rows); examples.to_csv(rep / "confused_pair_examples.csv", index=False)
    hc = err[err["confidence"] >= ev["high_confidence"]].sort_values("confidence", ascending=False)
    hc_ex = hc.head(15).assign(text_300=lambda x: x[mm[ref]["text_column"]].str[:300])[
        ["complaint_id", "service", "pred", "confidence", "text_300"]]
    hc_ex.to_csv(rep / "high_confidence_errors.csv", index=False)
    e = data[ext_key].copy(); yt_e = e["service"].map(cidx).to_numpy(); yp_e = P[(ref, ext_key)].argmax(1)
    monthly = pd.DataFrame([{"received_month": m, "n": int((e["received_month"] == m).sum()),
                             "macro_f1": round(macro_f1_int(yt_e[(e["received_month"] == m).to_numpy()],
                                                            yp_e[(e["received_month"] == m).to_numpy()], k), 4)}
                            for m in sorted(e["received_month"].unique())])
    monthly.to_csv(rep / f"monthly_macro_f1_{ext_key}_{ref}.csv", index=False)

    # --- lock + report
    if not rerun:
        write_json(lock_path, {"model_sha256": model_sha, "first_evaluation_utc":
                               datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "test_sha256": man["test"]["sha256"]})
    else:
        lock["reruns"] = lock.get("reruns", []) + [datetime.now(timezone.utc).isoformat(timespec="seconds")]
        write_json(lock_path, lock)
    pc_ref = pc[pc["variant"] == ref].pivot(index="service", columns="dataset", values="recall").reset_index()
    lines = [
        "# Évaluation finale — Phase 3c-ii", "",
        f"Généré le {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC par `src/models/evaluate_final.py`. "
        + ("**Réexécution** avec les mêmes modèles (consignée dans TEST_LOCK.json)." if rerun else
           "**Première évaluation du test** : verrou créé (reports/phase3c/TEST_LOCK.json)."), "",
        f"Variante de référence : `{ref}`. Intervalles : bootstrap percentile, {ev['bootstrap_resamples']} tirages.", "",
        "## 1. Métriques globales", "", md_table(metrics), "",
        "## 2. Écart dû aux noms d'entreprises (as_is − company_masked, bootstrap apparié)", "", md_table(gaps_df), "",
        "Le masquage étant incomplet (décision 3a), cet écart est une borne basse de la dépendance aux noms.", "",
        f"## 3. Rappel par service — `{ref}`", "", md_table(pc_ref), "",
        "Détail précision / rappel / F1 : `reports/phase3c/per_service.csv`.", "",
        "## 4. Calibrage (confiance de la classe prédite)", "", md_table(cal), "",
        f"ECE sur {ev['calibration_bins']} intervalles égaux ; Brier multiclasse. Le LinearSVC a été calibré sur la "
        "validation (Phase 3b). Figure : `reports/figures/phase3c_reliability.png`.", "",
        f"### Table de fiabilité — test_2026, `{ref}`", "", md_table(rel[("test_2026", ref)]), "",
        f"## 5. Matrices de confusion — `{ref}` (lignes = vrai, colonnes = prédit)", "",
    ]
    for ds in ("test_2026", ext_key):
        lines += [f"### {ds}", "", md_table(cms[(ds, ref)].reset_index().rename(columns={"index": "vrai \\ prédit"})), ""]
    lines += [
        f"## 6. Paires les plus confondues — test_2026, `{ref}`", "", md_table(pairs), "",
        f"### Exemples ({ev['examples_per_pair']} par paire, 300 premiers caractères)", "", md_table(examples), "",
        f"## 7. Erreurs à forte confiance (≥ {ev['high_confidence']}) — test_2026, `{ref}`", "",
        f"{len(hc):,} erreurs sur {len(err):,} ({100 * len(hc) / max(len(err), 1):.1f} %). Candidates au bruit "
        "d'étiquetage : à confirmer par lecture, pas par le score.", "", md_table(hc_ex), "",
        f"## 8. Macro-F1 mensuel — {ext_key}, `{ref}`", "", md_table(monthly), "",
        "## 9. Critères de sortie de la 3c-ii", "", "| Critère | Statut |", "|---|---|",
        "| sha256 des données et des modèles vérifiés | OK |",
        f"| Verrou du test respecté ({'réexécution, mêmes modèles' if rerun else 'première évaluation'}) | OK |",
        "| Métriques avec intervalles de confiance (test et externe) | OK |",
        "| Calibrage mesuré | OK |",
        "| Analyse d'erreurs produite | OK |",
        "| Prédictions sauvegardées pour la Phase 5 (data/processed/predictions/) | OK |",
    ]
    (ROOT / "reports" / "phase3c_evaluation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nMÉTRIQUES")
    print(metrics.to_string(index=False))
    print("\nÉCART as_is − company_masked")
    print(gaps_df.to_string(index=False))
    print("\nCALIBRAGE")
    print(cal.to_string(index=False))
    print(f"\nRapport : {ROOT / 'reports' / 'phase3c_evaluation.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
