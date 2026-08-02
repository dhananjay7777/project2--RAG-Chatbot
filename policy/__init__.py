"""Policy loaders and shared Phase 0 utilities."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_DIR = ROOT / "policy"
CONFIG_PATH = ROOT / "config.yaml"


def policy_path(name: str) -> Path:
    return POLICY_DIR / name
