# -*- coding: utf-8 -*-
"""사이트 글자 서브셋 글꼴 빌더 (2026-09-29).

왜: Pretendard «동적 서브셋»(CDN CSS·unicode-range 92조각)은 글자를 배치한 «뒤에야» 필요한 조각을 요청한다.
  그래서 새로 열 때마다(뒤로 가기 포함) 대체 글꼴로 먼저 그리고 나중에 바뀌며, 그때 화면에 있는 글이 전부
  줄바꿈을 다시 해 밀린다(/a 360px 뒤로 가기 CLS 0.4~0.6 실측). 또 CDN CSS 가 렌더를 막아 /a 첫 화면이 3.1초였다.
무엇: 사이트에 실제로 나오는 글자만 담은 woff2 를 굵기별로 만들어 자체 호스팅하고 <link rel=preload> 로
  글자 배치 «전에» 받는다(굵기 = build_rooms.FONT_PRELOAD). fonts.css 는 font-display: optional(09-30 대표 결정) —
  제때 없으면 그 페이지는 기기 기본 한글 글꼴로 끝까지. 서브셋에 없는 글자도 기기 글꼴로 나온다.

라이선스(SIL OFL 1.1 · Reserved Font Name «Pretendard»): 서브셋은 OFL 상 수정본이라 «Pretendard» 이름을 쓰지 않는다
  → 글꼴 내부 이름을 FAMILY 로 바꾸고, 원문 LICENSE 를 fonts/ 에 함께 둔다.

입력: 원본 woff2(Pretendard v1.3.9 static, 굵기별) = 인자 --src, 없으면 ~/.cache/nuvie-landing/pretendard-1.3.9 (없으면 고정 주소에서 받음)
출력: fonts/nuvie-sans-{400,500,600,700}.woff2 · fonts/LICENSE-Pretendard-OFL.txt · fonts/chars.txt(담은 글자)
실행: python build_fonts.py [--src 폴더]  (멱등 — 글자 집합이 같으면 파일을 다시 쓰지 않는다)
"""
import argparse
import json
import sys
from io import BytesIO
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "fonts"
FAMILY = "NuvieSans"
WEIGHTS = {400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold"}
# 사이트 글이 나오는 파일(HTML 속 JS 문자열 포함) + 후기·룸 데이터
TEXT_SOURCES = ["index.html", "a.html", "b.html", "404.html", "privacy.html", "room.template.html",
                "site.js", "rooms.data.js",   # JS 가 화면에 쓰는 문구(새 눈 검수 09-29: 빠져 있었다)
                "reviews_all.json", "reviews.json", "reviews_b.json", "rooms.json"]
# 늘 넣는 글자: 인쇄 가능한 ASCII 전부 + 자주 쓰는 기호(새 문구·후기에 흔한 것) + 테마 버튼 ☾☀
ALWAYS = "".join(chr(c) for c in range(0x20, 0x7F)) + "·…‘’“”«»〈〉「」『』–—→←↑↓★☆♥♡✓✔×÷°%₩~!?()[]☾☀"


def site_chars(root=HERE, sources=TEXT_SOURCES):
    """사이트 글자 집합. JSON 은 문자열 값만(키·이스케이프 무관), HTML 은 파일 전체 글자."""
    chars = set(ALWAYS)
    for name in sources:
        p = root / name
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        if name.endswith(".json"):
            def walk(v):
                if isinstance(v, str):
                    chars.update(v)
                elif isinstance(v, dict):
                    for x in v.values():
                        walk(x)
                elif isinstance(v, list):
                    for x in v:
                        walk(x)
            walk(json.loads(text))
        else:
            chars.update(text)
    return {c for c in chars if c.isprintable() and not c.isspace() or c == " "}


def rename(font, family=FAMILY, style="Regular"):
    """OFL RFN: 수정본은 «Pretendard» 이름을 쓰면 안 된다 → name 테이블의 이름 계열을 모두 바꾼다."""
    name = font["name"]
    full = f"{family} {style}"
    ps = f"{family}-{style}"
    for rec in list(name.names):
        if rec.nameID in (1, 16):
            rec.string = family
        elif rec.nameID in (2, 17):
            rec.string = style
        elif rec.nameID == 4:
            rec.string = full
        elif rec.nameID == 6:
            rec.string = ps
        elif rec.nameID == 3:
            rec.string = f"{ps};nuviestudio-subset"
    return font


def subset_one(src_path, chars, style):
    from fontTools import subset
    from fontTools.ttLib import TTFont
    font = TTFont(str(src_path))
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.name_languages = ["*"]
    opts.notdef_outline = True
    sub = subset.Subsetter(options=opts)
    sub.populate(unicodes=sorted(ord(c) for c in chars))
    sub.subset(font)
    rename(font, FAMILY, style)
    buf = BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    return buf.getvalue()


def build(src_dir, out_dir=OUT, root=HERE):
    chars = site_chars(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    listing = "".join(sorted(chars))
    chars_path = out_dir / "chars.txt"
    same = chars_path.exists() and chars_path.read_text(encoding="utf-8") == listing
    written = []
    for w, style in WEIGHTS.items():
        dst = out_dir / f"nuvie-sans-{w}.woff2"
        if same and dst.exists():
            continue
        src = Path(src_dir) / f"Pretendard-{style}.woff2"
        if not src.exists():
            raise SystemExit(f"[build_fonts] 원본 없음: {src}")
        dst.write_bytes(subset_one(src, chars, style))
        written.append(dst.name)
    chars_path.write_text(listing, encoding="utf-8")
    lic_src = Path(src_dir) / "LICENSE.txt"
    if lic_src.exists():
        (out_dir / "LICENSE-Pretendard-OFL.txt").write_text(lic_src.read_text(encoding="utf-8"), encoding="utf-8")
    return chars, written


# 원본은 레포에 싣지 않는다(굵기당 ~770KB·공개 레포). 없으면 고정 버전 주소에서 받아 로컬 캐시에 둔다.
SRC_CACHE = Path.home() / ".cache" / "nuvie-landing" / "pretendard-1.3.9"
SRC_BASE = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9"
SRC_FILES = {f"Pretendard-{s}.woff2": f"/packages/pretendard/dist/web/static/woff2/Pretendard-{s}.woff2"
             for s in WEIGHTS.values()}
SRC_FILES["LICENSE.txt"] = "/LICENSE"


def ensure_sources(src_dir=SRC_CACHE, fetch=None):
    """원본 woff2·LICENSE 가 없으면 받는다. woff2 는 매직(wOF2)을 확인해 오류 페이지를 글꼴로 착각하지 않는다."""
    import urllib.request
    src_dir = Path(src_dir)
    src_dir.mkdir(parents=True, exist_ok=True)

    def _get(url):
        req = urllib.request.Request(url, headers={"User-Agent": "nuvie-landing-build/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    fetch = fetch or _get
    for name, rel in SRC_FILES.items():
        dst = src_dir / name
        if dst.exists() and dst.stat().st_size > 0:
            continue
        data = fetch(SRC_BASE + rel)
        if name.endswith(".woff2") and data[:4] != b"wOF2":
            raise SystemExit(f"[build_fonts] {name} 가 woff2 가 아니다(받은 {len(data)}B) — 원본 주소 확인")
        dst.write_bytes(data)
    return src_dir


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=None, help="원본 폴더(기본 = 로컬 캐시, 없으면 받는다)")
    a = ap.parse_args(argv)
    src = a.src or str(ensure_sources())
    chars, written = build(src)
    sizes = {p.name: p.stat().st_size for p in sorted(OUT.glob("nuvie-sans-*.woff2"))}
    print(f"[build_fonts] 글자 {len(chars)}개 · 새로 씀 {written or '없음'} · 크기 {sizes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
