"""룸별 OG 이미지 생성 — /img/og-a.jpg · /img/og-b.jpg (1200×630, 1.91:1)

    python build_og.py

왜 필요한가(2026-08-04 검수 지적): 룸 페이지는 twitter:card=summary_large_image 인데
og:image 로 세로(3:4)·4:3 사진을 쓰면 X·카카오·페이스북 공유 카드에서 중앙이 잘린다.
공유 카드는 1.91:1 을 기대하므로 그 비율로 미리 만들어 둔다.

소스는 원본 비율을 유지한 채 **중앙 크롭**만 한다(찌그러뜨리지 않는다).
소스 사진을 바꾸면 이 스크립트를 다시 돌려라.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
TARGET_W, TARGET_H = 1200, 630
RATIO = TARGET_W / TARGET_H

# (출력, 소스) — 소스는 룸을 한 컷으로 대표하는 이미지
JOBS = [
    ("img/og-a.jpg", "img/hero.jpg"),
    ("img/og-b.jpg", "img/room-b.jpg"),
]

# ── 허브 OG (og.jpg) ──────────────────────────────────────────────────
# 🔴 2026-08-04 재생성 사유 3가지 (X 고정 트윗 카드에서 실물 확인):
#   ① 카피가 옛 것이었다 — "눈치 보지 않는 코스프레 무인 스튜디오"(현행 h1 은 "남과 겹치지 않는")
#   ② 골드 텍스트 — 08-04 Stayfolio 전환으로 폐기한 옛 디자인 시스템 잔재
#   ③ A룸 사진 단독 — 히어로는 룸 중립화했는데 OG 만 A룸 편향이 남아 있었다
# ⚠️ **카피는 index.html 의 h1 에서 읽어 온다.** 여기에 문자열을 또 적으면 갈라진다 —
#    ①이 바로 그렇게 생긴 결함이다(랜딩은 고쳤는데 OG 는 안 고쳐짐).
HUB_OG = "og.jpg"
HUB_W, HUB_H, HUB_BAND = 1200, 630, 250
INK = (17, 17, 18)


def read_hub_h1() -> tuple[str, str]:
    """index.html 히어로 h1 → (첫 줄, 둘째 줄). 못 읽으면 예외로 죽는다(조용한 옛 카피 금지)."""
    import re
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<h1 data-reveal[^>]*>(.*?)<br><span[^>]*>(.*?)</span></h1>', html, re.S)
    if not m:
        raise SystemExit("[build_og] index.html 에서 히어로 h1 을 못 찾았다 — 셀렉터 확인 필요")
    return m.group(1).strip(), m.group(2).strip()


def make_hub() -> None:
    from PIL import ImageDraw, ImageFont

    def font(sz, bold=True):
        cands = ([r"C:\Windows\Fonts\malgunbd.ttf"] if bold else []) + [r"C:\Windows\Fonts\malgun.ttf"]
        for fp in cands:
            try:
                return ImageFont.truetype(fp, sz)
            except Exception:
                pass
        return ImageFont.load_default()

    def cover(im, tw, th, ay=0.5):
        sw, sh = im.size
        s = max(tw / sw, th / sh)
        nw, nh = int(sw * s + 0.5), int(sh * s + 0.5)
        im = im.resize((nw, nh), Image.LANCZOS)
        x, y = int((nw - tw) * 0.5), int((nh - th) * ay)
        return im.crop((x, y, x + tw, y + th))

    line1, line2 = read_hub_h1()
    photo_h, half = HUB_H - HUB_BAND, HUB_W // 2
    a = cover(Image.open(ROOT / "img/hero.jpg").convert("RGB"), half, photo_h, ay=0.44)
    b = cover(Image.open(ROOT / "img/room-b.jpg").convert("RGB"), half, photo_h, ay=0.55)
    canvas = Image.new("RGB", (HUB_W, HUB_H), INK)
    canvas.paste(a, (0, 0)); canvas.paste(b, (half, 0))
    ImageDraw.Draw(canvas).line([(half, 0), (half, photo_h)], fill=(255, 255, 255), width=2)

    # 사진→밴드 전환을 부드럽게. 딱 자르면 싸구려로 보이고, 어두운 A룸 쪽은 자연히 녹는다.
    fade = 90
    grad = Image.new("L", (1, HUB_H), 0)
    for y in range(HUB_H):
        if y >= photo_h:
            v = 255
        elif y >= photo_h - fade:
            v = int(255 * ((y - (photo_h - fade)) / fade) ** 1.6)
        else:
            v = 0
        grad.putpixel((0, y), v)
    canvas = Image.composite(Image.new("RGB", (HUB_W, HUB_H), INK), canvas, grad.resize((HUB_W, HUB_H)))

    d = ImageDraw.Draw(canvas)
    pad, y = 60, photo_h + 26
    d.text((pad, y), "  ".join("COSPLAY CONCEPT STUDIO"), font=font(21), fill=(168, 168, 172))
    y += 38
    d.text((pad, y), "누비 스튜디오", font=font(60), fill=(255, 255, 255))
    y += 76
    d.text((pad, y), f"{line1} {line2}", font=font(31), fill=(232, 229, 224))
    y += 46
    d.text((pad, y), "서울 강서구 · 까치산역 도보 10분 · nuviestudio.com",
           font=font(22, bold=False), fill=(150, 148, 144))
    canvas.save(ROOT / HUB_OG, "JPEG", quality=88, optimize=True, progressive=True)
    print(f"  {HUB_OG}  <- 2분할 + h1(\"{line1} {line2}\")")


def make(dst: Path, src: Path) -> None:
    im = Image.open(src).convert("RGB")
    w, h = im.size
    if w / h > RATIO:  # 소스가 더 넓다 → 좌우를 자른다
        new_w = round(h * RATIO)
        box = ((w - new_w) // 2, 0, (w - new_w) // 2 + new_w, h)
    else:  # 소스가 더 높다 → 위아래를 자른다
        new_h = round(w / RATIO)
        box = (0, (h - new_h) // 2, w, (h - new_h) // 2 + new_h)
    im.crop(box).resize((TARGET_W, TARGET_H), Image.LANCZOS).save(
        dst, "JPEG", quality=86, optimize=True, progressive=True
    )
    print(f"  {dst.name}  <- {src.name}  crop{box} -> {TARGET_W}x{TARGET_H}  {dst.stat().st_size:,}B")


def main() -> int:
    for out, src in JOBS:
        make(ROOT / out, ROOT / src)
    make_hub()          # 허브 OG — 카피는 index.html h1 에서 읽어 온다
    print("완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
