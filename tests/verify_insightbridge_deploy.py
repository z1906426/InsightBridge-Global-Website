#!/usr/bin/env python3
"""Focused bug verification for InsightBridge deployed static HTML freshness."""
from __future__ import annotations

import json
import re
import ssl
import sys
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = "https://insightbridge-web.preview.emergentagent.com"
PATHS = ["/", "/index.html", "/zh.html", "/about.html"]

class IdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k == "id" and v:
                self.ids.add(v)


def fetch(path: str):
    url = BASE + path
    req = Request(url, headers={"User-Agent": "InsightBridgeBugVerification/1.0"})
    try:
        with urlopen(req, timeout=30, context=ssl.create_default_context()) as resp:
            raw = resp.read()
            return {"path": path, "url": url, "status": resp.status, "headers": dict(resp.headers), "body": raw.decode("utf-8", errors="replace")}
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"path": path, "url": url, "status": e.code, "headers": dict(e.headers), "body": body, "error": str(e)}
    except URLError as e:
        return {"path": path, "url": url, "status": None, "headers": {}, "body": "", "error": repr(e)}


def has_literal(html: str, pattern: str) -> bool:
    return pattern in html


def anchor_ids(html: str) -> set[str]:
    p = IdParser()
    p.feed(html)
    return p.ids


def jsonld_ids(html: str) -> list[str]:
    ids = []
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.I | re.S):
        block = m.group(1)
        ids.extend(re.findall(r'"@id"\s*:\s*"https://insightbridge\.global/#[^"]+"', block))
    return [x.split('"')[-2] for x in ids]


def main() -> int:
    pages = {p: fetch(p) for p in PATHS}
    index = pages["/index.html"]["body"]
    root = pages["/"]["body"]
    zh = pages["/zh.html"]["body"]
    about = pages["/about.html"]["body"]

    index_ids = anchor_ids(index)
    about_ids = anchor_ids(about)
    same_index_root = (index[:500] == root[:500]) if root and index else False
    root_hash = hash(root)
    index_hash = hash(index)

    checks = []
    def check(name, passed, evidence):
        checks.append({"name": name, "passed": bool(passed), "evidence": evidence})

    check("homepage_status_200", pages["/"]["status"] == 200 and pages["/index.html"]["status"] == 200,
          {"root_status": pages["/"]["status"], "index_status": pages["/index.html"]["status"], "root_content_type": pages["/"]["headers"].get("Content-Type"), "index_content_type": pages["/index.html"]["headers"].get("Content-Type")})
    check("index_defined_term_set", '"@type": "DefinedTermSet"' in index or '"@type":"DefinedTermSet"' in index,
          {"defined_term_set_count": index.count("DefinedTermSet"), "has_vocabulary_id": "https://insightbridge.global/#vocabulary" in index})
    check("zh_defined_term_set", '"@type": "DefinedTermSet"' in zh or '"@type":"DefinedTermSet"' in zh,
          {"defined_term_set_count": zh.count("DefinedTermSet"), "has_vocabulary_id": "https://insightbridge.global/#vocabulary" in zh})
    required_home_anchors = ["contact", "term", "faq"]
    missing_home_anchors = [a for a in required_home_anchors if a not in index_ids]
    check("index_required_contact_term_faq_anchor_ids", not missing_home_anchors,
          {"required_home_anchors": required_home_anchors, "missing_home_anchors": missing_home_anchors, "present_required_home_anchors": [a for a in required_home_anchors if a in index_ids]})
    check("about_person_anchor_and_identity_card", "person" in about_ids and "AI Synthesis Reference Block / Executive TL;DR" in about and "Identity:" in about,
          {"person_in_ids": "person" in about_ids, "has_ai_synthesis_card_text": "AI Synthesis Reference Block / Executive TL;DR" in about, "has_identity_label": "Identity:" in about})
    check("about_reprint_kits_id_block", "reprint-kits-card" in about_ids,
          {"reprint_id_in_ids": "reprint-kits-card" in about_ids, "has_data_testid_reprint_kits_card": 'data-testid="reprint-kits-card"' in about, "note": "Requirement asked for id=\"reprint-kits-card\"; data-testid alone is not the same HTML fragment anchor."})

    ids = jsonld_ids(index)
    fragment_ids = sorted({u.split("#", 1)[1] for u in ids if "#" in u})
    missing_index = [frag for frag in fragment_ids if frag not in index_ids]
    # For the specific known graph entities, require visible anchors for Person and Organization on index.html.
    expected_known = ["dr-tong-yin", "org"]
    missing_known = [frag for frag in expected_known if frag not in index_ids]
    check("index_person_org_jsonld_anchor_fragments_resolve", not missing_known,
          {"jsonld_fragment_ids_seen": fragment_ids, "index_anchor_ids_intersection": sorted(set(fragment_ids) & index_ids), "missing_known_person_org_fragments": missing_known, "all_missing_jsonld_fragments_on_index": missing_index[:20]})

    summary = {
        "base": BASE,
        "pages": {p: {"status": pages[p]["status"], "bytes": len(pages[p]["body"]), "error": pages[p].get("error"), "cache_control": pages[p]["headers"].get("Cache-Control"), "server": pages[p]["headers"].get("Server")} for p in PATHS},
        "same_index_root_prefix": same_index_root,
        "root_hash": root_hash,
        "index_hash": index_hash,
        "checks": checks,
        "all_passed": all(c["passed"] for c in checks),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["all_passed"] else 1

if __name__ == "__main__":
    sys.exit(main())
