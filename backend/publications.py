"""
Publications URL extractor.

Parses the homepage (`index.html`) Research & Publications section
(<section id="page-publications">) and returns the canonical absolute
URLs for every linked publication (PDF / DOCX / sub-page).

Used by:
  - POST /api/seo/push-publications  (manual push of pub URLs)
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List
from urllib.parse import urljoin

SITE_DOMAIN = os.environ.get("SITE_DOMAIN", "insightbridge.global")
SITE_BASE = f"https://{SITE_DOMAIN}/"

INDEX_HTML = Path(__file__).resolve().parent.parent / "frontend" / "site" / "index.html"


def extract_publication_urls() -> List[str]:
    """Return the deduped list of absolute URLs linked inside
    the Research & Publications section of index.html."""
    if not INDEX_HTML.exists():
        return []

    html = INDEX_HTML.read_text(encoding="utf-8")

    start_marker = 'id="page-publications"'
    end_marker = 'id="page-cases"'
    start = html.find(start_marker)
    end = html.find(end_marker, start)
    if start == -1 or end == -1:
        return []

    block = html[start:end]
    hrefs = re.findall(r'href="([^"]+)"', block)

    seen: set[str] = set()
    out: List[str] = []
    for h in hrefs:
        # Keep only doc / pub artefacts hosted on our domain
        if h.startswith("#") or h.startswith("mailto:") or h.startswith("tel:"):
            continue
        if "linkedin.com" in h or "javascript:" in h.lower():
            continue
        # Absolute? keep if same host; relative? join to base
        if h.startswith("http://") or h.startswith("https://"):
            if SITE_DOMAIN not in h:
                continue  # skip off-domain hrefs (linkedin etc)
            url = h
        else:
            url = urljoin(SITE_BASE, h.lstrip("/"))
        if url in seen:
            continue
        seen.add(url)
        out.append(url)

    return out
