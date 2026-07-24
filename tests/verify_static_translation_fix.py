#!/usr/bin/env python3
"""Focused verification for InsightBridge static translation copy fix."""

import os
import re
import sys
import urllib.request


ROOT = "/app/frontend"
ENV_PATH = os.path.join(ROOT, ".env")


def read_preview_url() -> str:
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.strip().split("=", 1)[1].rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not found")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "bug-verification/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise RuntimeError(f"{url} returned HTTP {resp.status}")
        return resp.read().decode("utf-8", errors="replace")


def main() -> int:
    base = read_preview_url()
    pages = {
        "index": fetch(base + "/index.html"),
        "about": fetch(base + "/about.html"),
        "zh": fetch(base + "/zh.html"),
    }

    index = pages["index"]
    standalone_old = re.findall(r"(?<!桥)全球洞察", index)
    results = {
        "preview_base": base,
        "index_new_cn_exact_count": index.count("洞见桥全球洞察"),
        "index_standalone_old_count": len(standalone_old),
        "index_lone_english_nav_count": index.count('<span class="lang-en">Intelligence</span>'),
        "index_full_english_span_count": index.count('<span class="lang-en">InsightBridge Global Intelligence</span>'),
        "index_lab_new_count": index.count("洞见桥全球实验室"),
        "index_lab_old_count": index.count("环球洞见实验室"),
        "index_duplicate_bad_cn_count": index.count("洞见桥洞见桥全球洞察"),
        "about_standalone_old_count": len(re.findall(r"(?<!桥)全球洞察", pages["about"])),
        "zh_standalone_old_count": len(re.findall(r"(?<!桥)全球洞察", pages["zh"])),
    }

    for key, value in results.items():
        print(f"{key}: {value}")

    failures = []
    if results["index_new_cn_exact_count"] != 6:
        failures.append("index.html does not contain exactly 6 occurrences of 洞见桥全球洞察")
    if results["index_standalone_old_count"] != 0:
        failures.append("index.html still contains standalone old 全球洞察")
    if results["index_lone_english_nav_count"] != 0:
        failures.append("index.html still contains lone English nav Intelligence span")
    if results["index_full_english_span_count"] < 3:
        failures.append("index.html contains fewer than 3 full English label spans")
    if results["about_standalone_old_count"] != 0 or results["zh_standalone_old_count"] != 0:
        failures.append("about.html or zh.html still contains standalone old 全球洞察")
    if results["index_lab_new_count"] != 2 or results["index_lab_old_count"] != 0:
        failures.append("Lab translation regression check failed")
    if results["index_duplicate_bad_cn_count"] != 0:
        failures.append("index.html contains malformed duplicated Chinese name 洞见桥洞见桥全球洞察")

    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("All focused static translation checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())