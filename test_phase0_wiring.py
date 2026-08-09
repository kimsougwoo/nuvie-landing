from pathlib import Path


ROOT = Path(__file__).parent


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_public_landing_has_no_duplicate_interest_surface_when_booking_is_open():
    html = read("index.html")
    for marker in ('href="#interest"', 'id="interest"', 'interestForm', '관심 접수', '빈 시간 알림'):
        assert marker not in html
    assert 'id="availability"' in html
    assert 'https://www.hourplace.co.kr/place/61823' in html
    assert 'https://www.hourplace.co.kr/place/62341' in html
    assert '<span class="no">04</span> 오시는 길' in html
    assert '<span class="no">05</span> FAQ' in html


def test_attribution_script_is_loaded_without_putting_contact_fields_in_analytics():
    index = read("index.html")
    attribution = read("attribution.js")
    template = read("room.template.html")
    assert '<script src="/attribution.js"></script>' in index
    assert '<script src="/attribution.js"></script>' in template
    assert "first_touch" in attribution and "last_touch" in attribution
    assert "landing_view" in attribution
    assert "booking_intent" in attribution
    assert "interest_form_" not in attribution
    assert "interestForm" not in attribution


def test_existing_booking_metric_definitions_remain_present():
    index = read("index.html")
    site = read("site.js")
    assert "gtag('event','book_click',{room:room,transport_type:'beacon',page:'hub'})" in index
    assert "gtag('event', 'book_click', { room: room, transport_type: 'beacon', page: PAGE_ORIGIN })" in site
    assert "ad_capture" in index and "ad_capture" in site


def test_dormant_interest_api_privacy_disclosure_remains_consistent():
    privacy = read("privacy.html")
    assert "자사몰 관심·예약 알림 접수" in privacy
    assert "개인정보처리방침 동의" in privacy
    assert "광고성 정보 동의" in privacy
    assert "Notion" in privacy
    assert "자동화된 의사결정" in privacy
