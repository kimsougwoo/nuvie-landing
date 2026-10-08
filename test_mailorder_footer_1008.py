from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent


def test_home_footer_shows_registered_mail_order_number():
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "통신판매업 신고번호: 2026-서울강서-2507" in index


def test_home_footer_links_to_ftc_business_check_safely():
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    match = re.search(
        r'<a\b[^>]*href="https://www\.ftc\.go\.kr/bizCommPop\.do\?wrkr_no=2412302118"[^>]*>사업자정보확인</a>',
        index,
    )
    assert match, "FTC business check link is missing from the home footer"
    opening_tag = match.group(0).split(">", 1)[0]
    assert 'target="_blank"' in opening_tag
    assert 'rel="noopener noreferrer"' in opening_tag
    assert 'class="nv-privacy"' in opening_tag


# 10-08 범위 고정용(총괄 승인 = 홈 푸터만, B룸 대외 표면 11/11 동결). 법정 요건이 아니다.
# a.html·b.html 푸터에도 신고번호를 맞출 때 이 시험을 지운다.
def test_room_pages_do_not_show_mail_order_registration_text():
    for page in ("a.html", "b.html"):
        html = (ROOT / page).read_text(encoding="utf-8")
        assert "통신판매업" not in html
