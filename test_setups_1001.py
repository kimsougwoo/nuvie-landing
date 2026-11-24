# -*- coding: utf-8 -*-
"""/a «블랙 호리존을 이렇게 꾸몄어요» 섹션 계약(2026-10-01 대표 «A룸 상세페이지에 블랙호리존 꾸며놓았던 사진들 따로 섹션으로 …
* 매일 조금씩 디테일이 달라질 순 있습니다 표기는 해야합니다» · «그동안 만들어놓은 내역들인거니까요»).

막는 사고
  ① 11/1 이 지나도 «할로윈 세팅 · 10월 31일까지»가 남아 손님이 지금도 있다고 오해한다.
  ② 대표 표기(디테일이 달라질 수 있다)가 빠진다.
  ③ B룸(11/11 문구 동결)에 섹션·빈 줄이 새어 든다.
"""
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("build_rooms", ROOT / "build_rooms.py")
BR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BR)
CAT = json.loads((ROOT / "rooms.json").read_text(encoding="utf-8"))
ROOMS = CAT.get("rooms", CAT)
ROOMS = ROOMS if isinstance(ROOMS, list) else list(ROOMS.values())
A = next(r for r in ROOMS if r.get("slug") == "a" or r.get("id") == "a")
B = next(r for r in ROOMS if r.get("slug") == "b" or r.get("id") == "b")


def _visible(html, attr):
    m = re.search(r"<span data-%s( hidden)?>" % attr, html)
    assert m, attr
    return m.group(1) is None


def test_a_setups_has_no_season_label():
    """11-22: A룸은 상시 세팅 기록으로 바꿔 «지난 세팅»/«10월 31일까지» 라벨과 날짜 스크립트를 넣지 않는다."""
    html = BR.render_setups(A, today="2026-10-31")
    assert 'id="setupSeason"' not in html
    assert "data-until" not in html
    assert "지난 세팅" not in html
    assert "toISOString().slice(0,10)" not in html


def test_b_setups_season_still_rendered_if_present():
    """season 이 있는 방은 기존 «지금/지난» 전환이 그대로 동작해야 한다."""
    room = {"setups": {"title": "t", "intro": "i", "note": "n",
                       "season": {"until": "2026-11-01", "now": "지금 세팅", "past": "지난 세팅"},
                       "items": [{"src": "/img/aset-1001-1.jpg", "alt": "x"}]}}
    before = BR.render_setups(room, today="2026-10-31")
    after = BR.render_setups(room, today="2026-11-01")
    assert _visible(before, "now") and not _visible(before, "past")
    assert _visible(after, "past") and not _visible(after, "now")


def test_owner_note_present_and_no_shoot_dates():
    """10-01 대표 «일자는 빼주세요» — 사진 아래 촬영일·alt 속 날짜를 쓰지 않는다."""
    html = (ROOT / "a.html").read_text(encoding="utf-8").replace(chr(0xa0), " ").replace(chr(0x2060), "")
    sec = re.search(r'<section id="setups">(.*?)</section>', html, re.S).group(1)
    assert "매일 조금씩 디테일이 달라질 수 있습니다" in sec
    assert "A룸을 입맛대로 세팅해보세요" in sec
    assert "aset-1001-12" not in sec   # 원창 장식 사진은 공간 갤러리로(같은 날 대표 지시)
    all_items = (A["setups"].get("hero") or []) + (A["setups"].get("trio") or []) + A["setups"]["items"]
    imgs = re.findall(r"<img [^>]*>", sec)
    assert len(imgs) == len(all_items) >= 5   # 11-24: hero(1)+trio(3)+2열(2)
    assert "촬영" not in sec, "촬영일 표기가 남아 있다"
    assert not re.search(r"\d+월 \d+일", sec), "사진 쪽에 날짜가 남아 있다"
    for it in all_items:
        assert it["src"] in sec and "date" not in it


def test_b_room_has_no_setups_section():
    # 11-24 대표: B룸 인물(모델) 사진 제거 → 결과/세팅 섹션 없음.
    assert BR.render_setups(B) == ""
    assert 'id="setups"' not in (ROOT / "b.html").read_text(encoding="utf-8")


def test_setup_images_exist_with_800_rung():
    all_items = (A["setups"].get("hero") or []) + (A["setups"].get("trio") or []) + A["setups"]["items"]
    for it in all_items:
        p = ROOT / it["src"].lstrip("/")
        assert p.exists(), p
        assert (ROOT / (it["src"][:-4] + "-800.jpg").lstrip("/")).exists()
