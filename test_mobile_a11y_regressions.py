# -*- coding: utf-8 -*-
"""2026-08-05 모바일 E2E 검수에서 고친 결함의 회귀 테스트.

전부 실기기 뷰포트(390×844) 실측으로 확인한 결함이고, CSS/마크업 한 줄만 되돌아가도 조용히 재발한다.

⚠️ 이 파일의 검사는 **주석을 걷어낸 뒤** 수행한다 — 2026-08-04 에 같은 종류의 테스트가
   「결함을 설명하는 자기 주석」에 걸려 통과/실패가 뒤집힌 적이 있다([[feedback_authoring_traps]]).
"""
import re
from pathlib import Path

ROOT = Path(__file__).parent
CSS = (ROOT / "styles.css").read_text(encoding="utf-8")
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
TPL = (ROOT / "room.template.html").read_text(encoding="utf-8")


def strip_css_comments(s: str) -> str:
    return re.sub(r"/\*.*?\*/", " ", s, flags=re.S)


def strip_html_comments(s: str) -> str:
    return re.sub(r"<!--.*?-->", " ", s, flags=re.S)


CSS_CODE = strip_css_comments(CSS)
INDEX_CODE = strip_html_comments(INDEX)
TPL_CODE = strip_html_comments(TPL)


def test_hero_scrim_has_class_on_both_templates():
    """스크림을 모바일에서 덮어쓰려면 선택할 이름이 있어야 한다(원래 익명 div였다)."""
    assert 'class="heroScrim"' in INDEX_CODE, "허브 히어로 스크림에 heroScrim 클래스가 없다"
    assert 'class="heroScrim"' in TPL_CODE, "룸 템플릿 히어로 스크림에 heroScrim 클래스가 없다"


def test_mobile_scrim_mid_stop_is_strong_enough():
    """🔴 핵심 결함: 스크림 중간 정지점이 alpha .06 이라 h1 이 밝은 사진 위에서 안 읽혔다.

    모바일 오버라이드의 **모든** 정지점이 0.4 이상이어야 한다(실측 기준: 최악 픽셀에서도 h1 2행 3:1 통과).
    """
    m = re.search(r"\.heroScrim\s*\{([^}]*)\}", CSS_CODE)
    assert m, "모바일 .heroScrim 오버라이드가 없다"
    rule = m.group(1)
    assert "linear-gradient" in rule, f"스크림 규칙에 그라디언트가 없다: {rule[:120]}"
    alphas = [float("0" + a) for a in re.findall(r"rgba\(6,\s*6,\s*7,\s*(\.\d+)\)", rule)]
    assert len(alphas) >= 3, f"스크림 alpha 를 못 읽었다: {rule[:160]}"
    assert min(alphas) >= 0.40, f"스크림 최소 alpha 가 {min(alphas)} — .06 결함이 되살아났다"


def test_hero_badges_have_class_and_tap_target():
    """히어로 뱃지가 실측 32px 이라 탭 타겟 44px 미달이었다."""
    assert 'class="herobadges"' in INDEX_CODE
    assert 'class="herobadges"' in TPL_CODE
    assert re.search(r"\.herobadges a\s*\{[^}]*min-height:44px", CSS_CODE), "herobadges 탭 타겟 규칙이 없다"


def test_light_faint_token_meets_aa():
    """--faint 라이트값이 흰 배경에서 4.5:1 을 넘어야 한다(구 #8A8A8E = 3.21:1)."""
    m = re.search(r'\[data-theme="light"\][^{]*\{[^}]*--faint:\s*(#[0-9A-Fa-f]{6})', CSS_CODE)
    assert m, "라이트 --faint 정의를 못 찾았다"
    hex_v = m.group(1)
    assert hex_v.upper() != "#8A8A8E", "라이트 --faint 가 AA 미달값으로 되돌아갔다"

    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex_v[i:i + 2], 16) for i in (1, 3, 5))
    L = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
    contrast = 1.05 / (L + 0.05)
    assert contrast >= 4.5, f"--faint {hex_v} 는 흰 배경 대비 {contrast:.2f}:1 로 AA 미달"


def test_review_carousel_inset_so_arrows_do_not_cover_text():
    """🔴 후기 캐러셀 화살표가 활성 카드 본문 위를 덮고 있었다."""
    assert re.search(r"#reviewCards\s*\{[^}]*padding-left:52px", CSS_CODE), "캐러셀 좌측 인셋이 없다"
    assert re.search(r"#reviewCards\s*\{[^}]*padding-right:52px", CSS_CODE), "캐러셀 우측 인셋이 없다"
    # 인셋만 하면 카드가 176px 로 쪼그라들어 더 나빠진다 — 패널 블리드가 짝으로 있어야 한다
    assert re.search(r"#reviews \.nv-carwrap\s*\{[^}]*margin-left:-20px", CSS_CODE), \
        "패널 블리드가 없다 — 인셋만 있으면 카드가 176px 로 좁아진다"


def test_review_source_line_is_not_faint():
    """후기 출처 표기는 신뢰 정보라 --faint(흐린 값)로 두지 않는다."""
    m = re.search(r'<p[^>]*>출처: 아워플레이스', INDEX_CODE)
    assert m, "출처 표기를 못 찾았다"
    tag = INDEX_CODE[m.start():m.start() + 200]
    assert "var(--faint)" not in tag, "출처 표기가 --faint 로 되돌아갔다"


def test_room_footer_links_have_tap_target_class():
    """룸 페이지 푸터 링크 2개가 실측 24px 이었다."""
    foot = TPL_CODE[TPL_CODE.find("<footer"):]
    assert foot.count('class="nv-privacy"') >= 2, "룸 푸터 링크에 탭 타겟 클래스가 빠졌다"


def test_generated_room_pages_carry_the_fixes():
    """a.html·b.html 은 생성물이다 — 템플릿만 고치고 빌드를 안 돌리면 라이브에 반영되지 않는다."""
    for name in ("a.html", "b.html"):
        html = strip_html_comments((ROOT / name).read_text(encoding="utf-8"))
        assert 'class="heroScrim"' in html, f"{name} 에 heroScrim 이 없다 — build_rooms.py 를 다시 돌릴 것"
        assert 'class="herobadges"' in html, f"{name} 에 herobadges 가 없다 — build_rooms.py 를 다시 돌릴 것"
