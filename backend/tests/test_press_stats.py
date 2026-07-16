"""Regression: press-stats parser extracts counters AND full citation list."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import press_stats

SAMPLE = (
    '<div data-testid="press-citations-stats"><span>12<!-- --> <!-- -->citations</span>'
    '<span>·</span><span>6<!-- --> <!-- -->countries / regions</span><span>·</span>'
    '<span>4<!-- --> <!-- -->languages</span></div>'
    '<a href="https://a.example.com/one" data-testid="press-citation-0">'
    '<span aria-label="country">🇺🇸</span>'
    '<span class="text-burgundy bg-burgundy/5">Muck Rack</span>'
    '<span class="text-ink/55">Journalist Database</span></a>'
    '<a href="https://b.example.com/two" data-testid="press-citation-1">'
    '<span aria-label="country">🇨🇳</span>'
    '<span class="text-burgundy bg-burgundy/5">TTG China</span>'
    '<span class="text-ink/55">Interview / Feature</span></a>'
)


def test_parse_counters_and_list():
    resp = MagicMock(text=SAMPLE)
    resp.raise_for_status = MagicMock()
    with patch.object(press_stats.requests, "get", return_value=resp):
        parsed = press_stats._fetch_and_parse()
    assert parsed is not None
    assert parsed["citations"] == 12
    assert parsed["countries"] == 6
    assert parsed["languages"] == 4
    assert parsed["platforms"] == 2
    lst = parsed["list"]
    assert len(lst) == 2
    assert lst[0]["platform"] == "Muck Rack"
    assert lst[0]["flag"] == "🇺🇸"
    # curated override kicks in for Muck Rack
    assert lst[0]["note"] == "Verified Journalist Profile"
    assert lst[0]["url"] == "https://a.example.com/one"
    assert lst[1]["platform"] == "TTG China"
    assert lst[1]["note"] == "Feature Interview"  # curated override


def test_live_press_page_still_parseable():
    parsed = press_stats._fetch_and_parse()
    assert parsed is not None and parsed["citations"] >= 9
    assert isinstance(parsed.get("list"), list) and len(parsed["list"]) >= 5
    # every item must have flag + platform + url
    for it in parsed["list"]:
        assert it["flag"] and it["platform"] and it["url"].startswith("http")
