# -*- coding: utf-8 -*-
"""비치 소품 페이지 — 2026-11-25 (허브 제거 · 룸 탭 전환형).

/props 한 장. 탭으로 A룸 ↔ B룸을 바꾸며 **한 번에 한 룸만** 보인다(섞임 0).
  · A룸 탭 = 장비(A) + A 소품 + 원단(A 전용, 재질별)
  · B룸 탭 = 장비(B) + B 소품
  · 딥링크 /props#a · /props#b
데이터 = props.json / 사진 = img/props/<id>.jpg (없으면 임시 칩)
"""
import html as _html
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "props.json")
PHOTO_DIR = os.path.join(HERE, "img", "props")

HEAD = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>비치 소품 · 조명·가구·원단 — 누비 스튜디오</title>
<meta name="description" content="A룸(동양풍·블랙 호리존)과 B룸(화이트 티타임 카페)에 비치된 조명·가구·소품·원단 목록. 룸을 골라 그 룸의 소품만 확인하세요.">
<link rel="canonical" href="https://www.nuviestudio.com/props">
<meta name="robots" content="index,follow">
<meta property="og:type" content="website">
<meta property="og:site_name" content="누비 스튜디오 NUVIE STUDIO">
<meta property="og:title" content="비치 소품 — 누비 스튜디오">
<meta property="og:description" content="A룸·B룸에 비치된 조명·가구·소품·원단 목록. 룸별로 확인하세요.">
<meta property="og:url" content="https://www.nuviestudio.com/props">
<meta property="og:image" content="https://www.nuviestudio.com/img/props-fabric.jpg">
<meta property="og:locale" content="ko_KR">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="stylesheet" href="/fonts.css">
<link rel="stylesheet" href="/styles.css">
<link rel="stylesheet" href="/props.css">
</head>
<body data-theme="dark" data-room="props">
<div id="root">

  <aside class="side">
    <div class="sidetop" style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px">
      <a href="/" style="text-decoration:none;display:block">
        <div style="font-family:var(--label-font);font-weight:700;font-size:25px;letter-spacing:.16em;color:var(--ink);line-height:1">NUVIE</div>
        <div class="brandsub" style="font-size:12px;letter-spacing:.02em;color:var(--accent);margin-top:6px;white-space:nowrap">누비 스튜디오</div>
      </a>
      <button id="themeBtn" aria-label="테마 전환" style="width:34px;height:34px;flex:none;border:1px solid var(--line);background:transparent;color:var(--dim);border-radius:3px;cursor:pointer;font-size:15px;display:inline-flex;align-items:center;justify-content:center">☾</button>
    </div>
    <div class="sidetag" style="color:var(--dim);font-size:12.5px;margin-top:14px;line-height:1.7">비치 소품 · 룸별<br>서울 강서구 · 까치산</div>
    <div class="siderule" style="height:1px;background:var(--line);margin:24px 0"></div>
    <nav class="sidenav" style="display:flex;flex-direction:column;gap:1px">
      <a href="/#rooms" class="nav"><span class="no">01</span> 룸 · 요금</a>
      <a href="/#availability" class="nav"><span class="no">02</span> 빈 시간</a>
      <a href="/a" class="nav"><span class="no">03</span> A룸 상세</a>
      <a href="/b" class="nav"><span class="no">04</span> B룸 상세</a>
      <a href="/props" class="nav active"><span class="no">05</span> 비치 소품</a>
    </nav>
    <div class="book" style="margin-top:24px;display:flex;flex-direction:column;gap:9px">
      <a class="btn" href="/#availability" style="width:100%">빈 시간 보기</a>
      <a class="book2 btn line" href="/#rooms" style="width:100%">룸 · 요금</a>
    </div>
  </aside>

  <main>
    <noscript><style>.panel{display:block!important}.panel+.panel{border-top:1px solid var(--line);margin-top:40px}.roomtabs{display:none}</style></noscript>
    <nav class="roomtabs" role="tablist" aria-label="룸 선택">
      <a class="rt on" role="tab" id="tab-a" aria-controls="panel-a" aria-selected="true" href="#a" data-room="a">
        A룸 소품 <b>13</b><span>동양풍 · 블랙 호리존</span>
      </a>
      <a class="rt" role="tab" id="tab-b" aria-controls="panel-b" aria-selected="false" href="#b" data-room="b">
        B룸 소품 <b>20</b><span>화이트 티타임 카페</span>
      </a>
    </nav>

    <header class="banner">
      <img id="heroImg" src="/img/galA-1001-7-wide.jpg" width="1200" height="675" alt="A룸 동양풍 세트와 블랙 호리존" fetchpriority="high">
      <div class="sc"></div>
      <div class="in">
        <p class="crumb"><a href="/">누비 스튜디오</a> &nbsp;›&nbsp; 비치 소품</p>
        <h1 id="heroTitle">A룸 소품</h1>
        <p class="lead" id="heroLead">동양존과 블랙 호리존에서 쓰는 소품과 장비입니다. 다른 룸 소품은 섞지 않았습니다.</p>
        <p class="staticnote">A룸·B룸 비치 소품·장비·원단 안내 — 룸을 골라 확인하세요.</p>
        <p class="caveat"><b>비치 품목과 수량은 촬영·세팅 상황에 따라 조금씩 달라질 수 있어요.</b> 꼭 필요한 소품은 예약 전에 아워플레이스 메시지로 확인해 주세요.</p>
      </div>
    </header>
"""

FOOT = """    <div class="cta">
      <div class="in">
        <div class="t">쓰고 싶은 소품이 정해졌다면 빈 시간을 확인하세요</div>
        <div class="acts">
          <a class="btn" href="/#availability" style="padding:13px 26px;font-size:14.5px">빈 시간 보기</a>
          <a class="btn line" href="/a" style="padding:13px 26px;font-size:14.5px">A룸 상세 &rarr;</a>
          <a class="btn line" href="/b" style="padding:13px 26px;font-size:14.5px">B룸 상세 &rarr;</a>
        </div>
      </div>
    </div>

    <footer class="sec" style="padding-top:40px;padding-bottom:48px;border-top:1px solid var(--line)">
      <div class="inner" style="display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;color:var(--faint);font-size:12.5px;line-height:1.9">
        <div>📍 서울 강서구 까치산역 도보 10분<br>예약: 아워플레이스<br>문의: 전화 070-8211-1103(10:00~19:00) · 아워플레이스 메시지</div>
        <div style="display:flex;gap:16px;flex-wrap:wrap">
          <a class="nv-privacy" href="/" style="color:var(--dim);text-decoration:none">누비 스튜디오 홈</a>
          <a class="nv-privacy" href="/privacy" style="color:var(--dim);text-decoration:none">개인정보처리방침</a>
        </div>
      </div>
    </footer>
  </main>
</div>
<script>
(function () {
  var btn = document.getElementById('themeBtn');
  if (btn) {
    function setTheme(t) {
      document.body.setAttribute('data-theme', t);
      btn.textContent = (t === 'dark' ? '☀' : '☾');
      btn.setAttribute('aria-label', t === 'dark' ? '라이트 모드로 전환' : '다크 모드로 전환');
    }
    setTheme(document.body.getAttribute('data-theme') || 'dark');
    btn.addEventListener('click', function () {
      setTheme(document.body.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
    });
  }

  var ROOM = {
    a: { img: '/img/galA-1001-7-wide.jpg', alt: 'A룸 동양풍 세트와 블랙 호리존',
         title: 'A룸 소품', lead: '동양존과 블랙 호리존에서 쓰는 소품과 장비입니다. 다른 룸 소품은 섞지 않았습니다.' },
    b: { img: '/img/galB-1003-1.jpg', alt: 'B룸 화이트 티타임 카페',
         title: 'B룸 소품', lead: '화이트 티타임 카페에서 쓰는 소품과 장비입니다. 다른 룸 소품은 섞지 않았습니다.' }
  };

  function show(room, push) {
    if (!ROOM[room]) room = 'a';
    ['a', 'b'].forEach(function (r) {
      var tab = document.getElementById('tab-' + r);
      var panel = document.getElementById('panel-' + r);
      var on = (r === room);
      tab.setAttribute('aria-selected', on ? 'true' : 'false');
      tab.classList.toggle('on', on);
      panel.hidden = !on;
    });
    var img = document.getElementById('heroImg');
    img.src = ROOM[room].img;
    img.alt = ROOM[room].alt;
    document.getElementById('heroTitle').textContent = ROOM[room].title;
    document.getElementById('heroLead').textContent = ROOM[room].lead;
    if (push && location.hash !== '#' + room) location.hash = '#' + room;
  }

  Array.prototype.forEach.call(document.querySelectorAll('.rt'), function (tab) {
    tab.addEventListener('click', function (e) {
      e.preventDefault();
      show(tab.dataset.room, true);
      window.scrollTo({ top: 0, behavior: 'auto' });
    });
    tab.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        var next = tab.dataset.room === 'a' ? 'b' : 'a';
        show(next, true);
        document.getElementById('tab-' + next).focus();
      }
    });
  });

  window.addEventListener('hashchange', function () { show(location.hash.replace('#', ''), false); });
  show(location.hash.replace('#', '') || 'a', false);
})();
</script>
</body>
</html>
"""


def load():
    with io.open(DATA, encoding="utf-8") as f:
        return json.load(f)


def photo_for(pid):
    for ext in ("jpg", "jpeg", "png", "webp"):
        if os.path.exists(os.path.join(PHOTO_DIR, pid + "." + ext)):
            return "/img/props/%s.%s" % (pid, ext)
    return None


def esc(s):
    return _html.escape(s or "", quote=True)


def render_items(items, key):
    out = ['        <ul class="items">']
    for it in items:
        sub = ('<small>%s</small>' % esc(it["sub"])) if it.get("sub") else ""
        src = photo_for(it["id"])
        ph = ('<span class="ph"><img src="%s" alt="%s" loading="lazy" width="600" height="450"></span>'
              % (src, esc(it["name"]))) if src else (
              '<span class="ph ph-tmp ph-%s"><em>&lt;사진첨부 예정&gt;</em></span>' % key)
        # 무료 태그는 그리지 않는다(2026-11-25 내부작업 검수: 카드 33장에 «무료» 반복 = 슬롭).
        # 데이터에는 tag:"무료"가 남아 있으므로 렌더에서만 무시하고, 값이 이상하면 즉시 실패한다.
        if it.get("tag") not in ("무료", "유료"):
            raise SystemExit("[build_props] 알 수 없는 tag: %r (%s)" % (it.get("tag"), it["id"]))
        tag_html = '<span class="tag paid">유료</span>' if it.get("tag") == "유료" else ""
        out.append('          <li>%s<span class="nm">%s%s</span>%s</li>'
                   % (ph, esc(it["name"]), sub, tag_html))
    out.append("        </ul>")
    return "\n".join(out)


def render_paid(rows, room):
    """유료 장비 — 사진 카드 + 큰 금액. 총액 상한은 «유료 장비» 머리 바로 아래."""
    paid_total = sum(int(r["price"].replace(",", "").replace("원", "")) for r in rows)
    label = ("%d종 모두 " % len(rows)) if len(rows) > 1 else ""
    allmax = ('<p class="allmax">' + label + '추가 시 최대 +%s원 (대관료 별도)</p>'
              % format(paid_total, ","))

    out = ['        <ul class="items paid">']
    for r in rows:
        pid = r.get("photo")
        src = photo_for(pid) if pid else None
        ph = ('<span class="ph"><img src="%s" alt="%s" loading="lazy" width="600" height="450"></span>'
              % (src, esc(r["name"]))) if src else (
              '<span class="ph ph-tmp"><em>&lt;사진첨부 예정&gt;</em></span>')
        benefit = ('<span class="benefit">%s</span>' % esc(r["benefit"])) if r.get("benefit") else ""
        out.append('          <li>%s<span class="nm">%s</span>'
                   '<span class="sub">%s</span>%s'
                   '<span class="price">%s</span></li>'
                   % (ph, esc(r["name"]), esc(r.get("sub", "")), benefit, esc(r["price"])))
    out.append("        </ul>")

    head = ('          <div class="ledger" id="paid-' + esc(room) + '">\n'
            '            <div class="paidhead"><span class="cap">유료 장비</span>'
            '<span class="capnote">대관 1회당 · 이용 시간과 무관</span></div>\n'
            + allmax)
    return head + "\n" + "\n".join(out) + "\n          </div>"


def render_fabrics(fabrics):
    order = ["오간자", "쉬폰", "공단", "흑백"]
    label = {"오간자": "오간자", "쉬폰": "쉬폰", "공단": "공단", "흑백": "수묵 프린트"}
    buckets = {k: [] for k in order}
    for f in fabrics:
        buckets.setdefault(f["mat"], []).append(f)
    out = []
    for key in order:
        rows = buckets.get(key) or []
        if not rows:
            continue
        out.append('          <div class="fgroup">')
        out.append('            <h3>%s <b>%d</b></h3>' % (label.get(key, key), len(rows)))
        out.append('            <ul class="swatches">')
        for f in rows:
            out.append('              <li><span class="chip" style="background:%s"></span>'
                       '<span class="nm">%s</span><span class="mat">%s</span></li>'
                       % (f["color"], esc(f["name"]), esc(f["mat"])))
        out.append('            </ul>')
        out.append('          </div>')
    return "\n".join(out)


EQ_ORDER = ["지속광", "순간광", "모디파이어", "스탠드·그립", "배경", "기타"]


def render_equipment(items):
    """장비도 소품과 같은 «사진 카드»로. 아워 A룸 표기처럼 지속광→순간광→모디파이어→스탠드 순으로 묶는다."""
    buckets = {}
    for it in items:
        buckets.setdefault(it.get("group", "기타"), []).append(it)
    out = []
    for g in EQ_ORDER:
        rows = buckets.get(g) or []
        if not rows:
            continue
        out.append('        <div class="fgroup">')
        out.append('          <h3>%s <b>%d</b></h3>' % (esc(g), len(rows)))
        out.append('          <ul class="items">')
        for it in rows:
            sub = ('<small>%s</small>' % esc(it["sub"])) if it.get("sub") else ""
            src = photo_for(it["id"])
            ph = ('<span class="ph"><img src="%s" alt="%s" loading="lazy" width="600" height="450"></span>'
                  % (src, esc(it["name"]))) if src else (
                  '<span class="ph ph-tmp ph-equipment"><em>&lt;사진첨부 예정&gt;</em></span>')
            tag = '<span class="tag paid">유료</span>' if it.get("tag") == "유료" else ""
            label = "" if it.get("hideLabel") else '<span class="nm">%s%s</span>' % (esc(it["name"]), sub)
            out.append('            <li>%s%s%s</li>' % (ph, label, tag))
        out.append('          </ul>')
        out.append('        </div>')
    return "\n".join(out)

def panel(doc, room, hidden):
    r = [x for x in doc["rooms"] if x["slug"] == room][0]
    free_n = sum(1 for x in doc["equipment"][room] if x.get("tag", "무료") == "무료") \
        + sum(1 for x in r["items"] if x.get("tag", "무료") == "무료")
    paid_n = len(doc["paid"][room])
    parts = ['    <section id="panel-%s" class="panel" role="tabpanel" aria-labelledby="tab-%s"%s>'
             % (room, room, " hidden" if hidden else "")]
    parts.append("""      <div class="layout">
        <div>
          <p class="psum">__PSUM__</p>
          <section class="cat" id="equipment-%s">
            <div class="cathead">
              <h2>조명 · 장비</h2>
              <div class="c">장비 %d종 · %s</div>
            </div>
            <p class="note">%s</p>
%s
%s
          </section>

          <section class="cat" id="props-%s">
            <div class="cathead">
              <h2>%s 소품</h2>
              <div class="c">소품 %d종</div>
            </div>
%s
%s
          </section>""" % (
        room, len(doc["equipment"][room]), r["short"],
        ("이 룸에서 쓰는 조명과 장비입니다." if room == "b"
         else "비치 조명은 무료입니다. 조명 기본값을 정해 두지 않으니 원하는 톤으로 직접 세팅하시면 됩니다."),
        render_paid(doc["paid"][room], room)
        + '<div class="freehead"><span class="cap">무료 장비</span>'
          '<span class="capnote">추가 결제 없이 사용</span></div>',
        render_equipment(doc["equipment"][room]),
        room, r["short"], len(r["items"]),
        ("""          <div class="duo">
            <figure><span class="frame"><img src="/img/galA-1001-7-wide.jpg" width="1200" height="675" loading="lazy" alt="A룸 동양존 — 붉은 드레이프와 나한상"></span><figcaption>동양존 — 나한상 · 병풍 · 격자 스크린</figcaption></figure>
            <figure><span class="frame"><img src="/img/props-horizon.jpg" width="1000" height="750" loading="lazy" alt="A룸 블랙 호리존 — 배경을 비운 기본 상태"></span><figcaption>블랙 호리존 — 배경을 비운 기본 상태</figcaption></figure>
          </div>""" if room == "a" else
         """          <figure class="plate"><img src="/img/galB-1003-1.jpg" width="1000" height="563" loading="lazy" alt="B룸 화이트 티타임 카페 — 레이스 테이블과 통창"><figcaption><span>레이스 테이블과 통창</span><span>오후엔 서향 햇빛</span></figcaption></figure>"""),
        render_items(r["items"], "room-" + room)))

    if room == "a":
        parts.append("""
          <section class="cat" id="fabric">
            <div class="cathead">
              <h2>원단 (A룸 전용 · 무료)</h2>
              <div class="c">14색 · 폭·길이는 현장 확인</div>
            </div>
            <figure class="plate">
              <img src="/img/props-fabric.jpg" width="1200" height="703" loading="lazy" alt="A룸 원단 색상별 정리 — 오간자 · 쉬폰 · 공단 · 수묵 프린트">
              <figcaption><span>색과 재질만 골라 쓰시면 됩니다</span><span>A룸</span></figcaption>
            </figure>
%s
          </section>""" % render_fabrics(doc["fabrics"]))

    other = "b" if room == "a" else "a"
    parts.append("""        </div>
        <aside class="rail" aria-label="바로가기">
          <div class="grp"><div class="k">This room</div>
            <a href="#paid-%(r)s">유료 장비</a>
            <a href="#equipment-%(r)s">조명 · 장비</a>
            <a href="#props-%(r)s">%(short)s 소품</a>
          </div>
          <div class="grp"><div class="k">Other</div>
            <a href="#%(o)s" data-switch="%(o)s">%(oshort)s 소품 →</a>
          </div>
          <div class="grp"><div class="k">Booking</div>
            <a href="/#availability">빈 시간 보기</a>
            <a href="/%(r)s">%(short)s 상세</a>
          </div>
        </aside>
      </div>
    </section>""" % {"r": room, "short": r["short"], "o": other,
                      "oshort": "B룸" if other == "b" else "A룸"})
    psum = ("<b>무료 %d</b> · <b>유료 %d</b> — 유료는 대관 1회당 요금입니다." % (free_n, paid_n))
    return "\n".join(parts).replace("__PSUM__", psum)


def main():
    doc = load()
    body = [HEAD]
    body.append(panel(doc, "a", hidden=False))
    body.append(panel(doc, "b", hidden=True))
    body.append(FOOT)
    html = "\n".join(body)

    with io.open(os.path.join(HERE, "props.html"), "w", encoding="utf-8", newline="") as f:
        f.write(html)

    total = sum(len(doc["equipment"][r]) + len(x["items"]) for r in ("a", "b") for x in doc["rooms"] if x["slug"] == r)
    withphoto = 0
    for r in ("a", "b"):
        withphoto += sum(1 for it in doc["equipment"][r] if photo_for(it["id"]))
    for x in doc["rooms"]:
        withphoto += sum(1 for it in x["items"] if photo_for(it["id"]))
    print("[build_props] props.html · items %d (%d with photo) · fabrics %d" % (total, withphoto, len(doc["fabrics"])))


if __name__ == "__main__":
    main()
