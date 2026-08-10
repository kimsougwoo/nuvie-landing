/* NUVIE WebMCP progressive enhancement
 *
 * 사람용 화면과 예약 흐름은 그대로 둔다.
 * WebMCP를 지원하는 브라우저/에이전트에만 읽기 도구를 등록한다.
 *
 * 안전 경계:
 * - 공개된 룸 메타데이터와 이름 없는 예약 블록만 반환한다.
 * - 결제·예약 확정·취소·환불·도어락·고객정보는 노출하지 않는다.
 * - 예약 준비 도구는 CTA를 화면에 표시하고 URL을 반환할 뿐, 외부 예약 페이지를 자동 제출/결제하지 않는다.
 */
(function () {
  'use strict';

  var NUVIE = (window.NUVIE = window.NUVIE || {});
  var ROOM_KEYS = ['a', 'b'];
  var VERSION = '2026-08-10';

  function asRoom(value) {
    var room = String(value || '').trim().toLowerCase();
    return room === 'a' || room === 'b' ? room : '';
  }

  function validDate(value) {
    var date = String(value || '').trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return '';
    var parsed = new Date(date + 'T00:00:00Z');
    if (isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== date) return '';
    return date;
  }

  function textResult(data, text) {
    return {
      content: [{ type: 'text', text: text || JSON.stringify(data) }],
      structuredContent: data
    };
  }

  function errorResult(code, message) {
    return textResult({ ok: false, error_code: code, message: message }, message);
  }

  function catalog() {
    var rooms = NUVIE.rooms || {};
    return ROOM_KEYS.map(function (key) {
      var room = rooms[key];
      if (!room) return null;
      var pricing = room.pricing || {};
      var capacity = room.capacity || {};
      return {
        room: key,
        label: room.label || (key.toUpperCase() + '룸'),
        name: room.name || '',
        status: room.status || 'unknown',
        capacity: { min: capacity.min || null, max: capacity.max || null },
        pricing: {
          weekday: pricing.weekday || null,
          weekend: pricing.weekend || null,
          unit: pricing.unit || 'hour',
          currency: pricing.currency || 'KRW',
          min_hours: pricing.minHours || null,
          base_guests: pricing.baseGuests || null,
          extra_guest_per_hour: pricing.extraGuestPerHour || null,
          tax_included: pricing.taxIncluded === true
        },
        booking_provider: (NUVIE.fulfillment || {}).provider || 'unknown'
      };
    }).filter(Boolean);
  }

  function bookingUrl(room) {
    var rooms = NUVIE.rooms || {};
    var data = rooms[room];
    if (!data) return '';
    if ((NUVIE.fulfillment || {}).mode === 'own') return '/book/' + room;
    if (!data.placeId) return '';
    return 'https://www.hourplace.co.kr/place/' + encodeURIComponent(String(data.placeId));
  }

  function listRooms() {
    var rooms = catalog();
    if (!rooms.length) return errorResult('catalog_unavailable', '룸 정본을 읽지 못했습니다. 예약 가능 여부를 추정하지 않습니다.');
    return textResult({
      ok: true,
      source: 'rooms.data.js',
      fulfillment: NUVIE.fulfillment || { mode: 'unknown', provider: 'unknown' },
      rooms: rooms
    }, rooms.map(function (room) {
      return room.label + ' — ' + room.name + ' · 평일 ' + room.pricing.weekday + '원/시간 · 최소 ' + room.pricing.min_hours + '시간';
    }).join('\n'));
  }

  function getAvailability(input) {
    input = input || {};
    var room = asRoom(input.room);
    var date = validDate(input.date);
    if (input.date && !date) return Promise.resolve(errorResult('invalid_date', '날짜는 YYYY-MM-DD 형식이어야 합니다.'));

    return fetch('/availability.json', { cache: 'no-store', headers: { Accept: 'application/json' } })
      .then(function (response) {
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.json();
      })
      .then(function (data) {
        if (!data || !Array.isArray(data.events)) throw new Error('invalid availability payload');
        var events = data.events.filter(function (event) {
          var sameRoom = !room || String(event.room || '').toLowerCase() === room;
          var sameDate = !date || event.date === date;
          return sameRoom && sameDate;
        }).map(function (event) {
          return {
            date: String(event.date || ''),
            start: Number(event.start),
            end: Number(event.end),
            room: String(event.room || '').toUpperCase()
          };
        });
        var result = {
          ok: true,
          source: '/availability.json',
          updated: data.updated || null,
          status: 'busy_blocks_only',
          room: room || null,
          date: date || null,
          busy_blocks: events,
          note: '이 데이터는 이름 없는 공개 예약 블록 참고값입니다. 빈 배열은 무료 확정이 아니며, 최종 가능 시간은 아워플레이스에서 확인해야 합니다.'
        };
        var scope = [room ? room.toUpperCase() + '룸' : '전체 룸', date || '요청 기간'];
        return textResult(result, scope.join(' · ') + ' 공개 예약 블록 ' + events.length + '건. 최종 가능 여부는 아워플레이스에서 확인하세요.');
      })
      .catch(function () {
        return errorResult('availability_unavailable', '예약현황을 불러오지 못했습니다. 무료로 추정하지 말고 아워플레이스에서 확인하세요.');
      });
  }

  function prepareBooking(input) {
    var room = asRoom(input && input.room);
    var rooms = catalog();
    var info = rooms.filter(function (item) { return item.room === room; })[0];
    if (!info) return errorResult('invalid_room', 'room 값은 a 또는 b여야 합니다.');

    // 현재 페이지에서 사람이 누를 CTA를 먼저 보여준다. 자동 외부 이동은 하지 않는다.
    try {
      var selector = '[data-book="' + room + '"]';
      var target = document.querySelector(selector);
      if (target) {
        target.setAttribute('data-agent-prepared', '1');
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        target.focus({ preventScroll: true });
        window.setTimeout(function () { target.removeAttribute('data-agent-prepared'); }, 2200);
      }
    } catch (e) {}

    var url = bookingUrl(room);
    return textResult({
      ok: true,
      action: 'prepare_only',
      room: room,
      label: info.label,
      booking_url: url || null,
      provider: info.booking_provider,
      requires_human_click: true,
      payment_started: false,
      reservation_confirmed: false
    }, info.label + ' 예약 버튼을 화면에 준비했습니다. 예약·결제 확정은 사용자가 버튼을 눌러 진행합니다.');
  }

  var TOOL_DEFINITIONS = [
    {
      name: 'nuvie_list_rooms',
      description: '누비 스튜디오의 공개 룸·가격·인원·예약 채널을 조회합니다. 읽기 전용이며 예약을 만들지 않습니다.',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      execute: function () { return listRooms(); }
    },
    {
      name: 'nuvie_get_availability',
      description: '이름이 제거된 공개 예약 블록을 조회합니다. room(a/b)와 date(YYYY-MM-DD)는 선택값입니다. 빈 결과를 무료 확정으로 해석하지 않습니다.',
      inputSchema: {
        type: 'object',
        properties: {
          room: { type: 'string', enum: ['a', 'b'], description: '조회할 룸. 생략하면 A룸·B룸 모두 조회합니다.' },
          date: { type: 'string', description: '조회할 날짜(YYYY-MM-DD). 생략하면 공개 데이터 전체를 조회합니다.' }
        },
        additionalProperties: false
      },
      execute: function (input) { return getAvailability(input); }
    },
    {
      name: 'nuvie_prepare_booking',
      description: '선택한 룸의 예약 CTA를 화면에 준비하고 예약 페이지 주소를 알려줍니다. 외부 이동·결제·예약 확정은 자동으로 하지 않으며 사용자의 최종 클릭이 필요합니다.',
      inputSchema: {
        type: 'object',
        properties: {
          room: { type: 'string', enum: ['a', 'b'], description: '예약을 준비할 룸(a 또는 b).' }
        },
        required: ['room'],
        additionalProperties: false
      },
      execute: function (input) { return Promise.resolve(prepareBooking(input)); }
    }
  ];

  var registered = [];
  var supported = !!(document && document.modelContext && typeof document.modelContext.registerTool === 'function');
  if (supported) {
    TOOL_DEFINITIONS.forEach(function (tool) {
      try {
        document.modelContext.registerTool({
          name: tool.name,
          description: tool.description,
          inputSchema: tool.inputSchema,
          execute: tool.execute
        });
        registered.push(tool.name);
      } catch (e) {}
    });
  }

  // 지원 브라우저가 아니어도 QA·문서화에서 현재 계약을 확인할 수 있는 읽기 전용 상태.
  window.NUVIE_WEBMCP = {
    version: VERSION,
    supported: supported,
    registered: registered,
    tools: TOOL_DEFINITIONS.map(function (tool) {
      return { name: tool.name, description: tool.description, inputSchema: tool.inputSchema };
    }),
    invoke: function (name, input) {
      var tool = TOOL_DEFINITIONS.filter(function (item) { return item.name === name; })[0];
      return tool ? tool.execute(input || {}) : Promise.resolve(errorResult('unknown_tool', '알 수 없는 NUVIE 도구입니다.'));
    }
  };
})();
