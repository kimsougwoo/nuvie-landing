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
  // page 출처 파라미터(2026-08-04 감사 개선): 허브(index.html)의 book_click 과 이 페이지의
  // book_click 이 동일 이벤트라 이탈 출처가 안 갈렸다. room.template.html 의 <body data-room="{{SLUG}}">
  // 에서만 읽는다 — ⚠️ book_click 의 기존 파라미터(room·transport_type)·이벤트명은 절대 불변, page 는 "추가"만.
  var PAGE_ORIGIN = 'room_' + (document.body.getAttribute('data-room') || '');
  function clarityTag(key, value) {
    try {
      var safe = String(value || '').slice(0, 80);
      if (window.clarity && safe) window.clarity("set", key, safe);
    } catch (e) {}
  }
  /* ---------- 아워플레이스 이동 통일 계측 (2026-08-18 신설) ----------
   * 허브(index.html)의 hourplaceClick 과 «같은 이벤트명·같은 파라미터»로 맞춘다.
   * 왜 필요했나: 룸 페이지에서 나가는 클릭이 HourplaceClick 총량에서 통째로 빠져 있어,
   *   광고 소재 A/B 를 볼 때 «룸 페이지를 거쳐 나간 손님»만큼 과소계상됐다.
   *   소재별로 그 비율이 다르면 실제보다 나쁜 소재로 잘못 판정된다.
   * ⚠️ book_click 은 이름도 파라미터도 안 건드린다(광고 파일럿 사전등록 판독 지표) — «추가»만 한다.
   * 🔜 자사몰 전환(FF.mode='own') 후에는 아워 이동이 아니므로 발화하지 않는다. */
  function hourplaceClick(room, dest, where) {
    var u = { utm_source: 'direct', utm_medium: 'none', utm_campaign: 'none', utm_content: 'none' };
    try {
      if (window.NUVIE_ATTRIBUTION && window.NUVIE_ATTRIBUTION.utmParams) u = window.NUVIE_ATTRIBUTION.utmParams();
    } catch (e) {}
    try {
      if (window.gtag) gtag('event', 'HourplaceClick', {
        room: room, destination_url: dest, button_location: where,
        utm_source: u.utm_source, utm_medium: u.utm_medium,
        utm_campaign: u.utm_campaign, utm_content: u.utm_content,
        transport_type: 'beacon'
      });
    } catch (e) {}
    clarityTag('event', 'HourplaceClick');
    clarityTag('button_location', where);
    clarityTag('utm_content', u.utm_content);
  }

  // 2026-09-30: 새 탭으로 나가는 예약 클릭은 계측을 «화면을 그린 뒤»로 늦춘다(내용·순서 불변, /b 는 동결이라 종전대로)
  //   — 규칙·예외는 attribution.js afterPaint 한 곳에 있다.
  function afterPaint(el, fn) {
    var A = window.NUVIE_ATTRIBUTION;
    if (A && A.afterPaint) A.afterPaint(el, fn); else fn();
  }
  function trackBook(room) {
    return function (ev) { afterPaint(ev && ev.currentTarget, function () {
      clarityTag('event', 'book_click');
      clarityTag('room', room);
      clarityTag('page', PAGE_ORIGIN);
      try {
        if (window.gtag) gtag('event', 'book_click', { room: room, transport_type: 'beacon', page: PAGE_ORIGIN });
        if (window.fbq) fbq('track', 'Lead', { room: room });
      } catch (e) {}
      try {
        if (NUVIE.isExternalBooking()) hourplaceClick(room, NUVIE.bookingUrl(room), 'room_page');
      } catch (e) {}
      try {
        var fbc = readCookie('_fbc'), fbp = readCookie('_fbp');
        if ((fbc || fbp) && window.gtag) {
          gtag('event', 'ad_capture', { fbc: fbc, fbp: fbp, room: room, transport_type: 'beacon' });
        }
      } catch (e) {}
    }); };
  }

  /* ---------- 히어로 CTA 계측(감사 개선 #2) ----------
   * 허브는 #hero-rooms·#hero-gallery 를 hero_cta_click 으로 계측하는데 룸 페이지 히어로엔 없었다.
   * 같은 이벤트명으로 맞춘다. book_click 과는 완전히 분리된 이벤트라 정의 오염이 없다. */
  function wireHeroCta(root) {
    root.querySelectorAll('#hero-gallery, #hero-rooms').forEach(function (el) {
      el.addEventListener('click', function () {
        clarityTag('event', 'hero_cta_click');
        clarityTag('placement', el.id);
        try { if (window.gtag) gtag('event', 'hero_cta_click', { target: el.id, transport_type: 'beacon' }); } catch (e) {}
      });
    });
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
    // 2026-09-17 P0: 룸 갤러리 사진 확대 라이트박스(모바일 dead_click) — 템플릿에 #reviewLightbox 있으면 배선.
    var lb=document.getElementById('reviewLightbox'), lbImg=document.getElementById('reviewLightboxImg'), lbClose=document.getElementById('reviewLightboxClose');
    if (lb && lbImg && lbClose) {
      var trig=null, prevOv='', lbTok=0;
      function openLb(src,el,alt){ trig=el||null; lbImg.src=src; lbImg.alt=alt||'사진 확대'; lb.style.display='flex'; prevOv=document.body.style.overflow; document.body.style.overflow='hidden'; try{lbClose.focus();}catch(e){} }
      // width/height 는 A룸 후기 확대(openReview)만 넣는다 — 닫을 때 지워 갤러리 확대에 남지 않게(/b 는 넣은 적이 없어 동작 동일)
      function closeLb(){ lbTok++; lb.style.display='none'; lbImg.src=''; lbImg.style.filter=''; lbImg.removeAttribute('width'); lbImg.removeAttribute('height'); document.body.style.overflow=prevOv; try{ if(trig) trig.focus(); }catch(e){} trig=null; }
      lb.addEventListener('click',function(e){ if(e.target===lb) closeLb(); });
      lbClose.addEventListener('click',closeLb);
      document.addEventListener('keydown',function(e){ if(e.key==='Escape'&&lb.style.display==='flex') closeLb(); });
      // 2026-09-29 UX 실측 U-07: /a 후기 사진은 <a target=_blank href=아워 CDN 원본> 이라 눌러도 사이트 안에서 안 커지고
      //   새 탭에 원본(최대 24.8MB)이 열렸다. 홈(index.html)과 같은 방식으로 이 페이지의 라이트박스로 연다 —
      //   reviews/img/map.json 의 thumb(흐린 자리표시)→full(축소 WebP)을 쓰고, 매핑이 없으면 원본으로 폴백한다.
      //   09-30 대표 지시로 /b 후기 사진도 같게(B룸 동결 중 이 항목만 해제). href 는 그대로라 JS 실패 시엔 종전대로 새 탭.
      if (/^[ab]$/.test(document.body.getAttribute('data-room') || '')) {
        var rvLinks = root.querySelectorAll('#reviews a[href^="https://img.hourplace.co.kr/"]');
        var rvOpenedAt = 0, rvMap = {};
        lb.addEventListener('click', function (e) {   // 로딩 중 «반응 없는 클릭» 이 곧바로 닫기로 처리되는 것 방지(홈과 동일 300ms)
          if (e.target === lb && Date.now() - rvOpenedAt < 300) e.stopImmediatePropagation();
        }, true);
        var openReview = function (a, e) {
          e.preventDefault();
          var href = a.getAttribute('href'), ent = rvMap[href] || {}, im = a.querySelector('img');
          var full = ent.full || href, thumb = ent.thumb || '';
          openLb(thumb || full, a, (im && im.alt) || '후기 사진 확대');
          // 2026-09-29: 흐린 미리보기가 확대본보다 작게 떴다가 커지며 튀던 것 — 원본 비율로 상자를 처음부터 최종 크기로
          if (ent.w && ent.h) { lbImg.width = ent.w; lbImg.height = ent.h; }
          rvOpenedAt = Date.now();
          if (thumb) {
            lbImg.style.filter = 'blur(6px)';
            var tok = lbTok, probe = new Image();
            var show = function () { if (tok !== lbTok) return; lbImg.src = full; lbImg.style.filter = ''; };
            probe.onload = function () { if (probe.decode) probe.decode().then(show, show); else show(); };
            probe.onerror = show;
            probe.src = full;
          }
        };
        Array.prototype.forEach.call(rvLinks, function (a) {
          a.addEventListener('click', function (e) { openReview(a, e); });
        });
        // 축소본 매핑은 늦게 와도 된다 — 도착하면 썸네일도 축소본으로 바꿔 원본 대용량을 덜 받는다(실패하면 원본 유지).
        fetch('reviews/img/map.json').then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { return {}; })
          .then(function (m) {
            rvMap = m || {};
            Array.prototype.forEach.call(rvLinks, function (a) {
              var ent = rvMap[a.getAttribute('href')], im = a.querySelector('img');
              if (ent && ent.thumb && im && im.getAttribute('src') !== ent.thumb) im.src = ent.thumb;
            });
          });
      }
      root.querySelectorAll('.gal img').forEach(function(img){
        img.tabIndex=0; img.setAttribute('role','button'); img.setAttribute('aria-label',(img.alt||'사진')+' 확대 보기'); img.style.cursor='zoom-in';
        function open(){ openLb(img.currentSrc||img.src,img,img.alt); try{ if(window.gtag) gtag('event','gallery_zoom',{src:(img.getAttribute('src')||'').slice(0,60),transport_type:'beacon'}); }catch(e){} }
        img.addEventListener('click',open);
        img.addEventListener('keydown',function(e){ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); open(); } });
      });
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

  /* 모바일 섹션 칩바(.nv-chipbar) 스티키 top 을 상단 헤더(.side) 높이로 맞춘다 — 허브(index.html)와 같은 방식.
   * 2026-09-29 UX 실측: /a 는 이 배선이 없어 칩바가 top:0 에 붙었고, 헤더(z-index 50)가 칩바(40)를 덮어
   *   스크롤 뒤에는 칩 대신 헤더 링크가 눌렸다(홈 상단 이동, 시나리오 9건). 🧊 /b 는 11/11 동결 → A룸 전용. */
  function wireChipbar() {
    if (document.body.getAttribute('data-room') !== 'a') return;
    var bar = document.querySelector('.nv-chipbar'), side = document.querySelector('.side');
    if (!bar || !side) return;
    var mq = window.matchMedia('(max-width:640px)');
    function set() { bar.style.top = mq.matches ? (Math.round(side.getBoundingClientRect().height) + 'px') : ''; }
    set();
    window.addEventListener('resize', set);
    window.addEventListener('load', set);
    if (mq.addEventListener) mq.addEventListener('change', set); else if (mq.addListener) mq.addListener(set);
    try { if (window.ResizeObserver) new ResizeObserver(set).observe(side); } catch (e) { /* 폰트 로드로 헤더 높이가 바뀌면 재계산 */ }
  }

  function init() {
    var root = document.getElementById('root') || document;
    wireChipbar();
    wireBooking(root);
    wireHeroCta(root);
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
