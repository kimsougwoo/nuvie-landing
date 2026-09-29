(function () {
  'use strict';

  var STORAGE_KEY = 'nv_attribution_v1';
  var MAX = 120;
  var TOUCH_KEYS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'gclid', 'fbclid'];

  function clip(value, limit) {
    return String(value || '').trim().slice(0, limit || MAX);
  }

  function readState() {
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      var parsed = raw ? JSON.parse(raw) : {};
      return parsed && typeof parsed === 'object' ? parsed : {};
    } catch (e) {
      return {};
    }
  }

  function writeState(state) {
    try { window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (e) {}
  }

  function currentTouch() {
    var q = new URLSearchParams(window.location.search);
    var touch = {};
    var hasCampaign = false;
    TOUCH_KEYS.forEach(function (key) {
      var value = clip(q.get(key));
      if (value) {
        touch[key] = value;
        hasCampaign = true;
      }
    });
    if (!hasCampaign) return null;

    touch.landing_path = clip(window.location.pathname, MAX);
    touch.captured_at = new Date().toISOString();
    return touch;
  }

  function referrerOrigin() {
    try {
      if (!document.referrer) return '';
      var ref = new URL(document.referrer);
      if (ref.origin === window.location.origin) return '';
      return clip(ref.origin, MAX);
    } catch (e) {
      return '';
    }
  }

  var state = readState();
  var incoming = currentTouch();
  var now = new Date().toISOString();
  if (!state.first_visit_at) state.first_visit_at = now;
  state.last_visit_at = now;
  if (incoming) {
    if (!state.first_touch) state.first_touch = incoming;
    state.last_touch = incoming;
  }
  var ref = referrerOrigin();
  if (ref) state.last_referrer_origin = ref;
  writeState(state);

  function snapshot() {
    return {
      first_touch: state.first_touch || null,
      last_touch: state.last_touch || null,
      first_visit_at: clip(state.first_visit_at, 40),
      last_visit_at: clip(state.last_visit_at, 40),
      last_referrer_origin: clip(state.last_referrer_origin, MAX)
    };
  }

  function event(name, params) {
    try {
      if (window.gtag) window.gtag('event', name, params || {});
    } catch (e) {}
  }

  // Clarity custom tags are aggregate labels only: never pass email, phone,
  // booking IDs, or query-string values.  Internal QA traffic is already
  // stubbed by the page loader, so this remains fail-safe when Clarity is off.
  function clarityTag(key, value) {
    try {
      var safe = clip(value, 80);
      if (window.clarity && safe) window.clarity("set", key, safe);
    } catch (e) {}
  }

  // 🔴 2026-08-18 신설 — UTM 을 «이벤트 파라미터»로 내놓는다.
  //   종전엔 last_touch 를 localStorage 에 저장만 하고 이벤트엔 utm_source 만 실었다.
  //   그래서 「훅 A 와 B 중 어느 쪽이 아워로 더 보냈나」를 이벤트 단위로 못 갈랐다
  //   (GA4 세션 차원으로 조인하면 나오긴 하나 탐색을 매번 짜야 한다).
  //   ⚠️ 값은 전부 clip() 을 거친다 — 쿼리스트링을 그대로 흘리지 않는다.
  function utmParams() {
    var t = state.last_touch || {};
    return {
      utm_source: clip(t.utm_source, 60) || 'direct',
      utm_medium: clip(t.utm_medium, 60) || 'none',
      utm_campaign: clip(t.utm_campaign, 60) || 'none',
      utm_content: clip(t.utm_content, 60) || 'none'
    };
  }

  /* 새 탭으로 나가는 클릭의 계측을 «다음 화면을 그린 뒤»로 미룬다 (2026-09-30).
   * 왜: 예약 버튼 한 번에 gtag·fbq·clarity 호출이 약 10번 클릭 처리 안에서 돌아, 추적이 켜진 모바일(CPU 4배)에서
   *   누른 뒤 화면이 344ms 늦게 그려졌다(nuvie_ux_lab 실측). 호출 내용·순서는 그대로 두고 시점만 옮긴다.
   * ⚠️ 같은 탭 이동은 미루지 않는다(페이지가 떠나며 계측이 사라진다) — target=_blank 일 때만.
   * ⚠️ 새 탭이 앞으로 오면 이 탭은 숨겨져 requestAnimationFrame 이 멈춘다 → 숨김 전환·200ms 시계로도 반드시 한 번 보낸다.
   * 🧊 /b 는 11/11 동결 — 종전처럼 바로 실행(해제 절차 = B_UNFREEZE_1111.md). 계약 = test_after_paint.js */
  var paintQ = [];
  var paintArmed = false;
  var paintGen = 0;   // 앞 클릭의 200ms 시계가 뒤 클릭 몫을 그리기 전에 비우지 않게
  function flushPaintQ(gen) {
    if (!paintArmed || (typeof gen === 'number' && gen !== paintGen)) return;
    paintArmed = false;
    document.removeEventListener('visibilitychange', flushPaintQ);
    var q = paintQ.splice(0);
    for (var i = 0; i < q.length; i++) {
      try { q[i](); } catch (e) {}
    }
  }
  function afterPaint(el, fn) {
    var frozen = false;
    try { frozen = document.body.getAttribute('data-room') === 'b'; } catch (e) {}
    if (!el || el.target !== '_blank' || frozen || typeof window.requestAnimationFrame !== 'function') {
      try { fn(); } catch (e) {}
      return;
    }
    paintQ.push(fn);
    if (paintArmed) return;
    paintArmed = true;
    var gen = ++paintGen;
    window.requestAnimationFrame(function () { window.setTimeout(function () { flushPaintQ(gen); }, 0); });
    window.setTimeout(function () { flushPaintQ(gen); }, 200);
    document.addEventListener('visibilitychange', flushPaintQ);
  }

  window.NUVIE_ATTRIBUTION = { get: snapshot, event: event, tag: clarityTag, utmParams: utmParams, afterPaint: afterPaint };

  var _u = utmParams();
  event('landing_view', {
    first_source: clip(state.first_touch && state.first_touch.utm_source, 60) || 'direct',
    last_source: _u.utm_source,
    utm_medium: _u.utm_medium,
    utm_campaign: _u.utm_campaign,
    utm_content: _u.utm_content,
    page: clip(window.location.pathname, 80),
    transport_type: 'beacon'
  });
  clarityTag('page', window.location.pathname);
  clarityTag('utm_source', state.last_touch && state.last_touch.utm_source || 'direct');
  clarityTag('utm_medium', state.last_touch && state.last_touch.utm_medium || 'none');
  // 🔴 2026-09-16 — 소재별(utm_content) Clarity 세그먼트를 «모든 세션»에서 가능하게 로드 시 태그.
  //   종전엔 utm_content 가 HourplaceClick 때만 태그돼, 아워 버튼을 안 누른 세션은 소재 구분 불가였다.
  //   (GA4 utm_content 커스텀 디멘션 등록과 짝 — 광고 URL 에 utm_content 가 붙으면 양쪽서 소재 분해.)
  clarityTag('utm_content', _u.utm_content);
  clarityTag('utm_campaign', _u.utm_campaign);

  function roomFor(el) {
    var room = el.getAttribute('data-room') || el.getAttribute('data-book');
    if (room === 'a' || room === 'b') return room;
    var id = el.id || '';
    if (/A$/.test(id) || /-a$/.test(id)) return 'a';
    if (/B$/.test(id) || /-b$/.test(id)) return 'b';
    return '';
  }

  document.addEventListener('click', function (e) {
    var target = e.target && e.target.closest ? e.target.closest('[data-book],#availBookA,#availBookB,#dayDetailBookA,#dayDetailBookB') : null;
    if (target) {
      afterPaint(target, function () {
        event('booking_intent', {
          room: roomFor(target),
          placement: clip(target.id || 'booking_cta', 60),
          transport_type: 'beacon'
        });
        clarityTag('event', 'booking_intent');
        clarityTag('room', roomFor(target) || 'unknown');
        clarityTag('placement', target.id || 'booking_cta');
      });
      return;
    }
  });
})();
