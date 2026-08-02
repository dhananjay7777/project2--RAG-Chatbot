"""Load project configuration from config.yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from policy import CONFIG_PATH


@lru_cache(maxsize=1)
def load_settings(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or CONFIG_PATH
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {cfg_path}")
    return data


def retrieval_settings() -> dict[str, Any]:
    return dict(load_settings().get("retrieval") or {})
