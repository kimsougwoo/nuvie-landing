# -*- coding: utf-8 -*-
"""A룸 할로윈 세팅 안내 한 줄 — 10/31 까지만 보이고 11/1 부터는 코드가 알아서 숨긴다 (2026-09-28).

- 기본은 hidden. 스크립트가 한국 시간 오늘이 data-until(2026-11-01) 전일 때만 보이게 한다.
  JS 가 없는 크롤러·11/1 이후에는 아무것도 보이지 않는다(치우는 사람이 필요 없다).
- 11월 이후 이야기는 쓰지 않는다(11/1 A룸 복귀는 가정일 뿐 대표 결정이 아니다).
- /b 는 건드리지 않는다.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))


def _index():
    return open(os.path.join(HERE, "index.html"), encoding="utf-8").read()


def _note(html):
    m = re.search(r'<p[^>]*id="seasonNoteA"[^>]*>(.*?)</p>', html, re.S)
    assert m, "A룸 할로윈 한 줄(#seasonNoteA)이 없다"
    return m.group(0), m.group(1)


def test_note_exists_hidden_by_default_with_until():
    tag, text = _note(_index())
    assert " hidden" in tag.split(">")[0]
    assert 'data-until="2026-11-01"' in tag
    assert "할로윈" in text and "10월 31일" in text
    assert "11월" not in text


def test_script_reveals_only_before_until_in_kst():
    html = _index()
    m = re.search(r"<script>(?:(?!</script>).)*?seasonNoteA.*?</script>", html, re.S)
    assert m, "#seasonNoteA 를 켜는 스크립트가 없다"
    js = m.group(0)
    assert "9*3600" in js or "9 * 3600" in js, "한국 시간(UTC+9) 기준이어야 한다"
    assert "dataset.until" in js or "getAttribute('data-until')" in js
    assert "hidden=false" in js.replace(" ", "")


def test_no_november_copy_and_b_untouched():
    html = _index()
    assert "할로윈" not in open(os.path.join(HERE, "b.html"), encoding="utf-8").read()
    for line in html.splitlines():
        if "할로윈" in line and "<!--" not in line:
            assert "11월" not in line
