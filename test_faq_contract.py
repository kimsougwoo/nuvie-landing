"""FAQ 화면 문구와 FAQPage JSON-LD의 단일 정합성 계약."""
import json
import re
from html import unescape
from pathlib import Path


HERE = Path(__file__).resolve().parent


def _normalize_visible_text(fragment):
    fragment = re.sub(r"<br\s*/?>", " ", fragment, flags=re.I)
    fragment = re.sub(r"</(?:li|p|div|ul)>", " ", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return " ".join(unescape(fragment).split())


def test_faq_details_text_matches_faqpage_ld():
    html = (HERE / "index.html").read_text(encoding="utf-8")
    blocks = re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.S
    )
    faq = next(json.loads(block) for block in blocks if json.loads(block).get("@type") == "FAQPage")
    ld_text = [item["acceptedAnswer"]["text"] for item in faq["mainEntity"]]
    details_text = [
        _normalize_visible_text(fragment)
        for fragment in re.findall(
            r"<details\b[^>]*>.*?<summary\b.*?</summary>(.*?)</details>",
            html,
            re.S,
        )
    ]
    assert len(details_text) == len(ld_text) == 10
    assert details_text == ld_text
