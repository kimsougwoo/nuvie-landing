/* Bottom booking bar "fastest free slot" label (2026-09-30 owner decision, relayed by 9a).
   Used by the hub (index.html: #book-mobile A, #book-mobile-b B) and room pages (.sticky-book a[data-book], /a and /b).
   Same data as the calendar: /availability.json events (booking and block both count as busy).
   - DAY_START 9: no dawn starts. Policy (ops v1.3 sec 0/2, price v6 sec 5) allows 24h booking with no hour limit, so the
     cut comes from real data (booking log 138 rows, 126 non-cancelled: zero starts at 1-7h, 0-8h starts = A 5 rows, 2 paid)
     and the 09-30 owner rule that groups 0:00-8:59 starts as dawn (door code sent the evening before).
   - LAST_START 21: latest paid start in the same booking log is 21h (the two 22h starts are both 0-won rows),
     so later starts are not shown even though a 2h slot could end by 24h.
   - HORIZON_DAYS 14: well inside the 120 days build_availability.py fetches; beyond it the default label stays.
   No free slot, bad data or no data -> the original label (never claim a slot we cannot see). hrefs/ids/tracking untouched. */
(function(w){
  var DAY_START = 9, LAST_START = 21, MIN_H = 2, HORIZON_DAYS = 14;
  var DOW = ['일', '월', '화', '수', '목', '금', '토'];

  w.nvFirstFree = function(events, nowMs, room){
    if (!Array.isArray(events) || typeof nowMs !== 'number' || !isFinite(nowMs)) return null;
    var k = new Date(nowMs + 9 * 3600 * 1000);
    var nowH = k.getUTCHours() + k.getUTCMinutes() / 60 + k.getUTCSeconds() / 3600;
    for (var i = 0; i < HORIZON_DAYS; i++){
      var d = new Date(Date.UTC(k.getUTCFullYear(), k.getUTCMonth(), k.getUTCDate() + i));
      var day = d.toISOString().slice(0, 10);
      var busy = [];
      for (var j = 0; j < events.length; j++){
        var e = events[j];
        if (!e || e.room !== room || e.date !== day) continue;
        var s = Number(e.start), t = Number(e.end);
        if (!isFinite(s) || !isFinite(t)) return null;
        busy.push([s, t]);
      }
      var h = i === 0 ? Math.max(DAY_START, Math.ceil(nowH)) : DAY_START;
      for (; h <= LAST_START; h++){
        var clash = false;
        for (var b = 0; b < busy.length; b++){
          if (busy[b][0] < h + MIN_H && busy[b][1] > h){ clash = true; break; }
        }
        if (!clash) return {date: day, hour: h, offset: i, dow: d.getUTCDay()};
      }
    }
    return null;
  };

  w.nvFreeText = function(slot){
    if (!slot) return null;
    if (slot.offset === 0) return '오늘 ' + slot.hour + '시';
    if (slot.offset === 1) return '내일 ' + slot.hour + '시';
    var p = slot.date.split('-');
    return Number(p[1]) + '/' + Number(p[2]) + '(' + DOW[slot.dow] + ') ' + slot.hour + '시';
  };

  w.nvApplyFreeLabel = function(a, label, room, events, nowMs){
    if (!a) return;
    if (a.dataset.nvDefault === undefined){
      a.dataset.nvDefault = a.textContent;
      a.dataset.nvAria = a.getAttribute('aria-label') || '';
    }
    var t = w.nvFreeText(w.nvFirstFree(events, nowMs, room));
    if (!t){
      a.textContent = a.dataset.nvDefault;
      if (a.dataset.nvAria) a.setAttribute('aria-label', a.dataset.nvAria);
      else if (a.removeAttribute) a.removeAttribute('aria-label');
      a.classList.toggle('wk2', false);
      return;
    }
    a.textContent = '';
    var l1 = document.createElement('span'); l1.className = 'fl1'; l1.textContent = label + ' 예약 · 빠른 빈 시간';
    var l2 = document.createElement('span'); l2.className = 'fl2'; l2.textContent = t + ' →';
    a.appendChild(l1); a.appendChild(l2);
    a.setAttribute('aria-label', label + ' 예약, 가장 빠른 빈 시간 ' + t + ' — 아워플레이스로 이동');
    a.classList.toggle('wk2', true);
  };

  w.nvApplyFreeLabels = function(events){
    if (typeof document === 'undefined') return;
    var now = Date.now();
    w.nvApplyFreeLabel(document.getElementById('book-mobile'), 'A룸', 'A', events, now);
    w.nvApplyFreeLabel(document.getElementById('book-mobile-b'), 'B룸', 'B', events, now);
    var rs = document.querySelectorAll('.sticky-book a[data-book]');
    for (var i = 0; i < rs.length; i++){
      var room = String(rs[i].getAttribute('data-book') || '').toUpperCase();
      if (room === 'A' || room === 'B') w.nvApplyFreeLabel(rs[i], room + '룸', room, events, now);
    }
  };

  // Room pages do not load the calendar, so they fetch the same file here. The hub calls nvApplyFreeLabels after its own fetch.
  if (typeof document !== 'undefined' && typeof fetch === 'function' && document.querySelector('.sticky-book a[data-book]')){
    fetch('/availability.json', {cache: 'no-store'})
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(d){ if (d && Array.isArray(d.events)) w.nvApplyFreeLabels(d.events); })
      .catch(function(){});
  }
})(window);
