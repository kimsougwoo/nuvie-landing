# -*- coding: utf-8 -*-
"""후기 사진 축소 사본 빌더 (2026-09-29).

reviews_all.json 의 photos URL(아워플레이스 원본, 최대 29MP·25MB)을 한 번만 내려받아
reviews/img/ 에 WebP 두 벌을 만든다: 썸네일 긴 변 640px · 확대용 긴 변 1600px.
매핑은 reviews/img/map.json = {원본URL: {thumb, full, w, h}} (w/h = 확대본 크기).

- 파일명 = 원본 URL sha1 앞 12자 + -640.webp / -1600.webp
- EXIF 방향을 반영해 똑바로 세운다(세로 사진이 눕지 않게)
- 이미 있으면 내려받지 않는다(멱등)
- 내려받기·디코드 실패 URL 은 map 에 넣지 않는다 → index.html 이 원본으로 폴백
- reviews_all.json / reviews.json 은 읽기만 한다(후기 원문 verbatim)

실행: python build_review_images.py
"""
import hashlib
import io
import json
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "reviews" / "img"
REL_PREFIX = "reviews/img"
THUMB_SIDE, THUMB_Q = 640, 78
FULL_SIDE, FULL_Q = 1600, 82
UA = "Mozilla/5.0 (compatible; nuvie-landing-build/1.0)"


def file_key(url):
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def http_fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def _resized(im, side):
    out = im.copy()
    out.thumbnail((side, side), Image.LANCZOS)  # 긴 변 기준·확대 없음
    return out


def _save_webp(im, path, quality):
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")
    im.save(path, "WEBP", quality=quality, method=6)


def collect_urls(reviews_path):
    d = json.loads(Path(reviews_path).read_text(encoding="utf-8"))
    seen, urls = set(), []
    for r in d.get("reviews", []):
        for u in r.get("photos") or []:
            if u not in seen:
                seen.add(u)
                urls.append(u)
    return urls


def build(urls, out_dir=OUT_DIR, fetch=http_fetch, rel_prefix=REL_PREFIX):
    """반환: (map, failed_urls). out_dir/map.json 도 쓴다."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result, failed = {}, []
    for url in urls:
        key = file_key(url)
        tp, fp = out_dir / f"{key}-{THUMB_SIDE}.webp", out_dir / f"{key}-{FULL_SIDE}.webp"
        try:
            if not (tp.exists() and fp.exists()):
                im = ImageOps.exif_transpose(Image.open(io.BytesIO(fetch(url))))
                im.load()
                full = _resized(im, FULL_SIDE)
                _save_webp(_resized(im, THUMB_SIDE), tp, THUMB_Q)
                _save_webp(full, fp, FULL_Q)
            with Image.open(fp) as f:
                w, h = f.size
        except Exception as e:  # 네트워크·디코드 실패 = 이 사진만 원본 폴백
            print(f"경고: {url} 사본 생성 실패({type(e).__name__}: {e}) — 원본으로 폴백", file=sys.stderr)
            for p in (tp, fp):
                if p.exists() and not (tp.exists() and fp.exists()):
                    p.unlink()
            failed.append(url)
            continue
        result[url] = {"thumb": f"{rel_prefix}/{tp.name}", "full": f"{rel_prefix}/{fp.name}", "w": w, "h": h}
    (out_dir / "map.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return result, failed


def main():
    urls = collect_urls(HERE / "reviews_all.json")
    m, failed = build(urls)
    total = sum((OUT_DIR / Path(e[k]).name).stat().st_size for e in m.values() for k in ("thumb", "full"))
    print(f"사진 URL {len(urls)}개 · 사본 {len(m)}개 · 실패(원본 폴백) {len(failed)}개 · 사본 합계 {total/1e6:.2f}MB")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
