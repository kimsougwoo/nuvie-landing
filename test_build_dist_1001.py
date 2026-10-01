# -*- coding: utf-8 -*-
"""배포 빌드(build_dist.mjs) 계약 — 2026-10-01 HTML 주석 제거.

막는 사고
  ① 빌드가 내부 파일(*.py·test_*·*.md·내부 보고서)을 다시 공개한다 / 사이트가 읽는 파일을 빠뜨린다.
  ② 주석을 지우다 화면 글자·줄바꿈 없는 공백(U+00A0)·연결 문자(U+2060)·JSON-LD 가 바뀐다.
  ③ 소유 확인 파일(naver*.html)이 바뀐다.
"""
import json
import re
import shutil
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None or not (HERE / "node_modules" / "html-minifier-terser").exists(),
                                reason="node 또는 html-minifier-terser 없음(npm install)")

SITE_PAGES = ("index.html", "a.html", "b.html", "404.html", "privacy.html")


@pytest.fixture(scope="module")
def dist():
    out = Path(tempfile.mkdtemp(prefix="nv_dist_"))
    r = subprocess.run([NODE, str(HERE / "build_dist.mjs"), "--out", str(out)], cwd=HERE,
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stderr
    yield out
    shutil.rmtree(out, ignore_errors=True)


class _Text(HTMLParser):
    """스크립트·스타일 밖의 글자와 JSON-LD 원문."""
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.text, self.ld, self._skip, self._ld = [], [], 0, False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
            self._ld = tag == "script" and dict(attrs).get("type") == "application/ld+json"

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip -= 1
            self._ld = False

    def handle_data(self, data):
        if self._ld:
            self.ld.append(data)
        elif not self._skip:
            self.text.append(data)


def _parse(html):
    p = _Text()
    p.feed(html)
    norm = lambda s: re.sub(r"[ \t\r\n]+", " ", s)   # 일반 공백만 정규화(U+00A0·U+2060 은 그대로 비교)
    return norm("".join(p.text)).strip(), [json.loads(x) for x in p.ld]


def test_no_comments_left_in_site_pages(dist):
    for name in SITE_PAGES:
        assert "<!--" not in (dist / name).read_text(encoding="utf-8"), name


def test_visible_text_and_jsonld_unchanged(dist):
    for name in SITE_PAGES:
        src_text, src_ld = _parse((HERE / name).read_text(encoding="utf-8"))
        out_text, out_ld = _parse((dist / name).read_text(encoding="utf-8"))
        assert out_text == src_text, name
        assert out_ld == src_ld, name
        assert out_text.count(" ") == src_text.count(" ") and out_text.count("⁠") == src_text.count("⁠"), name


def test_verification_files_byte_identical(dist):
    for p in HERE.glob("naver*.html"):
        assert (dist / p.name).read_bytes() == p.read_bytes(), p.name


def test_file_set_matches_public_set(dist):
    tracked = subprocess.run(["git", "ls-files"], cwd=HERE, capture_output=True, text=True, encoding="utf-8").stdout.split()
    import importlib.util
    spec = importlib.util.spec_from_file_location("vic", HERE / "test_vercelignore_contract.py")
    vic = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vic)
    pats = vic._patterns()
    build_only = {"package.json", "package-lock.json", "build_dist.mjs", ".gitignore", ".vercelignore", "vercel.json"}
    want = {f for f in tracked if not vic._ignored(f, pats) and f not in build_only
            and not f.startswith("api/") and not f.startswith(".")}
    got = {p.relative_to(dist).as_posix() for p in dist.rglob("*") if p.is_file()}
    assert got == want, {"빠짐": sorted(want - got)[:20], "더 나감": sorted(got - want)[:20]}


def test_vercel_json_builds_into_dist():
    v = json.loads((HERE / "vercel.json").read_text(encoding="utf-8"))
    assert v.get("buildCommand") == "npm run build"
    assert v.get("outputDirectory") == "dist"
