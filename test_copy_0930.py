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
    assert "a.textContent=on?'A룸 예약 · 이번 주 빈 시간 있음 →':'A룸 예약 →';" in html   # 줄바꿈 없는 공백(U+00A0) — 320px 두 줄 때 «이번 주» 안 갈림
    assert "이번 주 남은 시간 보기" not in html[html.index('<script id="aweek-js">'):html.index('<script id="aweek-js">') + 2000]


PHONE_PLACEHOLDER = "PHONE_TBD"


def test_allday_note_on_home_rooms_section():
    """U-06(대표 «전화·문자로 받기»): 올데이권이 FAQ 9번째(문서 82.7%) 안에만 있었다 → 룸 소개 아래 한 줄 + 전화·문자.
    금액 = 가격정책 v6 §1-0(09-28 대표 확정). 아워 메시지 경로는 넣지 않는다(§1-0 금지)."""
    html = _read("index.html")
    rooms = html[html.index('<section id="rooms"'):html.index('<section id="reviews"')]
    m = re.search(r'<div id="alldayNote"[^>]*>(.*?)</div>\s*<!-- /alldayNote -->', rooms, re.S)
    assert m, "룸 소개 섹션에 올데이권 한 줄이 없다"
    body = m.group(1)
    assert "평일 60만 원, 주말·공휴일 75만 원(12시간·부가세 포함)" in body
    assert "전화 070-8211-1103" in body and 'href="tel:07082111103"' in body
    # 070 인터넷전화라 문자를 받을 수 없다(대표 09-30) — 문자 버튼·«문자» 말 없음
    assert 'href="sms:' not in body and "문자" not in body
    assert "hourplace" not in body, "올데이권은 아워 밖 문의만(가격정책 v6 §1-0)"


def test_allday_faq_contact_is_phone_and_group_answer_links_to_it():
    html = _read("index.html")
    allday = html[html.index('<details id="allday"'):]
    allday = allday[:allday.index("</details>")]
    assert "x.com/nuvie_studio" not in allday
    assert '전화(<a href="tel:07082111103" style="color:var(--accent)">070-8211-1103</a>)로 날짜·시간·인원을 알려 주세요.' in allday
    assert "문자" not in allday and 'href="sms:' not in html
    details = [d for d in re.findall(r"<details\b.*?</details>", html, re.S) if "몇 명까지 이용할 수 있나요?" in d]
    assert details and 'href="#allday"' in details[0] and "올데이권(12시간) 문의" in details[0]
    # 구조화 데이터(JSON-LD FAQ)도 같은 연락 방법
    ld = re.search(r'"name":"단체로 하루 종일 쓸 수 있나요\?","acceptedAnswer":\{"@type":"Answer","text":"([^"]+)"', html)
    assert ld and "X @nuvie_studio" not in ld.group(1) and "전화(070-8211-1103)로 날짜·시간·인원을 알려 주세요." in ld.group(1)
    assert "문자" not in ld.group(1)
    llms = _read("llms.txt")
    assert "전화(070-8211-1103) 개별 문의" in llms


def test_allday_phone_number_filled_before_push():
    """🔒 push 가드: 대표 번호가 오기 전엔 자리표시가 남아 있고 이 테스트가 빨갛다(번호 없이 push 하지 않음 — 대표 09-30)."""
    for f in ("index.html", "llms.txt"):
        assert PHONE_PLACEHOLDER not in _read(f), f"{f}: 전화번호 자리표시가 남아 있다 — 대표 번호를 받은 뒤 채울 것"
    assert "X @nuvie_studio 개별 문의" not in _read("llms.txt"), "llms.txt 올데이권 문의 길도 전화·문자로"


def test_inquiry_button_names_its_destination():
    html = _read("index.html")
    m = re.search(r'data-hp="a\|inquiry_link"[^>]*>(.*?)</a>', html)
    assert m and m.group(1) == "아워플레이스 예약 페이지에서 문의 &rarr;", m and m.group(1)
