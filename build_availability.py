# -*- coding: utf-8 -*-
r"""
아워플레이스 iCal → availability.json (free/busy, 이름 비노출)
- iCal URL은 F:\무인 렌탈스튜디오 인수\.env 에서만 읽음(공개레포에 URL·이름 안 나감).
- A룸·B룸 iCal에서 예약 '날짜·시각·룸'만 추출(이름·UID·SUMMARY 전부 버림).
- 출력: events[{date,start,end,room}] (시간슬롯 "예약됨" 표시용) + busyDates(날짜만, 호환).
- 갱신: 이 스크립트 재실행 후 git push. 30분 스케줄=NUVIE_CS_Watch(run_cs_watch.bat 1번째 줄).
사용:  python build_availability.py            # 생성만
       python build_availability.py --push     # 변경 시에만 git commit+push (30분 스케줄용)
"""
import os, re, json, datetime, urllib.request, subprocess, sys

# 콘솔 인코딩 가드(2026-07-24): 작업 스케줄러로 돌면 stdout이 cp949라, 예약이 있는 날
# print하는 em-dash("예약 — OK")에서 UnicodeEncodeError로 죽었다 → CS_Watch RC=1 데드맨.
# 예약 없는 날은 그 줄을 안 타서 조용히 지나갔던 게 늦게 발견된 이유. UTF-8로 고정한다.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ENV = r"F:\무인 렌탈스튜디오 인수\.env"

# ⚠️ 2026-07-29(과거 예약 누적): 아워플레이스 iCal은 과거 예약을 보존하지 않는다(실측 오늘 이전
# VEVENT 0건) → 폴링 스냅샷을 안 남기면 지나간 예약은 영구 소실된다. 표시 여부는 아직 미정이라
# 공개 레포(availability.json)에는 절대 안 넣고, repo 밖 로컬 파일에만 append-only로 쌓는다.
HISTORY_PATH = r"C:\Users\kgr96\nuvie_morning\data\availability_history.json"

def load_env(path):
    d = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip()
    return d

def fetch(url):
    """iCal 본문 문자열, 실패 시 None(=구분가능 실패신호).

    ⚠️ 2026-07-17(3R 🔴HIGH): 예전엔 타임아웃/5xx/순단에도 ""를 반환 → parse_events("")=[]
       로 흘러 '진짜 페치 실패'와 '예약 0건'을 구분 못 했다. A룸만 순단해도 꽉 찬 날짜가
       사라져 changed=True→push→Vercel 재배포로 예약된 날이 '가능'으로 공개됐다(둘 다 실패면
       120일 전체 '가능'). 형제 booking_watch.fetch_ical의 None-신호(P0-1)와 정합하도록,
       실패는 None으로 올려 호출부(compute_events)가 그 룸을 이번 런에서 제외하게 한다.
       (성공한 빈 캘린더는 여전히 "" 등 문자열 → 정상 '예약 0건'으로 진행.)"""
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nuvie-availability/1.0"})
        return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    except Exception as e:
        print("  fetch 실패:", e)
        return None

def _to_dt(s):
    s = s.strip()
    if "T" in s:
        base = datetime.datetime.strptime(s[:15], "%Y%m%dT%H%M%S")
        if s.endswith("Z"):
            base += datetime.timedelta(hours=9)  # UTC → KST
        return base
    return datetime.datetime.strptime(s[:8], "%Y%m%d")

_MAX_SPAN_DAYS = 31   # 병적으로 긴 이벤트로 루프가 폭주하지 않게 하는 상한(호라이즌은 뒤에서 또 자른다)


def _split_across_days(start, end, room, kind):
    """자정을 넘기는 예약을 «날짜별 조각»으로 나눈다. 순수함수.

    🔴 2026-08-16 재현→수정 (대표 질문 「22:00-08:00 은 캘린더에 어떻게 보이나요」).
       종전엔 `end.date() != start.date()` 이면 **시작일 기준 24:00 으로 클립**하고 끝이었다
       (주석: "자정 넘기는 예약은 드묾"). 그래서 `8/19 22:00 ~ 8/20 08:00` 예약이
         · 8/19 22:00~24:00 만 남고
         · 🔴 **8/20 00:00~08:00 이 통째로 사라져 그 아침이 「예약 가능」으로 보였다.**
       조각이 안 이어지는 정도가 아니라 **막힌 시간이 없어지는** 결함 = 이중예약 위험이다.
       (심야 예약은 실재한다 — 8/20 A룸 00:00~06:00 확정 건이 라이브에 있고,
        `booking_watch.build_booking_alert` 에 00:00~08:59 시작 전용 도어락 선발송 분기가 있다.)

    `cont` = 이 조각이 «더 긴 한 예약»의 일부라는 표시. 랜딩이 이걸 보고 한 예약으로 이어 보여준다.
        "next"=다음 날로 이어짐 · "prev"=전날에서 이어짐 · "both"=하루를 통째로 차지하는 중간 날.
    ⚠️ 정확히 자정에 끝나면(DTEND 00:00) 마지막 날 조각은 길이 0이라 **버린다** — 그러면 이어지는
       것도 아니므로 앞 조각에 `cont` 를 붙이지 않는다(없는 연속을 그리지 않는다).
    """
    segs = []
    d, last = start.date(), end.date()
    if (last - d).days > _MAX_SPAN_DAYS:
        last = d + datetime.timedelta(days=_MAX_SPAN_DAYS)
    while d <= last:
        s = (start.hour + start.minute / 60.0) if d == start.date() else 0.0
        e = (end.hour + end.minute / 60.0) if d == last else 24.0
        if e - s > 1e-9:                      # 길이 0 조각(자정 정각 종료)은 버린다
            segs.append({"date": d.isoformat(), "start": round(s, 2), "end": round(e, 2),
                         "room": room, "kind": kind})
        d += datetime.timedelta(days=1)
    if len(segs) > 1:
        for i, seg in enumerate(segs):
            seg["cont"] = "next" if i == 0 else ("prev" if i == len(segs) - 1 else "both")
    return segs


def parse_events(ics, room, kind="booking"):
    """VEVENT → [{date,start,end,room,kind}] (KST, 시각 hour 소수). 이름/UID/SUMMARY 무시.

    🔒 **여기서 버리는 것이 개인정보 방어선이다.** 이 산출물은 공개 레포에 커밋된다.
       특히 「휴무·차단」 구글캘린더(kind="block")의 SUMMARY·DESCRIPTION 에는 **고객명·핸들과
       내부 메모가 들어 있다**(2026-08-16 원문 실측: 「단골 추가이용권 1h — 심재만(@…) 뒷타임」).
       ⇒ 시각 세 개와 룸·종류만 남기고 **나머지는 전부 버린다.** 필드를 늘리지 말 것.

    kind: "booking"(아워플레이스 예약) | "block"(우리가 막아둔 시간 — 청소·점검·답사·휴무).
    """
    out = []
    ics = ics.replace("\r\n", "\n").replace("\n ", "").replace("\n\t", "")
    for ev in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", ics, re.S):
        ds = re.search(r"DTSTART[^:]*:([0-9T]+Z?)", ev)
        de = re.search(r"DTEND[^:]*:([0-9T]+Z?)", ev)
        if not ds:
            continue
        try:
            start = _to_dt(ds.group(1))
            end = _to_dt(de.group(1)) if de else start
        except Exception:
            continue
        timed = "T" in ds.group(1)
        if timed:
            out += _split_across_days(start, end, room, kind)
        else:
            # 종일(날짜만) 예약 — 시각 없는 차단. start~end-1 각 날을 0~24 블록으로.
            d = start.date()
            last = end.date()
            # ⚠️ 2026-07-07(P2): DTEND 부재(de=None) 시 de.group()이 NoneType 크래시 → parse_events 전체 정지
            #   (availability.json 무음 미갱신). end=start 방어와 정합하도록 de None 가드. 종일 exclusive-end만 -1일.
            if de and "T" not in de.group(1) and last > d:
                last -= datetime.timedelta(days=1)
            while d <= last:
                out.append({"date": d.isoformat(), "start": 0, "end": 24,
                            "room": room, "kind": kind})
                d += datetime.timedelta(days=1)
    return out

MIN_BOOK_H = 2.0  # 최소 대여 2시간(운영정책). 2h 미만 블록 = 실예약 불가 → 무료연장/호의시간.


def _drop_contained(evs):
    """같은 (날짜·룸)에서 **다른 블록에 통째로 들어가는 블록**을 뺀다. 순수함수.

    ⚠️ 이건 '병합'이 아니다 — 합집합이 변하지 않는 것만 지운다(A ⊇ B 이면 A∪B = A).
    따라서 **막힌 시간이 줄어들 수 없다**(빈 시간을 잘못 여는 사고가 구조적으로 불가능).
    등을 맞댄 ≥2h 블록끼리는 서로를 포함하지 않으므로 merge_events 의 「≥2h 는 병합 금지」
    규칙과 충돌하지 않는다.

    🔴 2026-08-16 실측으로 신설 — 아워플레이스가 **추가결제(장비) 건에 대해 예약과 겹치는
       별도 VEVENT 를 하나 더 내보낸다.** 8/17 A룸 라이브 원문:
         56fa9f79  15:00~16:00  CREATED 2026-08-16T03:58Z  ← 추가결제 시각에 새로 생김
         3408bcf3  15:00~17:00  CREATED 2026-08-12T11:22Z  ← 실제 예약
       호스트 캘린더에는 15~16 카드가 **없다**(예약확정 15~17 · 완료 15~17「추가결제」뿐).
       ⇒ 15~16 은 방을 막는 일정이 아니라 결제 기록의 부산물인데 랜딩엔 "(1H) 예약됨"으로
       따로 떠서, 한 예약이 두 개로 보였다. 15~17 안에 들어가므로 지워도 막힌 시간은 그대로다.

    ⛔ **취소분 때문이 아니다.** 같은 날 실측에서 아워플레이스 iCal 은 취소 예약을 **빼고** 준다
       (호스트 화면 [취소] 8/17 14~16 · 8/16 11~13 둘 다 피드에 없음). 「취소가 CONFIRMED 로
       남는다」는 전제로 노션 대조 필터를 만들려던 계획은 이 실측으로 폐기했다 — 상세는
       `.claude/docs/handoff-availability-cancel-2026-08-16.md` 갱신분.
    """
    out, max_end = [], None
    for e in sorted(evs, key=lambda x: (x["start"], -x["end"])):
        if max_end is not None and e["end"] <= max_end:
            continue          # 앞선 블록(시작이 더 이르거나 같다)에 통째로 들어감 = 중복
        out.append(e)
        max_end = e["end"] if max_end is None else max(max_end, e["end"])
    return out


def merge_events(events):
    """무료 추가시간(2h 미만) 블록을 '바로 앞' 유료 블록에 흡수해 하나의 예약 블록으로 합친다.

    규칙(대표 확정 2026-07-15):
    - 최소 대여가 2시간이므로 **2h 미만 블록은 실예약일 수 없다 = 무료연장/호의시간**.
    - <2h 블록은 직전(맞닿은) 구간에 **뒤로 흡수**한다.
    - 🔴 **2026-08-04 보강 — 무료 1h 가 예약 '앞'에 붙는 사례가 실제로 발생했다**(대표 보고).
      07-15 규칙은 "무료 1h 는 항상 ≥2h 블록 '뒤'에만 붙는다"를 전제했는데 그게 틀렸다.
      라이브 실측: `2026-08-23 B룸 14-15(1h) | 15-18(3h)` — 앞에 붙어 흡수가 안 되고
      "(1H) 예약됨"으로 따로 떠서, 07-15 에 없애려던 오해가 그대로 재발했다.
      ⇒ 직전과 안 맞닿는 <2h 블록은 **바로 뒤 ≥2h 블록에 앞으로 흡수**한다.
      **뒤흡수가 우선**이다(앞뒤 양쪽에 맞닿으면 종전대로 앞 예약 것으로 본다).
    - **≥2h 블록끼리는 절대 병합하지 않는다**(다른 게스트가 등을 맞대도 각자 분리 유지 —
      게스트가 홈페이지 예약현황을 '내 예약 리마인드'로 봐도 옆 예약과 안 섞이게).
    - 앞뒤 어디에도 안 맞닿는 고립 <2h 는 그대로 둔다(슬롯이 실제로 막혀 있으므로).
    - 🔴 **2026-08-16 선처리 — 다른 블록에 통째로 들어가는 블록은 먼저 뺀다**(`_drop_contained`).
      추가결제 부산물 VEVENT 가 예약과 겹쳐 들어와 "(1H) 예약됨"이 따로 떴다(사유·실측은 그 함수).
      흡수 규칙보다 **먼저** 돌려야 한다 — 겹치는(맞닿지 않는) 블록은 흡수 대상이 아니라
      pending_free 로 흘러 고립 블록으로 확정돼 버리기 때문이다.

    이렇게 하면 무료연장이 별도 "(1H) 예약됨"으로 뜨지 않아 "1시간만 예약되나요?" 오해가 사라지고,
    게스트는 자기 전체 이용시간(유료+무료)을 한 블록으로 확인한다. iCal에 이름이 없어도
    '2h 미만 = 무료연장'이 게스트 신원 프록시가 되어 이름 없이 정확히 동작한다.

    🔴 **2026-08-16 — 종류(kind)가 다르면 서로 병합하지 않는다.** 「휴무·차단」(kind="block")은
      예약이 아니다. 1시간짜리 차단(예: 답사)이 옆 예약에 흡수되면 **손님에게 「예약됨」으로
      잘못 표시**되고, 그 예약의 이용시간까지 늘어난 것처럼 보인다. 그래서 묶음 키에 kind 를 넣어
      각자 처리한다 — 차단끼리·예약끼리만 위 규칙이 적용된다.
    """
    from collections import defaultdict
    EPS = 1e-6
    groups = defaultdict(list)
    for e in events:
        groups[(e["date"], e["room"], e.get("kind") or "booking")].append(e)
    out = []
    for (date, room, kind), evs in groups.items():
        evs = _drop_contained(evs)          # 겹쳐 들어온 중복 먼저 제거(막힌 시간 불변)
        evs.sort(key=lambda e: (e["start"], e["end"]))
        cur = None
        pending_free = []   # 앞에 붙은 무료 블록들 — 뒤에 올 ≥2h 를 기다린다
        for e in evs:
            dur = e["end"] - e["start"]
            # 🔴 2026-08-16: 자정을 넘겨 «잘린 조각»(cont)은 무료연장이 아니다 — 더 긴 한 예약의
            #   일부다. 예: 23:00~01:00 예약은 23-24 / 0-1 두 조각(각 1h)이 되는데, 이걸 <2h 라고
            #   옆 예약에 흡수하면 «남의 예약»이 늘어난 것처럼 보인다. 흡수 판정에서 제외한다.
            piece = bool(e.get("cont"))
            if (cur is not None and not piece and e["start"] <= cur["end"] + EPS
                    and dur < MIN_BOOK_H - EPS):
                # <2h(무료연장) + 앞 구간과 맞닿음 → 뒤로 흡수(직전 예약 확장). 뒤흡수 우선.
                cur["end"] = max(cur["end"], e["end"])
                continue
            if dur < MIN_BOOK_H - EPS and not piece:
                # 앞에 붙일 구간이 없는 <2h → 바로 뒤 ≥2h 에 붙을 수 있으니 일단 보류
                if pending_free and e["start"] > pending_free[-1]["end"] + EPS:
                    out.extend(pending_free)   # 체인이 끊겼다 = 앞 것들은 고립 확정
                    pending_free = []
                pending_free.append({"date": date, "start": e["start"], "end": round(e["end"], 2),
                                     "room": room, "kind": kind})
                continue
            # 여기부터 ≥2h 블록 — ≥2h 끼리는 병합 안 함
            start = e["start"]
            if pending_free and abs(pending_free[-1]["end"] - start) < EPS:
                # 보류된 무료 블록이 이 예약과 맞닿는다 → 앞으로 흡수(2026-08-04 보강)
                start = pending_free[0]["start"]
                pending_free = []
            elif pending_free:
                out.extend(pending_free)       # 안 맞닿으면 고립 블록으로 확정
                pending_free = []
            cur = {"date": date, "start": start, "end": round(e["end"], 2),
                   "room": room, "kind": kind}
            if e.get("cont"):
                cur["cont"] = e["cont"]        # 연속 표시는 병합을 거쳐도 살아남아야 한다
            out.append(cur)
        out.extend(pending_free)               # 뒤에 ≥2h 가 끝내 안 온 무료 블록은 그대로 유지
    out.sort(key=lambda e: (e["date"], e["start"], e["room"], e.get("kind") or ""))
    return out


def _load_old_events(dst):
    """직전 availability.json의 events 리스트(없거나 손상이면 None)."""
    if os.path.exists(dst):
        try:
            return json.load(open(dst, encoding="utf-8")).get("events")
        except Exception:
            pass
    return None


def _update_history(old_events, today, path=None):
    """직전 availability.json의 events 중 '오늘 이전으로 넘어간 것'을 repo 밖 로컬 히스토리에
    append-only 병합(중복 제거)한다. 과거 기록은 절대 삭제·수정하지 않음(보존기간 상한 없음).

    ⚠️ fetch 성공/실패와 완전히 무관하게 동작한다 — 오직 date 문자열 비교(< today)만으로 판단한다.
       old_events는 이미 compute_events의 안전장치(fetch 실패 룸=직전값 유지)를 거쳐온 값이므로,
       이 함수가 "이 룸 fetch가 실패했으니 사라진 걸로 치자"는 판단을 할 필요도, 해서도 안 된다
       (실패=모름이지 없음이 아니다 — 그래서 아직 미래인 이벤트는 fetch 실패 룸이라도 여기서
       손대지 않고 그대로 availability.json 쪽 로직에 맡긴다).
    공개 산출물(availability.json)은 절대 건드리지 않는다(별도 파일, repo 밖 경로).
    """
    path = path or HISTORY_PATH
    old_events = old_events or []
    today_iso = today.isoformat()
    # 🆕 2026-08-16: 「휴무·차단」은 예약이 아니다 — 과거 «예약» 히스토리에 섞으면 나중에
    #   가동률·매출 분석에서 없던 예약으로 세어진다. kind 가 없는 구 항목은 예약으로 본다.
    past = [e for e in old_events
            if str(e.get("date", "")) < today_iso and (e.get("kind") or "booking") == "booking"]
    if not past:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    hist = {"events": []}
    if os.path.exists(path):
        try:
            hist = json.load(open(path, encoding="utf-8"))
        except Exception:
            hist = {"events": []}
    existing = hist.get("events") or []
    seen = {(e.get("date"), e.get("start"), e.get("end"), e.get("room")) for e in existing}
    added = 0
    for e in past:
        key = (e.get("date"), e.get("start"), e.get("end"), e.get("room"))
        if key in seen:
            continue
        existing.append({"date": e.get("date"), "start": e.get("start"),
                         "end": e.get("end"), "room": e.get("room")})
        seen.add(key)
        added += 1
    if added:
        existing.sort(key=lambda e: (e.get("date") or "", e.get("start") or 0,
                                     e.get("end") or 0, e.get("room") or ""))
        hist["events"] = existing
        hist["updated"] = datetime.datetime.now().isoformat(timespec="minutes")
        json.dump(hist, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"  history: 과거예약 {added}건 누적(repo 밖 · 총 {len(existing)}건)")


def compute_events(env, today, old_events):
    """iCal 페치 → 최종 events + (fetched_ok, fetch_failed) 카운트.

    ⚠️ 2026-07-17(3R 🔴HIGH): fetch()가 실패하면 None을 준다. **페치 실패 룸은 빈 []로
       덮지 않고 직전 availability.json의 그 룸 값을 그대로 유지**한다 — 안 그러면 A룸 순단만으로
       예약된 날이 사라져 공개 사이트가 '가능'으로 뒤집힌다(둘 다 실패면 120일 전체 '가능').
       두 룸 모두 실패(fetched_ok==0)면 호출부가 push를 스킵한다. 성공한 룸은 신선 반영.
       (성공한 '빈 캘린더'=진짜 예약0은 정상 반영 → 예약 해제가 공개에 반영됨.)

    🆕 2026-08-16 — **「휴무·차단」 구글캘린더 2개를 함께 읽는다**(대표 지시 「달력에 띄워주세요」).
       그 시간은 아워플레이스에서 실제로 막히는데(구글캘린더 → 아워 iCal 구독 = 「연동」 배지),
       **아워가 내보내는 iCal 에는 안 실려서** 랜딩 달력에만 비어 보였다(8/17 12~13 답사 실측).
       ⇒ 원본 캘린더를 직접 읽어 kind="block" 으로 표시한다.
       ⚠️ **fetched_ok 는 예약 피드만 센다.** 차단 피드가 성공했다고 「예약 피드 전멸」 경보가
          꺼지면 안 된다 — 그 데드맨이 2026-07-17 에 만들어진 이유가 그것이다.
       🔒 URL 은 .env 에서만 읽는다. 공개 URL 이긴 하나 **SUMMARY·DESCRIPTION 에 고객명이 있어**
          공개 레포에 주소를 적으면 그게 곧 유출 경로가 된다(parse_events 는 시각만 남긴다)."""
    horizon = today + datetime.timedelta(days=120)
    old_events = old_events or []
    events = []
    fetched_ok = fetch_failed = 0
    feeds = (("ICAL_URL_HOURPLACE", "A", "booking"), ("ICAL_URL_HOURPLACE_B", "B", "booking"),
             ("ICAL_URL_BLOCK_A", "A", "block"), ("ICAL_URL_BLOCK_B", "B", "block"))
    for key, room, kind in feeds:
        url = env.get(key)
        label = f"{room}룸" + ("" if kind == "booking" else " 차단")
        # 그 (룸·종류) 직전값(실패 시 유지). 구 산출물엔 kind 가 없어 booking 으로 본다.
        prev = [e for e in old_events
                if e.get("room") == room and (e.get("kind") or "booking") == kind]
        if not url:
            print(f"{key} ({label}): 없음 — 미설정(직전 {len(prev)}건 유지)")
            events += prev
            continue
        ics = fetch(url)
        if ics is None:
            if kind == "booking":
                fetch_failed += 1
            print(f"{key} ({label}): 있음 — ❌ FETCH FAIL, 직전 {len(prev)}건 유지(빈값 덮어쓰기 금지)")
            events += prev
        else:
            if kind == "booking":
                fetched_ok += 1
            print(f"{key} ({label}): 있음 — OK")
            events += parse_events(ics, room, kind)
    # 오늘~120일(미래)만 + 무료연장(2h 미만) 흡수 + 정렬
    events = [e for e in events if today.isoformat() <= e["date"] <= horizon.isoformat()]
    events = merge_events(events)
    events.sort(key=lambda e: (e["date"], e["start"], e["room"], e.get("kind") or ""))
    return events, fetched_ok, fetch_failed


def _alert_fetch_fail(msg):
    """두 iCal 모두 실패(예약현황 갱신 불능) 경보 — silent-failure 방지.
    nuvie_morning.report.alert_throttled로 #이상감지 1회(6h 쿨다운). import 불가(단독 실행)·
    웹훅 미설정이면 stdout(=refresh_log.txt)에 남은 FETCH FAIL 로그만으로 폴백(graceful)."""
    try:
        try:
            import nuvie_morning.report as R
        except Exception:
            # 단독 실행(cwd=Projects\nuvie-landing) 시엔 홈(C:\Users\kgr96)이 path에 없음 → 보강 후 재시도
            home = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if home not in sys.path:
                sys.path.insert(0, home)
            import nuvie_morning.report as R
        R.alert_throttled("availability_fetch_down", msg, hours=6)
    except Exception as e:
        print(f"  (경보 전송 스킵 — refresh_log 폴백: {str(e)[:80]})")


def _worktree_dirty_besides_availability(repo):
    """워킹트리에 `availability.json` 말고 **작업 중인 변경**이 있으면 그 경로들. 없으면 빈 set.

    🔴 2026-08-16 실사고 방어용. 이 스크립트는 30분마다 무인으로 도는데, 충돌 자가치유 분기가
    `git reset --hard origin/main` 을 돌린다. 그게 «커밋 안 된 사람 작업»까지 지운다 —
    실제로 편집 중이던 3파일이 그렇게 사라졌다. 그래서 리셋 전에 이걸 먼저 묻는다.
    ⚠️ 추적 안 되는 파일(`??`)도 센다 — 새로 쓰던 파일이 제일 위험하다(git 에 사본이 없다).
    ⚠️ 판정 불가(git 실패)면 **「더럽다」고 본다** — 모르면 파괴하지 않는 쪽으로 기운다.
    """
    st = subprocess.run(["git", "-C", repo, "status", "--porcelain"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if st.returncode != 0:
        return {"(git status 실패 — 안전을 위해 더럽다고 본다)"}
    out = set()
    for line in (st.stdout or "").splitlines():
        path = line[3:].strip().strip('"')
        if path and path != "availability.json":
            out.add(path)
    return out


def push_changes(repo, n_events):
    """availability.json git add+commit+rebase+push (Vercel 자동 재배포). 반환 pushed:bool."""
    try:
        subprocess.run(["git", "-C", repo, "add", "availability.json"], check=True)
        subprocess.run(["git", "-C", repo,
                        "-c", "user.name=kimsougwoo",
                        "-c", "user.email=143887564+kimsougwoo@users.noreply.github.com",
                        "commit", "-q", "-m", f"예약현황 갱신(자동 30분): 예약 {n_events}건"], check=True)
        # ⚠️ 2026-07-03: push 전 rebase — 외부(수동 히어로 편집·GitHub 웹)로 origin이 앞서도
        # 강제덮어쓰기 없이 availability 커밋을 그 위에 리베이스(split-brain·수동수정 유실 방지).
        # availability.json은 봇 전용이라 index.html 등 수동파일과 충돌 사실상 없음.
        pr = subprocess.run(["git", "-C", repo, "pull", "--rebase", "origin", "main"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
        if pr.returncode != 0:
            subprocess.run(["git", "-C", repo, "rebase", "--abort"], capture_output=True)
            # 🔧 2026-07-23: 충돌 자가치유. availability.json은 봇 전용이라, 스톨된 로컬 커밋이
            #   이 파일만 건드렸다면 origin에 맞추고(스냅샷 폐기) 신선본은 다음 30분 런이 재생성한다.
            #   과거엔 abort 후 그냥 return False → 커밋이 영구 적체(ahead 누적)돼 스톨했다.
            #   ⚠️ 다른 파일이 섞였으면 자동 폐기 위험 → 종전대로 보류(수동 확인).
            diff = subprocess.run(["git", "-C", repo, "diff", "--name-only", "origin/main..HEAD"],
                                  capture_output=True, text=True, encoding="utf-8", errors="replace")
            touched = {f.strip() for f in (diff.stdout or "").splitlines() if f.strip()}
            dirty = _worktree_dirty_besides_availability(repo)
            if dirty:
                # 🔴 2026-08-16 실사고 — 여기서 곧장 `reset --hard` 를 돌려 **작업 중이던
                #   미커밋 편집 3파일을 날렸다**(build_availability.py·index.html·테스트).
                #   `touched` 는 «커밋된» 차이만 보므로 워킹트리는 검사 밖이었다.
                #   스톨은 눈에 보이고 되돌릴 수 있지만 **지워진 작업은 되돌릴 수 없다** ⇒
                #   작업 중인 게 있으면 자가치유를 «하지 않는다»(다음 런이 다시 시도한다).
                print(f"  ⛔ 자가치유 보류 — 작업 중인 미커밋 변경이 있다 {sorted(dirty)[:5]}. "
                      f"reset --hard 를 돌리면 그 작업이 사라진다(사람이 정리한 뒤 자동 회복).")
            elif touched and touched <= {"availability.json"}:
                subprocess.run(["git", "-C", repo, "reset", "--hard", "origin/main"], check=True)
                print("  rebase 충돌 → availability 전용 로컬커밋이라 origin에 맞춤(다음 런 재생성). 스톨 자가치유.")
            else:
                print(f"  rebase 충돌 → push 보류(availability 외 변경 {sorted(touched)} 有, 수동 확인):",
                      (pr.stderr or "")[:150])
            return False
        subprocess.run(["git", "-C", repo, "push", "origin", "main"], check=True)
        print("  변경 감지 → rebase+push 완료 (Vercel 자동 재배포)")
        return True
    except Exception as e:
        print("  push 실패:", e)
        return False


def main(argv=None, repo=None):
    argv = sys.argv if argv is None else argv
    env = load_env(ENV)
    today = datetime.date.today()
    repo = repo or os.path.dirname(os.path.abspath(__file__))
    dst = os.path.join(repo, "availability.json")
    old_events = _load_old_events(dst)

    # 과거 예약 누적(repo 밖 로컬 히스토리, 공개 산출물과 무관) — 여기서 예외가 나도 본래 기능
    # (availability.json 생성·push)은 절대 막히면 안 되므로 try/except로 감싸고 로그만 남긴다.
    try:
        _update_history(old_events, today)
    except Exception as e:
        print("  history 저장 실패(무시, 본 기능 계속):", e)

    events, fetched_ok, fetch_failed = compute_events(env, today, old_events)

    if fetched_ok == 0:
        # 신선 페치 0건 → 직전 availability.json을 **그대로 둔다**(빈값 덮어쓰기 = 예약된 날이
        # '가능'으로 공개 배포되는 사고). 파일 미접촉·push 스킵. 페치 실패가 원인이면 #이상감지 경보.
        print(f"  ❌ FETCH FAIL — availability.json 미갱신·push 스킵(직전값 유지, 실패 {fetch_failed})")
        if fetch_failed:
            _alert_fetch_fail(
                f"🔴 예약현황 iCal {fetch_failed}개 전부 페치 실패 — availability.json 갱신 중단"
                "(직전값 유지·공개 사이트 안전). 피드 URL·아워플레이스 점검 필요.")
        return False

    busy = sorted({e["date"] for e in events})
    changed = ((old_events or []) != events)
    # 🔧 2026-07-23: 변경이 있을 때만 파일을 쓴다. 종전엔 매 런 `updated` 타임스탬프를 무조건
    #   재기록 → 이벤트 변화가 없어도 워킹트리가 dirty → 다음 런의 `git pull --rebase`가 dirty로
    #   막혀 크론이 스톨했다(라이브 예약현황 8일 고착 사고, 2026-07-23). 변경 시에만 기록.
    if changed:
        out = {
            "updated": datetime.datetime.now().isoformat(timespec="minutes"),
            "note": ("free/busy (아워플레이스 iCal + 휴무·차단 캘린더 · 이름 비노출, 시간·룸·종류만). "
                     "kind=booking 예약 / kind=block 예약 불가(청소·점검·답사·휴무). "
                     "참고용 — 확정은 아워플레이스."),
            "events": events,
            "busyDates": busy,
        }
        json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"availability.json {'작성' if changed else '변화없음(미기록)'}: 예약 {len(events)}건 / "
          f"{len(busy)}일 (이름 0개 노출) · 변경={changed} · 페치성공 {fetched_ok}/실패 {fetch_failed}")
    print("  샘플:", events[:4])

    if "--push" in argv:
        if not changed:
            print("  변경 없음 → push 생략")
            # dirty-잔류 방지(멱등): 과거 버그로 남았을 수 있는 타임스탬프-only 오염을 되돌려
            #   다음 런의 pull --rebase가 막히지 않게 한다. 변경 없으니 되돌려도 무손실.
            subprocess.run(["git", "-C", repo, "checkout", "--", "availability.json"],
                           capture_output=True)
            return True
        return bool(push_changes(repo, len(events)))
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
