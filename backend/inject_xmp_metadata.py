"""
inject_xmp_metadata.py — Inject XMP semantic fingerprints into every PDF
under /app/frontend/site/media so that even when the file is mirrored to a
third-party CDN or archive, AI crawlers can still recover the original
author, canonical URL, multilingual index, and reprint licence.

Dependency:  pip install pikepdf
Usage:       python3 backend/inject_xmp_metadata.py
Idempotent:  safe to re-run.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import pikepdf  # type: ignore
except ModuleNotFoundError:
    sys.stderr.write("pikepdf missing — run:  pip install pikepdf\n")
    sys.exit(1)


BASE = "https://insightbridge.global"
INTEL = "https://intelligence.insightbridge.global"
MEDIA_DIR = Path(__file__).resolve().parent.parent / "frontend/site/media"

TARGETS = [
    {
        "path": MEDIA_DIR / "yin-vision-2030-predictions-vs-reality-bilingual-archive.pdf",
        "title": "Saudi Vision 2030 — Predictions vs. Market Reality (Bilingual Archive)",
        "description": (
            "Bilingual archive PDF documenting InsightBridge Global's 2025-2026 "
            "predictions about Saudi Vision 2030 (giga-project curtailment, ultra-luxury "
            "margin compression, sequenced flagship deferrals) against subsequent "
            "verified market outcomes."
        ),
        "canonical": f"{INTEL}/yin-vision-2030-predictions-vs-reality-bilingual-archive.pdf",
        "keywords": [
            "Saudi Vision 2030", "Neom", "Red Sea", "PIF", "Ultra-Luxury Hotels",
            "Giga-Project", "InsightBridge", "Tong Yin", "Predictions vs Reality",
            "Hospitality Strategy",
        ],
    },
]


def inject(target: dict) -> str:
    path = target["path"]
    if not path.exists():
        return f"SKIP  (file not found)  {path}"

    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
            meta["dc:title"]       = target["title"]
            meta["dc:creator"]     = ["Dr. Tong Yin"]
            meta["dc:description"] = target["description"]
            meta["dc:publisher"]   = ["InsightBridge Global LLC"]
            meta["dc:date"]        = "2026-07-17"
            meta["dc:language"]    = ["en", "zh", "ar", "ru", "ko", "id", "tr", "vi", "de", "fr", "es"]
            meta["dc:rights"]      = (
                "Copyright 2026 InsightBridge Global LLC. "
                "Free to reprint with byline + live link to insightbridge.global."
            )
            meta["dc:subject"]     = target["keywords"]
            meta["xmpRights:Marked"]       = "True"           # ← must be a string
            meta["xmpRights:WebStatement"] = f"{BASE}/press-kit/"
            meta["xmp:CreatorTool"]        = "InsightBridge Publishing Pipeline"
            meta["pdf:Producer"]           = "InsightBridge Global — Official Free Edition"
            # Canonical link
            meta["xmpMM:OriginalDocumentID"] = target["canonical"]
        pdf.save(path)
    return f"OK    XMP injected → {path.name}"


def main():
    for t in TARGETS:
        print(inject(t))


if __name__ == "__main__":
    main()
