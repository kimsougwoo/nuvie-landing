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
    print("완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
