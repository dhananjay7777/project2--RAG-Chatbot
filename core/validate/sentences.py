"""Sentence segmentation with abbreviation-aware protections."""

from __future__ import annotations

import re


_PROTECT = [
    (re.compile(r"\bRs\.?", re.I), "Rs§"),
    (re.compile(r"\bi\.e\.", re.I), "i§e§"),
    (re.compile(r"\be\.g\.", re.I), "e§g§"),
    (re.compile(r"\d+\.\d+%"), lambda m: m.group(0).replace(".", "§")),
    (re.compile(r"\d+\.\d+"), lambda m: m.group(0).replace(".", "§")),
]


def _protect(text: str) -> str:
    out = text
    for pat, repl in _PROTECT:
        if callable(repl):
            out = pat.sub(repl, out)
        else:
            out = pat.sub(repl, out)
    return out


def _unprotect(text: str) -> str:
    return text.replace("§", ".")


def split_sentences(text: str) -> list[str]:
    protected = _protect(text.strip())
    parts = re.split(r"(?<=[.!?])\s+", protected)
    sentences = [_unprotect(p.strip()) for p in parts if p.strip()]
    if not sentences and text.strip():
        return [text.strip()]
    return sentences


def sentence_count(text: str) -> int:
    return len(split_sentences(text))


def truncate_to_sentences(text: str, max_sentences: int = 3) -> str:
    sentences = split_sentences(text)
    return " ".join(sentences[:max_sentences])
