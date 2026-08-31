// Canonical-URL middleware for insightbridge.global.
//
// The whole site — navigation, <link rel="canonical">, og:url and
// sitemap.xml — uses ".html" URLs as the canonical form. Cloudflare
// Pages' built-in pretty-URL behavior 308-redirects "/foo.html" → "/foo",
// which left every canonical signal pointing at a redirecting URL
// (Naver/Google/Baidu guidelines: the canonical URL must serve content
// directly, not redirect).
//
// This middleware serves ".html" URLs directly with 200 by internally
// resolving the corresponding pretty URL against the static assets,
// keeping the outward URL unchanged.
//
// Exempt: search-engine verification files (codeva-*, naver*) have
// dedicated route Functions that must return their exact-URL 200 — pass
// those through untouched.

const VERIFY_FILE = /^\/(codeva-|naver)[^/]*\.html$/;

export async function onRequest(context) {
  const url = new URL(context.request.url);
  const p = url.pathname;

  if (VERIFY_FILE.test(p)) {
    return context.next();
  }

  if (p.endsWith("/index.html")) {
    const pretty = p.slice(0, -"index.html".length); // keeps trailing "/"
    return context.next(
      new Request(new URL(pretty + url.search, url), context.request)
    );
  }

  if (p.endsWith(".html")) {
    const pretty = p.slice(0, -".html".length);
    return context.next(
      new Request(new URL(pretty + url.search, url), context.request)
    );
  }

  return context.next();
}
