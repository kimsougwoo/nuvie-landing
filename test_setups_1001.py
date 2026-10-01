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


def test_label_is_now_until_oct31_and_past_from_nov1():
    before = BR.render_setups(A, today="2026-10-31")
    after = BR.render_setups(A, today="2026-11-01")
    assert _visible(before, "now") and not _visible(before, "past")
    assert _visible(after, "past") and not _visible(after, "now")
    assert "10월 31일까지" in before and "지난 세팅" in after


def test_page_script_flips_label_by_visit_date():
    html = BR.render_setups(A, today="2026-10-01")
    assert 'data-until="2026-11-01"' in html
    assert "toISOString().slice(0,10)" in html and "today>=s.dataset.until" in html


def test_owner_note_present_and_no_shoot_dates():
    """10-01 대표 «일자는 빼주세요» — 사진 아래 촬영일·alt 속 날짜를 쓰지 않는다(운영 기간 라벨 «10월 31일까지»는 별개)."""
    html = (ROOT / "a.html").read_text(encoding="utf-8").replace(chr(0xa0), " ").replace(chr(0x2060), "")
    sec = re.search(r'<section id="setups">(.*?)</section>', html, re.S).group(1)
    assert "매일 조금씩 디테일이 달라질 수 있습니다" in sec
    assert "A룸을 이렇게 꾸몄어요" in sec and "블랙 호리존을 이렇게" not in sec   # 10-01 대표 «가. 제목을 넓히고»
    imgs = re.findall(r"<img [^>]*>", sec)
    assert len(imgs) == len(A["setups"]["items"]) >= 8
    assert "촬영" not in sec, "촬영일 표기가 남아 있다"
    gallery = sec.split('<div class="gal"', 1)[1]
    assert not re.search(r"\d+월 \d+일", gallery), "사진 쪽에 날짜가 남아 있다"
    for it in A["setups"]["items"]:
        assert it["src"] in sec and "date" not in it


def test_b_room_has_no_setups_section():
    assert BR.render_setups(B) == ""
    assert 'id="setups"' not in (ROOT / "b.html").read_text(encoding="utf-8")


def test_setup_images_exist_with_800_rung():
    for it in A["setups"]["items"]:
        p = ROOT / it["src"].lstrip("/")
        assert p.exists(), p
        assert (ROOT / (it["src"][:-4] + "-800.jpg").lstrip("/")).exists()
