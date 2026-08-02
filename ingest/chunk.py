"""Phase 2 public chunk API."""

from ingest.processing.chunk import chunk_document
from ingest.processing.models import ParsedDocument


def chunk_document_public(doc: ParsedDocument):
    return chunk_document(doc)
