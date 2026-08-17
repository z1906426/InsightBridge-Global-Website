/**
 * InsightBridge × WeCom — Two-Layer Visitor Intelligence
 * =========================================================
 * Layer 1 · OAuth2 identity   — silently identifies who is viewing
 * Layer 2 · Behaviour tracker — pushes WeCom notifications to owner
 *
 * Only activates inside WeCom / WeChat browser.
 * Zero effect on regular desktop/mobile visitors.
 */

(function () {
  'use strict';

  var API_BASE = 'https://intelligence.insightbridge.global/api/wecom';

  /* ── Detect WeCom / WeChat browser ───────────────────────────────────── */
  var ua = navigator.userAgent || '';
  var isWecom  = /wxwork/i.test(ua);
  var isWechat = /micromessenger/i.test(ua);
  if (!isWecom && !isWechat) return;   // not in WeCom/WeChat — do nothing

  /* ── Read identity from URL params (set after OAuth2 redirect) ──────── */
  var identity = {};
  (function parseParams() {
    var qs = location.search.slice(1).split('&');
    qs.forEach(function (p) {
      var kv = p.split('=');
      if (kv[0] && kv[0].startsWith('wc_')) {
        identity[kv[0].slice(3)] = decodeURIComponent(kv[1] || '');
      }
    });
  })();

  var hasIdentity = !!identity.userid;

  /* ── Layer 1 · OAuth2 — trigger if no identity yet ─────────────────── */
  function startOAuth() {
    var returnUrl = encodeURIComponent(location.origin + location.pathname);
    location.href = API_BASE + '/oauth2/start?return_url=' + returnUrl;
  }

  if (!hasIdentity) {
    setTimeout(startOAuth, 1500);
    return;
  }

  /* ── Layer 2 · Behaviour tracker ───────────────────────────────────── */
  function sendEvent(eventType, label, url) {
    var payload = {
      visitor_name:    identity.name    || '访客',
      visitor_company: identity.company || '',
      event_type:      eventType,
      label:           label,
      url:             url || location.href,
    };
    fetch(API_BASE + '/track', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
      keepalive: true,
    }).catch(function () {});
  }

  /* — Initial page view ───────────────────────────────────────────────── */
  sendEvent('page_view', document.title || location.pathname);

  /* — SPA section navigation ─────────────────────────────────────────── */
  var lastHash = location.hash;
  var sectionNames = {
    '#home':         'Home — InsightBridge',
    '#news':         'News — 新闻动态',
    '#about':        'About — 关于我们',
    '#framework':    'Framework — 管理框架',
    '#ai-model':     'AI Models',
    '#publications': 'Publications — 出版研究',
    '#cases':        'Case Studies',
    '#tourism':      'Tourism Strategy',
    '#intelligence': 'Intelligence — 全球洞察',
    '#tools':        'Tools — AI Calculators',
    '#contact':      'Contact',
  };
  window.addEventListener('hashchange', function () {
    var h = location.hash;
    if (h !== lastHash) {
      lastHash = h;
      sendEvent('page_view', sectionNames[h] || h);
    }
  });

  /* — External article / publication clicks ───────────────────────────── */
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[href]');
    if (!a) return;
    var href = a.href || '';
    var text = (a.textContent || '').trim().slice(0, 80);
    if (/hospitalitynet|researchgate|ssrn|scholar\.google|skift|phocuswire/i.test(href)) {
      sendEvent('article_read', text || href, href);
    } else if (/\.(pdf|html)$/i.test(href) && href.includes('insightbridge')) {
      sendEvent('article_read', text || href, href);
    } else if (a.classList.contains('hero__cta') || /launch|demo|contact|get in touch/i.test(text)) {
      sendEvent('cta_click', text || href, href);
    }
  }, true);

  /* — OTA Calculator interaction ──────────────────────────────────────── */
  ['otac-adr','otach-adr','otaci-adr'].forEach(function (id) {
    var el = document.getElementById(id);
    if (!el) return;
    var fired = false;
    el.addEventListener('change', function () {
      if (!fired) { fired = true; sendEvent('calculator_used', 'OTA True Cost Calculator'); }
    });
  });

  /* — POLARIS Calculator (iframe postMessage) ────────────────────────────── */
  window.addEventListener('message', function (evt) {
    if (evt.data && evt.data.type === 'POLARIS_CALC_INTERACTION') {
      sendEvent('calculator_used', 'POLARIS v2.0 Pricing Calculator');
    }
  });

})();
