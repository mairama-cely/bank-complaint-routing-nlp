"""Shared helpers for Phase 1 scripts: project root, config, paths, hard stop."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]

# Windows consoles may default to cp1252: force UTF-8 so French accents and symbols (→, ≥) print safely.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def load_config() -> dict:
    cfg_path = ROOT / "config" / "config.yaml"
    if not cfg_path.exists():
        stop(f"config/config.yaml introuvable à {cfg_path}")
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8"))


def p(cfg: dict, key: str) -> Path:
    """Absolute path for a key of cfg['paths'], created if missing."""
    path = ROOT / cfg["paths"][key]
    path.mkdir(parents=True, exist_ok=True)
    return path


def selected_exports(cfg: dict) -> list[dict]:
    ids = set(cfg["selected_exports"])
    sel = [e for e in cfg["exports"] if e["id"] in ids]
    if len(sel) != len(ids):
        stop(f"selected_exports contient des id absents de exports: {sorted(ids - {e['id'] for e in sel})}")
    return sel


def read_json(path: Path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def stop(msg: str, code: int = 2) -> None:
    """Hard stop required by the Phase 1 rules: report the deviation, do not continue."""
    print(f"\n[STOP] {msg}\n", file=sys.stderr)
    sys.exit(code)
