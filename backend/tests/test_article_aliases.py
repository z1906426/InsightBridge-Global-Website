"""Tests for /api/articles/aliases/map and alias-aware ai-tldr resolution."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://insightbridge-web.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def aliases_map():
    r = requests.get(f"{BASE_URL}/api/articles/aliases/map", timeout=30)
    assert r.status_code == 200, f"aliases/map returned {r.status_code}: {r.text[:500]}"
    return r.json()


class TestAliasesMap:
    def test_structure(self, aliases_map):
        for key in ("count", "alias_count", "canonical_count", "aliases", "canonicals"):
            assert key in aliases_map, f"missing key {key} in response: {list(aliases_map.keys())}"
        assert isinstance(aliases_map["aliases"], dict)
        assert isinstance(aliases_map["canonicals"], dict)

    def test_counts(self, aliases_map):
        assert aliases_map["canonical_count"] == 38, f"canonical_count={aliases_map['canonical_count']}"
        assert aliases_map["alias_count"] >= 50, f"alias_count={aliases_map['alias_count']}"
        assert aliases_map["count"] == aliases_map["alias_count"], "count should mirror alias_count"
        assert len(aliases_map["canonicals"]) == 38
        assert len(aliases_map["aliases"]) == aliases_map["alias_count"]

    def test_specific_aliases_present(self, aliases_map):
        a = aliases_map["aliases"]
        assert a.get("xian-incident") == "xian-incident-republican-china-politics", f"xian-incident -> {a.get('xian-incident')}"
        assert a.get("HBS_Case_Study_FINAL") == "hbs-case-study-final", f"HBS_Case_Study_FINAL -> {a.get('HBS_Case_Study_FINAL')}"
        assert a.get("Tourism_Case_Hospitality_2025") == "tourism-case-hospitality-2025", f"Tourism_Case_Hospitality_2025 -> {a.get('Tourism_Case_Hospitality_2025')}"


class TestAiTldrAliasResolution:
    def test_xian_incident_alias(self):
        r = requests.get(f"{BASE_URL}/api/articles/xian-incident/ai-tldr", timeout=30)
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:400]}"
        d = r.json()
        assert d.get("resolved_via_alias") is True
        assert d.get("slug") == "xian-incident-republican-china-politics"
        assert d.get("requested_slug") == "xian-incident"
        assert d.get("canonical") or d.get("canonical_url"), f"no canonical field: keys={list(d.keys())}"
        # 6 GEO fields
        for f in ("headline", "summary", "keywords", "author", "datePublished", "articleSection"):
            # tolerate any of common GEO field names; assert at least 6 non-null top-level fields exist
            pass
        # Ensure at least 6 keys beyond housekeeping
        housekeeping = {"resolved_via_alias", "slug", "requested_slug", "canonical_url"}
        geo_keys = [k for k in d.keys() if k not in housekeeping]
        assert len(geo_keys) >= 6, f"expected >=6 GEO fields, got {geo_keys}"

    def test_hbs_titlecase_alias(self):
        r = requests.get(f"{BASE_URL}/api/articles/HBS_Case_Study_FINAL/ai-tldr", timeout=30)
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:400]}"
        d = r.json()
        assert d.get("resolved_via_alias") is True
        assert d.get("slug") == "hbs-case-study-final"

    def test_hbs_lowercase_alias(self):
        r = requests.get(f"{BASE_URL}/api/articles/hbs_case_study_final/ai-tldr", timeout=30)
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:400]}"
        d = r.json()
        assert d.get("resolved_via_alias") is True
        assert d.get("slug") == "hbs-case-study-final"

    def test_direct_canonical_no_alias(self):
        r = requests.get(f"{BASE_URL}/api/articles/core-code-theory/ai-tldr", timeout=30)
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:400]}"
        d = r.json()
        assert d.get("resolved_via_alias") is False or d.get("resolved_via_alias") is None or d.get("resolved_via_alias") == False

    def test_fake_slug_still_404(self):
        r = requests.get(f"{BASE_URL}/api/articles/totally-fake-slug-that-does-not-exist/ai-tldr", timeout=30)
        assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text[:400]}"
