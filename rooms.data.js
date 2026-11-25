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
      "freeEquipment": [
        "지속광 3대",
        "순간광 2대(동조기 포함)",
        "모디파이어 7종",
        "스탠드 7대",
        "붐암 1개",
        "스모그머신(무료)"
      ],
      "equipmentFees": [
        {
          "label": "FC-60B 세트",
          "amount": 10000
        },
        {
          "label": "파보튜브 15C",
          "amount": 10000
        },
        {
          "label": "브이플랫(1대·A·B 공용)",
          "amount": 5000
        }
      ],
      "equipmentTotalMax": 25000
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
      "freeEquipment": [
        "지속광 1대",
        "순간광 2대(동조기 포함)",
        "사각 소프트박스",
        "팔각 소프트박스",
        "스탠드 5대"
      ],
      "equipmentFees": [
        {
          "label": "브이플랫(1대·A·B 공용)",
          "amount": 5000
        }
      ],
      "equipmentTotalMax": 5000
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
