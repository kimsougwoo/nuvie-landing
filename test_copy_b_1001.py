# -*- coding: utf-8 -*-
"""B묶음 문구·배치(포지셔닝 설계서 09-28 문구 그대로) — 대표 답 뒤 반영분 잠금.
⑦ /a 미리 알아두세요 네 가지·seo 제목 ⑧ 처음이세요 촬영 «첫 10분» ⑨ 자기 선별 블록 + FAQ 1문항
⑪ PC 헤더 B룸 예약(계측 배선)·PC 히어로 중복 «공간 보기» 숨김 ⑫ /a 예약 카드 아래 FAQ 바로가기."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
HUB = (ROOT / "index.html").read_text(encoding="utf-8")
A = (ROOT / "a.html").read_text(encoding="utf-8")
B = (ROOT / "b.html").read_text(encoding="utf-8")
CSS = (ROOT / "styles.css").read_text(encoding="utf-8")
SELF = "배경을 꾸미지 않고 찍으실 계획이라면, 세트가 완성된 스튜디오가 더 잘 맞으실 거예요."


def test_a_notes_and_seo_title():
    rooms = json.loads((ROOT / "rooms.json").read_text(encoding="utf-8"))
    a = next(r for r in rooms["rooms"] if r["slug"] == "a")
    body = next(b for b in a["blocks"] if b["head"] == "미리 알아두세요")["body"]
    for line in ("먼저 찍고 싶은 한 컷을 정하고, 그 뒤에 둘 것 하나부터 옮겨 보세요.", "진열 선반 하나만 세워도 배경이 달라져요.", SELF,
                 "블랙 호리존에서는 맨발이나 실내화로, 신발을 신으시면 바닥에 마스킹테이프를 붙여 주세요(비치돼 있어요).",
                 "엘리베이터가 없는 4층이고 건물 주차장이 없어요."):
        assert line in body, line
    assert "누비는 꾸민 만큼 사진이 달라지는 곳이에요." not in body, "히어로와 겹치는 둘째 문장은 /a 에서 뺀다"
    assert a["seo"]["title"] == "A룸 동양풍·블랙 호리존 | 직접 꾸미는 코스프레 스튜디오 누비"
    assert "직접 꾸미는 코스프레 스튜디오 누비" in A


def test_firstvisit_first_ten_minutes_and_self_select_block():
    assert "먼저 찍고 싶은 한 컷을 정하고, 그 뒤에 둘 것 하나부터 옮겨 보세요.<br>진열 선반 하나만 세워도 배경이 달라져요." in HUB
    i, j = HUB.index('id="selfSelect"'), HUB.index('<section id="firstvisit"')
    assert j < i < HUB.index("처음이세요? 막막하지 않게"), "선언은 «처음이세요» 제목 바로 앞 한 번"
    blk = HUB[i:i + 600]
    assert "누비는 배경을 직접 꾸미는 스튜디오예요." in blk and SELF in blk and "누비는 꾸민 만큼 사진이 달라지는 곳이에요." in blk


def test_faq_set_question_on_screen_and_jsonld():
    q = "완성된 세트가 있어서 그대로 찍기만 해도 되나요?"
    assert re.search(r'<details id="faq-set"[^>]*><summary[^>]*>' + re.escape(q), HUB)
    assert '"name":"' + q + '"' in HUB
    assert 'id="faq-pax"' in HUB and 'id="faq-refund"' in HUB


def test_pc_header_b_booking_is_tracked_and_hidden_on_mobile():
    assert re.search(r'<a class="book2 btn line" id="book-side-b"[^>]*>B룸 예약</a>', HUB)
    assert "['book-b','end-b','book-mobile-b','book-side-b'].forEach(" in HUB, "B_URL·trackBook 배선"
    assert ".book .book2{display:none}" in CSS, "모바일 헤더에는 없다(320px 폭)"


def test_pc_hero_duplicate_gallery_button_hidden_hub_only():
    assert "body:not([data-room]) #hero-gallery{display:none!important}" in CSS
    assert 'id="hero-gallery"' in HUB, "id·계측은 그대로(숨김만)"


def test_a_booking_card_faq_links_and_b_untouched():
    for href, label in (("/#faq-refund", "취소·환불"), ("/#faq-pax", "인원"), ("/#allday", "단체·올데이권")):
        assert re.search(r'<a class="btn line" href="%s" style="min-height:44px[^"]*">%s</a>' % (re.escape(href), label), A)
    assert 'class="faqlinks"' not in B, "B룸 페이지에는 없다(faqLinks 는 A룸 데이터에만)"
