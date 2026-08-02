"""Phase 1 corpus acquisition package."""

from ingest.acquisition.pipeline import (
    CorpusIncompleteError,
    SnapshotDirectoryFetcher,
    acquire_corpus,
)
from ingest.acquisition.registry import (
    RegistryValidationError,
    load_source_definitions,
    validate_manifest,
)
from ingest.acquisition.storage import RawArtifactStore

__all__ = [
    "CorpusIncompleteError",
    "RawArtifactStore",
    "RegistryValidationError",
    "SnapshotDirectoryFetcher",
    "acquire_corpus",
    "load_source_definitions",
    "validate_manifest",
]
