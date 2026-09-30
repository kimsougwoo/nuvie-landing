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
    return (ROOT / n).read_text(encoding="utf-8").replace(" ", " ").replace("\u2060", "")  # 10-01 줄바꿈 다듬기(ko_glue): 본문 공백 일부가 U+00A0 — 화면 글자는 같으니 보통 공백으로 바꿔 비교


def _room(slug):
    r = json.loads(_read("rooms.json"))
    rooms = r.get("rooms", r)
    return ({x["slug"]: x for x in rooms} if isinstance(rooms, list) else rooms)[slug]


NEW_SUB = "조명 색과 각도, 소품과 천의 자리를 직접 정하는 룸이에요.<br>꾸민 만큼 사진이 달라져요."


def test_a_hero_sub_is_self_directed_not_a_promise():
    assert _room("a")["hero"]["sub"] == NEW_SUB
    a = _read("a.html")
    assert NEW_SUB in a and "그 자리에서 원하는 그림이 나와요" not in a


def test_rooms_intro_lines_split_by_topic():
    """대표 09-30: 소개 문단 줄바꿈(문구 그대로) · 무드/인원/도어락 문단은 주제별 한 줄 + 사실은 정본대로
    (가격정책 v6 §2 «5인째부터 +5,500원/인·시간» · 게스트 안내 §2 «00~08:59 시작 예약은 전날 저녁 선발송»)."""
    html = _read("index.html")
    assert "무인 코스프레 컨셉 렌탈 스튜디오입니다.<br>A룸(동양풍·블랙 호리존)과 B룸(화이트 티타임 카페·자연광)을 각각 따로 예약합니다.</p>" in html
    m = re.search(r'<p class="desc" data-reveal style="margin:0 0 40px">(.*?)</p>', html)
    lines = m.group(1).split("<br>")
    assert lines[0] == "A룸과 B룸은 무드가 다릅니다."
    # 권고안 A: 09-28 확정 문구 «기준 4인, 초과 시 인원요금, 단체는 문의» 그대로 한 줄 + 도어락 시점은 게스트 안내 정본대로
    assert lines[1:] == ["기준 4인, 초과 시 인원요금, 단체는 문의", "예약 확정 후, 이용 당일 오전에 도어락 비밀번호를 보내드립니다(0시~8시 59분에 시작하는 예약은 전날 저녁)."]
    assert "프라이빗" not in m.group(1)


def test_faq_booking_answer_one_step_per_line():
    html = _read("index.html")
    assert "아니요, 문의 없이 바로 예약돼요.<br>① 캘린더에서 빈 시간 확인 →<br>② 아워플레이스에서 바로 결제 →<br>③ 이용 당일 아침, 주소·도어락·주차 안내 메시지 도착.<br>답장을 기다릴 일이 없습니다.</p>" in html


def test_firstvisit_card2_drops_curtain_colour_line():
    """대표 09-30 «이 문장 한 줄 지워 주세요» — 나머지 세 줄(스위치·소품과 천·커튼레일 위치)은 그대로."""
    html = _read("index.html")
    m = re.search(r'<p id="fv-body-2"[^>]*>(.*?)</p>', html)
    assert m.group(1) == "조명·에어컨 스위치는 룸 안에 안내돼 있어요.<br>소품과 천은 자유롭게 꺼내 쓰세요.<br>월동문 위·문가벽 상단·블랙 호리존 천장에 커튼레일이 있어요."
    assert "모르고 지나치시는 분이 많아요" not in html


def test_firstvisit_cards_start_open():
    html = _read("index.html")
    heads = re.findall(r'<div class="fv-h"[^>]*aria-expanded="(true|false)"', html)
    assert heads == ["true"] * 4, heads


def test_mobile_bar_week_label_starts_with_booking():
    """09-30 U-12 «아워로 가는 버튼은 «예약»으로 시작»은 그대로 지킨다. 같은 날 저녁 대표 결정으로 문구가
    «이번 주 빈 시간 있음» → «가장 빠른 빈 시간»(avail-label.js)으로 바뀌어 새 문구 기준으로 확인한다(상세 = test_free_slot_0930.py)."""
    js = _read("avail-label.js")
    assert "label + ' 예약 · 빠른 빈 시간'" in js, "하단 바 문구는 «○룸 예약»으로 시작"
    assert "남은 시간 보기" not in js and "남은 시간 보기" not in _read("index.html")


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
    assert '<br>올데이권은 아워플레이스 상품이 아니라 개별 문의로 잡아 드려요.<br>전화 <a href="tel:07082111103" style="color:var(--accent)">070-8211-1103</a>으로 날짜·시간·인원을 알려 주세요.' in allday
    assert allday.count('<br>') == 7, '주제별 다섯 줄 + 한 줄 안 두 문장은 문장 끝에서 한 번 더(대표 «전부 줄바꿈»)'
    assert "문자" not in allday and 'href="sms:' not in html
    details = [d for d in re.findall(r"<details\b.*?</details>", html, re.S) if "몇 명까지 이용할 수 있나요?" in d]
    assert details and 'href="#allday"' in details[0] and "올데이권(12시간) 문의" in details[0]
    # 구조화 데이터(JSON-LD FAQ)도 같은 연락 방법
    ld = re.search(r'"name":"단체로 하루 종일 쓸 수 있나요\?","acceptedAnswer":\{"@type":"Answer","text":"([^"]+)"', html)
    assert ld and "X @nuvie_studio" not in ld.group(1) and "전화 070-8211-1103으로 날짜·시간·인원을 알려 주세요." in ld.group(1)
    assert "문자" not in ld.group(1)
    llms = _read("llms.txt")
    assert "개별 문의 — 전화 070-8211-1103으로 날짜·시간·인원을 알려 주세요." in llms


def test_allday_phone_number_filled_before_push():
    """🔒 push 가드: 대표 번호가 오기 전엔 자리표시가 남아 있고 이 테스트가 빨갛다(번호 없이 push 하지 않음 — 대표 09-30)."""
    for f in ("index.html", "llms.txt"):
        assert PHONE_PLACEHOLDER not in _read(f), f"{f}: 전화번호 자리표시가 남아 있다 — 대표 번호를 받은 뒤 채울 것"
    assert "X @nuvie_studio 개별 문의" not in _read("llms.txt"), "llms.txt 올데이권 문의 길도 전화·문자로"


def test_inquiry_button_names_its_destination():
    html = _read("index.html")
    m = re.search(r'data-hp="a\|inquiry_link"[^>]*>(.*?)</a>', html)
    assert m and m.group(1) == "아워플레이스 예약 페이지에서 문의&nbsp;&rarr;", m and m.group(1)   # 320px 에서 화살표만 다음 줄로 가지 않게
