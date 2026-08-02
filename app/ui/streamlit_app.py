"""Phase 7: Chat-style Streamlit UI with fixed bottom input."""

from __future__ import annotations

import html
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app.ui import backend
from app.ui.presenter import (
    DISCLAIMER,
    WELCOME_BODY,
    WELCOME_TITLE,
    AnswerView,
    check_input,
    corpus_scheme_names,
    example_questions,
    max_input_chars,
)
from app.ui.styles import CSS

logger = logging.getLogger(__name__)


def _init_state() -> None:
    st.session_state.setdefault("history", [])


def _ask_and_store(question: str) -> None:
    question = question.strip()
    if not question:
        return
    logger.info("UI ask: %s", question[:120])
    with st.spinner("Looking that up…"):
        view = backend.answer(question)
    st.session_state["history"].append({"question": question, "view": view})


def _render_header() -> None:
    st.markdown(
        f"""
        <div class="mf-shell-header">
          <div class="mf-shell-header__left">
            <div class="mf-avatar">◆</div>
            <div class="mf-shell-header__meta">
              <h1>Mutual Fund FAQ</h1>
              <p>Chat with facts from five Groww Direct Growth schemes</p>
            </div>
          </div>
          <div class="mf-shell-header__disclaimer">{html.escape(DISCLAIMER)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_corpus_schemes(*, prominent: bool = False) -> None:
    items = "".join(
        f"<li>{html.escape(name)}</li>" for name in corpus_scheme_names()
    )
    css_class = "mf-corpus mf-corpus--hero" if prominent else "mf-corpus"
    st.markdown(
        f"""
        <div class="{css_class}">
          <div class="mf-corpus__label">Covered schemes (Groww Direct Growth)</div>
          <ol class="mf-corpus__list">{items}</ol>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_empty_state() -> None:
    st.markdown(
        f"""
        <div class="mf-empty">
          <div class="mf-empty__eyebrow">Facts-only assistant</div>
          <h2>{html.escape(WELCOME_TITLE)}</h2>
          <p>{html.escape(WELCOME_BODY)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_corpus_schemes(prominent=True)


def _user_bubble(text: str) -> None:
    body = html.escape(text).replace("\n", "<br>")
    st.markdown(
        f'<div class="mf-row mf-row--user">'
        f'<div class="mf-bubble mf-bubble--user">{body}</div></div>',
        unsafe_allow_html=True,
    )


def _bot_bubble(view: AnswerView) -> None:
    # Streamlit's markdown parser treats blank lines as block breaks and then
    # escapes following HTML as literal text. Keep this as one compact HTML tree.
    note = (
        f'<p class="mf-note">{html.escape(view.note)}</p>' if view.note else ""
    )
    citation = (
        f'<p><a class="mf-cite" href="{html.escape(view.citation_url)}" '
        f'target="_blank" rel="noopener noreferrer">'
        f"{html.escape(view.citation_label)} ↗</a></p>"
        if view.citation_url
        else ""
    )
    footer = (
        f'<p class="mf-footer">{html.escape(view.footer)}</p>'
        if view.footer
        else ""
    )
    # Escape newlines in the answer so they cannot introduce markdown block breaks.
    answer = html.escape(view.answer).replace("\n", "<br>")
    block = (
        f'<div class="mf-row mf-row--bot">'
        f'<div class="mf-bubble-avatar">◆</div>'
        f'<div class="mf-bubble mf-bubble--bot" style="--accent: {view.accent};">'
        f'<span class="mf-badge">{html.escape(view.badge)}</span>'
        f'<p class="mf-answer">{answer}</p>'
        f"{note}{citation}{footer}"
        f"</div></div>"
    )
    st.markdown(block, unsafe_allow_html=True)


def _render_scrollable_body() -> None:
    # Keep each HTML block self-contained — Streamlit renders each st.markdown
    # separately, so open/close wrappers across calls show up as literal "</div>".
    history = st.session_state["history"]
    if not history:
        _render_empty_state()
        _render_suggestions()
    else:
        _render_corpus_schemes(prominent=False)
        for turn in history:
            _user_bubble(turn["question"])
            _bot_bubble(turn["view"])

    st.markdown(
        '<div class="mf-fineprint">Answers come from five Groww scheme pages only. '
        "No accounts, uploads, or exports — this chat stays in memory for this session.</div>",
        unsafe_allow_html=True,
    )


def _render_suggestions() -> None:
    st.markdown(
        '<div class="mf-suggestions-label">Start with a prompt</div>',
        unsafe_allow_html=True,
    )
    questions = example_questions()
    cols = st.columns(len(questions))
    for column, question in zip(cols, questions):
        with column:
            if st.button(question, key=f"chip-{abs(hash(question))}"):
                _ask_and_store(question)
                st.rerun()


def _handle_chat_input(prompt: str | None) -> None:
    if not prompt:
        return
    limit = max_input_chars()
    check = check_input(prompt, max_chars=limit)
    for warning in check.warnings:
        st.markdown(
            f'<div class="mf-warning">{html.escape(warning)}</div>',
            unsafe_allow_html=True,
        )
    if not check.ok:
        st.warning(check.error or "Enter a question first.")
        return
    _ask_and_store(prompt.strip())
    st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="Mutual Fund FAQ Assistant",
        page_icon="◆",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.markdown(CSS, unsafe_allow_html=True)
    _init_state()
    _render_header()
    _render_scrollable_body()

    # Fixed bottom bar with send control inside the input (Streamlit chat_input).
    prompt = st.chat_input(
        "Ask about expense ratio, exit load, minimum SIP…",
        max_chars=max_input_chars(),
    )
    _handle_chat_input(prompt)


if __name__ == "__main__":
    main()
