from pathlib import Path


ROOT = Path(__file__).parent


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_interest_form_requires_separate_privacy_consent_and_has_safe_action():
    html = read("index.html")
    assert 'id="interestForm"' in html
    assert 'action="/api/interest"' in html
    assert 'name="privacy_consent"' in html
    assert 'name="marketing_consent"' in html
    assert 'name="privacy_consent" type="checkbox" required' in html
    assert 'name="website"' in html
    assert 'href="/privacy.html"' in html


def test_attribution_script_is_loaded_without_putting_contact_fields_in_analytics():
    index = read("index.html")
    attribution = read("attribution.js")
    template = read("room.template.html")
    assert '<script src="/attribution.js"></script>' in index
    assert '<script src="/attribution.js"></script>' in template
    assert "first_touch" in attribution and "last_touch" in attribution
    assert "landing_view" in attribution
    assert "booking_intent" in attribution
    assert "interest_form_submitted" in attribution
    assert "event('interest_form_submit_attempt', { room: room, transport_type: 'beacon' })" in attribution
    assert "event('interest_form_submitted', { room: room, transport_type: 'beacon' })" in attribution
    assert "interest_form_submitted', { room: room, email:" not in attribution
    assert "interest_form_submitted', { room: room, phone:" not in attribution


def test_existing_booking_metric_definitions_remain_present():
    index = read("index.html")
    site = read("site.js")
    assert "gtag('event','book_click',{room:room,transport_type:'beacon',page:'hub'})" in index
    assert "gtag('event', 'book_click', { room: room, transport_type: 'beacon', page: PAGE_ORIGIN })" in site
    assert "ad_capture" in index and "ad_capture" in site


def test_privacy_page_discloses_first_party_interest_collection_and_optional_marketing_consent():
    privacy = read("privacy.html")
    assert "자사몰 관심·예약 알림 접수" in privacy
    assert "개인정보처리방침 동의" in privacy
    assert "광고성 정보 동의" in privacy
    assert "Notion" in privacy
    assert "자동화된 의사결정" in privacy
