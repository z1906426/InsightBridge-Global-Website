"""
Regression: sister-site headlines must be sorted by article publish date,
not by sitemap <lastmod> (which can be skewed by bulk republishes).
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sister_articles import _fetch_rss_articles, ARTICLES_FOR_BRIEF  # noqa: E402


def test_rss_returns_articles_sorted_newest_first():
    items = _fetch_rss_articles(ARTICLES_FOR_BRIEF)
    assert len(items) > 0, "RSS feed returned zero articles"
    # All entries should look like article URLs
    for it in items:
        assert "/articles/" in it["loc"]
        assert it.get("title")
    # Confirm strictly non-increasing publish dates
    pubs = [it.get("published") for it in items]
    assert all(pubs), f"Some items have no published date: {pubs}"
    assert pubs == sorted(pubs, reverse=True), (
        "Headlines not sorted newest-first by publish date: " + str(pubs)
    )


if __name__ == "__main__":
    test_rss_returns_articles_sorted_newest_first()
    print("OK")
