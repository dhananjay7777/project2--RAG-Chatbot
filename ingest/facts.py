"""Phase 2 public facts API."""

from ingest.processing.facts import build_fact_cards, extract_pass_a


def extract_facts(source_id: str) -> list:
    raise NotImplementedError(
        "Use ingest.processing.pipeline.process_corpus() or build_fact_cards()"
    )
