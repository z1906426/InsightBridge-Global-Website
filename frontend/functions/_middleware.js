// Canonical-URL middleware for insightbridge.global.
//
// 2026-09-06: canonical form flipped from ".html" to extensionless pretty URLs.
// Previously the site used ".html" as canonical and this middleware served those
// URLs directly with 200 (because Cloudflare Pages natively 308-redirects
// "/foo.html" → "/foo", which would have made the canonical URL redirect).
//
// New behavior:
//   1. hostname normalization — anything other than the apex (www., the
//      *.pages.dev preview domain, etc.) 301-redirects to insightbridge.global,
//      so analytics/SEO stop being split across host variants.
//   2. "/foo.html" → 301 → "/foo" and "/index.html" → 301 → "/".
//   3. Everything else passes through (Pages serves pretty URLs natively).
//
// Exempt: search-engine verification files (codeva-*, naver*) have dedicated
// route Functions that must return their exact-URL 200 — pass those through
// untouched, but only AFTER the apex hostname check.

const VERIFY_FILE = /^\/(codeva-|naver)[^/]*\.html$/;

export async function onRequest(context) {
  const url = new URL(context.request.url);

  // 1. Hostname normalization (apex only).
  if (url.hostname !== "insightbridge.global") {
    url.hostname = "insightbridge.global";
    return Response.redirect(url.toString(), 301);
  }

  const p = url.pathname;

  // 2. Verification files must be served at their exact .html URL.
  if (VERIFY_FILE.test(p)) {
    return context.next();
  }

  // 3. /index.html → / (directory root).
  if (p.endsWith("/index.html")) {
    const pretty = p.slice(0, -"index.html".length); // keeps trailing "/"
    return Response.redirect(new URL(pretty + url.search, url).toString(), 301);
  }

  // 4. /foo.html → /foo.
  if (p.endsWith(".html")) {
    const pretty = p.slice(0, -".html".length);
    return Response.redirect(new URL(pretty + url.search, url).toString(), 301);
  }

  return context.next();
}
