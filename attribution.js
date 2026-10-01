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
   * ⚠️ 새 탭이 앞으로 오면 이 탭은 숨겨져 requestAnimationFrame 이 멈춘다 → 숨김 전환·페이지 떠남(pagehide)·200ms 시계로도
   *   반드시 한 번 보낸다. 숨김·떠남은 window «캡처» 단계에 건다 — gtag·픽셀·Clarity 가 로드 때 건 숨김 처리보다 먼저 돌게.
   * ⚠️ 앱 안 브라우저(인스타·페북·카톡·네이버·라인·안드로이드 웹뷰)는 새 탭 링크를 같은 화면에서 열 수 있어 종전처럼 바로 실행
   *   (광고 유입 대부분이 여기라 광고 지표 안전을 먼저 — 새 눈 검수 09-30).
   * 🧊 /b 는 11/11 동결 — 종전처럼 바로 실행(해제 절차 = wt/b-unfreeze-1111 의 B_UNFREEZE_1111.md). 계약 = test_after_paint.js */
  var IN_APP = /FBAN|FBAV|FB_IAB|FBIOS|Instagram|KAKAOTALK|NAVER\(inapp|Line\/|DaumApps|; wv\)/i;
  var paintQ = [];
  var paintArmed = false;
  var paintGen = 0;   // 앞 클릭의 200ms 시계가 뒤 클릭 몫을 그리기 전에 비우지 않게
  function flushPaintQ(gen) {
    if (!paintArmed || (typeof gen === 'number' && gen !== paintGen)) return;
    paintArmed = false;
    window.removeEventListener('visibilitychange', onLeave, true);
    window.removeEventListener('pagehide', onLeave, true);
    var q = paintQ.splice(0);
    for (var i = 0; i < q.length; i++) {
      try { q[i](); } catch (e) {}
    }
  }
  function onLeave() { flushPaintQ(); }
  function afterPaint(el, fn) {
    var sync = !el || el.target !== '_blank' || typeof window.requestAnimationFrame !== 'function';
    try { sync = sync || document.body.getAttribute('data-frozen') !== null; } catch (e) {}
    try { sync = sync || IN_APP.test(window.navigator.userAgent || ''); } catch (e) {}
    if (sync) {
      try { fn(); } catch (e) {}
      return;
    }
    paintQ.push(fn);
    if (paintArmed) return;
    paintArmed = true;
    var gen = ++paintGen;
    window.requestAnimationFrame(function () { window.setTimeout(function () { flushPaintQ(gen); }, 0); });
    window.setTimeout(function () { flushPaintQ(gen); }, 200);
    window.addEventListener('visibilitychange', onLeave, true);
    window.addEventListener('pagehide', onLeave, true);
  }

  window.NUVIE_ATTRIBUTION = { get: snapshot, event: event, tag: clarityTag, utmParams: utmParams, afterPaint: afterPaint };

  /* 실사용자 INP 수집 (2026-09-30) — GA4 이벤트 web_vitals.
   * 왜: Clarity INP 는 조회 11회 표본이라 한두 건에 p75 가 1.6초로 튀었고 어느 버튼이 느린지도 몰랐다(09-29 조사).
   *   web-vitals 6.2.2(Apache-2.0, /vendor/ 자체 호스팅)의 onINP 가 «느린 상호작용 대상·구간»을 알려 준다.
   * 문서 해석이 끝난 뒤 유휴 때 불러온다 · 내부 방문·/b(11/11 동결)는 불러오지 않는다 · 대상은 태그·id·class 모양,
   *   스크립트는 경로만(쿼리 제거) · 계약 = test_rum_inp.js
   * GA4 보고서용 맞춤 정의(배포 뒤 등록): 측정기준 metric_name·metric_id·metric_rating·interaction_target·interaction_type·loaf_script,
   *   측정항목 metric_value·metric_delta·input_delay·processing_duration·presentation_delay(밀리초)
   * 알려진 치우침: 불러오기 전 상호작용은 104ms 이상만 남는다 · 새 탭으로 나간 뒤엔 돌아와 다시 떠날 때 보고된다 */
  var VITALS_SRC = '/vendor/web-vitals-6.2.2.attribution.iife.js';
  var vitalsLoaded = false;
  function pathOnly(url) {
    if (!url) return '';   // 출처 없는 스크립트 — '/' 로 적으면 홈페이지 스크립트처럼 보인다
    try { var u = new URL(url, window.location.origin); return clip(u.hostname === window.location.hostname ? u.pathname : u.hostname + u.pathname, 100); } catch (e) { return ''; }
  }
  function sendInp(m) {
    try {
      var a = m.attribution || {};
      var ls = a.longestScript && a.longestScript.entry;
      event('web_vitals', {
        metric_name: m.name,
        metric_value: Math.round(m.value),
        metric_id: clip(m.id, 40),                 // INP 가 커지면 같은 id 로 다시 보고된다 — id 로 묶어 최댓값만 쓴다
        metric_delta: Math.round(m.delta || 0),
        metric_rating: m.rating,
        interaction_target: String(a.interactionTarget || '').slice(-100),
        interaction_type: clip(a.interactionType, 20),
        input_delay: Math.round(a.inputDelay || 0),
        processing_duration: Math.round(a.processingDuration || 0),
        presentation_delay: Math.round(a.presentationDelay || 0),
        loaf_script: ls ? pathOnly(ls.sourceURL || '') : '',   // 페이지는 GA4 기본 «페이지 경로»로 본다(별도 매개변수 없음)
        transport_type: 'beacon'
      });
    } catch (e) {}
  }
  function sendVital(m) {
    try {
      var a = m.attribution || {};
      // CLS 는 0.05 같은 소수라 metric_value(정수)에 1000 을 곱해 싣는다(0.05 → 50). LCP 는 밀리초 그대로.
      var scale = m.name === 'CLS' ? 1000 : 1;
      event('web_vitals', {
        metric_name: m.name,
        metric_value: Math.round(m.value * scale),
        metric_id: clip(m.id, 40),
        metric_delta: Math.round((m.delta || 0) * scale),
        metric_rating: m.rating,
        interaction_target: String(a.target || a.largestShiftTarget || '').slice(-100),   // LCP 요소·가장 크게 밀린 요소
        transport_type: 'beacon'
      });
    } catch (e) {}
  }
  function loadVitals() {
    if (vitalsLoaded) return;
    vitalsLoaded = true;
    try {
      var s = document.createElement('script');
      s.async = true;
      s.src = VITALS_SRC;
      s.onload = function () {
        try { if (window.webVitals && window.webVitals.onINP) window.webVitals.onINP(sendInp); } catch (e) {}
        // 10-01: 실험실(Lighthouse) 값만으로 LCP 를 판정하지 않으려고 실사용 LCP·CLS 도 보낸다(같은 이벤트·metric_name 으로 구분).
        try { if (window.webVitals && window.webVitals.onLCP) window.webVitals.onLCP(sendVital); } catch (e) {}
        try { if (window.webVitals && window.webVitals.onCLS) window.webVitals.onCLS(sendVital); } catch (e) {}
      };
      document.head.appendChild(s);
    } catch (e) {}
  }
  function whenIdle(fn) {
    if (typeof window.requestIdleCallback === 'function') window.requestIdleCallback(fn, { timeout: 3000 });
    else window.setTimeout(fn, 1);
  }
  (function scheduleVitals() {
    try {
      var frozen = false;
      try { frozen = document.body.getAttribute('data-frozen') !== null; } catch (e) {}
      if (window.__nvInternal || frozen) return;
      // load 까지 기다리지 않는다 — 불러오기 전 상호작용은 104ms 이상만 버퍼에 남아, 로드 전 빠른 탭이 빠지고 느린 탭만 잡힌다
      if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { whenIdle(loadVitals); });
      else whenIdle(loadVitals);
    } catch (e) {}   // 수집이 실패해도 계측 본체는 살아 있어야 한다
  })();

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
