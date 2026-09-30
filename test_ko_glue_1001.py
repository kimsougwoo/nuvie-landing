# -*- coding: utf-8 -*-
"""10-01 대표 «줄바꿈 처리를 하든 얼른 전면재수정» — 모바일 줄바꿈 잠금(글자 불변).
라이브 캡처(320·360·390·430)에서 본 것: «카페·/자연광», «(12시간·/부가세 포함)», «최소 / 2시간», «팔각 / 소프트박스», «부가세 / 포함»,
«평점 5.0 / / 5», 줄 머리 «·». 한국어 낱말을 통째로 유지(keep-all)하고, 문단 안 가운뎃점·빗금 앞 공백과 짧은 괄호·두 글자 낱말 짝은
빌드 때 줄바꿈 없는 공백으로 붙인다(ko_glue.py)."""
import re
from pathlib import Path

from ko_glue import glue_html

ROOT = Path(__file__).parent
CSS = (ROOT / "styles.css").read_text(encoding="utf-8")


def test_body_keeps_korean_words_whole():
    assert re.search(r"body\{word-break:keep-all;overflow-wrap:break-word\}", CSS)


def test_hub_and_room_pages_are_already_glued():
    for name in ("index.html", "a.html", "b.html"):
        html = (ROOT / name).read_text(encoding="utf-8")
        assert glue_html(html) == html, f"{name}: 줄바꿈 다듬기가 안 된 문단이 있다(python ko_glue.py {name} · 룸 페이지는 build_rooms.py)"


def test_room_build_applies_glue():
    src = (ROOT / "build_rooms.py").read_text(encoding="utf-8")
    assert "from ko_glue import glue_html" in src and "out = glue_html(out)" in src


def test_glue_rules_on_samples():
    NB = " "
    assert glue_html("<p>평일 40,000원 · 최소 2시간</p>") == "<p>평일" + NB + "40,000원" + NB + "· 최소" + NB + "2시간</p>"
    assert glue_html("<p>평점 5.0 / 5 · 3건</p>").count(" / ") == 0
    WJ = "\u2060"
    assert "(12시간" + WJ + "·" + WJ + "부가세" + NB + "포함)" in glue_html("<p>75만 원(12시간·부가세 포함)</p>"), "괄호 안·붙은 가운뎃점 앞에서 안 끊김"
    assert glue_html('<p>이용 <a href="#">A룸 예약 →</a></p>').endswith('<a href="#">A룸 예약 →</a></p>'), "링크 글자는 그대로"
    assert glue_html("<h2>두 개의 컨셉룸</h2>") == "<h2>두 개의 컨셉룸</h2>", "문단 밖(제목·버튼)은 그대로"
