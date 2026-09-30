# -*- coding: utf-8 -*-
"""룸 페이지 시즌 안내(2026-09-30, UX 막힘 U-01).

왜: 9/30 19:00 A룸 할로윈 X 글이 /a 로 링크하는데 /a 에는 할로윈 언급이 0회였다(홈 룸 카드 #seasonNoteA 에만 있음).
무엇: rooms.json 의 룸별 seasonNote {text, until} 을 히어로 설명 바로 밑에 보인다. 문구는 홈 카드와 «같은 문장»(새 문구 없음),
      until(KST 날짜) 이 되면 스스로 숨는다 — 시즌이 끝났는데 안내가 남는 사고 방지(홈 카드와 같은 방식).
🧊 /b 는 seasonNote 가 없고 11/11 동결 — b.html 바이트는 test_ux0929_1_anchor 가 지킨다.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent


def _read(n):
    return (ROOT / n).read_text(encoding="utf-8")


def _rooms():
    r = json.loads(_read("rooms.json"))
    rooms = r.get("rooms", r)
    return {x["slug"]: x for x in rooms} if isinstance(rooms, list) else rooms


def _lines(text):
    """대표 09-30 «기간 줄바꿈 처리»: rooms.json 은 « · » 로 한 문장, 화면은 « · » 자리에서 줄을 바꾼다."""
    return text.split(" · ")


def test_a_season_note_matches_home_card_sentence():
    home = re.search(r'<p id="seasonNoteA" data-until="([^"]+)"[^>]*>(.*?)</p>', _read("index.html"))
    sn = _rooms()["a"]["seasonNote"]
    assert home.group(2) == "<br>".join(_lines(sn["text"])), "홈 카드와 같은 문장·같은 줄바꿈이어야 한다(새 문구 금지)"
    assert sn["until"] == home.group(1)
    assert _lines(sn["text"])[-1] == "10월 31일까지", "기간이 둘째 줄"


def test_a_html_shows_season_note_under_hero_sub_with_auto_hide():
    a = _read("a.html")
    m = re.search(r'<p id="seasonNote" data-until="(\d{4}-\d{2}-\d{2})" hidden[^>]*>(.*?)</p><script>(.*?)</script>', a, re.S)
    assert m, "a.html 에 시즌 안내가 없다"
    assert m.group(2) == "<br>".join(_lines(_rooms()["a"]["seasonNote"]["text"])), "« · » 자리에서 줄바꿈"
    js = m.group(3)
    assert "9*3600*1000" in js and "n.hidden=false" in js, "KST 기준 until 전만 보이게"
    hero_sub_end = a.index("</p>", a.index("{{SUB}}") if "{{SUB}}" in a else a.index('text-wrap:pretty">'))
    assert a.index('id="seasonNote"') > hero_sub_end, "히어로 설명 뒤에 와야 한다"
    assert a.index('id="seasonNote"') < a.index('class="herobadges"')


def test_b_has_no_season_note():
    assert "seasonNote" not in _rooms()["b"]
    assert 'id="seasonNote"' not in _read("b.html")
