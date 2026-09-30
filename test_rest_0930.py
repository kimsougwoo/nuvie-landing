# -*- coding: utf-8 -*-
"""09-30 저녁 라이브 캡처(320·390·1440)에서 찾은 결함 잠금 — 문구 변화 없음.

D-1 320px 홈 후기 요약 배지 «A · B ROOMS · 후기»가 3줄로 꺾이고, 후기 카드 작성자·날짜 줄도 3줄로 꺾였다.
D-2 320px 칩 바 마지막 칩이 화면 끝에서 잘렸다(가로 스크롤은 되지만 표시가 없다).
D-3 320px «주소 복사» 버튼 높이 37px(줄 높이 기본값 · .btn 44px 규칙이 모바일 일부 요소에만 걸림).
"""
import re
from pathlib import Path

ROOT = Path(__file__).parent
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "styles.css").read_text(encoding="utf-8")


def test_review_summary_head_wraps_without_breaking_badge():
    m = re.search(r'<div class="rev-sumhead"[^>]*>\s*<span[^>]*>A · B ROOMS · 후기</span>', INDEX)
    assert m, "후기 요약 머리줄에 rev-sumhead 클래스가 있어야 함"
    assert re.search(r"\.rev-sumhead\{[^}]*flex-wrap:wrap", CSS), "머리줄은 좁으면 다음 줄로 넘겨야 함"
    assert re.search(r"\.rev-sumhead>span\{[^}]*white-space:nowrap", CSS), "배지·별점·건수는 각자 한 줄을 지켜야 함"


def test_review_card_meta_wraps_as_whole_units():
    assert re.search(r"#reviewCards>\[role=listitem\]>div:first-child\{[^}]*flex-wrap:wrap", CSS)
    assert re.search(r"#reviewCards>\[role=listitem\]>div:first-child>span\{[^}]*white-space:nowrap", CSS)


def test_copy_address_button_is_44px():
    m = re.search(r'<button[^>]*id="copyAddr"[^>]*style="([^"]*)"', INDEX)
    assert m and "min-height:44px" in m.group(1)


def test_chipbar_fits_320px():
    m = re.search(r"@media\(max-width:374px\)\{([^@]*?\.nv-chipbar\{[^}]*\}[^@]*?\.nv-chip\{[^}]*\})", CSS)
    assert m, "374px 이하 칩 바 압축 규칙이 있어야 함"
    assert "min-height" not in m.group(1), "압축해도 44px 누름 높이는 건드리지 않음"


def test_inline_cta_links_get_44px_hit_area_without_layout_change():
    """U-25: 문장 안 링크(가격 줄 A·B룸 예약, 오시는 길 문의, FAQ 답 올데이권·전화)는 글자·줄 배치를 그대로 두고
    보이지 않는 ::after 로 누름 영역만 44px 이상으로 넓힌다(padding 을 주면 줄 간격이 바뀐다)."""
    m = re.search(r"([^{}]*price_link[^{}]*)\{position:relative\}", CSS)
    assert m, "누름 영역 넓힐 링크 선택자 묶음이 있어야 함"
    sel = m.group(1)
    for key in ("price_link", "directions_inquiry", 'a[href^="tel:"]', 'a[href="#allday"]'):
        assert key in sel, key
    assert re.search(r"::after\{content:\"\";position:absolute;inset:-1[4-9]px", CSS)


def test_review_carousel_shows_position_counter_on_mobile():
    """U-14: 모바일 후기 캐러셀은 23장인데 몇 번째인지 표시가 없었다. 숫자만(«3 / 23») 붙인다 — 문구 없음."""
    assert re.search(r'<div class="nv-count" id="reviewCount2"[^>]*aria-live="polite"[^>]*>', INDEX)
    assert re.search(r"\.nv-count\{display:none\}", CSS)
    assert re.search(r"@media\(max-width:640px\)\{[^@]*#reviews \.nv-count\{display:block", CSS)
    js = INDEX[INDEX.find("4b)"):INDEX.find("/* 9)")]
    assert "reviewCount2" in js and "scroll" in js and "' / '" in js


def _far_jump_block(src):
    i = src.find("U-15")
    return src[i:i + 1600] if i >= 0 else ""


def test_far_anchor_jumps_are_instant_on_hub_and_room_pages():
    """U-15: 홈 히어로 «예약 가능 시간 →»은 4,143px 을 부드럽게 굴러 로드 중에는 4.9초 걸렸다.
    같은 페이지 안 앵커가 화면 2장보다 멀면 부드러운 스크롤을 잠시 끄고 바로 이동한다(가까운 이동은 그대로 부드럽게)."""
    site = (ROOT / "site.js").read_text(encoding="utf-8")
    for name, src in (("index.html", INDEX), ("site.js", site)):
        blk = _far_jump_block(src)
        assert blk, f"{name}: U-15 블록 없음"
        assert "innerHeight*2" in blk.replace(" ", ""), name
        assert "scrollBehavior='auto'" in blk.replace(" ", ""), name
        assert "getElementById" in blk, f"{name}: 해시는 id 로만 찾는다(선택자 해석 금지)"
        assert "defaultPrevented" in blk, f"{name}: 다른 핸들러가 막은 클릭은 건드리지 않는다"


def _block(src, tag):
    i = src.find("/* " + tag)
    j = src.find("})();", i)
    return src[i:j + 5] if i >= 0 and j > i else ""


def test_duplicated_hub_and_room_snippets_are_identical():
    """U-15·U-16 은 index.html(홈)과 site.js(룸 페이지)에 같은 코드를 둔다 — 한쪽만 고치는 드리프트 방지."""
    site = (ROOT / "site.js").read_text(encoding="utf-8")
    for tag in ("U-15", "U-16"):
        a, b = _block(INDEX, tag), _block(site, tag)
        assert a and a == b, f"{tag} 블록이 두 파일에서 다르다"


def test_sticky_bars_collapse_on_scroll_down_mobile_hub_and_a_only():
    """U-16: 모바일 고정 막 3겹(헤더 61 + 칩 바 63 + 하단 바 54 = 화면 21~28%). 아래로 스크롤하면 헤더·칩 바를 숨기고
    위로 올리면 다시 보인다. 하단 예약 바는 그대로. /b 는 11/11 동결이라 제외(행동 변경)."""
    blk = _block(INDEX, "U-16")
    assert blk, "U-16 블록 없음"
    # 앵커 이동(즉시·부드러움)·해시 첫 진입 재정렬 동안은 숨기지 않는다 — 146px 도착 여백이 막이 보이는 상태를 전제로 한다.
    assert "holdUntil" in blk and "hashchange" in blk and 'a[href^="#"]' in blk and "6500" in blk
    assert "focusin" in blk, "키보드 초점이 숨은 막 안으로 들어가면 다시 보여야 함"
    assert "max-width:640px" in blk
    css = re.search(r'body:not\(\[data-room="b"\]\)\[data-nav="hidden"\] \.side\{[^}]*transform:translateY\(-100%\)', CSS)
    assert css, "헤더 숨김 규칙(/b 제외)"
    assert re.search(r'body:not\(\[data-room="b"\]\)\[data-nav="hidden"\] \.nv-chipbar\{[^}]*--nv-head-h', CSS)
    assert re.search(r"prefers-reduced-motion:reduce\)\{[^}]*\.side[^}]*\.nv-chipbar[^}]*transition:none", CSS)
    assert "--nv-head-h" in INDEX and "--nv-head-h" in (ROOT / "site.js").read_text(encoding="utf-8")


def test_b_chipbar_sits_below_header_like_a():
    """D-4(09-30 저녁 라이브): /b 칩 바가 top:0 에 붙어 헤더(z-index 50) 밑에 깔렸다 — 스크롤 뒤 칩을 누르면 헤더가 눌린다
    (/a 는 224b5ab 에서 고쳤다). 문구 변화 없는 결함이라 대표 09-30 «B룸도 동일» 대상."""
    site = (ROOT / "site.js").read_text(encoding="utf-8")
    fn = site[site.find("function wireChipbar"):site.find("function init")]
    assert "'a'" in fn and "'b'" in fn, "wireChipbar 가 /a·/b 둘 다 배선해야 함"
    assert re.search(r'body\[data-room="b"\]\s+\.nv-chipbar\s*\{[^}]*top:\s*61px', CSS), "JS 전 대비값"
