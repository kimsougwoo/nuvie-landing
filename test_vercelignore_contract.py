# -*- coding: utf-8 -*-
"""배포 제외 목록(.vercelignore) 계약 — 2026-09-27 공개 노출 점검.

실측: 빌드 스크립트·테스트·운영 문서·내부 보고서 HTML 35개가 https://www.nuviestudio.com/<파일> 로 200 이었다
(`.vercelignore` 없음 — Vercel 은 저장소 파일을 전부 정적 자산으로 올린다). 비밀값은 없었지만 공개할 이유가 없다.
Vercel 은 Git 연동 배포에서도 `.vercelignore`(gitignore 문법)를 플랫폼에서 적용한다
(vercel/vercel packages/build-utils/src/get-ignore-filter.ts).

막는 사고 두 가지
  ① 내부 파일(*.py·*.md·test_*·내부 보고서)이 다시 공개된다.
  ② 제외 규칙이 넓어져 사이트가 실제로 읽는 파일(예약 달력·후기·룸 데이터·API)이 빠진다.
"""
import fnmatch
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
IGNORE = HERE / ".vercelignore"


def _patterns():
    out = []
    for line in IGNORE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def _ignored(path, patterns):
    """gitignore 문법의 부분집합(이 파일이 쓰는 것만): 이름 글롭·디렉터리(끝 /)."""
    parts = path.split("/")
    for pat in patterns:
        if pat.endswith("/"):
            if pat.rstrip("/") in parts[:-1]:
                return True
            continue
        if "/" in pat:
            if fnmatch.fnmatch(path, pat.lstrip("/")):
                return True
            continue
        if fnmatch.fnmatch(parts[-1], pat):
            return True
    return False


def _tracked():
    r = subprocess.run(["git", "ls-files"], cwd=HERE, capture_output=True, text=True, encoding="utf-8")
    return [p for p in r.stdout.splitlines() if p]


def test_vercelignore_exists():
    assert IGNORE.exists(), ".vercelignore 가 없으면 내부 파일이 전부 공개된다"


def test_internal_files_are_excluded():
    pats = _patterns()
    leaked = [p for p in _tracked()
              if (p.endswith((".py", ".md")) or pathlib.PurePosixPath(p).name.startswith("test_")
                  or re.search(r"(audit-report|e2e-report)-.*\.html$", p))
              and not _ignored(p, pats)]
    assert not leaked, f"공개되는 내부 파일: {leaked}"


RUNTIME_MUST_SHIP = [
    "index.html", "a.html", "b.html", "privacy.html", "404.html",
    "site.js", "styles.css", "attribution.js", "rooms.data.js",
    "availability.json", "reviews_all.json", "rooms.json",
    "robots.txt", "sitemap.xml", "llms.txt", "og.jpg", "vercel.json",
    "api/interest.js",
]


def test_runtime_files_still_ship():
    pats = _patterns()
    tracked = set(_tracked())
    dropped = [p for p in RUNTIME_MUST_SHIP if p in tracked and _ignored(p, pats)]
    assert not dropped, f"사이트가 쓰는 파일이 배포에서 빠진다: {dropped}"
    assert not [p for p in tracked if p.startswith(("img/", "reviews/")) and _ignored(p, pats)]
    assert not [p for p in tracked if p.startswith("naver") and _ignored(p, pats)], "네이버 사이트 인증 파일"


def test_every_json_the_site_fetches_still_ships():
    """HTML·JS 가 이름으로 부르는 .json 은 전부 배포에 남아야 한다(예약 달력·후기 누락 방지)."""
    pats = _patterns()
    tracked = set(_tracked())
    refs = set()
    for f in list(HERE.glob("*.html")) + list(HERE.glob("*.js")):
        if f.name.startswith("test_") or _ignored(f.name, pats):
            continue
        refs.update(re.findall(r"([A-Za-z0-9_.-]+\.json)", f.read_text(encoding="utf-8", errors="ignore")))
    shipped_refs = [r for r in refs if r in tracked]
    assert shipped_refs, "참조 탐지가 비었다 — 검사 자체가 깨졌다"
    dropped = [r for r in shipped_refs if _ignored(r, pats)]
    assert not dropped, f"사이트가 부르는 JSON 이 빠진다: {dropped}"
