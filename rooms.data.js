/* 생성 파일 — 고치지 말 것. 값은 rooms.json, 생성은 build_rooms.py */
window.NUVIE = window.NUVIE || {};
window.NUVIE.rooms = {
  "a": {
    "slug": "a",
    "label": "A룸",
    "name": "동양풍 & 블랙 호리존",
    "placeId": 61823,
    "availabilityKey": "A",
    "pricing": {
      "weekday": 40000,
      "weekend": 45000,
      "minHours": 2,
      "unit": "hour",
      "currency": "KRW",
      "taxIncluded": true,
      "baseGuests": 4,
      "extraGuestPerHour": 5500,
      "weekendDefinition": "토·일·공휴일",
      "accessoryFeePerItem": 10000
    },
    "capacity": {
      "min": 1,
      "max": 4
    },
    "status": "open"
  },
  "b": {
    "slug": "b",
    "label": "B룸",
    "name": "화이트 티타임 카페",
    "placeId": 62341,
    "availabilityKey": "B",
    "pricing": {
      "weekday": 40000,
      "weekend": 45000,
      "minHours": 2,
      "unit": "hour",
      "currency": "KRW",
      "taxIncluded": true,
      "baseGuests": 4,
      "extraGuestPerHour": 5500,
      "weekendDefinition": "토·일·공휴일",
      "accessoryFeePerItem": 10000
    },
    "capacity": {
      "min": 1,
      "max": 4
    },
    "status": "open"
  }
};
window.NUVIE.fulfillment = {
  "mode": "external",
  "provider": "hourplace",
  "note": "예약·결제·정산 전부 아워플레이스. 자사 결제는 흑자 게이트 통과 후 PortOne V2."
};
