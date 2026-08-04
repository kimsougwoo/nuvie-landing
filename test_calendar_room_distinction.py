# -*- coding: utf-8 -*-
"""예약 현황 달력에서 A룸/B룸이 실제로 구분되는가 — 회귀 테스트 (2026-08-04).

🔴 재현한 결함 (대표 지적 「A룸과 B룸의 차이가 안보입니다」·「회색끼리 두면 의미가 없잖아요」)
  ① `--calA`/`--calB` 가 **명도만 다른 회색 2개**였다(다크 #F5F5F6/#B8B8BE · 라이트 #181818/#4A4A4E).
     Stayfolio 전환(08-04) 때 「룸을 색으로 구분하지 않는다」 원칙을 세우며 달력까지 뉴트럴로
     내렸는데, 달력 칩은 주석 스스로 「기능적 구분이라 예외」라고 적어 둔 자리였다.
     ⇒ 예외를 선언하고 회색으로 구현하면 예외가 죽는다.
  ② 칩 텍스트가 `"12:00 - 15:00 (3H) 예약됨"` 으로 **룸을 어디에도 안 적었다.**
     구분이 색 하나뿐 = 색만으로 정보 전달(WCAG 1.4.1 위반)인데 그 색마저 회색이었다.
  ③ 모바일(≤640px)은 칩 텍스트를 `font-size:0` 으로 숨기고 5px 바만 남긴다 →
     ①②가 겹쳐 **구분 수단이 0** 이었다.

이 테스트가 막는 것 = 「회색으로 되돌아가는 것」과 「룸 라벨이 사라지는 것」.
토큰 값을 바꾸는 건 자유지만, **회색이거나 두 색이 비슷하면 실패한다.**
"""
import re
import colorsys
from pathlib import Path

ROOT = Path(__file__).parent
CSS = (ROOT / "styles.css").read_text(encoding="utf-8")
HTML = (ROOT / "index.html").read_text(encoding="utf-8")

# 칩 배경 틴트 비율 — index.html 의 ROOM 인라인 스타일과 같은 값이어야 한다.
TINT = {"A": 15, "B": 18}
MIN_CONTRAST = 4.5          # 10px 본문 크기라 large-text 예외 대상이 아니다
MIN_SAT = 0.20              # 회색 금지선
MIN_HUE_GAP = 60.0          # 두 룸 색상(도) 최소 간격


def _hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lum(rgb):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (f(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = _lum(_hex2rgb(a)), _lum(_hex2rgb(b))
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def over(fg, bg, pct):
    """color-mix(in srgb, fg pct%, transparent) 를 bg 위에 얹은 실제 색."""
    f, b, a = _hex2rgb(fg), _hex2rgb(bg), pct / 100
    return "#%02X%02X%02X" % tuple(round(f[i] * a + b[i] * (1 - a)) for i in range(3))


def hue_sat(h):
    r, g, b = (v / 255 for v in _hex2rgb(h))
    hh, _l, s = colorsys.rgb_to_hls(r, g, b)
    return hh * 360, s


def _block(name):
    """styles.css 에서 해당 셀렉터 블록의 본문을 뽑는다."""
    i = CSS.index(name)
    j = CSS.index("{", i)
    depth, k = 1, j + 1
    while depth:
        if CSS[k] == "{":
            depth += 1
        elif CSS[k] == "}":
            depth -= 1
        k += 1
    return CSS[j:k]


def tokens(selector):
    blk = _block(selector)
    out = {}
    for room in ("A", "B"):
        m = re.search(r"--cal%s\s*:\s*(#[0-9A-Fa-f]{6})" % room, blk)
        assert m, "--cal%s 를 %s 블록에서 못 찾음" % (room, selector)
        out[room] = m.group(1).upper()
    return out


# 다크 = :root 기본값, 라이트 = [data-theme="light"] 오버라이드
THEMES = {
    "dark": (tokens(":root"), "#151517", "#1C1C1F"),          # panel · elev
    "light": (tokens('[data-theme="light"]'), "#F7F7F8", "#FFFFFF"),
}


def test_두_룸_색이_회색이_아니다():
    """🔴 이게 원래 결함이다 — 채도 0 근처면 무슨 값을 넣어도 구분이 안 된다."""
    for theme, (tok, _p, _e) in THEMES.items():
        for room, col in tok.items():
            _h, s = hue_sat(col)
            assert s >= MIN_SAT, (
                "%s/--cal%s=%s 채도 %.2f — 회색이라 룸 구분이 안 된다"
                "(2026-08-04 대표 「회색끼리 두면 의미가 없잖아요」)" % (theme, room, col, s)
            )


def test_두_룸_색상이_충분히_멀다():
    """명도만 다른 두 색(= 옛 결함)도, 같은 계열 두 색도 막는다."""
    for theme, (tok, _p, _e) in THEMES.items():
        ha, _ = hue_sat(tok["A"])
        hb, _ = hue_sat(tok["B"])
        gap = abs(ha - hb)
        gap = min(gap, 360 - gap)
        assert gap >= MIN_HUE_GAP, (
            "%s: A=%s(%.0f°) B=%s(%.0f°) 색상차 %.0f° < %.0f° — 한눈에 안 갈린다"
            % (theme, tok["A"], ha, tok["B"], hb, gap, MIN_HUE_GAP)
        )


def test_칩_텍스트_대비가_4_5_이상():
    """칩은 15/18% 틴트 배경 위에 같은 색 글자를 올린다 — 그 조합에서 읽혀야 한다."""
    for theme, (tok, panel, elev) in THEMES.items():
        for room, col in tok.items():
            for bgname, bg in (("panel", panel), ("elev", elev)):
                c = contrast(col, over(col, bg, TINT[room]))
                assert c >= MIN_CONTRAST, (
                    "%s %s룸 on %s: 대비 %.2f:1 < %.1f" % (theme, room, bgname, c, MIN_CONTRAST)
                )


def test_칩에_룸_글자가_들어간다():
    """색맹·흑백 인쇄 안전판. 색만으로 정보를 전달하면 안 된다(WCAG 1.4.1).

    ⚠️ 모바일은 칩 텍스트를 숨기므로(font-size:0) 라벨이 화면엔 안 보이지만,
       그 경우에도 title 속성·dayDetail 칩으로 룸을 확인할 수 있어야 한다."""
    assert "var label=(e.room||'A')+'룸';" in HTML, "renderCal 이 룸 라벨을 만들지 않는다"
    assert "ev.textContent=label+' '+fmt(e.start)" in HTML, "칩 텍스트에 룸 라벨이 안 붙는다"
    assert "ev.title=label+" in HTML, "칩 title(hover 보완)이 사라졌다"
    # dayDetail(날짜 상세) 쪽 라벨은 원래 있었다 — 함께 사라지지 않게 박제.
    assert "chip.textContent=(e.room||'A')+'룸';" in HTML, "날짜 상세의 룸 칩이 사라졌다"


def test_faq가_넓은_화면에서_비지_않는다():
    """🔴 대표 지적 「05 FAQ … 빈공간이 좀 보여요 pc로 봤을때」 (2026-08-04).

    inner 는 1380px 인데 FAQ 본문만 `max-width:760px` 한 컬럼이라 우측 620px 이 통째로
    비었다(실측). 같은 페이지의 「오시는 길」·리뷰는 이미 grid 였고 FAQ 만 문법이 달랐다.
    ⇒ auto-fit minmax 로 통일. 이 테스트는 「한 컬럼 고정으로 되돌아가는 것」을 막는다."""
    i = HTML.index('id="faq"')
    j = HTML.index("<details", i)
    # ⚠️ HTML 주석을 먼저 걷어낸다 — 이 결함을 설명하는 주석이 옛 값을 그대로 인용하고 있어서,
    #   날것으로 검사하면 «주석 때문에 실패»한다(2026-08-04 실제로 한 번 걸렸다).
    head = re.sub(r"<!--.*?-->", "", HTML[i:j], flags=re.S)
    assert "max-width:760px" not in head, "FAQ 가 다시 760px 한 컬럼으로 고정됐다(우측이 빈다)"
    assert "repeat(auto-fit,minmax(" in head, "FAQ 본문이 auto-fit grid 가 아니다"
    # 하한 480px 미만이면 넓은 화면에서 3열이 되어 열이 좁아지고 마지막 행이 또 빈다(실측).
    m = re.search(r"minmax\(min\(100%,\s*(\d+)px\)", head)
    assert m and int(m.group(1)) >= 480, "FAQ 컬럼 하한이 480px 미만 — 3열로 쪼개진다"
    assert "align-items:start" in head, "align-items:start 가 없으면 details 를 열 때 행 높이가 튄다"


def test_범례가_같은_토큰을_쓴다():
    """범례 점과 칩이 다른 색이면 범례가 거짓말을 한다."""
    for room in ("A", "B"):
        assert "background:var(--cal%s)" % room in HTML, "%s룸 범례가 --cal%s 를 안 쓴다" % (room, room)
