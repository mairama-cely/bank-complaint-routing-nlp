"""Generate the 9 project notebooks (00-08) with the same structure as the portfolio's refugee project.

Structure of every notebook: title cell "# NN_Name — Subtitle", working-directory cell (moves to the project root),
imports cell ending with "✓ Libraries loaded", numbered sections, text outputs via print(), figures saved to
output/NN_<name>.png (dpi 300) followed by "✓ Saved: ...", empty last cell.

The notebooks READ the artefacts produced by the pipeline scripts (src/...). They never retrain a model nor
re-evaluate the test set (locks in reports/phase3c and reports/phase5 stay untouched).

Usage (from the project root):  python scripts/create_notebooks.py
"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB_DIR = ROOT / "notebooks"

WD = """import os
if 'notebooks' in os.getcwd():
    os.chdir('..')
os.makedirs('output', exist_ok=True)
print(f'Working directory: {os.getcwd()}')"""

IMPORTS = """import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
plt.style.use('seaborn-v0_8-whitegrid')
pd.set_option('display.width', 200)
print('✓ Libraries loaded')"""


def save(name: str) -> str:
    return (f"plt.tight_layout()\nplt.savefig('output/{name}', dpi=300, bbox_inches='tight')\n"
            f"plt.show()\nprint('✓ Saved: {name}')")


def build(fname: str, title: str, cells: list[tuple[str, str]]) -> None:
    nb = nbf.v4.new_notebook()
    nb["cells"] = [nbf.v4.new_markdown_cell(title), nbf.v4.new_code_cell(WD), nbf.v4.new_code_cell(IMPORTS)]
    for kind, src in cells:
        nb["cells"].append(nbf.v4.new_markdown_cell(src) if kind == "md" else nbf.v4.new_code_cell(src))
    nb["cells"].append(nbf.v4.new_code_cell(""))
    nb["metadata"]["kernelspec"] = {"display_name": "Python 3 (ipykernel)", "language": "python", "name": "python3"}
    for c in nb["cells"]:
        c.pop("id", None)
    nb.nbformat_minor = 4
    nbf.write(nb, NB_DIR / fname)
    print(f"✓ {fname} ({len(nb['cells'])} cells)")


# ---------------------------------------------------------------- 00
build("00_Data_Acquisition.ipynb",
      "# 00_Data_Acquisition — CFPB Narratives Archive\n\n**Objectif:** Load & validate source files, manifests and integrity of the frozen datasets",
      [
("code", """probe = pd.read_csv('reports/source_probe.csv')
inv = pd.read_csv('reports/local_inventory.csv')
print(f'✓ Source URLs probed: {len(probe)} (HTTP 200: {(probe["http_status"].astype(str) == "200").sum()})')
print(f'✓ Local CSV files: {int(inv["present"].sum())}/21 — {inv.loc[inv["present"], "size_mb"].astype(float).sum() / 1024:.2f} GB')
sel = inv[inv['selected']]
print(f'Selected exports (2026): {sel["id"].tolist()} — {sel["size_mb"].astype(float).sum() / 1024:.2f} GB')"""),
("md", "## 1. Selected Exports"),
("code", """print(sel[['id', 'file', 'size_mb', 'detected_format', 'n_header_fields']].to_string(index=False))"""),
("md", "## 2. Schema"),
("code", """cols = json.load(open('data/interim/columns.json', encoding='utf-8'))
print('Original -> normalised column names:')
for o, n in cols['original_to_normalized'].items():
    print(f'  {o:<35} -> {n}')
print('\\nKey columns:', cols['keys'])
print(f"Rows loaded (2026): {cols['n_rows_all']:,} | with narrative: {cols['n_rows_with_narrative']:,}")"""),
("md", "## 3. Integrity of the Frozen Datasets (sha256)"),
("code", """import hashlib
def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(8 * 1024**2), b''):
            h.update(b)
    return h.hexdigest()

man = json.load(open('data/processed/MANIFEST.json', encoding='utf-8'))
for name in ('all', 'train', 'val', 'test'):
    ok = sha256(f"data/processed/{man[name]['file']}") == man[name]['sha256']
    print(f"{'✓' if ok else '✗'} {man[name]['file']:<28} rows={man[name]['rows']:>7,}  sha256 {'OK' if ok else 'MISMATCH'}")"""),
("md", "## 4. CSV Reading Check (strict sequential mode vs Phase 1)"),
("code", """print(open('reports/csv_parsing_check.md', encoding='utf-8').read())"""),
      ])

# ---------------------------------------------------------------- 01
build("01_EDA.ipynb", "# 01_EDA — Profiling of the 2026 Exports", [
("code", """T = {q: pd.read_csv(f'reports/tables/{q}.csv') for q in
     ['Q1', 'Q2_global', 'Q2_by_export', 'Q2_by_product', 'Q3', 'Q4_product', 'Q5_across_exports',
      'Q5_within_export', 'Q6', 'Q6b', 'Q7', 'Q8', 'Q9']}
g = T['Q2_global'].iloc[0]
print(f"Rows: {int(g['n_rows']):,} | with narrative: {int(g['n_with_narrative']):,} ({g['pct_with_narrative']}%)")"""),
("md", "## 1. Volume per Export"),
("code", """print(T['Q1'].merge(T['Q2_by_export'][['source_export_id', 'n_with_narrative', 'pct_with_narrative']],
                     on='source_export_id').to_string(index=False))"""),
("code", """d = T['Q2_by_export']
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(d['source_export_id'].astype(str), d['n_with_narrative'], color='steelblue', edgecolor='black')
ax.set_title('Narratives per Export (2026)', fontsize=12, fontweight='bold')
ax.set_xlabel('Export'); ax.set_ylabel('Narratives')
""" + save("01_narratives_per_export.png")),
("md", "## 2. Narrative Rate by Product"),
("code", """d = T['Q2_by_product'].sort_values('pct_with_narrative')
print(d.to_string(index=False))
fig, ax = plt.subplots(figsize=(10, 6))
ax.barh(d['product'], d['pct_with_narrative'], color='coral')
ax.set_title('Share of Complaints with a Narrative, by Product', fontsize=12, fontweight='bold')
ax.set_xlabel('% with narrative')
""" + save("01_narrative_rate_by_product.png")),
("md", "## 3. Taxonomy Stability (Product × Month)"),
("code", """pivot = T['Q3'].pivot_table(index='product', columns='received_month', values='n_narratives', fill_value=0)
print(pivot.to_string())
fig, ax = plt.subplots(figsize=(12, 6))
im = ax.imshow(pivot.values, aspect='auto', cmap='viridis')
ax.set_xticks(range(pivot.shape[1]), pivot.columns, rotation=90)
ax.set_yticks(range(pivot.shape[0]), pivot.index)
fig.colorbar(im, ax=ax, label='Narratives')
ax.set_title('Narratives by Product and Month', fontsize=12, fontweight='bold')
""" + save("01_product_month_heatmap.png")),
("md", "## 4. Duplicates"),
("code", """print(f"Complaint ids in several exports: {int(T['Q5_across_exports'].iloc[0, 0]):,}")
print(f"Duplicated ids within an export: {int(T['Q5_within_export']['n_duplicated_ids'].sum()):,}")
print(f"Identical narratives: {int(T['Q6']['n_texts_duplicated'].iloc[0]):,} texts on {int(T['Q6']['n_rows_involved'].iloc[0]):,} rows")
print(f"  of which with different products: {int(T['Q6b']['n_texts_multi_product'].iloc[0]):,} texts on {int(T['Q6b']['n_rows_involved'].iloc[0]):,} rows")"""),
("md", "## 5. Narrative Length & Masks"),
("code", """print('Words per narrative:'); print(T['Q7'].to_string(index=False))
print('\\nMasks (XXXX):'); print(T['Q8'].to_string(index=False))"""),
("code", """import duckdb
narr = json.load(open('data/interim/columns.json', encoding='utf-8'))['keys']['narrative']
words = duckdb.sql(f\"\"\"SELECT len(string_split(trim(regexp_replace("{narr}", '\\\\s+', ' ', 'g')), ' ')) AS n
                      FROM read_parquet('data/interim/complaints_with_narrative.parquet')\"\"\").df()['n']
fig, ax = plt.subplots(figsize=(10, 5))
ax.hist(words, bins=100, color='steelblue', edgecolor='black')
ax.set_xscale('log')
ax.set_title('Narrative Length (words, log scale)', fontsize=12, fontweight='bold')
ax.set_xlabel('Words'); ax.set_ylabel('Narratives')
""" + save("01_narrative_length_hist.png")),
("md", "## 6. Excluded Product & Frozen Mapping"),
("code", """import yaml
print(T['Q9'].to_string(index=False))
mapping = yaml.safe_load(open('config/label_mapping.yaml', encoding='utf-8'))
print(f"\\nMapping status: {mapping['status']} (frozen on {mapping['frozen_on']})")
for p, s in mapping['product_to_service'].items():
    print(f'  {p:<60} -> {s}')"""),
])

# ---------------------------------------------------------------- 02
build("02_Data_Cleaning.ipynb", "# 02_Data_Cleaning — Text Audit, Cleaning Rules, Deduplication & Split", [
("code", """A = {n: pd.read_csv(f'reports/phase2a/{n}.csv') for n in
     ['A1_date_shapes', 'A3_brace_shapes', 'A4_pattern_coverage', 'A5_length_by_service', 'A7_dedup_preview',
      'A9c_artifact_coverage']}
rules = pd.read_csv('reports/phase2b/rules_counts.csv')
split = pd.read_csv('reports/phase2b/split_by_service.csv')
man = json.load(open('data/processed/MANIFEST.json', encoding='utf-8'))
print(f"Scope (Jan–Jul 2026, frozen mapping): {int(A['A7_dedup_preview']['n_rows_scope'].iloc[0]):,} narratives")"""),
("md", "## 1. Text Audit (masks, dates, amounts, artefacts)"),
("code", """print('Pattern coverage (%):'); print(A['A4_pattern_coverage'].to_string(index=False))
print('\\nDate shapes (top 5):'); print(A['A1_date_shapes'].head().to_string(index=False))
print('\\nBrace shapes (top 5):'); print(A['A3_brace_shapes'].head().to_string(index=False))
print('\\nArtefacts:'); print(A['A9c_artifact_coverage'].to_string(index=False))"""),
("md", "## 2. Cleaning Rules R1–R8"),
("code", """print(rules.to_string(index=False))
fig, ax = plt.subplots(figsize=(10, 5))
ax.barh(rules['rule'][::-1], rules['n_narratives'][::-1], color='coral')
ax.set_title('Narratives Modified per Cleaning Rule', fontsize=12, fontweight='bold')
ax.set_xlabel('Narratives')
""" + save("02_cleaning_rules.png")),
("md", "## 3. Deduplication Funnel"),
("code", """scope = int(A['A7_dedup_preview']['n_rows_scope'].iloc[0])
r8 = int(rules.loc[rules['rule'] == 'R8_dropped_no_letter', 'n_narratives'].iloc[0])
final = man['all']['rows']
funnel = pd.DataFrame({'step': ['Scope', 'After R8 (no letter)', 'After dedup on cleaned text'],
                       'rows': [scope, scope - r8, final]})
print(funnel.to_string(index=False))
print(f'\\nRemoved by deduplication: {scope - r8 - final:,}')"""),
("md", "## 4. Stratified Split 70/15/15"),
("code", """split['train_pct'] = (100 * split['train'] / split['total']).round(2)
split['val_pct'] = (100 * split['val'] / split['total']).round(2)
split['test_pct'] = (100 * split['test'] / split['total']).round(2)
print(split.to_string(index=False))
fig, ax = plt.subplots(figsize=(10, 5))
bottom = np.zeros(len(split))
for col, color in [('train', 'steelblue'), ('val', 'orange'), ('test', 'seagreen')]:
    ax.barh(split['service'], split[col], left=bottom, color=color, label=col)
    bottom += split[col].to_numpy()
ax.set_title('Train / Validation / Test by Service', fontsize=12, fontweight='bold')
ax.set_xlabel('Narratives'); ax.legend()
""" + save("02_split_by_service.png")),
("md", "## 5. Language Check (heuristic, no filtering)"),
("code", """print(pd.read_csv('reports/phase2b/language_by_service.csv').to_string(index=False))
print('\\nNote: unvalidated stopword heuristic — flags are hints, not labels.')"""),
])

# ---------------------------------------------------------------- 03
build("03_Text_Exploration.ipynb", "# 03_Text_Exploration — Train Set Only", [
("code", """import hashlib, re
from collections import Counter
import yaml
cfg = yaml.safe_load(open('config/config.yaml', encoding='utf-8'))
man = json.load(open('data/processed/MANIFEST.json', encoding='utf-8'))
h = hashlib.sha256()
with open('data/processed/train.parquet', 'rb') as f:
    for b in iter(lambda: f.read(8 * 1024**2), b''):
        h.update(b)
assert h.hexdigest() == man['train']['sha256'], 'train.parquet modified since Phase 2b'
train = pd.read_parquet('data/processed/train.parquet')
assert set(train['split']) == {'train'}
SERVICES = sorted(train['service'].unique())
print(f'✓ Loaded train: {train.shape} (sha256 OK)')"""),
("md", "## 1. Distribution & Length by Service"),
("code", """dist = train.groupby('service').agg(n=('complaint_id', 'size'), median_words=('n_words_clean', 'median'))
dist['share_pct'] = (100 * dist['n'] / dist['n'].sum()).round(2)
dist = dist.sort_values('n', ascending=False)
print(dist.to_string())
order = dist.index.tolist()
fig, ax = plt.subplots(figsize=(10, 5))
ax.boxplot([train.loc[train['service'] == s, 'n_words_clean'] for s in order], showfliers=False)
ax.set_xticks(range(1, len(order) + 1), order, rotation=20, ha='right')
ax.set_title('Narrative Length by Service (train)', fontsize=12, fontweight='bold')
ax.set_ylabel('Words after cleaning')
""" + save("03_length_by_service.png")),
("md", "## 2. Mask Tokens by Service"),
("code", """tokens = [cfg['phase2']['mask_tokens']['date'], cfg['phase2']['amount_token'], cfg['phase2']['mask_tokens']['generic']]
tok = pd.DataFrame({t: [100 * (train.loc[train['service'] == s, 'text_clean'].str.count(re.escape(t)) > 0).mean()
                        for s in order] for t in tokens}, index=order).round(2)
print('% of narratives containing the token:'); print(tok.to_string())
ax = tok.plot.bar(figsize=(10, 5), rot=20)
ax.set_title('Mask Tokens by Service (train)', fontsize=12, fontweight='bold'); ax.set_ylabel('% of narratives')
""" + save("03_mask_tokens_by_service.png")),
("md", "## 3. Discriminant Vocabulary (log-odds, informative Dirichlet prior)"),
("code", """STOP = set(('the a an and or but to of in on at for with from by is was were are be been have has had i my me '
            'you your it this that they them their not no do did does as so if we our he she his her '
            'would could should will can there what when which who all any also about after into than then '
            'out up just only been being because over more very am').split())
WORD_RE = re.compile(r'\\[(?:redacted|date|amount)\\]|[a-z]+(?:\\'[a-z]+)?')
def toks(t):
    return [w for w in WORD_RE.findall(t.lower()) if w not in STOP and (w.startswith('[') or len(w) > 2)]
docs = train['text_clean'].map(toks)
by_s = {s: Counter() for s in SERVICES}
for s, d in zip(train['service'], docs):
    by_s[s].update(d)
total = Counter()
for c in by_s.values():
    total.update(c)
vocab = [w for w, n in total.items() if n >= 50]
counts = pd.DataFrame({s: [by_s[s].get(w, 0) for w in vocab] for s in SERVICES}, index=vocab)
alpha = counts.sum(axis=1).astype(float); a0 = alpha.sum()
def z(i):
    yi = counts[i]; yj = counts.drop(columns=i).sum(axis=1); ni, nj = yi.sum(), yj.sum()
    d = np.log((yi + alpha) / (ni + a0 - yi - alpha)) - np.log((yj + alpha) / (nj + a0 - yj - alpha))
    return d / np.sqrt(1 / (yi + alpha) + 1 / (yj + alpha))
Z = pd.DataFrame({s: z(s) for s in SERVICES})
top = pd.DataFrame({s: pd.Series(Z[s].nlargest(15).index.tolist(), dtype=object) for s in SERVICES})
top.index = top.index + 1
print(f'Vocabulary kept: {len(vocab):,} words'); print(top.to_string())"""),
("code", """fig, axes = plt.subplots(2, 3, figsize=(14, 8))
for ax, s in zip(axes.ravel(), SERVICES):
    t = Z[s].nlargest(12)[::-1]
    ax.barh(t.index, t.values, color='steelblue'); ax.set_title(s, fontsize=10); ax.tick_params(labelsize=8)
fig.suptitle('Most Characteristic Words by Service (z-score, train)', fontsize=12, fontweight='bold')
""" + save("03_discriminant_words.png")),
("md", "## 4. Top Bigrams by Service"),
("code", """big = {s: Counter() for s in SERVICES}
for s, d in zip(train['service'], docs):
    big[s].update(f'{a} {b}' for a, b in zip(d, d[1:]) if not (a.startswith('[') and b.startswith('[')))
for s in SERVICES:
    print(f'\\n=== {s} ===')
    for b, n in big[s].most_common(10):
        print(f'  {b:<35} {n:>7,}')"""),
])

# ---------------------------------------------------------------- 04
build("04_Company_Masking.ipynb", "# 04_Company_Masking — Brand Shortcuts & [COMPANY] Variant", [
("code", """lex = pd.read_csv('reports/phase3a/lexicon_patterns.csv', keep_default_na=False)
cand = pd.read_csv('reports/phase3a/single_token_candidates.csv')
cov = pd.read_csv('reports/phase3a/coverage_by_split_service.csv')
ba = pd.read_csv('reports/phase3a/top15_words_before_after.csv')
print(f"Lexicon patterns: {len(lex):,} (single tokens selected: {int(cand['selected'].sum())} of {len(cand)})")"""),
("md", "## 1. Coverage by Split and Service"),
("code", """print('% of narratives with at least one [COMPANY]:'); print(cov.to_string(index=False))
ax = cov.set_index('service')[['train', 'val', 'test']].plot.bar(figsize=(10, 5), rot=20)
ax.set_title('[COMPANY] Coverage by Split', fontsize=12, fontweight='bold'); ax.set_ylabel('% of narratives')
""" + save("04_company_mask_coverage.png")),
("md", "## 2. Most Frequent Matches"),
("code", """print(pd.read_csv('reports/phase3a/top_matches.csv').head(20).to_string(index=False))"""),
("md", "## 3. Discriminant Words Before / After Masking (train)"),
("code", """d = ba.dropna(subset=['pct_removed']).sort_values('pct_removed', ascending=False).head(25)
print(d.to_string(index=False))
fig, ax = plt.subplots(figsize=(10, 7))
ax.barh(d['word'][::-1], d['pct_removed'][::-1], color='coral')
ax.set_title('Share of Occurrences Masked (top discriminant words)', fontsize=12, fontweight='bold')
ax.set_xlabel('% removed')
""" + save("04_brand_words_removed.png")),
("md", "## 4. Residual Brands & False-Positive Bound"),
("code", """print('Discriminant words NOT captured (pct_removed = 0):')
print(', '.join(ba.loc[ba['pct_removed'] == 0, 'word'].tolist()))
s = cand[cand['selected'] & (cand['concentration'] < 0.8)].copy()
s['max_false_positive_docs'] = (s['n_docs'] * (1 - s['concentration'])).round().astype(int)
print('\\nSelected single tokens with concentration < 0.8 (upper bound of false positives):')
print(s.sort_values('max_false_positive_docs', ascending=False).head(15)[
    ['token', 'n_docs', 'concentration', 'n_company_names', 'max_false_positive_docs']].to_string(index=False))"""),
])

# ---------------------------------------------------------------- 05
build("05_Baseline_Models.ipynb", "# 05_Baseline_Models — TF-IDF Grid & Selection on Validation", [
("code", """grid = pd.read_csv('reports/phase3b/grid_results.csv')
best = pd.read_csv('reports/phase3b/best_by_variant.csv')
mm = json.load(open('models/MANIFEST_models.json', encoding='utf-8'))
print(f'Grid fits: {len(grid)} | scikit-learn {mm["_sklearn"]} | test set not used in this step')"""),
("md", "## 1. Grid Results (validation)"),
("code", """print(grid[['variant', 'model', 'C', 'class_weight', 'val_macro_f1', 'val_accuracy', 'val_top2_accuracy',
            'val_min_recall', 'fit_seconds']].to_string(index=False))"""),
("code", """grid['config'] = grid['model'] + ' C=' + grid['C'].astype(str) + ' ' + grid['class_weight']
fig, ax = plt.subplots(figsize=(12, 5))
for v, color in [('as_is', 'steelblue'), ('company_masked', 'coral')]:
    d = grid[grid['variant'] == v]
    ax.plot(d['config'], d['val_macro_f1'], marker='o', label=v, color=color)
ax.set_title('Validation Macro-F1 by Configuration', fontsize=12, fontweight='bold')
ax.set_ylabel('Macro-F1'); ax.tick_params(axis='x', rotation=60); ax.legend()
""" + save("05_grid_macro_f1.png")),
("md", "## 2. Selected Models"),
("code", """print(best.to_string(index=False))
gap = best.set_index('variant').loc['as_is', 'val_macro_f1'] - best.set_index('variant').loc['company_masked', 'val_macro_f1']
print(f'\\nMacro-F1 gap (as_is − company_masked, val): {gap:+.4f}')"""),
("md", "## 3. Recall by Service (validation, selected models)"),
("code", """rec = grid.loc[grid.groupby('variant')['val_macro_f1'].idxmax()].set_index('variant')
rec = rec[[c for c in rec.columns if c.startswith('recall_')]].T
rec.index = rec.index.str.replace('recall_', '')
print(rec.round(4).to_string())
ax = rec.plot.barh(figsize=(10, 5))
ax.set_title('Validation Recall by Service', fontsize=12, fontweight='bold'); ax.set_xlabel('Recall')
""" + save("05_val_recall_by_service.png")),
("md", "## 4. Validation Confusion Matrix — company_masked"),
("code", """cm = pd.read_csv('reports/phase3b/confusion_val_company_masked.csv', index_col=0)
print(cm.to_string())
fig, ax = plt.subplots(figsize=(8, 7))
im = ax.imshow(cm.values, cmap='Blues')
ax.set_xticks(range(len(cm)), cm.columns, rotation=45, ha='right'); ax.set_yticks(range(len(cm)), cm.index)
for i in range(len(cm)):
    for j in range(len(cm)):
        ax.text(j, i, cm.values[i, j], ha='center', va='center', fontsize=8)
ax.set_xlabel('Predicted'); ax.set_ylabel('True'); fig.colorbar(im, ax=ax)
ax.set_title('Validation Confusion — company_masked', fontsize=12, fontweight='bold')
""" + save("05_val_confusion_company_masked.png")),
])

# ---------------------------------------------------------------- 06
build("06_Final_Evaluation.ipynb", "# 06_Final_Evaluation — Test 2026 (used once) & External 2025", [
("code", """lock = json.load(open('reports/phase3c/TEST_LOCK.json', encoding='utf-8'))
metrics = pd.read_csv('reports/phase3c/metrics.csv')
gap = pd.read_csv('reports/phase3c/variant_gap.csv')
ps = pd.read_csv('reports/phase3c/per_service.csv')
cal = pd.read_csv('reports/phase3c/calibration.csv')
print(f"Test first evaluated: {lock['first_evaluation_utc']} | re-runs: {len(lock.get('reruns', []))}")
print('This notebook reads the saved results: it does not re-evaluate the test set.')"""),
("md", "## 1. Global Metrics (95% bootstrap CI)"),
("code", """print(metrics.to_string(index=False))
def ci(s):
    lo, hi = s.strip('[]').split(';')
    return float(lo), float(hi)
fig, ax = plt.subplots(figsize=(9, 5))
labels = metrics['dataset'] + '\\n' + metrics['variant']
lo = np.array([ci(s)[0] for s in metrics['macro_f1_ci95']]); hi = np.array([ci(s)[1] for s in metrics['macro_f1_ci95']])
ax.bar(labels, metrics['macro_f1'], yerr=[metrics['macro_f1'] - lo, hi - metrics['macro_f1']], capsize=6,
       color=['steelblue', 'coral'] * 2, edgecolor='black')
ax.set_ylim(0.75, 0.9); ax.set_ylabel('Macro-F1')
ax.set_title('Macro-F1 with 95% CI', fontsize=12, fontweight='bold')
""" + save("06_macro_f1_ci.png")),
("md", "## 2. Brand-Name Dependency (paired bootstrap)"),
("code", """print(gap.to_string(index=False))
print('\\nLower bound: masking is incomplete (brands absent from the Company column stay visible).')"""),
("md", "## 3. Recall by Service — company_masked"),
("code", """r = ps[ps['variant'] == 'company_masked'].pivot(index='service', columns='dataset', values='recall')
print(r.round(4).to_string())
ax = r.plot.barh(figsize=(10, 5))
ax.set_title('Recall by Service — company_masked', fontsize=12, fontweight='bold'); ax.set_xlabel('Recall')
""" + save("06_recall_by_service.png")),
("md", "## 4. Calibration"),
("code", """print(cal.to_string(index=False))
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
for ax, ds in zip(axes, ['test_2026', 'external_2025']):
    ax.plot([0, 1], [0, 1], '--', color='grey', lw=1)
    for v, color in [('as_is', 'steelblue'), ('company_masked', 'coral')]:
        t = pd.read_csv(f'reports/phase3c/reliability_{ds}_{v}.csv')
        ax.plot(t['mean_confidence'], t['accuracy'], marker='o', label=v, color=color)
    ax.set_title(ds); ax.set_xlabel('Mean confidence'); ax.set_ylabel('Observed accuracy'); ax.legend()
fig.suptitle('Reliability Curves', fontsize=12, fontweight='bold')
""" + save("06_reliability.png")),
("md", "## 5. Test Confusion Matrix — company_masked"),
("code", """cm = pd.read_csv('reports/phase3c/confusion_test_2026_company_masked.csv', index_col=0)
print(cm.to_string())
fig, ax = plt.subplots(figsize=(8, 7))
im = ax.imshow(cm.values, cmap='Blues')
ax.set_xticks(range(len(cm)), cm.columns, rotation=45, ha='right'); ax.set_yticks(range(len(cm)), cm.index)
for i in range(len(cm)):
    for j in range(len(cm)):
        ax.text(j, i, cm.values[i, j], ha='center', va='center', fontsize=8)
ax.set_xlabel('Predicted'); ax.set_ylabel('True'); fig.colorbar(im, ax=ax)
ax.set_title('Test 2026 Confusion — company_masked', fontsize=12, fontweight='bold')
""" + save("06_test_confusion.png")),
("md", "## 6. Error Analysis"),
("code", """print('Most confused pairs (test 2026):')
print(pd.read_csv('reports/phase3c/top_confused_pairs.csv').to_string(index=False))
hc = pd.read_csv('reports/phase3c/high_confidence_errors.csv')
print(f'\\nHigh-confidence errors (examples, label-noise candidates): {len(hc)} shown')
for _, r in hc.head(5).iterrows():
    print(f"  [{r['service']} -> {r['pred']}, conf {r['confidence']:.2f}] {str(r['text_300'])[:150]}…")"""),
("md", "## 7. External 2025 — Monthly Macro-F1"),
("code", """m = pd.read_csv('reports/phase3c/monthly_macro_f1_external_2025_company_masked.csv')
print(m.to_string(index=False))
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(m['received_month'], m['macro_f1'], marker='o', linewidth=2, color='#2c3e50')
ax.set_title('Monthly Macro-F1 — External 2025 (company_masked)', fontsize=12, fontweight='bold')
ax.set_ylabel('Macro-F1'); ax.tick_params(axis='x', rotation=45)
""" + save("06_monthly_macro_f1_2025.png")),
])

# ---------------------------------------------------------------- 07
build("07_Routing_Threshold.ipynb", "# 07_Routing_Threshold — Coverage, Precision & Business Impact", [
("code", """lock = json.load(open('reports/phase5/ROUTING_LOCK.json', encoding='utf-8'))
sel = pd.read_csv('reports/phase5/val_selection.csv')
res = pd.read_csv('reports/phase5/routing_results.csv')
psr = pd.read_csv('reports/phase5/routing_per_service.csv')
imp = pd.read_csv('reports/phase5/business_impact.csv')
print(f"Locked rule: {lock['rule']} | threshold: {lock['threshold']} | target precision: {lock['target_precision']}")"""),
("md", "## 1. Selection on Validation"),
("code", """print(sel.to_string(index=False))"""),
("md", "## 2. Coverage vs Precision"),
("code", """fig, ax = plt.subplots(figsize=(10, 6))
for ds, color in [('val_2026', 'grey'), ('test_2026', 'steelblue'), ('external_2025', 'coral')]:
    c = pd.read_csv(f"reports/phase5/curve_{ds}_{lock['rule']}.csv")
    ax.plot(c['coverage'], c['precision'], label=ds, color=color)
    p = c[c['threshold'] == lock['threshold']]
    ax.scatter(p['coverage'], p['precision'], color=color, zorder=3)
ax.axhline(lock['target_precision'], ls='--', color='black', lw=1)
ax.set_xlabel('Coverage (share auto-routed)'); ax.set_ylabel('Precision of auto-routed complaints')
ax.set_title(f"Coverage vs Precision (threshold {lock['threshold']})", fontsize=12, fontweight='bold'); ax.legend()
""" + save("07_coverage_precision.png")),
("md", "## 3. Results at the Locked Threshold"),
("code", """print(res.to_string(index=False))"""),
("md", "## 4. By Service (test 2026)"),
("code", """t = psr[psr['dataset'] == 'test_2026'].set_index('service')
print(t.to_string())
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
t['share_auto_routed_pct'].sort_values().plot.barh(ax=axes[0], color='steelblue')
axes[0].set_title('Share Auto-Routed (%)', fontsize=11, fontweight='bold')
t['precision_auto_pred_as_service'].sort_values().plot.barh(ax=axes[1], color='coral')
axes[1].axvline(lock['target_precision'], ls='--', color='black', lw=1)
axes[1].set_title('Precision of Auto-Routing', fontsize=11, fontweight='bold')
""" + save("07_per_service_routing.png")),
("md", "## 5. Business Impact (illustrative volume, assumed triage time)"),
("code", """print(imp.to_string(index=False))
d = imp[imp['dataset'] == 'test_2026']
fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(d['triage_minutes_assumed'].astype(str) + ' min', d['triage_hours_saved_per_month'], color='seagreen',
       edgecolor='black')
ax.set_title('Triage Hours Saved per 1,000 Complaints / Month (test 2026)', fontsize=12, fontweight='bold')
ax.set_xlabel('Assumed manual triage time'); ax.set_ylabel('Hours saved')
""" + save("07_business_impact.png")),
])

# ---------------------------------------------------------------- 08
build("08_Final_Synthesis.ipynb", "# 08_Final_Synthesis — Executive Summary & Actionable Insights", [
("code", """metrics = pd.read_csv('reports/phase3c/metrics.csv')
gap = pd.read_csv('reports/phase3c/variant_gap.csv')
res = pd.read_csv('reports/phase5/routing_results.csv')
psr = pd.read_csv('reports/phase5/routing_per_service.csv')
imp = pd.read_csv('reports/phase5/business_impact.csv')
lock = json.load(open('reports/phase5/ROUTING_LOCK.json', encoding='utf-8'))
man = json.load(open('data/processed/MANIFEST.json', encoding='utf-8'))
ext = json.load(open('data/processed/MANIFEST_external.json', encoding='utf-8'))
print(f"2026 narratives: {man['all']['rows']:,} (train {man['train']['rows']:,} / val {man['val']['rows']:,} / test {man['test']['rows']:,})")
print(f"External 2025 narratives: {ext['rows']:,}")"""),
("md", "## 1. Key Findings"),
("code", """print('\\n=== CLASSIFIER (reference: company_masked) ===')
for _, r in metrics[metrics['variant'] == 'company_masked'].iterrows():
    print(f"{r['dataset']:<15} macro-F1 {r['macro_f1']:.3f} {r['macro_f1_ci95']} | accuracy {r['accuracy']:.3f} | top-2 {r['top2_accuracy']:.3f}")
print('\\n=== AUTOMATIC ROUTING (threshold ' + str(lock['threshold']) + ') ===')
for _, r in res[res['dataset'] != 'val_2026'].iterrows():
    print(f"{r['dataset']:<15} coverage {100 * r['coverage']:.1f}% {r['coverage_ci95']} | precision {100 * r['precision_auto']:.1f}% {r['precision_ci95']}")
print('\\n=== BRAND-NAME DEPENDENCY (lower bound) ===')
for _, r in gap.iterrows():
    print(f"{r['dataset']:<15} {100 * r['gap_as_is_minus_masked']:.2f} macro-F1 points {r['gap_ci95']}")"""),
("md", "## 2. Executive Summary Dashboard"),
("code", """fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.35)
ax1 = fig.add_subplot(gs[0, 0])
r = res[res['dataset'] != 'val_2026']
x = np.arange(len(r))
ax1.bar(x - 0.2, 100 * r['coverage'], 0.4, label='Coverage', color='steelblue')
ax1.bar(x + 0.2, 100 * r['precision_auto'], 0.4, label='Precision', color='coral')
ax1.set_xticks(x, r['dataset']); ax1.set_ylim(0, 100); ax1.legend(); ax1.set_title('Auto-Routing (%)', fontweight='bold')
ax2 = fig.add_subplot(gs[0, 1:])
t = psr[psr['dataset'] == 'test_2026'].set_index('service')['precision_auto_pred_as_service'].sort_values()
ax2.barh(t.index, 100 * t.values, color=['#e74c3c' if v < 0.9 else '#2ecc71' for v in t.values])
ax2.axvline(100 * lock['target_precision'], ls='--', color='black'); ax2.set_xlim(70, 100)
ax2.set_title('Auto-Routing Precision by Service — test 2026 (%)', fontweight='bold')
ax3 = fig.add_subplot(gs[1, 0])
m = metrics[metrics['variant'] == 'company_masked']
ax3.bar(m['dataset'], m['macro_f1'], color='#2c3e50'); ax3.set_ylim(0.75, 0.9)
ax3.set_title('Classifier Macro-F1', fontweight='bold')
ax4 = fig.add_subplot(gs[1, 1])
d = imp[imp['dataset'] == 'test_2026']
ax4.bar(d['triage_minutes_assumed'].astype(str) + ' min', d['triage_hours_saved_per_month'], color='seagreen')
ax4.set_title('Hours Saved / 1,000 Complaints', fontweight='bold')
ax5 = fig.add_subplot(gs[1, 2])
mm = pd.read_csv('reports/phase3c/monthly_macro_f1_external_2025_company_masked.csv')
ax5.plot(mm['received_month'], mm['macro_f1'], marker='o', color='#2c3e50'); ax5.tick_params(axis='x', rotation=60)
ax5.set_title('Monthly Macro-F1 — 2025', fontweight='bold')
fig.suptitle('Bank Complaint Routing — Executive Dashboard', fontsize=15, fontweight='bold')
plt.savefig('output/08_executive_dashboard.png', dpi=300, bbox_inches='tight')
plt.show()
print('✓ Saved: 08_executive_dashboard.png')"""),
("md", "## 3. Recommendations for the Bank"),
("code", """recommendations = [
    ('Measure the current process first', 'Monthly volume, manual triage time and manual error rate are unknown: without them the real gain cannot be quantified.'),
    ('Retrain on French complaints', 'Results validate the method on US data; the model itself is not reusable as is.'),
    ('Pilot on the most reliable services', 'Debt collection and mortgage (96–97% precision); keep human review for Transfers & Payments and Accounts until per-service thresholds are validated.'),
    ('Log every automatic decision', 'Proposed service and confidence level, for Compliance traceability.'),
]
print('\\n=== RECOMMENDATIONS ===')
for i, (title, text) in enumerate(recommendations, 1):
    print(f'\\n{i}. {title}\\n   {text}')"""),
("md", "## 4. Data Quality & Limitations"),
("code", """limitations = [
    'English US corpus: the pipeline transfers to a French-speaking bank, not the model weights.',
    'Only narratives with consumer consent are published: sample not representative of all complaints.',
    'Target precision of 95% approached, not reached (94.7% test, 94.8% 2025): threshold set without safety margin.',
    'Precision uneven across services (Transfers & Payments 84% on test).',
    'Company masking incomplete (brands absent from the Company column remain).',
    'Labels = product chosen by the consumer: label noise not quantified (needs manual annotation).',
    'Business impact illustrative: volume and triage time are assumptions.',
    'DistilBERT (Phase 4) not done in this version.',
]
print('\\n=== LIMITATIONS ===')
for l in limitations:
    print(f'  - {l}')"""),
])
