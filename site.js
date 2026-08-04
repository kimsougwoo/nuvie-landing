/* 누비 스튜디오 — 룸 페이지(/a·/b) 공통 스크립트
 *
 * ⚠️ 허브(index.html)는 이 파일을 쓰지 않는다. 허브의 인라인 스크립트에는
 *    광고 파일럿 사전등록 지표(book_click)와 달력·후기 렌더가 얽혀 있어
 *    계측 연속성을 위해 손대지 않는다. 여기는 룸 페이지 전용 복제본이다.
 *
 * 🔜 PortOne V2 자사몰 전환 지점 = NUVIE.bookingUrl() 한 곳.
 *    지금은 rooms.json 의 catalog.fulfillment.mode='external' → 아워플레이스로 보낸다.
 *    자사 결제가 붙는 날 mode='own' 으로 바꾸면 /book/<slug> 로 넘어간다.
 *    ⇒ 예약 버튼 href 를 HTML 에 박지 말 것. data-book="a" 만 달면 여기서 채운다.
 */
(function () {
  'use strict';

  var NUVIE = (window.NUVIE = window.NUVIE || {});
  // ROOMS·FULFILLMENT 는 build_rooms.py 가 rooms.data.js 로 생성해 먼저 로드한다.
  var ROOMS = NUVIE.rooms || {};
  var FF = NUVIE.fulfillment || { mode: 'external', provider: 'hourplace' };

  /* ---------- 예약 목적지 (전환 스위치) ---------- */
  NUVIE.bookingUrl = function (slug) {
    var r = ROOMS[slug];
    if (!r) return '/';
    if (FF.mode === 'own') return '/book/' + slug;          // PortOne V2 체크아웃
    return 'https://www.hourplace.co.kr/place/' + r.placeId; // 현재: 아워플레이스 위탁
  };
  NUVIE.isExternalBooking = function () { return FF.mode !== 'own'; };

  /* ---------- 계측 ----------
   * 이벤트명·파라미터는 허브와 동일하게 맞춘다(GA4 custom dimension `room` 분해 유지).
   * book_click 정의는 광고 파일럿 판독 지표라 여기서도 넓히지 않는다. */
  function readCookie(name) {
    try {
      var m = document.cookie.match(
        new RegExp('(?:^|; )' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '=([^;]*)')
      );
      return m ? decodeURIComponent(m[1]) : '';
    } catch (e) { return ''; }
  }
  function trackBook(room) {
    return function () {
      try {
        if (window.gtag) gtag('event', 'book_click', { room: room, transport_type: 'beacon' });
        if (window.fbq) fbq('track', 'Lead', { room: room });
      } catch (e) {}
      try {
        var fbc = readCookie('_fbc'), fbp = readCookie('_fbp');
        if ((fbc || fbp) && window.gtag) {
          gtag('event', 'ad_capture', { fbc: fbc, fbp: fbp, room: room, transport_type: 'beacon' });
        }
      } catch (e) {}
    };
  }

  function wireBooking(root) {
    root.querySelectorAll('[data-book]').forEach(function (el) {
      var slug = el.getAttribute('data-book');
      if (!ROOMS[slug]) return;
      el.href = NUVIE.bookingUrl(slug);
      if (NUVIE.isExternalBooking()) {
        el.target = '_blank';
        el.rel = 'noopener';
      } else {
        el.removeAttribute('target');
      }
      el.addEventListener('click', trackBook(slug));
    });
  }

  /* ---------- 공통 UI (허브 동작과 동일) ---------- */
  function wireTheme() {
    var btn = document.getElementById('themeBtn');
    if (!btn) return;
    function setTheme(t) {
      document.body.setAttribute('data-theme', t);
      btn.textContent = (t === 'dark' ? '☀' : '☾');
      btn.setAttribute('aria-label', t === 'dark' ? '라이트 모드로 전환' : '다크 모드로 전환');
    }
    btn.addEventListener('click', function () {
      setTheme(document.body.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
    });
  }

  function wireImages(root) {
    root.querySelectorAll('img[data-fallback]').forEach(function (img) {
      function hide() { img.style.display = 'none'; }
      if (img.complete && img.naturalWidth === 0) hide();
      img.addEventListener('error', hide);
    });
    var ken = root.querySelector('img[data-ken]');
    if (ken && !(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches)) {
      ken.style.animation = 'nvKen 18s ease-out forwards';
    }
    var canHover = !window.matchMedia || window.matchMedia('(hover:hover)').matches;
    if (!canHover) return;
    root.querySelectorAll('img[data-zoom]').forEach(function (img) {
      var p = img.parentElement;
      p.addEventListener('mouseenter', function () { img.style.transform = 'scale(1.03)'; });
      p.addEventListener('mouseleave', function () { img.style.transform = 'none'; });
    });
  }

  function wireReveal(root) {
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion:reduce)').matches;
    var els = Array.prototype.slice.call(root.querySelectorAll('[data-reveal]'));
    function reveal(el) { el.style.opacity = '1'; el.style.transform = 'none'; }
    var supportsVT = !!(window.CSS && CSS.supports && CSS.supports('animation-timeline', 'view()'));
    if (reduce) { els.forEach(reveal); return; }
    if (supportsVT) { document.documentElement.classList.add('nv-vt'); return; }
    root.querySelectorAll('header,section').forEach(function (sec) {
      sec.querySelectorAll('[data-reveal]').forEach(function (el, i) {
        el.style.transitionDelay = Math.min(i * 70, 340) + 'ms';
      });
    });
    els.forEach(function (el) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(24px)';
      el.style.transition = 'opacity .8s cubic-bezier(.22,.61,.36,1), transform .8s cubic-bezier(.22,.61,.36,1)';
    });
    var vh = window.innerHeight || 800;
    els.forEach(function (el) { if (el.getBoundingClientRect().top < vh * 1.1) reveal(el); });
    try {
      var io = new IntersectionObserver(function (es) {
        es.forEach(function (e) { if (e.isIntersecting) { reveal(e.target); io.unobserve(e.target); } });
      }, { threshold: 0.08 });
      els.forEach(function (el) { io.observe(el); });
    } catch (e) { els.forEach(reveal); }
    setTimeout(function () { els.forEach(reveal); }, 1200);
  }

  function init() {
    var root = document.getElementById('root') || document;
    wireBooking(root);
    wireTheme();
    wireImages(root);
    wireReveal(root);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
