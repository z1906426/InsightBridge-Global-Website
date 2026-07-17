"""Regression tests for the main-site RSS feed generator."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from rss_feed import RSS_OUTPUT_PATH, SECTIONS, SITE_URL, build_rss_xml, write_rss


NS = {"atom": "http://www.w3.org/2005/Atom"}


def test_rss_xml_is_well_formed():
    xml = build_rss_xml()
    root = ET.fromstring(xml)
    assert root.tag == "rss"
    assert root.attrib.get("version") == "2.0"


def test_rss_contains_all_declared_sections():
    xml = build_rss_xml()
    root = ET.fromstring(xml)
    channel = root.find("channel")
    assert channel is not None

    # guid is the stable, un-tagged identifier — use it, not <link>, for lookup
    guids = {item.findtext("guid") for item in channel.findall("item")}
    for s in SECTIONS:
        expected = f"{SITE_URL}{s['path']}"
        assert expected in guids, f"missing {expected} in RSS"


def test_rss_links_carry_utm_but_guids_do_not():
    """Links point to tagged URLs so GA/Clarity/Yandex attribute the click to
    the RSS channel. guid stays clean so RSS readers de-dupe correctly."""
    xml = build_rss_xml()
    root = ET.fromstring(xml)
    channel = root.find("channel")
    items = channel.findall("item")
    assert items, "RSS has no items"
    for item in items:
        link = item.findtext("link")
        guid = item.findtext("guid")
        assert "utm_source=rss" in link, f"link missing UTM: {link}"
        assert "utm_medium=feed" in link
        assert "utm_campaign=rss-main-site" in link
        assert "utm_content=" in link
        assert "utm_" not in (guid or ""), f"guid must NOT have UTM: {guid}"
        # guid must remain a valid parseable URL for the same domain
        assert guid.startswith(SITE_URL)


def test_rss_channel_metadata():
    xml = build_rss_xml()
    root = ET.fromstring(xml)
    channel = root.find("channel")
    assert channel.findtext("title")
    assert channel.findtext("link") == f"{SITE_URL}/"
    assert channel.findtext("language") == "en-US"
    assert channel.findtext("lastBuildDate")
    # atom:link self-reference
    atom_link = channel.find("atom:link", NS)
    assert atom_link is not None
    assert atom_link.attrib.get("href") == f"{SITE_URL}/rss.xml"
    assert atom_link.attrib.get("rel") == "self"


def test_write_rss_produces_file(tmp_path: Path):
    target = tmp_path / "rss.xml"
    result = write_rss(target)
    assert result["ok"] is True
    assert target.exists()
    # Valid XML on disk
    ET.parse(str(target))
    assert target.stat().st_size > 500


def test_production_rss_file_exists_and_parses():
    """Guard: /app/frontend/site/rss.xml must always be parseable if present."""
    if not RSS_OUTPUT_PATH.exists():
        pytest.skip("rss.xml not yet generated")
    ET.parse(str(RSS_OUTPUT_PATH))
