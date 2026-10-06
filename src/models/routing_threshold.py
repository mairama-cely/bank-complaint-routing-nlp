"""Phase 5 — Routing threshold and business impact (complete phase).

Protocol (fixed in config.yaml before any computation):
  1. Two decision rules are compared on VALIDATION only:
       A calibrated_argmax : class = argmax of calibrated probabilities (model evaluated in Phase 3c)
       B raw_svc_argmax    : class = argmax of the raw LinearSVC scores, confidence = calibrated proba of that class
  2. For each rule, threshold t* = smallest t of the grid whose val precision on auto-routed complaints >= target.
     Selected rule = highest val coverage at t* (tie -> A). Sensitivity targets are reported, not selected.
  3. Selected rule + t* applied ONCE to test 2026 and to external 2025 (bootstrap CIs). A lock
     (reports/phase5/ROUTING_LOCK.json) refuses any later change of rule or threshold.
  4. Business impact for an illustrative monthly volume and assumed triage times.

Outputs: reports/phase5/*.csv, reports/figures/phase5_*.png, reports/phase5_routing.md
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))
from common import ROOT, load_config, read_json, stop, write_json  # noqa: E402
from profile_report import md_table  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(8 * 1024**2), b""):
            h.update(b)
    return h.hexdigest()


def macro_f1(yt, yp, k):
    cm = np.bincount(yt * k + yp, minlength=k * k).reshape(k, k).astype(float)
    tp = np.diag(cm)
    with np.errstate(divide="ignore", invalid="ignore"):
        p = np.where(cm.sum(0) > 0, tp / cm.sum(0), 0.0)
        r = np.where(cm.sum(1) > 0, tp / cm.sum(1), 0.0)
        f = np.where(p + r > 0, 2 * p * r / (p + r), 0.0)
    return float(f.mean())


def curve(conf, correct, grid):
    rows = []
    for t in grid:
        auto = conf >= t
        n = int(auto.sum())
        rows.append({"threshold": round(float(t), 3), "coverage": auto.mean(),
                     "precision": correct[auto].mean() if n else np.nan, "n_auto": n})
    return pd.DataFrame(rows)


def pick(cv: pd.DataFrame, target: float):
    ok = cv[(cv["n_auto"] > 0) & (cv["precision"] >= target)]
    return None if ok.empty else ok.iloc[0]          # grid ascending -> smallest t -> max coverage


def main() -> int:
    cfg = load_config()
    p3, p5 = cfg.get("phase3", {}), cfg.get("phase5")
    if not p5:
        stop("Section phase5 absente de config.yaml.")
    proc, models_dir = ROOT / "data" / "processed", ROOT / "models"
    rep = ROOT / "reports" / "phase5"; rep.mkdir(parents=True, exist_ok=True)
    fig_dir = ROOT / cfg["paths"]["figures"]; fig_dir.mkdir(parents=True, exist_ok=True)

    print("[1/6] Contrôles d'intégrité…", flush=True)
    man, mman, eman = (read_json(proc / n) for n in ("MANIFEST.json", "MANIFEST_company_masked.json",
                                                      "MANIFEST_external.json"))
    mm = read_json(models_dir / "MANIFEST_models.json")
    lock3 = read_json(ROOT / "reports" / "phase3c" / "TEST_LOCK.json")
    if None in (man, mman, eman, mm, lock3):
        stop("Manifeste ou verrou de la Phase 3c absent : la Phase 3 doit être close.")
    ref = p5["reference_variant"]
    mpath = models_dir / mm[ref]["file"]
    if sha256(mpath) != mm[ref]["sha256"] or lock3["model_sha256"][ref] != mm[ref]["sha256"]:
        stop("Le modèle de référence diffère de celui évalué et verrouillé en Phase 3c.")
    for name in ("val", "test"):
        if sha256(proc / f"{name}.parquet") != man[name]["sha256"]:
            stop(f"{name}.parquet ne correspond pas à son sha256.")
    for m in (mman, eman):
        if sha256(proc / m["file"]) != m["sha256"]:
            stop(f"{m['file']} ne correspond pas à son sha256.")

    print("[2/6] Chargement des textes et du modèle…", flush=True)
    col = mm[ref]["text_column"]
    masked = pd.read_parquet(proc / mman["file"], columns=["complaint_id", "text_company_masked"])
    def load(name):
        d = pd.read_parquet(proc / f"{name}.parquet", columns=["complaint_id", "service", "text_clean"])
        return d.merge(masked, on="complaint_id", how="left", validate="one_to_one")
    ext_key = f"external_{eman['label']}"
    data = {"val_2026": load("val"), "test_2026": load("test"),
            ext_key: pd.read_parquet(proc / eman["file"], columns=["complaint_id", "service", "text_clean",
                                                                  "text_company_masked"])}
    pipe = joblib.load(mpath)
    vec, clf = pipe.named_steps["tfidf"], pipe.named_steps["clf"]
    classes = np.array(clf.classes_); k = len(classes); cidx = {c: i for i, c in enumerate(classes)}
    raw_svc = None
    if hasattr(clf, "calibrated_classifiers_"):
        est = clf.calibrated_classifiers_[0].estimator
        raw_svc = getattr(est, "estimator", est)          # FrozenEstimator -> LinearSVC
    rules = [r for r in p5["decision_rules"] if r == "calibrated_argmax" or raw_svc is not None]

    print("[3/6] Scores (probabilités calibrées et scores bruts)…", flush=True)
    S = {}
    for ds, d in data.items():
        X = vec.transform(d[col])
        proba = clf.predict_proba(X)
        saved = pd.read_parquet(proc / "predictions" / f"{ds}_{ref}.parquet")
        if not (saved["complaint_id"].to_numpy() == d["complaint_id"].to_numpy()).all() or \
                np.abs(saved[[f"p_{c}" for c in classes]].to_numpy() - proba).max() > 1e-6:
            stop(f"{ds} : probabilités différentes de celles sauvegardées en Phase 3c.")
        yt = d["service"].map(cidx).to_numpy()
        S[ds] = {"yt": yt, "proba": proba, "raw": raw_svc.decision_function(X) if raw_svc is not None else None}

    def decide(ds, rule):
        s = S[ds]
        pred = s["proba"].argmax(1) if rule == "calibrated_argmax" else s["raw"].argmax(1)
        conf = s["proba"][np.arange(len(pred)), pred]
        return pred, conf

    print("[4/6] Sélection de la règle et du seuil sur la validation…", flush=True)
    g = p5["threshold_grid"]
    grid = np.round(np.arange(g["start"], g["stop"] + 1e-9, g["step"]), 3)
    targets = [p5["target_precision"]] + list(p5["sensitivity_precisions"])
    sel_rows, curves = [], {}
    for rule in rules:
        pred, conf = decide("val_2026", rule)
        correct = pred == S["val_2026"]["yt"]
        cv = curve(conf, correct, grid); curves[("val_2026", rule)] = cv
        cv.to_csv(rep / f"curve_val_2026_{rule}.csv", index=False)
        for tp in targets:
            pk = pick(cv, tp)
            sel_rows.append({"rule": rule, "target_precision": tp,
                             "threshold": None if pk is None else pk["threshold"],
                             "val_coverage": None if pk is None else round(pk["coverage"], 4),
                             "val_precision": None if pk is None else round(pk["precision"], 4),
                             "val_macro_f1_no_threshold": round(macro_f1(S["val_2026"]["yt"], pred, k), 4)})
    sel = pd.DataFrame(sel_rows); sel.to_csv(rep / "val_selection.csv", index=False)
    main_t = sel[sel["target_precision"] == p5["target_precision"]].dropna(subset=["threshold"])
    if main_t.empty:
        stop(f"Aucune règle n'atteint {p5['target_precision']} de précision sur la validation.")
    best = main_t.sort_values(["val_coverage", "rule"], ascending=[False, True]).iloc[0]
    if (main_t["val_coverage"] == best["val_coverage"]).sum() > 1:
        best = main_t[main_t["rule"] == "calibrated_argmax"].iloc[0]
    rule, t_star = best["rule"], float(best["threshold"])

    lock_path = rep / "ROUTING_LOCK.json"
    lock = read_json(lock_path)
    if lock is not None and (lock["rule"] != rule or abs(lock["threshold"] - t_star) > 1e-9
                             or lock["model_sha256"] != mm[ref]["sha256"]):
        stop(f"Règle ou seuil différents de ceux verrouillés ({lock['rule']}, {lock['threshold']}) : refusé.")

    print(f"[5/6] Application unique : règle {rule}, seuil {t_star} (test 2026 et {ext_key})…", flush=True)
    rng = np.random.default_rng(p3.get("random_state", 42))
    B = p5["bootstrap_resamples"]
    res_rows, per_service, impact = [], [], []
    for ds in ("val_2026", "test_2026", ext_key):
        pred, conf = decide(ds, rule); yt = S[ds]["yt"]
        auto = conf >= t_star; correct = pred == yt
        cov, prec = auto.mean(), correct[auto].mean()
        bc, bp = np.empty(B), np.empty(B)
        for b in range(B):
            i = rng.integers(0, len(yt), len(yt))
            a = auto[i]; bc[b] = a.mean(); bp[b] = correct[i][a].mean()
        res_rows.append({"dataset": ds, "n": len(yt), "coverage": round(cov, 4),
                         "coverage_ci95": f"[{np.percentile(bc, 2.5):.4f} ; {np.percentile(bc, 97.5):.4f}]",
                         "precision_auto": round(prec, 4),
                         "precision_ci95": f"[{np.percentile(bp, 2.5):.4f} ; {np.percentile(bp, 97.5):.4f}]",
                         "macro_f1_no_threshold": round(macro_f1(yt, pred, k), 4),
                         "accuracy_human_queue_if_model_kept": round(correct[~auto].mean(), 4) if (~auto).any() else None})
        for i, c in enumerate(classes):
            m_true = yt == i
            per_service.append({"dataset": ds, "service": c,
                                "share_auto_routed_pct": round(100 * auto[m_true].mean(), 2),
                                "precision_auto_pred_as_service": round(correct[auto & (pred == i)].mean(), 4)
                                if (auto & (pred == i)).any() else None,
                                "n_true": int(m_true.sum())})
        cv = curve(conf, correct, grid); curves[(ds, rule)] = cv
        cv.to_csv(rep / f"curve_{ds}_{rule}.csv", index=False)
    res = pd.DataFrame(res_rows); res.to_csv(rep / "routing_results.csv", index=False)
    ps = pd.DataFrame(per_service); ps.to_csv(rep / "routing_per_service.csv", index=False)

    vol = p5["volume_per_month"]
    for ds in ("test_2026", ext_key):
        r = res[res["dataset"] == ds].iloc[0]
        for m in p5["triage_minutes"]:
            impact.append({"dataset": ds, "triage_minutes_assumed": m,
                           "auto_routed_per_month": round(vol * r["coverage"]),
                           "human_review_per_month": round(vol * (1 - r["coverage"])),
                           "misrouted_auto_per_month": round(vol * r["coverage"] * (1 - r["precision_auto"])),
                           "triage_hours_saved_per_month": round(vol * r["coverage"] * m / 60, 1)})
    imp = pd.DataFrame(impact); imp.to_csv(rep / "business_impact.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 5))
    for (ds, rl), cv in curves.items():
        if rl != rule and ds != "val_2026":
            continue
        ax.plot(cv["coverage"], cv["precision"], label=f"{ds} — {rl}")
    ax.axhline(p5["target_precision"], ls="--", color="grey", lw=1)
    ax.set_xlabel("Couverture (part routée automatiquement)"); ax.set_ylabel("Précision des routages automatiques")
    ax.set_title(f"Couverture vs précision (seuil retenu {t_star}, règle {rule})"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(fig_dir / "phase5_coverage_precision.png", dpi=150); plt.close(fig)

    print("[6/6] Verrou et rapport…", flush=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if lock is None:
        write_json(lock_path, {"rule": rule, "threshold": t_star, "model_sha256": mm[ref]["sha256"],
                               "target_precision": p5["target_precision"], "created_utc": now})
        lock_note = "Première application : verrou créé (reports/phase5/ROUTING_LOCK.json)."
    else:
        lock["reruns"] = lock.get("reruns", []) + [now]; write_json(lock_path, lock)
        lock_note = "Réexécution avec la même règle et le même seuil (consignée)."
    lines = [
        "# Seuil de routage et impact métier — Phase 5", "",
        f"Généré le {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC par `src/models/routing_threshold.py`. {lock_note}", "",
        f"Modèle : `{ref}` (verrouillé en Phase 3c). Protocole fixé avant calcul (config.yaml, section phase5).", "",
        "## 1. Sélection sur la validation", "",
        "Règles : `calibrated_argmax` (A, modèle évalué en 3c) ; `raw_svc_argmax` (B, classe du SVC brut, confiance "
        "= probabilité calibrée de cette classe). Seuil = plus petit seuil atteignant la précision cible.", "",
        md_table(sel), "",
        f"**Règle retenue : `{rule}` ; seuil : {t_star}** (couverture val maximale à précision ≥ "
        f"{p5['target_precision']}). Le rappel de Transferts sous la règle A avait déjà été vu sur le test (3c) : "
        "le choix est donc fait par ce critère mécanique, fixé à l'avance.", "",
        "## 2. Application unique (bootstrap 95 %)", "", md_table(res), "",
        "`accuracy_human_queue_if_model_kept` : exactitude qu'aurait eue le modèle sur les réclamations envoyées en "
        "revue humaine (montre ce que le seuil évite).", "",
        "## 3. Par service", "", md_table(ps[ps["dataset"] != "val_2026"]), "",
        "## 4. Impact métier (illustratif)", "",
        f"Volume **illustratif** de {vol:,} réclamations par mois (pas un chiffre Afriland). Temps de tri manuel "
        "**supposé** (hypothèse du cadrage, non mesurée). Aucun coût de réacheminement n'est chiffré : seul le nombre "
        "de réclamations mal routées est donné ; le taux d'erreur du tri manuel actuel n'est pas connu.", "",
        md_table(imp), "",
        "Figure : `reports/figures/phase5_coverage_precision.png`.", "",
        "## 5. Critères de sortie de la Phase 5", "", "| Critère | Statut |", "|---|---|",
        "| Modèle identique à celui verrouillé en 3c ; données et probabilités vérifiées | OK |",
        "| Règle et seuil choisis sur la validation uniquement, par critère fixé à l'avance | OK |",
        f"| Précision cible atteinte sur le test (≥ {p5['target_precision']}) | "
        f"{'OK' if res.loc[res['dataset'] == 'test_2026', 'precision_auto'].iloc[0] >= p5['target_precision'] else 'KO — voir intervalle'} |",
        f"| Précision cible atteinte sur {ext_key} | "
        f"{'OK' if res.loc[res['dataset'] == ext_key, 'precision_auto'].iloc[0] >= p5['target_precision'] else 'KO — voir intervalle'} |",
        "| Impact métier calculé avec hypothèses explicites | OK |",
        "| Verrou de routage enregistré | OK |",
    ]
    (ROOT / "reports" / "phase5_routing.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nSÉLECTION (val)")
    print(sel.to_string(index=False))
    print(f"\nRègle retenue : {rule} ; seuil : {t_star}")
    print("\nAPPLICATION")
    print(res.to_string(index=False))
    print(f"\nRapport : {ROOT / 'reports' / 'phase5_routing.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
