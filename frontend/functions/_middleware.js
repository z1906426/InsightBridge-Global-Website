/**
 * Canonical-host middleware — 301 www → apex.
 *
 * Cloudflare Pages serves every custom domain attached to the project, so
 * www.insightbridge.global and insightbridge.global both served full content
 * (duplicate URLs, canonical tag was the only dedup signal). This middleware
 * enforces the canonical host at the edge: www requests get a single-hop 301
 * to the apex domain with path + query preserved and https forced.
 *
 * All other hosts pass through untouched — static assets and the /api/*
 * functions (polaris, headlines) are unaffected.
 */
export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (url.hostname === 'www.insightbridge.global') {
    url.protocol = 'https:';
    url.hostname = 'insightbridge.global';
    return Response.redirect(url.toString(), 301);
  }
  return context.next();
}
