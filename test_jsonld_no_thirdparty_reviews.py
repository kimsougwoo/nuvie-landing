# -*- coding: utf-8 -*-
"""구조화 데이터에 다른 사이트(아워플레이스) 후기·별점을 싣지 않는다 (2026-09-28).

구글 리뷰 스니펫 가이드라인(2026-09-08 갱신본, 09-28 재조회):
  - "Don't aggregate reviews or ratings from other websites."
  - "If the entity that's being reviewed controls the reviews about itself, their pages that use
     LocalBusiness or any other type of Organization structured data are ineligible for star review feature."
우리 후기는 전부 아워플레이스에서 가져온 것이라 JSON-LD 의 aggregateRating·review 는 규칙 위반이다.
화면에 보이는 후기(출처 표기 포함)는 그대로 둔다 — 여기서 막는 것은 구조화 데이터뿐이다.
"""
import json
import os
import re

import build_rooms as R

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = ["index.html", "a.html", "b.html"]
BANNED = ("aggregateRating", "review")


def _ld_nodes(html):
    for block in re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.S):
        data = json.loads(block)
        for node in (data if isinstance(data, list) else [data]):
            yield node


def _walk_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_keys(v)


def test_published_pages_have_no_review_markup():
    bad = []
    for page in PAGES:
        html = open(os.path.join(HERE, page), encoding="utf-8").read()
        for node in _ld_nodes(html):
            hit = sorted({k for k in _walk_keys(node) if k in BANNED})
            if hit:
                bad.append((page, node.get("@type"), hit))
    assert not bad, f"JSON-LD 에 다른 사이트 후기·별점이 남아 있다: {bad}"


def test_room_builder_does_not_emit_review_markup():
    """생성기가 다시 넣지 않아야 한다 — 다음 build_rooms.py 실행에서 되살아나면 소용없다."""
    pages = {k: v for k, v in R.generate().items() if k.endswith(".html")}
    assert pages, "generate() 가 룸 페이지를 내지 않았다"
    for name, html in pages.items():
        for node in _ld_nodes(html):
            hit = set(_walk_keys(node)) & set(BANNED)
            assert not hit, (name, node.get("@type"), hit)
