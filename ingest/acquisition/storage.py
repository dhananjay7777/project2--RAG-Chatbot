"""Immutable raw-artifact and atomic manifest storage."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from ingest.acquisition.models import AcquisitionManifest

_SAFE_SOURCE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class StorageError(RuntimeError):
    """Raw artifact or manifest persistence failed."""


class RawArtifactStore:
    """Content-addressed storage rooted at ``data/raw``.

    Artifact names are their SHA-256 digest. Existing artifacts are never
    rewritten, which makes unchanged re-fetches cheap and preserves history.
    """

    def __init__(self, root: Path):
        self.root = root

    def write_artifact(
        self,
        source_id: str,
        content: bytes,
        *,
        suffix: str,
    ) -> tuple[str, str, bool]:
        """Return ``(sha256, relative_path, created)`` after an atomic write."""

        if not _SAFE_SOURCE_ID.fullmatch(source_id):
            raise StorageError(f"Unsafe source_id: {source_id!r}")
        if suffix not in {".html", ".md"}:
            raise StorageError(f"Unsupported raw artifact suffix: {suffix}")
        if not content:
            raise StorageError("Refusing to persist an empty raw artifact")

        digest = hashlib.sha256(content).hexdigest()
        source_dir = self.root / source_id
        destination = source_dir / f"{digest}{suffix}"
        relative_path = destination.relative_to(self.root).as_posix()

        if destination.exists():
            return digest, relative_path, False

        source_dir.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{digest}.",
                suffix=".tmp",
                dir=source_dir,
                delete=False,
            ) as temp:
                temp.write(content)
                temp.flush()
                os.fsync(temp.fileno())
                temp_path = Path(temp.name)
            os.replace(temp_path, destination)
        except OSError as exc:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise StorageError(
                f"Failed to atomically write {destination}: {exc}"
            ) from exc

        return digest, relative_path, True

    def write_manifest(self, manifest: AcquisitionManifest) -> Path:
        """Persist run manifest; update ``latest.json`` only for complete runs."""

        runs_dir = self.root / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        run_path = runs_dir / f"{manifest.run_id}.json"
        self._atomic_json(run_path, manifest.model_dump(mode="json"))

        if manifest.active_count == 5:
            latest_path = self.root / "latest.json"
            self._atomic_json(latest_path, manifest.model_dump(mode="json"))
            if manifest.promotion_ready:
                self._atomic_json(
                    self.root / "latest-live.json",
                    manifest.model_dump(mode="json"),
                )
        return run_path

    def load_latest(self, *, live_only: bool = False) -> AcquisitionManifest | None:
        name = "latest-live.json" if live_only else "latest.json"
        path = self.root / name
        if not path.exists():
            return None
        try:
            return AcquisitionManifest.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as exc:
            raise StorageError(f"Cannot load manifest {path}: {exc}") from exc

    @staticmethod
    def _atomic_json(destination: Path, payload: dict) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                prefix=f".{destination.name}.",
                suffix=".tmp",
                dir=destination.parent,
                delete=False,
            ) as temp:
                json.dump(payload, temp, ensure_ascii=False, indent=2)
                temp.write("\n")
                temp.flush()
                os.fsync(temp.fileno())
                temp_path = Path(temp.name)
            os.replace(temp_path, destination)
        except OSError as exc:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise StorageError(
                f"Failed to atomically write manifest {destination}: {exc}"
            ) from exc
