# -*- coding: utf-8 -*-
"""룸 페이지 생성기(build_rooms.py) 재현·정합 테스트.

허브(/) + 룸별 페이지(/a·/b) 분리 구조의 SSOT는 rooms.json 하나다. 이 테스트는
그 불변식을 박제한다: 생성물 최신성 · 멱등성 · 가격 SSOT · 룸 간 가격 비교 금지 ·
h1 길이 가드 · canonical/sitemap 정합 · JSON-LD 유효성 · 후기 정본 가드 ·
예약 목적지 스위치(site.js 단일화).

⚠️ rooms.json·build_rooms.py·room.template.html·site.js·a.html·b.html 은 이 테스트가
   건드리지 않는다. 가드 재현 테스트는 실 파일을 임시 디렉터리에 복사한 뒤
   B.ROOT 를 monkeypatch 해서 돌린다(원본 미접촉).
"""
import json
import os
import re
import shutil
import subprocess
import sys

import build_rooms as B

HERE = os.path.dirname(os.path.abspath(__file__))
SLUGS = ["a", "b"]

MONEY_RE = re.compile(r"(\d{1,3}(?:,\d{3})*)원")


def _load_spec():
    return json.loads(open(os.path.join(HERE, "rooms.json"), encoding="utf-8").read())


def _read(name):
    return open(os.path.join(HERE, name), encoding="utf-8").read()


def _money_values(html_text):
    """페이지에 등장하는 '1,234원' 형태 금액을 정수 집합으로."""
    return {int(m.replace(",", "")) for m in MONEY_RE.findall(html_text)}


def _prep_tmp_root(tmp_path, spec):
    """rooms.json 만 바꾼 임시 작업 디렉터리 생성(template·reviews.json 은 실물 복사).

    실 rooms.json/room.template.html/reviews.json 은 절대 건드리지 않는다."""
    shutil.copy(os.path.join(HERE, "room.template.html"), tmp_path / "room.template.html")
    shutil.copy(os.path.join(HERE, "reviews.json"), tmp_path / "reviews.json")
    (tmp_path / "rooms.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    return tmp_path


# ── 1. 생성물 최신성 ────────────────────────────────────────────────
def test_check_flag_exits_zero_when_committed_outputs_are_current():
    """커밋된 a.html·b.html·rooms.data.js·sitemap.xml 이 rooms.json+템플릿과 일치해야 한다.
    어긋나면(= 빌드 후 커밋을 안 했으면) 여기서 exit 1로 걸린다."""
    # ⚠️ encoding 을 명시하지 않으면 자식 stdout 을 cp949 로 읽어 한글에서 UnicodeDecodeError 가 난다
    #    (스레드 예외라 테스트는 통과하고 경고만 남아 진짜 오류를 가린다).
    result = subprocess.run(
        [sys.executable, "build_rooms.py", "--check"],
        cwd=HERE, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert result.returncode == 0, (
        f"생성물이 최신이 아니다(build_rooms.py 실행+커밋 필요)\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )


# ── 2. 멱등성 ───────────────────────────────────────────────────────
def test_generate_is_idempotent():
    first = B.generate()
    second = B.generate()
    assert first == second
    assert set(first.keys()) == {"a.html", "b.html", "rooms.data.js", "sitemap.xml"}


# ── 3. 가격 SSOT ────────────────────────────────────────────────────
def test_price_strings_come_from_rooms_json():
    """페이지에 나오는 모든 '1,234원' 값은 그 룸의 rooms.json pricing 값과 정확히 일치해야 한다.
    rooms.json 에 없는 금액이 페이지에 있으면 실패(이중기재 사고)."""
    spec = _load_spec()
    rooms_by_slug = {r["slug"]: r for r in spec["rooms"]}
    for slug in SLUGS:
        room = rooms_by_slug[slug]
        p = room["pricing"]
        # 시간당 요금 + 추가요금 고지(5인째 추가·조명 액세서리)까지 전부 pricing 에서 나와야 한다.
        expected = {
            p["weekday"],
            p["weekend"],
            p["extraGuestPerHour"],
            p["accessoryFeePerItem"],
        }
        html_text = _read(f"{slug}.html")
        found = _money_values(html_text)
        assert found == expected, (
            f"{slug}.html 의 금액 표기 {found} 가 rooms.json pricing {expected} 와 다르다"
        )


def test_surcharge_disclosure_present():
    """추가요금 조건이 룸 페이지에 고지돼야 한다. 룸 페이지엔 FAQ 가 없어
    빠뜨리면 조건이 0이 되고, CTA 를 태우는 페이지에서 그건 기대 불일치다."""
    spec = _load_spec()
    rooms_by_slug = {r["slug"]: r for r in spec["rooms"]}
    for slug in SLUGS:
        p = rooms_by_slug[slug]["pricing"]
        html_text = _read(f"{slug}.html")
        assert f"{p['extraGuestPerHour']:,}원" in html_text, f"{slug}.html 에 초과인원 추가요금 고지가 없다"
        assert f"{p['accessoryFeePerItem']:,}원" in html_text, f"{slug}.html 에 액세서리 요금 고지가 없다"
        assert p["weekendDefinition"] in html_text, f"{slug}.html 에 주말 정의가 없다"
        assert f"{p['baseGuests']}인 기준" in html_text, f"{slug}.html 에 기준 인원 표기가 없다"


# ── 4. 룸 간 가격 비교 금지 ─────────────────────────────────────────
def test_other_room_block_has_no_price():
    """'다른 룸' 카드(Other room)는 라벨·링크만 있고 가격은 절대 없어야 한다.
    두 룸 가격이 우연히 같은 값이라 숫자 비교로는 못 잡으므로, '다른 룸' 블록 자체에
    금액 패턴이 있는지를 직접 검사한다."""
    for slug in SLUGS:
        html_text = _read(f"{slug}.html")
        idx = html_text.index("Other room")
        end = html_text.index("</section>", idx)
        block = html_text[idx:end]
        assert not MONEY_RE.search(block), (
            f"{slug}.html 의 'Other room' 블록에 금액이 있다 — 룸 간 가격 비교 노출: {block!r}"
        )


def test_other_room_link_has_no_price_query_or_fragment():
    """다른 룸 링크는 슬러그 경로 하나뿐이어야 한다(가격이 붙은 딥링크 금지)."""
    spec = _load_spec()
    rooms = spec["rooms"]
    for i, room in enumerate(rooms):
        other = rooms[(i + 1) % len(rooms)]
        html_text = _read(f"{room['slug']}.html")
        assert f'href="/{other["slug"]}"' in html_text
        assert f'href="/{other["slug"]}?' not in html_text
        assert f'href="/{other["slug"]}#' not in html_text


def test_own_page_does_not_mention_other_room_price_context():
    """각 페이지 안에서 '다른 룸 라벨'과 '금액'이 같은 블록에 동시 등장하지 않는다.
    (지금은 두 룸 가격이 같은 값이라 문자열만 봐서는 못 잡는다 — 라벨-금액 인접성으로 판별한다.)"""
    spec = _load_spec()
    rooms_by_slug = {r["slug"]: r for r in spec["rooms"]}
    for slug in SLUGS:
        other_slug = "b" if slug == "a" else "a"
        other_label = rooms_by_slug[other_slug]["label"]  # 예: "B룸"
        html_text = _read(f"{slug}.html")
        for m in MONEY_RE.finditer(html_text):
            window = html_text[max(0, m.start() - 200): m.end() + 200]
            assert other_label not in window, (
                f"{slug}.html: 금액 {m.group(0)} 근처(±200자)에 다른 룸 라벨 '{other_label}' 이 있다"
            )


# ── 5. h1 첫 줄 상한 가드 ───────────────────────────────────────────
def test_h1_first_line_over_limit_raises(tmp_path):
    """공백 제외 8글자를 넘는 h1 첫 줄은 빌드가 SystemExit 으로 막아야 한다."""
    spec = _load_spec()
    spec["rooms"][0]["hero"]["h1"][0] = "이것은너무길게쓴제목이다"  # 공백없이 12글자
    _prep_tmp_root(tmp_path, spec)
    orig_root = B.ROOT
    try:
        B.ROOT = tmp_path
        try:
            B.generate()
            assert False, "h1 첫 줄이 8글자를 넘는데 SystemExit 이 안 났다"
        except SystemExit as e:
            assert "8" in str(e) or "h1" in str(e)
    finally:
        B.ROOT = orig_root


def test_h1_first_line_at_limit_does_not_raise(tmp_path):
    """경계값(공백 제외 정확히 8글자)은 통과해야 한다(과잉 가드 아님을 함께 못박는다)."""
    spec = _load_spec()
    spec["rooms"][0]["hero"]["h1"][0] = "일이삼사오육칠팔"  # 정확히 8글자
    _prep_tmp_root(tmp_path, spec)
    orig_root = B.ROOT
    try:
        B.ROOT = tmp_path
        out = B.generate()
        assert "일이삼사오육칠팔" in out["a.html"]
    finally:
        B.ROOT = orig_root


# ── 6. canonical / sitemap 정합 ────────────────────────────────────
def test_canonical_matches_slug():
    for slug in SLUGS:
        html_text = _read(f"{slug}.html")
        assert f'<link rel="canonical" href="https://www.nuviestudio.com/{slug}">' in html_text


def test_sitemap_contains_all_required_paths():
    sitemap = _read("sitemap.xml")
    for loc in ("https://www.nuviestudio.com/",
                "https://www.nuviestudio.com/a",
                "https://www.nuviestudio.com/b",
                "https://www.nuviestudio.com/privacy"):
        assert f"<loc>{loc}</loc>" in sitemap, f"sitemap.xml 에 {loc} 이 없다"
    # cleanUrls:true 라 .html 은 308 된다 — 사이트맵에 리다이렉트 URL 을 넣지 않는다.
    assert ".html</loc>" not in sitemap, "sitemap.xml 에 .html URL 이 있다(cleanUrls 로 리다이렉트된다)"


# ── 7. JSON-LD 유효성 ───────────────────────────────────────────────
def _extract_jsonld(html_text):
    m = re.search(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html_text, re.S
    )
    assert m, "ld+json 스크립트 블록을 찾지 못했다"
    return json.loads(m.group(1))


def test_jsonld_parses_and_product_in_stock():
    for slug in SLUGS:
        html_text = _read(f"{slug}.html")
        data = _extract_jsonld(html_text)
        assert isinstance(data, list) and len(data) >= 1
        product = next(x for x in data if x.get("@type") == "Product")
        assert product["offers"]["availability"] == "https://schema.org/InStock"


def test_jsonld_breadcrumb_present():
    for slug in SLUGS:
        html_text = _read(f"{slug}.html")
        data = _extract_jsonld(html_text)
        types = {x.get("@type") for x in data}
        assert "BreadcrumbList" in types


# ── 8. 후기 정본 가드 ───────────────────────────────────────────────
def test_reviews_placeid_mismatch_raises(tmp_path):
    """showReviews=true 인 룸의 external.placeId 가 reviews.json place_id 와 다르면
    빌드가 SystemExit 으로 막아야 한다(거짓 사회적 증거 방지)."""
    spec = _load_spec()
    a_room = next(r for r in spec["rooms"] if r["slug"] == "a")
    assert a_room["showReviews"] is True
    a_room["external"]["placeId"] = a_room["external"]["placeId"] + 1  # 실제 후기 출처와 어긋나게
    _prep_tmp_root(tmp_path, spec)
    orig_root = B.ROOT
    try:
        B.ROOT = tmp_path
        try:
            B.generate()
            assert False, "showReviews 룸의 placeId 가 reviews.json 과 다른데 SystemExit 이 안 났다"
        except SystemExit as e:
            assert "showReviews" in str(e) or "place_id" in str(e)
    finally:
        B.ROOT = orig_root


def test_reviews_placeid_match_does_not_raise(tmp_path):
    """placeId 가 일치하면 정상 빌드(과잉 가드 아님을 함께 못박는다)."""
    spec = _load_spec()
    _prep_tmp_root(tmp_path, spec)
    orig_root = B.ROOT
    try:
        B.ROOT = tmp_path
        out = B.generate()
        assert "a.html" in out
    finally:
        B.ROOT = orig_root


# ── 9. 예약 목적지 스위치 ───────────────────────────────────────────
def _data_book_href_pairs(html_text, slug):
    """data-book="<slug>" 앵커의 href 목록."""
    return re.findall(rf'data-book="{slug}"\s+href="([^"]*)"', html_text)


def test_template_has_no_hardcoded_booking_destination():
    """템플릿에 예약 목적지 리터럴이 있으면 안 된다 — 목적지는 rooms.json 에서만 나온다.
    (생성물 HTML 에는 목적지가 박히는 게 맞다. JS 가 죽어도 예약이 되게 하는 폴백이다.)"""
    tpl = _read("room.template.html")
    assert "hourplace" not in tpl, "room.template.html 에 hourplace URL 이 하드코딩됐다"
    assert "{{BOOKING_HREF}}" in tpl, "예약 CTA 가 rooms.json 유래 href 를 쓰지 않는다"


def test_booking_destination_follows_fulfillment_mode(tmp_path):
    """예약 목적지는 rooms.json 의 fulfillment.mode + external.placeId 에서만 갈려야 한다.

    - mode='external' → 그 룸의 placeId 로 만든 아워플레이스 URL
    - mode='own'      → /book/<slug> 이고 hourplace 흔적이 0
    ⇒ PortOne V2 전환은 rooms.json 한 줄 + 재빌드로 끝난다.
    """
    spec = _load_spec()
    rooms_by_slug = {r["slug"]: r for r in spec["rooms"]}

    external_out = B.generate()  # 실 rooms.json = mode 'external'
    for slug in SLUGS:
        place_id = rooms_by_slug[slug]["external"]["placeId"]
        expected = f"https://www.hourplace.co.kr/place/{place_id}"
        hrefs = _data_book_href_pairs(external_out[f"{slug}.html"], slug)
        assert hrefs, f"{slug}.html 에 data-book 예약 앵커가 없다"
        assert set(hrefs) == {expected}, (
            f"{slug}.html 예약 href {set(hrefs)} 가 rooms.json placeId({place_id}) 유래가 아니다"
        )

    own_spec = _load_spec()
    own_spec["catalog"]["fulfillment"]["mode"] = "own"
    _prep_tmp_root(tmp_path, own_spec)
    orig_root = B.ROOT
    try:
        B.ROOT = tmp_path
        own_out = B.generate()
    finally:
        B.ROOT = orig_root

    for slug in SLUGS:
        own_html = own_out[f"{slug}.html"]
        assert "hourplace" not in own_html, (
            f"{slug}.html(mode=own) 에 hourplace URL 이 남았다 — 전환 스위치가 새고 있다"
        )
        hrefs = _data_book_href_pairs(own_html, slug)
        assert set(hrefs) == {f"/book/{slug}"}, (
            f"{slug}.html(mode=own) 예약 href 가 /book/{slug} 이 아니다: {set(hrefs)}"
        )
        # CTA 개수는 모드와 무관하게 같아야 한다(전환으로 버튼이 사라지면 안 된다)
        assert len(hrefs) == len(_data_book_href_pairs(external_out[f"{slug}.html"], slug))


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
