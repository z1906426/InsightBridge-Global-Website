"""Regression: press-stats parser extracts counters from sister-site SSR HTML."""
import re
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import press_stats

SAMPLE = (
    '<div data-testid="press-citations-stats"><span>12<!-- --> <!-- -->citations</span>'
    '<span>·</span><span>6<!-- --> <!-- -->countries / regions</span><span>·</span>'
    '<span>4<!-- --> <!-- -->languages</span></div>'
    '<a data-testid="press-citation-0"></a><a data-testid="press-citation-1"></a>'
)


def test_parse_counters():
    resp = MagicMock(text=SAMPLE)
    resp.raise_for_status = MagicMock()
    with patch.object(press_stats.requests, "get", return_value=resp):
        stats = press_stats._fetch_and_parse()
    assert stats == {"citations": 12, "countries": 6, "languages": 4, "platforms": 2}


def test_live_press_page_still_parseable():
    stats = press_stats._fetch_and_parse()
    assert stats is not None and stats["citations"] >= 9
