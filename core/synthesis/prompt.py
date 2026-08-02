"""Prompt assembly for generative synthesis."""

from __future__ import annotations

from core.retrieval.models import ScoredChunk

SYSTEM_PROMPT = """You state facts from the provided context. You are not an advisor.

HARD RULES
1. Use ONLY the CONTEXT. No outside knowledge, no arithmetic, no inference.
2. Maximum 3 sentences. Prefer 1.
3. No advice, opinions, recommendations, comparisons, or predictions.
4. Copy numbers, dates, and percentages exactly as written in CONTEXT.
5. Do not write the citation or footer; the system appends them.
6. If CONTEXT does not contain the answer, output exactly: INSUFFICIENT_CONTEXT"""


def format_context_block(chunks: list[ScoredChunk]) -> str:
    blocks: list[str] = []
    for item in chunks:
        chunk = item.chunk
        eff = chunk.effective_date.isoformat() if chunk.effective_date else "unknown"
        header = (
            f"[chunk_id: {chunk.chunk_id}] "
            f"[source: {item.source_id} | effective_date: {eff}]"
        )
        blocks.append(f"{header}\n{chunk.text.strip()}")
    return "\n\n".join(blocks)


def build_user_prompt(query: str, chunks: list[ScoredChunk]) -> str:
    context = format_context_block(chunks)
    return f"CONTEXT\n{context}\n\nQUERY\n{query.strip()}"
