"""Full ask pipeline: route → synthesize → validate → envelope."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from core.compose import compose_answer
from core.observability.telemetry import log_query_event
from core.synthesis.orchestrator import answer_query
from core.synthesis.llm import ChatCompleter
from schemas.answer import AnswerEnvelope


def ask(
    query: str,
    *,
    query_id: UUID | None = None,
    last_source_id: str | None = None,
    processed_root: Path | None = None,
    completer: ChatCompleter | None = None,
    emit_telemetry: bool = True,
) -> AnswerEnvelope:
    synthesis = answer_query(
        query,
        last_source_id=last_source_id,
        processed_root=processed_root,
        completer=completer,
    )
    envelope = compose_answer(
        synthesis,
        query_id=query_id,
        processed_root=processed_root,
    )
    if emit_telemetry:
        log_query_event(
            query,
            envelope,
            token_cost_usd=0.0 if not synthesis.used_llm else 0.0005,
            extra={"synthesis_path": synthesis.path.value},
        )
    return envelope
