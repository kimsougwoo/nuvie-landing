# -*- coding: utf-8 -*-
"""2026-10-07 approved phone-contact copy stays consistent across surfaces."""
import json
import re
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).parent


def _read(name):
    return (ROOT / name).read_text(encoding="utf-8")


def _rooms():
    data = json.loads(_read("rooms.json"))
    return data, {room["slug"]: room for room in data["rooms"]}


def _phone_values():
    data, _ = _rooms()
    tel = data.get("business", {}).get("tel")
    assert isinstance(tel, str) and re.fullmatch(r"070\d{8}", tel), (
        "rooms.json business.tel must be the 070 href target digits"
    )
    display = f"{tel[:3]}-{tel[3:7]}-{tel[7:]}"
    return tel, display


class _AnchorCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.anchors = []
        self._current = None
        self._anchor_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            if self._current is None:
                self._current = {"attrs": dict(attrs), "text": "", "raw": ""}
            self._anchor_depth += 1
        if self._current is not None:
            self._current["raw"] += self.get_starttag_text() or ""

    def handle_data(self, data):
        if self._current is not None:
            self._current["text"] += data
            self._current["raw"] += data

    def handle_comment(self, data):
        if self._current is not None:
            self._current["raw"] += "<!--" + data + "-->"

    def handle_endtag(self, tag):
        if self._current is None:
            return
        self._current["raw"] += f"</{tag}>"
        if tag == "a":
            self._anchor_depth -= 1
            if self._anchor_depth == 0:
                self.anchors.append(self._current)
                self._current = None


def _anchors(html):
    parser = _AnchorCollector()
    parser.feed(html)
    return parser.anchors


def _jsonld_objects(html):
    blocks = re.findall(
        r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script\s*>',
        html,
        flags=re.I | re.S,
    )
    parsed = []
    for block in blocks:
        value = json.loads(block.strip())
        parsed.extend(value if isinstance(value, list) else [value])
    return parsed


def test_rooms_json_tel_matches_every_index_tel_href_and_display_copy():
    tel, display = _phone_values()
    html = _read("index.html")
    hrefs = re.findall(r'href=["\']tel:([^"\']+)', html, flags=re.I)
    assert hrefs, "index.html must retain a telephone link"
    assert set(hrefs) == {tel}, "every index.html tel: href must use rooms.json business.tel"
    assert html.count(display) >= 2, "formatted phone must appear in the index contact card and footer"


def test_localbusiness_jsonld_uses_canonical_phone_without_phone_hours_schema():
    tel, _ = _phone_values()
    html = _read("index.html")
    objects = _jsonld_objects(html)
    business = next(
        (item for item in objects if item.get("@type") == "LocalBusiness"), None
    )
    assert business is not None, "LocalBusiness JSON-LD was not found"
    telephone = re.sub(r"\D", "", str(business.get("telephone", "")))
    if telephone.startswith("82"):
        telephone = "0" + telephone[2:]
    assert telephone == tel, "LocalBusiness telephone must normalize to rooms.json business.tel"
    assert "openingHoursSpecification" not in html, "do not add phone hours as business opening hours"


def test_a_room_and_llms_txt_publish_the_canonical_contact_copy():
    tel, display = _phone_values()
    data, rooms = _rooms()
    a, b = rooms["a"], rooms["b"]
    a_html = _read("a.html")
    b_html = _read("b.html")
    llms = _read("llms.txt")

    expected_inquiry = "문의는 전화(10:00~19:00) 또는 아워플레이스 메시지"
    assert a.get("inquiryLine") == expected_inquiry
    assert a["inquiryLine"] in a_html
    footer_template = [
        "예약: 아워플레이스",
        "문의: 전화 {business.tel}(10:00~19:00) · 아워플레이스 메시지",
    ]
    assert a.get("footerLines") == footer_template
    rendered_footer = footer_template[1].replace("{business.tel}", display)
    assert rendered_footer in a_html
    assert rendered_footer in _read("index.html")
    assert display in a_html

    assert f"문의: 전화 {display}(10:00~19:00, 문자 불가) 또는 아워플레이스 메시지" in llms
    assert tel not in llms

    # B remains on its existing copy and receives none of A's new phone-only content.
    assert b.get("inquiryLine") == "문의는 아워플레이스 메시지"
    assert b.get("footerLines") == ["예약·문의: 아워플레이스"]
    assert b["inquiryLine"] in b_html
    assert all(line in b_html for line in b["footerLines"])
    assert tel not in b_html and display not in b_html
    assert "문자는 받지 않아요" not in b_html
    assert "전화(10:00~19:00)" not in b_html
    assert "문의: 전화" not in b_html


def test_hourplace_booking_anchors_do_not_contain_phone_details():
    tel, display = _phone_values()
    html = _read("index.html")
    booking_ids = {"end-a", "end-b", "book-mobile", "book-mobile-b"}
    booking_anchors = []
    for anchor in _anchors(html):
        attrs = anchor["attrs"]
        href = attrs.get("href", "")
        if (
            "hourplace.co.kr/place" in href
            or "data-book" in attrs
            or "data-hp" in attrs
            or attrs.get("id") in booking_ids
        ):
            booking_anchors.append(anchor)
    assert booking_anchors, "no booking anchors were found to validate"
    for anchor in booking_anchors:
        content = anchor["raw"]
        assert tel not in content and display not in content, (
            "telephone details must not appear inside an Hourplace booking anchor"
        )


def test_phone_buttons_are_at_least_44px_tall():
    html = _read("index.html")
    tel, _ = _phone_values()
    buttons = [
        anchor for anchor in _anchors(html)
        if anchor["attrs"].get("href", "").lower() == f"tel:{tel}"
        and "btn" in anchor["attrs"].get("class", "").split()
    ]
    assert buttons, "no phone button anchor found"
    assert all(
        re.search(r"min-height\s*:\s*(?:4[4-9]|[5-9]\d|\d{3,})px", anchor["raw"].split(">", 1)[0])
        for anchor in buttons
    ), (
        "phone CTA must specify a minimum height of at least 44px"
    )
