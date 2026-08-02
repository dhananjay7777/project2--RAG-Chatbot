"""Chat-style CSS for the Streamlit UI."""

from __future__ import annotations

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Instrument+Serif:ital@0;1&display=swap');

:root {
  --ink: #10231f;
  --muted: #5b6b66;
  --line: #d9e2de;
  --teal: #0f766e;
  --teal-deep: #0b4f4a;
  --glow: rgba(15, 118, 110, 0.14);
  --composer-h: 88px;
}

html, body, [class*="css"] {
  font-family: 'DM Sans', system-ui, sans-serif;
}

.stApp {
  background:
    radial-gradient(900px 420px at 12% -8%, rgba(15,118,110,0.12), transparent 55%),
    radial-gradient(700px 360px at 100% 0%, rgba(16,35,31,0.06), transparent 48%),
    linear-gradient(180deg, #f4f7f5 0%, #eef3f0 100%);
}

/* Scrollable page; room for fixed chat input */
section.main > div.block-container {
  max-width: 820px;
  padding-top: 0.6rem;
  padding-bottom: calc(var(--composer-h) + 2rem);
}

#MainMenu, footer, header[data-testid="stHeader"] {
  visibility: hidden;
  height: 0;
}

.mf-shell-header {
  position: sticky;
  top: 0;
  z-index: 100;
  margin: 0 0 0.85rem 0;
  padding: 0.85rem 1.1rem;
  border-radius: 20px;
  background: linear-gradient(135deg, #0b1f1c 0%, #12352f 52%, #0f766e 100%);
  box-shadow: 0 16px 40px rgba(11, 31, 28, 0.24);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.mf-shell-header__left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.mf-avatar {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: rgba(255,255,255,0.12);
  border: 1px solid rgba(255,255,255,0.28);
  color: #a7f3d0;
  font-size: 1.05rem;
}
.mf-shell-header__meta h1 {
  margin: 0;
  color: #f5faf8;
  font-size: 1.02rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.mf-shell-header__meta p {
  margin: 0.12rem 0 0 0;
  color: rgba(236,253,245,0.78);
  font-size: 0.74rem;
}
.mf-shell-header__disclaimer {
  background: rgba(255,255,255,0.12);
  border: 1px solid rgba(255,255,255,0.28);
  color: #ecfdf5;
  font-size: 0.74rem;
  font-weight: 650;
  padding: 0.38rem 0.78rem;
  border-radius: 999px;
}

.mf-scroll-region {
  min-height: 0;
}

.mf-empty {
  text-align: center;
  padding: 1.6rem 1.25rem 1.35rem;
  margin: 0 0 0.35rem 0;
  background: rgba(255,255,255,0.72);
  border: 1px solid var(--line);
  border-radius: 22px;
}
.mf-empty__eyebrow {
  display: inline-block;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--teal);
  margin-bottom: 0.7rem;
}
.mf-empty h2 {
  margin: 0 0 0.55rem 0;
  font-family: 'Instrument Serif', Georgia, serif;
  font-size: 2rem;
  font-weight: 400;
  color: var(--ink);
  letter-spacing: -0.02em;
}
.mf-empty p {
  margin: 0 auto;
  max-width: 34rem;
  color: var(--muted);
  font-size: 0.96rem;
  line-height: 1.65;
}

.mf-corpus {
  margin: 0 0 0.85rem 0;
  padding: 0.75rem 1rem;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: rgba(255,255,255,0.55);
}
.mf-corpus--hero {
  margin-top: 0.65rem;
  padding: 1rem 1.15rem 1.05rem;
  background: rgba(255,255,255,0.82);
  border-radius: 18px;
}
.mf-corpus__label {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #7a8a84;
  margin-bottom: 0.45rem;
}
.mf-corpus__list {
  margin: 0;
  padding-left: 1.15rem;
  color: var(--ink);
  font-size: 0.88rem;
  line-height: 1.55;
}
.mf-corpus__list li {
  margin: 0.18rem 0;
}
.mf-corpus--hero .mf-corpus__list {
  font-size: 0.92rem;
  line-height: 1.65;
}

.mf-suggestions-label {
  margin: 1.1rem 0 0.55rem 0.35rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #7a8a84;
}

/* Suggestion chips only — not chat send */
div[data-testid="stButton"] > button {
  width: 100%;
  background: rgba(255,255,255,0.92);
  color: #1e2f2b !important;
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 0.8rem 0.95rem;
  font-size: 0.84rem;
  font-weight: 550;
  line-height: 1.4;
  text-align: left;
  min-height: 76px;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
div[data-testid="stButton"] > button:hover {
  border-color: #14b8a6;
  color: #0b1f1c !important;
  background: #ffffff !important;
  transform: translateY(-1px);
  box-shadow: 0 10px 22px var(--glow);
}

.mf-row {
  display: flex;
  gap: 0.65rem;
  margin: 0.85rem 0.25rem;
  align-items: flex-end;
}
.mf-row--user { justify-content: flex-end; }
.mf-row--bot { justify-content: flex-start; }
.mf-bubble-avatar {
  width: 30px;
  height: 30px;
  border-radius: 11px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  font-size: 0.78rem;
  background: #12352f;
  color: #a7f3d0;
}
.mf-bubble {
  max-width: min(78%, 560px);
  padding: 0.85rem 1rem;
  border-radius: 18px;
  font-size: 0.95rem;
  line-height: 1.6;
  box-shadow: 0 8px 22px rgba(16,35,31,0.06);
}
.mf-bubble--user {
  background: linear-gradient(160deg, #12352f, #0f766e);
  color: #f4fffb;
  border-bottom-right-radius: 6px;
}
.mf-bubble--bot {
  background: #ffffff;
  color: var(--ink);
  border: 1px solid var(--line);
  border-bottom-left-radius: 6px;
  border-left: 3px solid var(--accent, var(--teal));
}
.mf-badge {
  display: inline-block;
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent, var(--teal));
  background: color-mix(in srgb, var(--accent, var(--teal)) 10%, #fff);
  border: 1px solid color-mix(in srgb, var(--accent, var(--teal)) 22%, #fff);
  padding: 0.18rem 0.5rem;
  border-radius: 999px;
  margin-bottom: 0.45rem;
}
.mf-answer { margin: 0; white-space: pre-wrap; }
.mf-note {
  margin: 0.5rem 0 0 0;
  font-size: 0.82rem;
  color: var(--muted);
}
.mf-cite {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  margin-top: 0.75rem;
  padding: 0.4rem 0.7rem;
  border-radius: 999px;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  color: #115e59 !important;
  font-size: 0.78rem;
  font-weight: 650;
  text-decoration: none !important;
}
.mf-footer {
  margin: 0.7rem 0 0 0;
  padding-top: 0.55rem;
  border-top: 1px dashed #d9e2de;
  font-size: 0.72rem;
  color: #8a9792;
}
.mf-bubble--bot > p.mf-cite,
.mf-bubble--bot > p:has(> a.mf-cite) {
  margin: 0.75rem 0 0 0;
}

.mf-warning {
  margin-top: 0.45rem;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  color: #9a3412;
  border-radius: 12px;
  padding: 0.55rem 0.75rem;
  font-size: 0.8rem;
}
.mf-fineprint {
  margin: 1.25rem 0 0.5rem;
  text-align: center;
  font-size: 0.72rem;
  color: #93a09b;
  line-height: 1.55;
}

/* Fixed bottom chat composer — send is inside the field */
[data-testid="stBottomBlock"] {
  background: transparent !important;
}
[data-testid="stChatInput"],
.stChatFloatingInputContainer {
  max-width: 820px;
  margin: 0 auto;
  padding: 0 1rem 0.75rem;
}
[data-testid="stChatInput"] > div {
  background: rgba(255,255,255,0.96) !important;
  border: 1px solid var(--line) !important;
  border-radius: 22px !important;
  box-shadow: 0 -6px 28px rgba(16,35,31,0.1) !important;
  backdrop-filter: blur(12px);
  padding: 0.35rem 0.5rem 0.35rem 0.85rem !important;
}
[data-testid="stChatInput"] textarea {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  font-size: 0.95rem !important;
  min-height: 44px !important;
  max-height: 120px !important;
  padding: 0.55rem 0.25rem !important;
  resize: none !important;
}
[data-testid="stChatInput"] textarea:focus {
  outline: none !important;
  box-shadow: none !important;
}

/* Send control inside input — visible on hover */
[data-testid="stChatInputSubmitButton"] button,
[data-testid="stChatInput"] button {
  background: linear-gradient(135deg, var(--teal), var(--teal-deep)) !important;
  color: #ecfdf5 !important;
  border: none !important;
  border-radius: 14px !important;
  min-width: 44px !important;
  min-height: 44px !important;
}
[data-testid="stChatInputSubmitButton"] button:hover,
[data-testid="stChatInput"] button:hover {
  background: var(--teal-deep) !important;
  color: #ffffff !important;
  border: none !important;
  filter: brightness(1.05);
}
[data-testid="stChatInputSubmitButton"] button:active,
[data-testid="stChatInput"] button:active {
  background: #083f3b !important;
  color: #ffffff !important;
}
[data-testid="stChatInputSubmitButton"] svg,
[data-testid="stChatInput"] svg {
  fill: #ecfdf5 !important;
  color: #ecfdf5 !important;
}
[data-testid="stChatInputSubmitButton"] button:hover svg,
[data-testid="stChatInput"] button:hover svg {
  fill: #ffffff !important;
}

@media (max-width: 640px) {
  .mf-shell-header { flex-direction: column; align-items: flex-start; }
  .mf-empty h2 { font-size: 1.55rem; }
  .mf-bubble { max-width: 88%; }
}
</style>
"""
