# -*- coding: utf-8 -*-
"""P1 (2026-08-22): 모바일 사진 우선 스와이프 갤러리 — Clarity 실측 기반 구현의 회귀 가드.

왜: Clarity 실측에서 모바일 방문자의 1위 클릭이 캐러셀 «›»(후기/캘린더) 41%로 새고,
    소셜 유입은 0.9초에 이탈했다(AI 세션 인사이트 2건 동일 패턴: 착지→›연타→이탈).
    시각 상품인데 룸 사진을 빨리 못 보여준 것 → 착지 직후 «룸 사진 스와이프»를 상단에 둔다.

이 테스트가 박는 불변식:
  · 모바일 갤러리(.mgal)가 존재하고 룸 사진 6장을 싣는다.
  · 데스크탑에는 «안 보인다»(display:none 기본) — 데스크탑 회귀 0이 이 구현의 전제.
  · ≤640px 에서만 display:block (모바일 전용).
  · 갤러리 룸 버튼은 data-room-detail 로 계측된다(room_detail_click 배선 재사용).
  · 갤러리가 «계측 안 된 아워플레이스 앵커»를 만들지 않는다(내부 /a·/b 로만 링크).
  · 히어로/heroImg 는 그대로다(테마 배경·LCP 불변 — 별도 테스트가 이미 가드하지만 여기서도 재확인).
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
HTML = (HERE / "index.html").read_text(encoding="utf-8")
CSS = (HERE / "styles.css").read_text(encoding="utf-8")


def test_mgal_섹션이_존재하고_룸사진_6장을_싣는다():
    assert 'class="mgal"' in HTML, "모바일 사진 갤러리(.mgal) 섹션이 없다"
    # mgal 블록만 잘라 그 안의 룸 사진 수를 센다
    m = re.search(r'<section class="mgal".*?</section>', HTML, re.S)
    assert m, "mgal 섹션 블록을 못 찾았다"
    block = m.group(0)
    imgs = re.findall(r'/img/gal[AB]\d\.jpg', block)
    assert len(imgs) >= 6, f"갤러리 룸 사진이 6장 미만이다: {imgs}"
    assert any("galA" in i for i in imgs) and any("galB" in i for i in imgs), \
        "A룸·B룸 사진이 둘 다 있어야 한다(한 룸도 편들지 않음)"


def test_갤러리는_데스크탑에서_안_보이고_모바일에서만_보인다():
    # 기본 display:none (데스크탑 회귀 0의 전제)
    assert re.search(r"\.mgal\s*\{[^}]*display:\s*none", CSS), \
        ".mgal 기본값이 display:none 이 아니다 — 데스크탑에 새 블록이 새어 나온다"
    # ≤640px 미디어쿼리 안에서 display:block 으로 켜진다
    mobile_blocks = re.findall(r"@media\s*\(max-width:\s*640px\)\s*\{(.*?)\n  \}", CSS, re.S)
    on_mobile = any(re.search(r"\.mgal\s*\{[^}]*display:\s*block", b) for b in mobile_blocks)
    assert on_mobile, "≤640px 에서 .mgal 이 display:block 으로 켜지지 않는다(모바일 전용 배선 실패)"


def test_갤러리_룸버튼이_room_detail로_계측된다():
    m = re.search(r'<section class="mgal".*?</section>', HTML, re.S)
    block = m.group(0)
    assert 'data-room-detail="a"' in block and 'data-room-detail="b"' in block, \
        "갤러리 A/B 버튼에 data-room-detail 계측이 없다"
    assert 'data-room-detail-from="mgal"' in block, \
        "귀속(placement)용 data-room-detail-from='mgal' 이 없다"


def test_갤러리가_계측안된_아워플레이스_앵커를_만들지_않는다():
    m = re.search(r'<section class="mgal".*?</section>', HTML, re.S)
    block = m.group(0)
    # 갤러리는 내부 /a·/b 로만 링크한다(외부 아워플레이스 직링크 금지 — 계측 우회 방지)
    assert "hourplace.co.kr" not in block, \
        "갤러리가 아워플레이스로 직링크한다 — 내부 /a·/b(data-room-detail)로만 링크할 것"


def test_히어로와_heroImg는_그대로다():
    # 구현이 히어로를 건드리지 않았는지 재확인(테마 배경·LCP 불변)
    assert '<img id="heroImg"' in HTML, "heroImg 가 사라졌다 — 히어로를 건드리면 안 된다"
    assert "HERO_BG" in HTML, "HERO_BG 테마 매핑이 사라졌다"
    assert 'fetchpriority="high"' in HTML, "히어로 LCP fetchpriority 가 사라졌다"


def test_갤러리_첫사진외에는_lazy로_LCP를_지킨다():
    m = re.search(r'<section class="mgal".*?</section>', HTML, re.S)
    block = m.group(0)
    # 갤러리 이미지 중 최소 하나는 lazy(히어로가 LCP를 유지하도록 갤러리는 지연 로드)
    assert block.count('loading="lazy"') >= 4, \
        "갤러리 사진 대부분이 lazy 가 아니다 — 히어로 LCP 와 경쟁한다"
