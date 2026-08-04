# -*- coding: utf-8 -*-
"""허브(index.html) 시각 회귀 모음 — 2026-08-04 대표 지적 4건을 박제한다.

[1] 예약 현황 달력에서 A룸/B룸이 실제로 구분되는가

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


# ── [4] 히어로 배경이 테마를 따라가는가 (2026-08-04 대표 안) ──────────────────
def test_히어로가_테마별로_다른_룸을_쓴다():
    """대표 안 「라이트일 땐 B룸, 다크일 땐 A룸」.

    A룸=어둠(달 조명) · B룸=빛(통창)이라 테마와 그대로 대응하고, 어느 룸도 편들지 않는다.
    🔴 이전 상태: h1 은 룸 중립("코스프레 스튜디오")인데 배경은 A룸 사진 하나였다 —
       08-04 디자인 재설계의 사유가 「액센트 하나가 A룸에 붙어 B룸을 못 받는다」였는데
       정작 가장 큰 표면에 같은 편향이 남아 있었다."""
    m = re.search(r"var HERO_BG=\{(.*?)\};", HTML, re.S)
    assert m, "HERO_BG 매핑이 사라졌다"
    blk = m.group(1)
    assert re.search(r"dark\s*:\{src:'/img/hero\.jpg'", blk), "다크 = A룸(hero.jpg) 이 아니다"
    assert re.search(r"light\s*:\{src:'/img/room-b\.jpg'", blk), "라이트 = B룸(room-b.jpg) 이 아니다"
    assert "paintHero(t);}" in HTML, "setTheme 이 배경을 갈아끼우지 않는다"


def test_히어로_초기_이미지가_초기_테마와_일치한다():
    """🔴 어긋나면 LCP 이미지를 버리고 다시 받는다(첫 화면 깜빡임 + 낭비).

    초기 테마는 <body data-theme="..."> 하드코딩이고 setTheme 은 토글 때만 돈다 →
    **초기 src 는 HTML 이 정본**이라 손으로 맞춰야 하고, 그래서 조용히 어긋나기 쉽다."""
    theme = re.search(r'<body data-theme="(\w+)"', HTML).group(1)
    want = "/img/room-b.jpg" if theme == "light" else "/img/hero.jpg"
    hero = re.search(r'<img id="heroImg"[^>]*src="([^"]+)"', HTML)
    assert hero, "heroImg 를 못 찾음"
    assert hero.group(1) == want, (
        "초기 테마가 %s 인데 히어로 초기 src 가 %s (기대 %s)" % (theme, hero.group(1), want))


def test_faq_열이_독립_컨테이너다():
    """🔴 대표 지적 「하나를 열면 옆열에 있는 것도 길어져요」 (2026-08-04).

    grid 아이템을 그냥 늘어놓으면 한 행의 높이가 그 행의 가장 큰 아이템에 맞춰져,
    한쪽 details 를 펴면 반대쪽 칸 아래에 빈 공간이 생긴다.
    align-items:start 로는 못 막는다(아이템을 늘리지 않을 뿐 행 높이는 커진다).
    ⇒ 각 열을 div 하나로 묶어야 열마다 독립적으로 흐른다."""
    i = HTML.index('id="faq"')
    j = HTML.index("</section>", i)
    seg = re.sub(r"<!--.*?-->", "", HTML[i:j], flags=re.S)
    body = seg[seg.index("display:grid"):]
    # 그리드 직계 자식이 details 가 아니라 컬럼 div 여야 한다
    first = body.index(">") + 1
    after = body[first:].lstrip()
    assert after.startswith("<div>"), "그리드 첫 자식이 컬럼 div 가 아니다(details 가 직접 놓였다)"
    assert body.count("<div>") >= 2, "컬럼 div 가 2개 미만 — 열이 독립돼 있지 않다"


def test_반대_테마_히어로_이미지를_미리_받는다():
    """🔴 없으면 테마 토글 때마다 히어로가 검게 깜빡인다(2026-08-04 라이브 관찰).

    사진을 그 자리에서 로드하기 때문. load 이후 프리로드로 교체를 즉시로 만든다.
    ⚠️ load 이전에 받으면 초기 LCP 대역을 뺏는다 — 그래서 window load 훅이어야 한다."""
    assert "window.addEventListener('load',heroMakeBack)" in HTML, "뒤 레이어 생성이 load 훅에 없다"
    assert "heroBack.src=HERO_BG[other].src" in HTML, "반대 테마 이미지를 미리 받지 않는다"


def test_히어로_전환이_크로스페이드다():
    """🔴 대표 「히어로 전환이 좀 딱딱하네요」 (2026-08-04).

    같은 <img> 의 src 를 갈아끼우면 교체 순간 사진이 사라져 뒤의 검은 그라디언트가 드러난다.
    두 레이어를 겹쳐 opacity 만 넘겨야 부드럽다."""
    assert "function heroSwap(" in HTML, "크로스페이드 스왑이 없다(src 직접 교체로 회귀)"
    assert "transition:opacity" in HTML, "히어로 img 에 opacity 트랜지션이 없다"
    assert "heroFront=b; heroBack=f;" in HTML, "레이어 역할 교대가 없다"
    # 🔴 두 장을 동시에 페이드하면 중간이 검어진다(라이브 실측). 아래 레이어는 켜둔 채
    #    위 레이어만 올려야 한다 — f.style.opacity='0' 을 다시 넣으면 그 결함이 재발한다.
    assert "f.parentNode.appendChild(b);" in HTML, "새 사진을 맨 위로 올리지 않는다"
    assert "void b.offsetWidth;" in HTML, "리플로우 강제가 없으면 0→1 이 합쳐져 전환이 사라진다"
    swap = HTML[HTML.index("function heroSwap("):HTML.index("function paintHero(")]
    assert "f.style.opacity='0'" not in swap, "아래 레이어를 끄면 전환 중간에 배경이 비친다"
    # 접근성: 숨은 레이어는 스크린리더에서 빠져야 한다
    assert "b.removeAttribute('aria-hidden')" in HTML and "f.setAttribute('aria-hidden','true')" in HTML,         "전환 시 aria-hidden 이 따라가지 않는다(같은 사진이 두 번 읽힌다)"
    assert "heroReduce" in HTML, "prefers-reduced-motion 을 존중하지 않는다"


# ── [5] 허브 OG 카피가 h1 과 갈라지지 않는가 (2026-08-04) ─────────────
def test_og_생성기가_h1을_읽어온다():
    """🔴 실제로 갈라졌던 결함: 랜딩 h1 은 「남과 겹치지 않는」인데 og.jpg 는
    옛 카피 「눈치 보지 않는 코스프레 무인 스튜디오」를 담고 있었다.
    X 고정 트윗 카드에서 그 옛 문구가 그대로 노출됐다(2026-08-04 실물 확인).

    ⇒ 생성기가 index.html 의 h1 을 **읽어서** 쓰게 했다. 여기에 문자열을 또 적으면
      같은 방식으로 다시 갈라지므로, 그걸 막는다."""
    src = (ROOT / "build_og.py").read_text(encoding="utf-8")
    assert "def read_hub_h1(" in src, "OG 생성기가 h1 을 읽지 않는다"
    assert "make_hub()" in src.split("def main(")[1], "main() 이 허브 OG 를 안 만든다"
    # 카피를 하드코딩으로 되돌리는 회귀 차단.
    # ⚠️ 주석 줄을 먼저 걷는다 — 이 결함을 설명하는 주석이 옛/현 카피를 그대로 인용하고 있어서,
    #   날것으로 검사하면 «주석 때문에» 실패한다(2026-08-04 FAQ 테스트에서 한 번 겪고 또 겪었다).
    code = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
    assert "남과 겹치지" not in code, "OG 생성기에 카피가 하드코딩됐다(h1 과 갈라진다)"
    assert "{line1} {line2}" in code, "읽어온 h1 을 실제로 그리지 않는다"


def test_og_생성기가_읽는_셀렉터가_실제_h1과_맞는다():
    """셀렉터가 어긋나면 빌드가 SystemExit 으로 죽어야 한다 — 조용히 옛 이미지를 남기면 안 된다."""
    import re
    m = re.search(r'<h1 data-reveal[^>]*>(.*?)<br><span[^>]*>(.*?)</span></h1>', HTML, re.S)
    assert m, "build_og.read_hub_h1 의 정규식이 현재 index.html 과 안 맞는다"
    assert m.group(1).strip() and m.group(2).strip()
