from pathlib import Path


ROOT = Path(__file__).resolve().parent


def test_public_room_titles_do_not_use_location_as_studio_brand():
    """까치산은 역명으로만 쓰고, 대외 브랜드명은 누비 스튜디오로 유지한다."""
    sources = (
        ROOT / "a.html",
        ROOT / "b.html",
        ROOT / "rooms.json",
    )
    forbidden = (
        "까치산 코스프레 스튜디오",
        "까치산 자연광 스튜디오",
    )

    for source in sources:
        text = source.read_text(encoding="utf-8")
        assert not any(term in text for term in forbidden), source.name
