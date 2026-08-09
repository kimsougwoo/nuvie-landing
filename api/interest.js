'use strict';

const { randomUUID } = require('node:crypto');

const DEFAULT_ORIGIN = 'https://www.nuviestudio.com';
const DEFAULT_NOTION_VERSION = '2025-09-03';
const ROOMS = new Set(['A룸', 'B룸', '둘 다']);
const CHANNELS = { email: '이메일', phone: '문자', both: '이메일' };
const TOUCH_KEYS = [
  'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
  'gclid', 'fbclid', 'landing_path', 'referrer_origin', 'captured_at'
];

function clip(value, limit) {
  return String(value == null ? '' : value).trim().slice(0, limit);
}

function asBoolean(value) {
  return value === true || value === 'true' || value === 1 || value === '1';
}

function parseBody(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  if (typeof req.body !== 'string' || req.body.length > 32768) return null;
  try { return JSON.parse(req.body); } catch (e) { return null; }
}

function cleanTouch(touch) {
  if (!touch || typeof touch !== 'object') return null;
  const clean = {};
  TOUCH_KEYS.forEach((key) => {
    const value = clip(touch[key], key === 'captured_at' ? 40 : 120);
    if (value) clean[key] = value;
  });
  return Object.keys(clean).length ? clean : null;
}

function cleanAttribution(value) {
  if (!value || typeof value !== 'object') return { first: null, last: null };
  return {
    first: cleanTouch(value.first_touch || value.first),
    last: cleanTouch(value.last_touch || value.last),
    first_visit_at: clip(value.first_visit_at, 40),
    last_visit_at: clip(value.last_visit_at, 40),
    last_referrer_origin: clip(value.last_referrer_origin, 120)
  };
}

function sourceName(attribution) {
  const first = attribution.first || {};
  if (first.utm_source) return clip(first.utm_source, 80);
  if (first.referrer_origin) {
    try { return clip(new URL(first.referrer_origin).hostname, 80); } catch (e) {}
  }
  return 'direct';
}

function richText(value) {
  const text = clip(value, 1900);
  return text ? { rich_text: [{ type: 'text', text: { content: text } }] } : undefined;
}

function buildNotionProperties(input, now, leadId) {
  const attribution = cleanAttribution(input.attribution);
  const contact = input.email ? 'email' : input.phone ? 'phone' : 'both';
  const properties = {
    '리드ID': { title: [{ type: 'text', text: { content: leadId } }] },
    '룸 관심': { select: { name: input.room } },
    '상태': { select: { name: '신규' } },
    '개인정보처리방침 동의': { checkbox: true },
    '광고성 정보 동의': { checkbox: asBoolean(input.marketing_consent) },
    '동의시각': { date: { start: now } },
    '최초 유입시각': { date: { start: attribution.first_visit_at || now } },
    '최근 유입시각': { date: { start: attribution.last_visit_at || now } },
    '첫 유입 소스': { rich_text: [{ type: 'text', text: { content: sourceName(attribution) } }] },
    '수신 채널': { select: { name: CHANNELS[contact] } }
  };

  if (input.email) properties['이메일'] = { email: input.email };
  if (input.phone) properties['전화번호'] = { phone_number: input.phone };
  const utm = JSON.stringify({ first: attribution.first, last: attribution.last, referrer: attribution.last_referrer_origin || '' });
  const utmProperty = richText(utm);
  const inquiryProperty = richText(input.inquiry);
  if (utmProperty) properties['원본 UTM'] = utmProperty;
  if (inquiryProperty) properties['문의내용'] = inquiryProperty;
  return properties;
}

function reply(res, status, body) {
  if (typeof res.status === 'function' && typeof res.json === 'function') return res.status(status).json(body);
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  return res.end(JSON.stringify(body));
}

function originOf(req) {
  return (req.headers && (req.headers.origin || req.headers.Origin)) || '';
}

function vercelOrigin(name) {
  const value = process.env[name];
  if (!value) return '';
  return (value.startsWith('http://') || value.startsWith('https://') ? value : `https://${value}`).replace(/\/$/, '');
}

function allowedOrigin(origin) {
  const configured = process.env.NUVIE_SITE_ORIGIN || DEFAULT_ORIGIN;
  const runtimeOrigins = [
    vercelOrigin('VERCEL_URL'),
    vercelOrigin('VERCEL_BRANCH_URL'),
    vercelOrigin('VERCEL_PROJECT_PRODUCTION_URL')
  ].filter(Boolean);
  return !origin || origin === configured || runtimeOrigins.includes(origin) || origin === 'http://localhost:3000' || origin === 'http://127.0.0.1:3000';
}

module.exports = async function interestHandler(req, res) {
  const origin = originOf(req);
  if (!allowedOrigin(origin)) return reply(res, 403, { ok: false, error: 'forbidden origin' });
  if (origin) res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Vary', 'Origin');
  res.setHeader('Cache-Control', 'no-store');

  if (req.method === 'OPTIONS') {
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    res.statusCode = 204;
    return res.end();
  }
  if (req.method !== 'POST') return reply(res, 405, { ok: false, error: 'method not allowed' });

  const input = parseBody(req);
  if (!input || typeof input !== 'object') return reply(res, 400, { ok: false, error: 'invalid request' });
  if (clip(input.website, 40)) return reply(res, 400, { ok: false, error: 'invalid request' });
  if (!asBoolean(input.privacy_consent)) return reply(res, 400, { ok: false, error: 'privacy consent required' });

  const room = clip(input.room, 20);
  const email = clip(input.email, 254).toLowerCase();
  const phone = clip(input.phone, 40).replace(/[\s().-]/g, '');
  const inquiry = clip(input.inquiry, 1000);
  const emailValid = !email || /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email);
  const phoneValid = !phone || /^\+?\d{9,15}$/.test(phone);
  if (!ROOMS.has(room) || !emailValid || !phoneValid || (!email && !phone)) {
    return reply(res, 400, { ok: false, error: 'invalid contact or room' });
  }

  const token = process.env.NOTION_TOKEN;
  const dataSourceId = process.env.NOTION_CRM_DATA_SOURCE_ID;
  if (!token || !dataSourceId) return reply(res, 503, { ok: false, error: 'submission unavailable' });

  const now = new Date().toISOString();
  const leadId = `WEB-${randomUUID()}`;
  const notionBody = {
    parent: { type: 'data_source_id', data_source_id: dataSourceId },
    properties: buildNotionProperties({ ...input, room, email, phone, inquiry }, now, leadId)
  };

  try {
    const response = await fetch('https://api.notion.com/v1/pages', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Notion-Version': process.env.NOTION_VERSION || DEFAULT_NOTION_VERSION
      },
      body: JSON.stringify(notionBody)
    });
    if (!response.ok) throw new Error('notion write failed');
  } catch (e) {
    // Never log the request body: it contains contact information.
    return reply(res, 502, { ok: false, error: 'submission failed' });
  }

  return reply(res, 200, { ok: true });
};
