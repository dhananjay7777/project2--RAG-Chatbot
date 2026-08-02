"""Deploy readiness checks (index + registry)."""

from __future__ import annotations

from pathlib import Path

from core.settings import load_settings
from ingest.acquisition.registry import load_source_definitions
from ingest.indexing.pipeline import index_paths


def registry_cardinality() -> int:
    return len(load_source_definitions())


def index_ready(index_root: Path | None = None) -> tuple[bool, list[str]]:
    """Return whether read-only Phase 9 index artifacts are present."""

    settings = load_settings()
    root = index_root or Path(settings.get("paths", {}).get("data_index", "data/index"))
    _idx, _chroma, bm25_path = index_paths(root)
    missing: list[str] = []
    for path in (
        root / "index_manifest.json",
        bm25_path,
        Path(settings.get("paths", {}).get("data_processed", "data/processed"))
        / "chunks.jsonl",
    ):
        if not path.exists():
            missing.append(str(path.as_posix()))
    # Dense store: Chroma dir or pickle fallback
    chroma = root / "chroma"
    dense_pkl = root / "dense_vectors.pkl"
    if not chroma.exists() and not dense_pkl.exists():
        missing.append("data/index/chroma or data/index/dense_vectors.pkl")
    return (not missing, missing)


def deploy_rate_limit_per_hour() -> int:
    import os

    env = os.getenv("MF_RATE_LIMIT_PER_HOUR", "").strip()
    if env:
        return max(1, int(env))
    cfg = load_settings().get("deploy") or {}
    return int(cfg.get("rate_limit_per_ip_per_hour", 30))


def cors_origins() -> list[str]:
    import os

    raw = os.getenv("CORS_ORIGINS", "").strip()
    if raw:
        return [part.strip() for part in raw.split(",") if part.strip()]
    cfg = load_settings().get("deploy") or {}
    origins = cfg.get("cors_origins") or []
    return [str(o).strip() for o in origins if str(o).strip()]
