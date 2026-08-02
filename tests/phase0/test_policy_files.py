"""Phase 0 — policy YAML integrity (taxonomy, lexicon, PII)."""

from pathlib import Path

import re
import yaml

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "policy"

REQUIRED_CLASSES = {
    "FACTUAL_ATTRIBUTE",
    "FACTUAL_PROCESS",
    "ADVISORY",
    "RANKING_COMPARATIVE",
    "PERFORMANCE_RETURNS",
    "SPECULATIVE_FORECAST",
    "PII_BEARING",
    "OUT_OF_SCOPE",
    "AMBIGUOUS",
}

REQUIRED_LEXICON = {
    "should",
    "recommend",
    "suggest",
    "best",
    "ideal",
    "worth it",
    "safe bet",
    "guaranteed",
    "outperform",
    "better than",
    "expect returns of",
}


def _load(name: str) -> dict:
    return yaml.safe_load((POLICY / name).read_text(encoding="utf-8"))


def test_refusal_taxonomy_classes_and_examples():
    data = _load("refusal_taxonomy.yaml")
    classes = data["classes"]
    assert REQUIRED_CLASSES <= set(classes.keys())
    for name, spec in classes.items():
        examples = spec.get("examples") or []
        assert len(examples) >= 5, f"{name} needs >=5 examples"
        assert "route" in spec


def test_refusal_templates_have_single_citation_placeholder():
    data = _load("refusal_taxonomy.yaml")
    allowlist = set(_load("source_allowlist.yaml")["urls"])
    default_url = data["default_citation_url"]
    assert default_url in allowlist

    for name, spec in data["classes"].items():
        template = spec.get("template")
        if template is None:
            continue
        count = template.count("{{citation_url}}")
        assert count == 1, f"{name} template must have exactly one citation_url"
        # No AMFI/SEBI URLs hard-coded
        assert "amfiindia.com" not in template.lower()
        assert "sebi.gov.in" not in template.lower()


def test_performance_template_has_no_digit_characters_in_body():
    data = _load("refusal_taxonomy.yaml")
    template = data["classes"]["PERFORMANCE_RETURNS"]["template"]
    # Strip placeholder; remaining body must have no digits (URL filled later).
    body = template.replace("{{citation_url}}", "").replace("{{citation_label}}", "")
    assert not re.search(r"\d", body), "PERFORMANCE_RETURNS template must be numeral-free"


def test_prohibited_lexicon_has_required_terms():
    data = _load("prohibited_lexicon.yaml")
    terms = {t.lower() for t in data["terms"]}
    missing = REQUIRED_LEXICON - terms
    assert not missing, f"Missing lexicon terms: {missing}"


def test_pii_patterns_compile_and_cover_types():
    data = _load("pii_patterns.yaml")
    required = {"pan", "aadhaar", "account_number", "otp", "email", "phone"}
    assert required <= set(data["patterns"].keys())
    for name, spec in data["patterns"].items():
        re.compile(spec["regex"])


def test_pan_regex_matches_and_negatives():
    data = _load("pii_patterns.yaml")
    pan_re = re.compile(data["patterns"]["pan"]["regex"], re.IGNORECASE)
    assert pan_re.search("My PAN is ABCDE1234F today")
    for sample in data["negative_examples"]:
        assert not pan_re.search(sample), f"False positive on: {sample}"


def test_config_yaml_loads():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    assert cfg["corpus"]["expected_source_count"] == 5
    assert cfg["project"]["disclaimer"] == "Facts-only. No investment advice."
    assert cfg["generation"]["temperature"] == 0
    assert cfg["generation"]["max_sentences"] == 3
    assert cfg["llm"]["provider"] == "groq"
    assert "llama" in cfg["generation"]["model"]
