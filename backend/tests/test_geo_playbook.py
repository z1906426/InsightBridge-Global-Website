"""Tests for GEO SEO Playbook: Step 2/3 (HTML injection) + Step 6 (APIs)."""
import os
import re
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://insightbridge-web.preview.emergentagent.com").rstrip("/")

ARTICLE_PATHS = [
    "theories/core-code-theory.html",
    "theories/ddrt.html",
    "theories/home-model.html",
    "theories/management-debt.html",
    "publications/xian-incident-republican-china-politics.html",
    "intelligence-market-report.html",
    "intelligence-vol01.html",
    "landing/ai-pricing.html",
]

SLUGS = [
    "core-code-theory", "ddrt", "home-model", "management-debt",
    "xian-incident-republican-china-politics",
    "intelligence-market-report", "intelligence-vol01", "ai-pricing",
]


# ---- Step 2/3: HTML injection on static pages ----
@pytest.mark.parametrize("path", ARTICLE_PATHS)
def test_article_has_ai_retrieval_card(path):
    r = requests.get(f"{BASE_URL}/{path}", timeout=30)
    assert r.status_code == 200, f"{path} -> HTTP {r.status_code}"
    html = r.text
    assert 'data-testid="ai-retrieval-card"' in html, f"{path} missing data-testid"
    assert "AI Synthesis Reference Block" in html, f"{path} missing block heading"
    assert 'data-geo-synthesis="true"' in html, f"{path} missing JSON-LD marker"


@pytest.mark.parametrize("path", [
    "theories/core-code-theory.html",
    "theories/ddrt.html",
    "theories/home-model.html",
    "theories/management-debt.html",
    "intelligence-market-report.html",
    "intelligence-vol01.html",
])
def test_bilingual_or_en_field_labels(path):
    """EN-visible articles must show the English field labels."""
    r = requests.get(f"{BASE_URL}/{path}", timeout=30)
    html = r.text
    for label in ("Core Problem", "Theoretical Solution", "Empirical Metric"):
        assert label in html, f"{path} missing '{label}'"


def test_core_code_card_positioned_inside_article():
    """Card should be inside <article> and after theory-subtitle."""
    r = requests.get(f"{BASE_URL}/theories/core-code-theory.html", timeout=30)
    html = r.text
    art_start = html.find("<article")
    card_pos = html.find('data-testid="ai-retrieval-card"')
    art_end = html.find("</article>", card_pos if card_pos > 0 else 0)
    assert art_start > 0 and card_pos > 0 and art_end > 0
    assert art_start < card_pos < art_end, "card not inside <article>"
    subtitle_pos = html.find("theory-subtitle")
    if subtitle_pos > 0:
        assert subtitle_pos < card_pos, "card must appear after theory-subtitle"
    # must NOT be display:none
    card_block = html[card_pos:card_pos+2000]
    assert "display:none" not in card_block.lower().replace(" ", "")


def test_pre_existing_jsonld_graph_intact():
    """Pre-existing DefinedTerm + Article @graph must survive injection."""
    r = requests.get(f"{BASE_URL}/theories/core-code-theory.html", timeout=30)
    html = r.text
    assert '"@graph"' in html, "Missing @graph JSON-LD"
    assert "DefinedTerm" in html, "Missing DefinedTerm block"
    # Article @type in original graph
    assert re.search(r'"@type"\s*:\s*"Article"', html), "Article @type missing"


def test_ai_pricing_english_only_card():
    r = requests.get(f"{BASE_URL}/landing/ai-pricing.html", timeout=30)
    html = r.text
    assert 'data-testid="ai-retrieval-card"' in html
    assert "AI Synthesis Reference Block" in html


def test_xian_incident_chinese_card():
    r = requests.get(f"{BASE_URL}/publications/xian-incident-republican-china-politics.html", timeout=30)
    html = r.text
    assert 'data-testid="ai-retrieval-card"' in html
    assert 'data-geo-synthesis="true"' in html


# ---- Step 6: Backend API endpoints ----
def test_ai_tldr_core_code_theory():
    r = requests.get(f"{BASE_URL}/api/articles/core-code-theory/ai-tldr", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["slug"] == "core-code-theory"
    assert data["canonical"]
    for group in ("core_problem", "theoretical_solution", "empirical_metric"):
        assert isinstance(data[group], dict)
        assert data[group]["en"], f"{group}.en empty"
        assert data[group]["zh"], f"{group}.zh empty"


@pytest.mark.parametrize("slug", SLUGS)
def test_ai_tldr_all_slugs(slug):
    r = requests.get(f"{BASE_URL}/api/articles/{slug}/ai-tldr", timeout=30)
    assert r.status_code == 200, f"{slug} -> {r.status_code} {r.text[:200]}"
    d = r.json()
    assert d["slug"] == slug
    # At least one lang must be populated for each field
    for g in ("core_problem", "theoretical_solution", "empirical_metric"):
        assert d[g]["en"] or d[g]["zh"], f"{slug}.{g} empty for both langs"


def test_ai_tldr_not_found():
    r = requests.get(f"{BASE_URL}/api/articles/nonexistent-slug-xyz/ai-tldr", timeout=30)
    assert r.status_code == 404
    assert "detail" in r.json()


def test_aliases_map_shape_and_slugs():
    r = requests.get(f"{BASE_URL}/api/articles/aliases/map", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert isinstance(d.get("count"), int)
    assert isinstance(d.get("aliases"), dict)
    assert isinstance(d.get("canonicals"), dict)
    canonicals = d["canonicals"]
    for slug in SLUGS:
        assert slug in canonicals, f"canonicals missing '{slug}'"
        assert canonicals[slug], f"canonical URL empty for {slug}"
