# -*- coding: utf-8 -*-
"""한국어 줄바꿈 다듬기(10-01 대표 «줄바꿈 처리 … 전면재수정»). 글자는 바꾸지 않고, 갈라지면 어색한 곳의 공백만
줄바꿈 없는 공백(U+00A0)으로 바꾼다. 화면 글자·FAQ 계약(공백 정규화 비교)·B룸 동결 픽스처(공백 정규화)는 그대로다.

규칙(보이는 본문 글자에만 — <head>·<script>·<style>·태그 속성·FAQ <details>·후기 카드는 건드리지 않는다):
  R1  « · »  → 앞 공백을 붙인다: «…원 · 최소» (가운뎃점이 줄 머리에 오지 않게)
  R2  « / »  → 앞 공백을 붙인다: «5.0 / 5» 가 갈려도 «/» 가 줄 머리에 오지 않게, 짧은 «5.0 / 5» 는 통째로
  R3  괄호 «( … )» 안이 20자 이하면 안쪽 공백을 모두 붙인다: «(대관 1회당, …)» 처럼 괄호 안에서 안 끊기게
  R4  두 글자 이하 낱말과 그 다음(또는 앞) 낱말을 붙인다(«최소 2시간»·«부가세 포함»·«팔각 소프트박스»).
      붙인 덩어리가 12자를 넘으면 붙이지 않는다(좁은 화면 넘침 방지).
사용: python ko_glue.py index.html   (파일을 제자리에서 고친다 · build_rooms.py 는 a.html·b.html 을 만들 때 glue_html 을 부른다)
"""
import re
import sys
from pathlib import Path

NB = " "
WJ = "⁠"
MAX_RUN = 12
_SKIP_BLOCK = re.compile(
    r"(<head\b.*?</head>|<script\b.*?</script>|<style\b.*?</style>|<details\b.*?</details>"
    r"|<!-- REVIEWS:STATIC:START -->.*?<!-- REVIEWS:STATIC:END -->|<div class=\"room-reviews\".*?</section>)",
    re.S | re.I)
_TAG = re.compile(r"(<[^>]+>)")


def _run_len(s):
    return len(s)


def glue_text(t):
    if not t.strip():
        return t
    t = re.sub(r"(?<=\d) / (?=\d)", NB + "/" + NB, t)   # R2b «5.0 / 5» 통째로
    t = t.replace(" · ", NB + "· ").replace(" / ", NB + "/ ")
    # R5  공백 없이 붙은 가운뎃점(«주말·공휴일»·«12시간·부가세») 앞뒤는 브라우저가 줄바꿈 자리로 본다 → 보이지 않는 연결 문자(U+2060)
    t = re.sub(r"(?<=[^\s⁠])·(?=[^\s⁠])", WJ + "·" + WJ, t)

    def paren(m):
        inner = m.group(1)
        return "(" + (inner.replace(" ", NB) if len(inner) <= 20 else inner) + ")"
    t = re.sub(r"\(([^()]{1,40})\)", paren, t)
    parts = t.split(" ")
    if len(parts) < 2:
        return t
    out = [parts[0]]
    for nxt in parts[1:]:
        prev = out[-1]
        last_prev = prev.split(NB)[-1]
        first_next = nxt.split(NB)[0]
        short = (0 < len(re.sub(r"[^\w가-힣]", "", last_prev)) <= 2) or (0 < len(re.sub(r"[^\w가-힣]", "", first_next)) <= 2)
        hangul_pair = bool(re.search(r"[가-힣0-9]", last_prev)) and bool(re.search(r"[가-힣0-9]", first_next))
        if short and hangul_pair and _run_len(prev.split(" ")[-1] + NB + nxt) <= MAX_RUN and not re.search(r"[.!?:]$", last_prev):
            out[-1] = prev + NB + nxt
        else:
            out.append(nxt)
    return " ".join(out)


_BLOCK = re.compile(r"(<(p|li|dd)\b[^>]*>)(.*?)(</\2>)", re.S | re.I)
_NOGLUE_OPEN = re.compile(r"<(a|button|code|svg)\b", re.I)
_NOGLUE_CLOSE = re.compile(r"</(a|button|code|svg)>", re.I)


def _glue_inner(inner):
    """문단 안: 태그는 그대로, 링크·버튼 안 글자는 그대로(테스트·스크립트가 정확한 문자열로 찾는다), 나머지 글자만 다듬는다."""
    pieces = _TAG.split(inner)
    depth, out = 0, []
    for i, p in enumerate(pieces):
        if i % 2 == 1:
            if _NOGLUE_OPEN.match(p):
                depth += 1
            elif _NOGLUE_CLOSE.match(p):
                depth = max(0, depth - 1)
            out.append(p)
        else:
            out.append(p if depth else glue_text(p))
    return _glue_bold_edges("".join(out))


_SHORT_BEFORE_BOLD = re.compile(r"(^|[\s> ])([0-9A-Za-z가-힣]{1,2}) (<(?:b|strong)\b)")


def _glue_bold_edges(inner):
    """«주말 <b>45,000원</b>» 처럼 짧은 낱말 뒤 굵은 글씨가 오면 그 공백을 붙인다(글자 조각이 태그로 나뉘어 R4 가 못 본다)."""
    return _SHORT_BEFORE_BOLD.sub(lambda m: m.group(1) + m.group(2) + NB + m.group(3), inner)


def _glue_segment(seg):
    return _BLOCK.sub(lambda m: m.group(1) + _glue_inner(m.group(3)) + m.group(4), seg)


def glue_html(html):
    """<p>·<li>·<dd> 문단 안의 본문 글자에만 적용한다(버튼·메뉴·제목·링크 글자는 그대로)."""
    out, pos = [], 0
    for m in _SKIP_BLOCK.finditer(html):
        out.append(_glue_segment(html[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(_glue_segment(html[pos:]))
    return "".join(out)


if __name__ == "__main__":
    for f in sys.argv[1:]:
        p = Path(f)
        s = p.read_text(encoding="utf-8")
        g = glue_html(s)
        if g != s:
            p.write_text(g, encoding="utf-8")
        print(f, "changed" if g != s else "same", s.count(" · ") - g.count(" · "))
