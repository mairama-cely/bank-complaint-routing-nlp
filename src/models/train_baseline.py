"""Phase 3b — TF-IDF baselines, hyper-parameter selection on the VALIDATION set only.

Variants : as_is (text_clean) and company_masked (text_company_masked, Phase 3a).
Models   : LogisticRegression (lbfgs, multinomial) and LinearSVC; grid on C and class_weight.
Selection: best macro-F1 on val, per variant. If the winner is LinearSVC, it is calibrated (sigmoid) on val
           so that Phase 5 gets probabilities (calibration quality is assessed in 3c on test).
The test split is never read by this script.

Outputs: models/<variant>_best.joblib, models/MANIFEST_models.json, reports/phase3b/*.csv,
         reports/phase3b_selection.md
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))
from common import ROOT, load_config, read_json, stop, write_json  # noqa: E402
from profile_report import md_table  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(8 * 1024**2), b""):
            h.update(b)
    return h.hexdigest()


def top2_accuracy(scores: np.ndarray, y: np.ndarray, classes: np.ndarray) -> float:
    top2 = classes[np.argsort(-scores, axis=1)[:, :2]]
    return float(np.mean((top2 == y[:, None]).any(axis=1)))


def load_split(name: str, proc: Path, manifest: dict, masked: pd.DataFrame) -> pd.DataFrame:
    path = proc / f"{name}.parquet"
    if sha256(path) != manifest[name]["sha256"]:
        stop(f"{path.name} ne correspond pas au sha256 de MANIFEST.json.")
    df = pd.read_parquet(path, columns=["complaint_id", "service", "text_clean"])
    df = df.merge(masked[["complaint_id", "text_company_masked"]], on="complaint_id", how="left", validate="one_to_one")
    if df["text_company_masked"].isna().any():
        stop(f"{name} : textes masqués manquants après jointure.")
    return df


def main() -> int:
    t_start = time.time()
    cfg = load_config()
    p3 = cfg.get("phase3")
    if not p3 or "tfidf" not in p3 or "grid" not in p3:
        stop("phase3.tfidf ou phase3.grid absent de config.yaml.")
    proc = ROOT / "data" / "processed"
    manifest = read_json(proc / "MANIFEST.json")
    mman = read_json(proc / "MANIFEST_company_masked.json")
    if manifest is None or mman is None:
        stop("Manifeste de la Phase 2b ou de la Phase 3a absent.")
    if sha256(proc / mman["file"]) != mman["sha256"] or mman["_source_sha256"] != manifest["all"]["sha256"]:
        stop("company_masked.parquet incohérent avec son manifeste ou avec la Phase 2b.")

    print("[1/4] Chargement de train et val (sha256 vérifiés ; test non lu)…", flush=True)
    masked = pd.read_parquet(proc / mman["file"], columns=["complaint_id", "text_company_masked"])
    train = load_split("train", proc, manifest, masked)
    val = load_split("val", proc, manifest, masked)
    y_tr, y_va = train["service"].to_numpy(), val["service"].to_numpy()
    classes = np.array(sorted(np.unique(y_tr)))

    tf = p3["tfidf"]; grid = p3["grid"]; rs = p3["random_state"]
    variants = {"as_is": "text_clean", "company_masked": "text_company_masked"}
    rows, fitted = [], {}
    n_fits = len(variants) * (len(grid["logreg_C"]) + len(grid["linear_svc_C"])) * len(grid["class_weight"])
    k = 0
    for variant, col in variants.items():
        print(f"[2/4] Variante {variant} : TF-IDF ajusté sur train…", flush=True)
        t0 = time.time()
        vec = TfidfVectorizer(lowercase=True, ngram_range=tuple(tf["ngram_range"]), min_df=tf["min_df"],
                              max_df=tf["max_df"], max_features=tf["max_features"],
                              sublinear_tf=tf["sublinear_tf"], token_pattern=tf["token_pattern"], dtype=np.float32)
        X_tr = vec.fit_transform(train[col]); X_va = vec.transform(val[col])
        print(f"      vocabulaire : {len(vec.vocabulary_):,} termes ({time.time() - t0:.0f} s)", flush=True)
        for model_name, Cs in (("logreg", grid["logreg_C"]), ("linear_svc", grid["linear_svc_C"])):
            for C in Cs:
                for cw in grid["class_weight"]:
                    k += 1
                    t0 = time.time()
                    if model_name == "logreg":
                        clf = LogisticRegression(C=C, class_weight=cw, max_iter=3000, random_state=rs)
                    else:
                        clf = LinearSVC(C=C, class_weight=cw, random_state=rs, max_iter=5000)
                    clf.fit(X_tr, y_tr)
                    scores = clf.predict_proba(X_va) if model_name == "logreg" else clf.decision_function(X_va)
                    pred = clf.classes_[np.argmax(scores, axis=1)]
                    assert list(clf.classes_) == list(classes)
                    rec = recall_score(y_va, pred, labels=classes, average=None)
                    row = {"variant": variant, "model": model_name, "C": C, "class_weight": cw or "none",
                           "val_macro_f1": round(f1_score(y_va, pred, average="macro"), 4),
                           "val_accuracy": round(accuracy_score(y_va, pred), 4),
                           "val_top2_accuracy": round(top2_accuracy(scores, y_va, clf.classes_), 4),
                           "val_min_recall": round(float(rec.min()), 4),
                           "fit_seconds": round(time.time() - t0, 1)}
                    row.update({f"recall_{c}": round(float(r), 4) for c, r in zip(classes, rec)})
                    rows.append(row)
                    fitted[(variant, model_name, C, cw)] = (vec, clf)
                    print(f"      [{k}/{n_fits}] {model_name} C={C} cw={cw or 'none'} -> macro-F1 "
                          f"{row['val_macro_f1']:.4f} ({row['fit_seconds']} s)", flush=True)
        # keep memory bounded: drop non-best fits of this variant once done
        best_v = max((r for r in rows if r["variant"] == variant), key=lambda r: r["val_macro_f1"])
        for key in [kk for kk in fitted if kk[0] == variant]:
            if not (key[1] == best_v["model"] and key[2] == best_v["C"]
                    and (key[3] or "none") == best_v["class_weight"]):
                del fitted[key]

    res = pd.DataFrame(rows)
    rep = ROOT / "reports" / "phase3b"; rep.mkdir(parents=True, exist_ok=True)
    res.to_csv(rep / "grid_results.csv", index=False)

    print("[3/4] Sélection, calibrage éventuel et sauvegarde…", flush=True)
    models_dir = ROOT / "models"; models_dir.mkdir(exist_ok=True)
    best_rows, cms, mman_out = [], {}, {}
    for variant, col in variants.items():
        b = res[res["variant"] == variant].sort_values(["val_macro_f1", "val_top2_accuracy"], ascending=False).iloc[0]
        cw = None if b["class_weight"] == "none" else b["class_weight"]
        vec, clf = fitted[(variant, b["model"], b["C"], cw)]
        X_va = vec.transform(val[col])
        calibrated = False
        if b["model"] == "linear_svc":
            clf = CalibratedClassifierCV(FrozenEstimator(clf), method="sigmoid").fit(X_va, y_va)
            calibrated = True
        pipe = Pipeline([("tfidf", vec), ("clf", clf)])
        path = models_dir / f"{variant}_best.joblib"
        joblib.dump(pipe, path)
        pred = pipe.predict(val[col])
        cms[variant] = pd.DataFrame(confusion_matrix(y_va, pred, labels=classes), index=classes, columns=classes)
        cms[variant].to_csv(rep / f"confusion_val_{variant}.csv")
        mman_out[variant] = {"file": path.name, "sha256": sha256(path), "model": b["model"], "C": float(b["C"]),
                             "class_weight": b["class_weight"], "calibrated_on_val": calibrated,
                             "text_column": col, "val_macro_f1": float(b["val_macro_f1"])}
        best_rows.append({"variant": variant, "model": b["model"], "C": b["C"], "class_weight": b["class_weight"],
                          "calibrated_on_val": calibrated, "val_macro_f1": b["val_macro_f1"],
                          "val_accuracy": b["val_accuracy"], "val_top2_accuracy": b["val_top2_accuracy"],
                          "val_min_recall": b["val_min_recall"]})
    mman_out["_created_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    mman_out["_sklearn"] = sklearn.__version__
    mman_out["_data_sha256"] = {"train": manifest["train"]["sha256"], "val": manifest["val"]["sha256"],
                                "company_masked": mman["sha256"]}
    write_json(models_dir / "MANIFEST_models.json", mman_out)
    best = pd.DataFrame(best_rows)
    best.to_csv(rep / "best_by_variant.csv", index=False)
    gap = float(best.set_index("variant").loc["as_is", "val_macro_f1"]
                - best.set_index("variant").loc["company_masked", "val_macro_f1"])

    print("[4/4] Rapport…", flush=True)
    rec_cols = ["variant"] + [c for c in res.columns if c.startswith("recall_")]
    best_rec = res.loc[res.groupby("variant")["val_macro_f1"].idxmax(), rec_cols]
    checklist = [
        ("Jeu de test non lu (aucune lecture de test.parquet dans ce script)", "OK"),
        ("sha256 de train, val et company_masked vérifiés", "OK"),
        (f"Grille complète exécutée ({n_fits} ajustements)", "OK" if len(res) == n_fits else "KO"),
        ("Meilleur modèle par variante sauvegardé avec sha256 (models/MANIFEST_models.json)", "OK"),
        ("Probabilités disponibles pour la Phase 5 (régression logistique ou LinearSVC calibré)", "OK"),
    ]
    lines = [
        "# Baselines TF-IDF — sélection sur la validation (Phase 3b)", "",
        f"Généré le {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC par `src/models/train_baseline.py` "
        f"(scikit-learn {sklearn.__version__}, durée {time.time() - t_start:.0f} s). **Le jeu de test n'a pas été lu.**", "",
        f"Train : {len(train):,} ; val : {len(val):,}. TF-IDF ajusté sur train uniquement : {tf}.", "",
        "## 1. Meilleur modèle par variante (val)", "", md_table(best), "",
        f"Écart de macro-F1 val (as_is − company_masked) : **{gap:+.4f}**. Mesure préliminaire sur val ; "
        "la mesure retenue sera celle du test (Phase 3c). Le masquage étant incomplet (marques absentes de la "
        "colonne Company non masquées, décision 3a), cet écart est une **borne basse** de la dépendance aux noms "
        "d'entreprises.", "",
        "## 2. Rappel par service du meilleur modèle (val)", "", md_table(best_rec), "",
        "## 3. Grille complète (val)", "",
        md_table(res[["variant", "model", "C", "class_weight", "val_macro_f1", "val_accuracy", "val_top2_accuracy",
                      "val_min_recall", "fit_seconds"]], max_rows=100), "",
        "## 4. Matrices de confusion du meilleur modèle (val ; lignes = vrai service, colonnes = prédit)", "",
    ]
    for v, cm_df in cms.items():
        lines += [f"### {v}", "", md_table(cm_df.reset_index().rename(columns={"index": "vrai \\ prédit"})), ""]
    lines += ["## 5. Critères de sortie de la Phase 3b", "", "| Critère | Statut |", "|---|---|"]
    lines += [f"| {c} | {s} |" for c, s in checklist]
    lines += ["", "Note : si un LinearSVC est retenu, il est calibré sur la validation, qui a aussi servi à la "
              "sélection ; la qualité du calibrage sera mesurée sur le test en Phase 3c."]
    (ROOT / "reports" / "phase3b_selection.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nMEILLEUR MODÈLE PAR VARIANTE (val)")
    print(best.to_string(index=False))
    print(f"\nÉcart macro-F1 (as_is − company_masked) : {gap:+.4f}")
    print(f"Rapport : {ROOT / 'reports' / 'phase3b_selection.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
