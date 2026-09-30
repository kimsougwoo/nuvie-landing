// 실사용자 INP 수집 계약 (node 실행: `node test_rum_inp.js`) — 2026-09-30
//
// 왜: Clarity 의 INP 는 조회 11회 표본이라 한두 건에 p75 가 1.6초로 튀었고(2026-09-29 조사), 어느 버튼이 느린지도 몰랐다.
//   web-vitals(Apache-2.0, 자체 호스팅 /vendor/)의 onINP 로 «느린 상호작용 대상·구간»을 GA4 이벤트 web_vitals 로 보낸다.
// 지키는 선: ① 페이지가 다 뜬 뒤에 불러온다(첫 화면과 다투지 않게) ② 내부 방문(?nvdev=1 등)은 불러오지도 않는다
//   ③ /b 는 11/11 동결 ④ 개인정보·쿼리스트링을 싣지 않는다(대상은 태그·id·class 모양만, 페이지는 경로만)
//   ⑤ 기존 이벤트(book_click 등)와 이름이 겹치지 않는다
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

function makeEnv({ room = null, internal = false, readyState = 'complete' } = {}) {
  const injected = [];
  const winListeners = {};
  const sent = [];
  const timers = [];
  const window = {
    __nvInternal: internal,
    localStorage: { getItem: () => null, setItem: () => {} },
    location: { origin: 'https://nuvie.example', pathname: '/a', search: '?utm_source=meta&email=x@y.z' },
    gtag: (t, n, p) => sent.push({ n, p }),
    addEventListener: (t, fn) => { (winListeners[t] = winListeners[t] || []).push(fn); },
    setTimeout: (fn) => timers.push(fn),
    requestIdleCallback: (fn) => timers.push(fn),
  };
  window.window = window;
  const document = {
    referrer: '',
    readyState,
    body: { getAttribute: (k) => (k === 'data-room' ? room : null) },
    head: { appendChild: (el) => injected.push(el) },
    createElement: (tag) => ({ tagName: tag.toUpperCase() }),
    addEventListener: () => {},
    removeEventListener: () => {},
  };
  const ctx = { window, document, URL, URLSearchParams, Date, Math, JSON, Object, String, Array,
    setTimeout: window.setTimeout, requestIdleCallback: window.requestIdleCallback };
  vm.runInNewContext(fs.readFileSync('attribution.js', 'utf8'), ctx, { filename: 'attribution.js' });
  return {
    window, injected, sent, winListeners,
    runTimers() { timers.splice(0).forEach((f) => f()); },
    fireLoad() { (winListeners.load || []).forEach((f) => f()); },
  };
}

const vitalsScripts = (E) => E.injected.filter((s) => /web-vitals/.test(s.src || ''));

// ① 이미 로드가 끝난 페이지 → 유휴 때 한 번 불러온다(바로 끼워 넣지 않는다)
{
  const E = makeEnv();
  assert.strictEqual(vitalsScripts(E).length, 0, '실행 즉시 불러오면 첫 화면과 다툰다');
  E.runTimers();
  const s = vitalsScripts(E);
  assert.strictEqual(s.length, 1, 'web-vitals 를 한 번 불러와야 한다');
  assert.ok(/^\/vendor\/web-vitals-6\.2\.2\.attribution\.iife\.js$/.test(s[0].src), '자체 호스팅 고정 버전 경로: ' + s[0].src);
  assert.ok(s[0].async, 'async');
}

// 로드 전이면 load 이벤트 뒤
{
  const E = makeEnv({ readyState: 'loading' });
  E.runTimers();
  assert.strictEqual(vitalsScripts(E).length, 0, 'load 전에 불러오면 안 된다');
  E.fireLoad(); E.runTimers();
  assert.strictEqual(vitalsScripts(E).length, 1);
}

// ② 내부 방문 · ③ /b 동결 → 불러오지 않는다
{
  const I = makeEnv({ internal: true }); I.runTimers(); I.fireLoad(); I.runTimers();
  assert.strictEqual(vitalsScripts(I).length, 0, '내부 방문은 불러오지 않는다');
  const B = makeEnv({ room: 'b' }); B.runTimers(); B.fireLoad(); B.runTimers();
  assert.strictEqual(vitalsScripts(B).length, 0, '/b 는 11/11 동결');
}

// ④⑤ 보낼 때 모양
{
  const E = makeEnv();
  E.runTimers();
  const s = vitalsScripts(E)[0];
  let cb = null, opts = null;
  E.window.webVitals = { onINP: (f, o) => { cb = f; opts = o; } };
  s.onload();
  assert.strictEqual(typeof cb, 'function', 'onINP 를 등록해야 한다');
  const before = E.sent.length;
  cb({
    name: 'INP', value: 344.4, rating: 'needs-improvement', id: 'v5-1', navigationType: 'navigate',
    attribution: {
      interactionTarget: 'a#book-mobile.btn', interactionType: 'pointer',
      inputDelay: 10.2, processingDuration: 291.7, presentationDelay: 42.5,
      longestScript: { entry: { sourceURL: 'https://connect.facebook.net/en_US/fbevents.js?v=1&uid=abc', invoker: 'DOCUMENT.onclick' }, subpart: 'processing-duration', intersectingDuration: 120.3 },
    },
  });
  const ev = E.sent.slice(before);
  assert.strictEqual(ev.length, 1);
  assert.strictEqual(ev[0].n, 'web_vitals', '이벤트 이름은 web_vitals 하나');
  const p = ev[0].p;
  assert.strictEqual(p.metric_name, 'INP');
  assert.strictEqual(p.metric_value, 344);
  assert.strictEqual(p.metric_rating, 'needs-improvement');
  assert.strictEqual(p.interaction_target, 'a#book-mobile.btn');
  assert.strictEqual(p.interaction_type, 'pointer');
  assert.strictEqual(p.input_delay, 10);
  assert.strictEqual(p.processing_duration, 292);
  assert.strictEqual(p.presentation_delay, 43);
  assert.strictEqual(p.loaf_script, 'connect.facebook.net/en_US/fbevents.js', '스크립트는 호스트+경로만(쿼리 제거)');
  assert.ok(!('page_path' in p), '페이지는 GA4 기본 페이지 경로로 본다 — 쿼리가 섞일 수 있는 별도 매개변수를 싣지 않는다');
  assert.strictEqual(p.transport_type, 'beacon');
  assert.ok(!JSON.stringify(p).includes('@'), '개인정보 모양이 섞이면 안 된다');
  for (const k of Object.keys(p)) assert.ok(String(p[k]).length <= 100, k + ' 길이 100 이하(GA4 매개변수 한도)');
}

// 한 페이지에서 web-vitals 가 여러 번 불러와지지 않는다
{
  const E = makeEnv();
  E.runTimers(); E.fireLoad(); E.runTimers();
  assert.strictEqual(vitalsScripts(E).length, 1);
}

console.log('rum inp contract OK');
