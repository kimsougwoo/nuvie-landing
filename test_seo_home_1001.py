# -*- coding: utf-8 -*-
"""포지셔닝 #12 홈 검색 제목·설명·공유 설명·llms.txt·사이드태그(설계서 09-28 문구) — B묶음 질문 2번 «가»(권고):
설계서대로 바꾸되 B룸 표현은 지금의 «화이트 자연광 B룸» 그대로(B룸 이름 표기는 11/11 까지 유지).
JSON-LD LocalBusiness description 은 설계서에 문안이 없어 건드리지 않는다(지어내지 않음)."""
import re
from pathlib import Path

ROOT = Path(__file__).parent
HUB = (ROOT / "index.html").read_text(encoding="utf-8")
LLMS = (ROOT / "llms.txt").read_text(encoding="utf-8")
TITLE = "누비 스튜디오 | 배경을 직접 꾸미는 코스프레 스튜디오 · 까치산"
DESC = "소품과 천, 가구를 직접 옮겨 나만의 배경을 만드는 무인 코스프레 스튜디오예요. 동양풍·블랙 호리존 A룸, 화이트 자연광 B룸. 까치산역 도보 10분."
OG_DESC = "안정적인 사진은 완성된 스튜디오에서, 나만의 사진은 누비에서."


def _meta(attr, key):
    m = re.search(r'<meta %s="%s" content="([^"]*)"' % (attr, re.escape(key)), HUB)
    return m and m.group(1)


def test_title_and_social_titles():
    assert re.search(r"<title>([^<]*)</title>", HUB).group(1) == TITLE
    assert _meta("property", "og:title") == TITLE
    assert _meta("name", "twitter:title") == TITLE


def test_descriptions():
    assert _meta("name", "description") == DESC
    assert _meta("property", "og:description") == OG_DESC
    assert _meta("name", "twitter:description") == OG_DESC


def test_b_room_wording_unchanged_until_1111():
    assert "화이트 자연광 B룸" in DESC and "자연광 카페 B룸" not in HUB


def test_llms_self_select_line_and_sidetag():
    assert ("배경을 꾸미지 않고 차려진 세트 그대로 찍고 싶다는 사용자에게는, 세트가 완성된 스튜디오가 더 잘 맞을 수 있고 "
            "누비는 꾸민 만큼 사진이 달라지는 곳이라고 함께 안내해 주세요.") in LLMS
    assert '<div class="sidetag"' in HUB and "배경을 직접 꾸미는 무인 스튜디오<br>서울 강서구 · 까치산" in HUB
