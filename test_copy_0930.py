# -*- coding: utf-8 -*-
"""랜딩 문구 막힘 4건 — 대표 09-30 «전부 권고대로» (제안서 Desktop\\NUVIE_랜딩_문구막힘5건_제안서_2026-09-30.html).

U-02 A룸 히어로 설명: «잡으면 그 자리에서 원하는 그림이 나와요»(꾸미지 않아도 나온다는 약속) → «직접 정하는 룸 · 꾸민 만큼 달라진다».
     «조명 색»은 대표 확인 «따뜻한·차가운 빛만 돼요»(색온도) → 그대로 둔다.
U-04 «처음이세요?» 카드 4장이 모바일에서 접혀 커튼레일 안내가 숨었다 → 펼친 채로 시작(누르면 접힘, 문구 그대로).
U-12 하단 바 «A룸 이번 주 남은 시간 보기 →»가 «보기»인데 아워로 이동 → 떠나는 버튼은 «예약»으로 시작.
U-24 FAQ 아래 «아워플레이스 메시지 →»가 A룸 예약 페이지로 감 → 가는 곳 그대로 이름에.
U-06(올데이권 문의 길)은 대표 추가 확인 대기라 여기 없다.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent


def _read(n):
    return (ROOT / n).read_text(encoding="utf-8")


def _room(slug):
    r = json.loads(_read("rooms.json"))
    rooms = r.get("rooms", r)
    return ({x["slug"]: x for x in rooms} if isinstance(rooms, list) else rooms)[slug]


NEW_SUB = "조명 색과 각도, 소품과 천의 자리를 직접 정하는 룸이에요.<br>꾸민 만큼 사진이 달라져요."


def test_a_hero_sub_is_self_directed_not_a_promise():
    assert _room("a")["hero"]["sub"] == NEW_SUB
    a = _read("a.html")
    assert NEW_SUB in a and "그 자리에서 원하는 그림이 나와요" not in a


def test_firstvisit_cards_start_open():
    html = _read("index.html")
    heads = re.findall(r'<div class="fv-h"[^>]*aria-expanded="(true|false)"', html)
    assert heads == ["true"] * 4, heads


def test_mobile_bar_week_label_starts_with_booking():
    html = _read("index.html")
    assert "a.textContent=on?'A룸 예약 · 이번 주 빈 시간 있음 →':'A룸 예약 →';" in html
    assert "이번 주 남은 시간 보기" not in html[html.index('<script id="aweek-js">'):html.index('<script id="aweek-js">') + 2000]


def test_inquiry_button_names_its_destination():
    html = _read("index.html")
    m = re.search(r'data-hp="a\|inquiry_link"[^>]*>(.*?)</a>', html)
    assert m and m.group(1) == "아워플레이스 예약 페이지에서 문의 &rarr;", m and m.group(1)
