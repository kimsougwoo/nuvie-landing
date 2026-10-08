from pathlib import Path

ROOT = Path(__file__).resolve().parent


# 10-09 대표 확정: 올데이권 = 12시간 독립 상품, 9시간 이상 자동 전환 없음.
def test_allday_has_no_nine_hour_auto_switch_sentence():
    for name in ("index.html", "llms.txt"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "9시간" not in text, name


def test_allday_answer_keeps_price_and_phone_inquiry():
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
    for text in (index, llms):
        assert "평일 600,000원 / 주말·공휴일 750,000원" in text
        assert "인원 추가요금" in text
    assert "인원 추가요금은 없습니다.<br>미리 알아 두실 점" in index
    assert "인원 추가요금은 없습니다. 미리 알아 두실 점" in index
    assert "인원 추가요금 없음. 아워플레이스 상품이 아니라" in llms
