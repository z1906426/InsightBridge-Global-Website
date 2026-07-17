"""Regression: Baidu URL smart-selector honours must-push list + cooldown."""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import seo_push


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class _FakeCursor:
    def __init__(self, docs): self._docs = list(docs)
    def sort(self, *_a, **_kw): return self
    def __aiter__(self):
        self._it = iter(self._docs)
        return self
    async def __anext__(self):
        try: return next(self._it)
        except StopIteration: raise StopAsyncIteration


class _FakeColl:
    def __init__(self, docs=None): self._docs = docs or []
    def find(self, query=None, projection=None):
        return _FakeCursor(self._docs)


class _FakeDB:
    def __init__(self, docs=None):
        self.baidu_url_lastpush = _FakeColl(docs)


def test_must_push_always_first_and_included():
    db = _FakeDB()
    candidates = ["https://insightbridge.global/", "https://insightbridge.global/about.html"]
    selected = _run(seo_push._select_baidu_urls(db, candidates))
    assert selected[:3] == seo_push.BAIDU_MUST_PUSH
    assert len(selected) <= seo_push.BAIDU_PUSH_CAP


def test_cooldown_filters_recently_pushed_candidates():
    now = datetime.now(timezone.utc)
    fresh = (now - timedelta(days=1)).isoformat()
    docs = [
        {"url": "https://insightbridge.global/", "pushed_at": fresh},
        {"url": "https://insightbridge.global/about.html", "pushed_at": fresh},
    ]
    db = _FakeDB(docs=docs)
    candidates = [
        "https://insightbridge.global/",           # in cooldown → skip
        "https://insightbridge.global/about.html", # in cooldown → skip
        "https://insightbridge.global/zh.html",    # fresh → include
    ]
    selected = _run(seo_push._select_baidu_urls(db, candidates))
    for u in seo_push.BAIDU_MUST_PUSH:
        assert u in selected
    non_must = [u for u in selected if u not in seo_push.BAIDU_MUST_PUSH]
    assert "https://insightbridge.global/zh.html" in non_must
    assert "https://insightbridge.global/" not in non_must


def test_no_db_falls_back_to_priority_only():
    """When db is None, no cooldown — just priority + cap."""
    candidates = [f"https://insightbridge.global/p{i}.html" for i in range(20)]
    selected = _run(seo_push._select_baidu_urls(None, candidates))
    assert selected[:3] == seo_push.BAIDU_MUST_PUSH
    assert len(selected) == seo_push.BAIDU_PUSH_CAP
