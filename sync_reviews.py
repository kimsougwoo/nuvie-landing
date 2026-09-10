#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""아워플레이스 후기 → 랜딩 후기 데이터 «완전 자동» 동기화 (2026-08-25 대표 지시).

배경: 종전엔 reviews.json 을 «수동 큐레이션»(verbatim 검증·이름 마스킹·사진 수기 선별)했다.
2026-08-25 대표 결정으로 그 게이트를 모두 폐기한다:
  · verbatim 게이트 → 무마(본문을 아워 원문 그대로 가져오니 정의상 verbatim).
  · 후기 사진 게이트 → 무마(후기 사진은 게스트 본인이 아워에 직접 올린 것 → 대표 승인).
  · 수동 선별 → 폐기(아워 공개 후기를 «전부» 자동 반영).
⇒ A룸·B룸 동일하게, 아워 호스트 API 원문을 그대로 랜딩 데이터로 굳힌다.

출력(멱등):
  reviews.json          A룸(61823) 후기 — index.html(허브)·a.html(룸 페이지)가 읽음
  reviews_b.json        B룸(62341) 후기 — b.html(룸 페이지)가 읽음
  reviews_all.json      A+B 통합 후기 — index.html(메인 집계)가 읽음
  reviews_originals.json 양 룸 원문 스냅샷(feedback_id 기준) — build_reviews verbatim 대조 정합용

사진: 아워 CDN URL 을 그대로 참조한다(다운로드·커밋 없음). 렌더러는 src 를 그대로 쓴다.
이름: mask_name(build_reviews) 로 앞 2글자+*** (공개 레포라 노출 축소 — 이건 큐레이션이 아니라 개인정보 처리).
blind 처리된 후기는 제외(아워에서 숨긴 것).

사용:
  python sync_reviews.py            # 스크래이프→4파일 재생성→build_reviews→build_rooms
  python sync_reviews.py --no-build # 데이터 파일만 재생성(HTML 빌드는 생략)
  python sync_reviews.py --from FILE # 스크래이프 대신 기존 스크래이프 JSON 파일에서 생성(테스트/오프라인)
  python sync_reviews.py --offline   # 기존 reviews.json+reviews_b.json 만 병합→메인만 재빌드
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from build_reviews import mask_name  # 이름 마스킹 규칙 재사용(정본 1개)

PLACE_A, PLACE_B = 61823, 62341
REVIEWS_ALL = ROOT / "reviews_all.json"


def _iso_date(s: str) -> str:
    """아워 작성일 '2026.08.23' → '2026-08-23'. 이미 ISO 면 그대로."""
    s = (s or "").strip()
    return s.replace(".", "-").strip("-") if "." in s else s


def _room_doc(room: dict, source_label: str) -> dict:
    """스크래이프 room dict → 랜딩 reviews 문서(공개 후기만·최신순)."""
    reviews = []
    for r in room.get("reviews", []):
        if r.get("blind"):
            continue  # 아워에서 숨긴 후기는 랜딩에도 안 싣는다
        text = (r.get("후기") or "").strip()
        if not text:
            continue
        reviews.append({
            "name": mask_name(r.get("작성자") or ""),
            "date": _iso_date(r.get("작성일") or ""),
            "rating": int(round(float(r.get("평점") or 5))),
            "text": text,
            "photos": [p for p in (r.get("사진") or []) if p],
        })
    reviews.sort(key=lambda v: v.get("date") or "0000-00-00", reverse=True)
    count = len(reviews)
    rating = round(sum(v["rating"] for v in reviews) / count, 1) if count else 5.0
    return {
        "updated": max((v["date"] for v in reviews), default=""),
        "source": source_label,
        "place_id": room.get("place_id"),
        "rating": float(rating),
        "count": count,
        "auto": "hourplace_reviews_scrape (2026-08-25 대표 지시로 완전 자동·수동 큐레이션 폐기)",
        "reviews": reviews,
    }


def _all_doc(room_docs: list[dict]) -> dict:
    """룸별 공개 후기 문서를 합쳐 메인 페이지용 통합 문서를 만든다."""
    reviews = [review for doc in room_docs for review in (doc.get("reviews") or [])]
    reviews.sort(key=lambda v: v.get("date") or "0000-00-00", reverse=True)
    count = len(reviews)
    rating = round(sum(float(review.get("rating") or 5) for review in reviews) / count, 1) if count else 5.0
    return {
        "updated": max((review.get("date") or "" for review in reviews), default=""),
        "source": "A+B 통합(메인 집계)",
        "rating": float(rating),
        "count": count,
        "auto": "hourplace_reviews_scrape (2026-08-25 대표 지시로 완전 자동·수동 큐레이션 폐기)",
        "reviews": reviews,
    }


def _originals(rooms: list[dict]) -> dict:
    """양 룸 원문 스냅샷(feedback_id 기준). 이름은 담지 않는다(대조는 본문으로만)."""
    out = []
    for room in rooms:
        for r in room.get("reviews", []):
            if r.get("blind"):
                continue
            text = (r.get("후기") or "").strip()
            if not text:
                continue
            out.append({
                "feedback_id": r.get("feedback_id"),
                "date": _iso_date(r.get("작성일") or ""),
                "rating": float(r.get("평점") or 5),
                "text": text,
            })
    out.sort(key=lambda v: v.get("date") or "0000-00-00", reverse=True)
    return {
        "_note": "아워 호스트 API 원문 스냅샷 — 완전 자동 생성(sync_reviews.py). 손으로 고치지 말 것.",
        "_source": "api2.hourplace.co.kr /place/{id}/feedback",
        "reviews": out,
    }


def _dump(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def scrape_live() -> dict:
    """nuvie_morning 스크래이프를 서브프로세스로 호출(홈 repo·브라우저 세션 사용)."""
    proc = subprocess.run(
        [sys.executable, "-m", "nuvie_morning.hourplace_reviews_scrape"],
        capture_output=True, text=True, encoding="utf-8", cwd=r"C:\Users\kgr96",
    )
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        raise SystemExit(f"[sync_reviews] 스크래이프 실패 rc={proc.returncode}: {(proc.stderr or '')[:300]}")
    return json.loads(proc.stdout)


def _load_existing_docs() -> tuple[dict, dict]:
    """기존 룸별 SSOT를 읽어 메인 통합본만 재생성한다(네트워크 없음)."""
    docs = []
    for path in (ROOT / "reviews.json", ROOT / "reviews_b.json"):
        if not path.exists():
            raise SystemExit(f"[sync_reviews] 오프라인 병합 입력 없음: {path.name}")
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"[sync_reviews] 오프라인 병합 입력 읽기 실패: {path.name}: {exc}") from exc
        if not isinstance(doc.get("reviews"), list):
            raise SystemExit(f"[sync_reviews] 오프라인 병합 입력 형식 오류: {path.name}")
        docs.append(doc)
    return docs[0], docs[1]


def _run_build(module: str) -> None:
    r = subprocess.run([sys.executable, str(ROOT / f"{module}.py")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    summary = (r.stdout or "").strip()[-160:]
    safe_summary = summary.encode("ascii", "backslashreplace").decode("ascii")
    print(f"[sync_reviews] {module}: rc={r.returncode} {safe_summary}")
    if r.returncode != 0:
        error = (r.stderr or "")[:300].encode("ascii", "backslashreplace").decode("ascii")
        raise SystemExit(f"[sync_reviews] {module} 실패: {error}")


def main(argv: list[str]) -> int:
    if "--offline" in argv:
        if "--from" in argv:
            raise SystemExit("[sync_reviews] --offline 와 --from 은 함께 쓸 수 없습니다")
        doc_a, doc_b = _load_existing_docs()
        if not doc_a["reviews"]:
            raise SystemExit("[sync_reviews] 오프라인 병합 A룸 후기 0건 — 기존 데이터 확인 필요(거짓 0 방지)")
        all_doc = _all_doc([doc_a, doc_b])
        _dump(REVIEWS_ALL, all_doc)
        print(f"[sync_reviews] 오프라인 병합 완료: A룸 {len(doc_a['reviews'])}건 · B룸 {len(doc_b['reviews'])}건 → 메인 {all_doc['count']}건")
        if "--no-build" not in argv:
            _run_build("build_reviews")
        return 0

    from_file = None
    if "--from" in argv:
        from_file = argv[argv.index("--from") + 1]
    data = json.loads(Path(from_file).read_text(encoding="utf-8")) if from_file else scrape_live()
    if not data.get("ok"):
        raise SystemExit(f"[sync_reviews] 스크래이프 ok=false: {data.get('reason')}")

    rooms = data.get("rooms", [])
    by_place = {r.get("place_id"): r for r in rooms}
    room_a = by_place.get(PLACE_A, {"place_id": PLACE_A, "reviews": []})
    room_b = by_place.get(PLACE_B, {"place_id": PLACE_B, "reviews": []})

    doc_a = _room_doc(room_a, "아워플레이스 A룸 후기 (자동)")
    doc_b = _room_doc(room_b, "아워플레이스 B룸 후기 (자동)")
    # 🔴 거짓 0 가드 — A룸은 상시 후기가 있다(현재 15건). 0건이면 스크래이프 이상이므로
    #    기존 데이터를 «빈 값으로 덮어쓰지» 않는다(빈렌더 SOP·아워 stats-sync 「거짓 0」 규율과 동일).
    if doc_a["count"] == 0:
        raise SystemExit("[sync_reviews] A룸 후기 0건 — 스크래이프 이상 의심, 덮어쓰기 중단(거짓 0 방지)")
    _dump(ROOT / "reviews.json", doc_a)
    _dump(ROOT / "reviews_b.json", doc_b)
    _dump(ROOT / "reviews_originals.json", _originals([room_a, room_b]))
    all_doc = _all_doc([doc_a, doc_b])
    _dump(REVIEWS_ALL, all_doc)
    print(f"[sync_reviews] A룸 {doc_a['count']}건 · B룸 {doc_b['count']}건 · 메인 {all_doc['count']}건 재생성 완료")

    if "--no-build" not in argv:
        for mod in ("build_reviews", "build_rooms"):
            _run_build(mod)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
