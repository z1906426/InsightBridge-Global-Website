// Cloudflare Pages Function — GET /api/headlines?limit=7
// Ports backend/sister_articles.py: pull newest articles from the sister
// site's RSS feed for the main-site hero brief. Runs at the CF edge, so the
// brief keeps auto-updating on Pages (no FastAPI backend needed).

const SISTER_RSS = "https://intelligence.insightbridge.global/api/rss.xml?lang=en";

// Legacy hotel-vertical republications — kept live on the sister site's
// archive but excluded from the main-site hero brief (owner directive).
const EXCLUDED_FROM_BRIEF = new Set([
  "the-real-cost-of-bookingcom-five-practical-steps-for-southeast-asian-hotels",
  "when-the-crisis-comes-will-your-hotels-people-stay-or-go",
  "why-vision-2030-hotels-need-more-than-traditional-revenue-management",
  "ai-will-not-make-hotels-smarter-unless-managers-become-smarter-decision-makers",
  "ai-will-not-transform-hotels-until-it-changes-the-meeting",
  "saudi-arabias-next-hospitality-chapter-why-demand-is-not-enough-without-profitab",
]);

function slug(loc) {
  return loc.replace(/\/+$/, "").split("/").pop();
}

function unwrap(text) {
  if (!text) return "";
  const m = text.match(/<!\[CDATA\[([\s\S]*?)\]\]>/);
  return (m ? m[1] : text).trim();
}

function parseItems(xml) {
  const items = [];
  const blocks = xml.match(/<item\b[\s\S]*?<\/item>/gi) || [];
  for (const block of blocks) {
    const linkM = block.match(/<link>([\s\S]*?)<\/link>/i);
    if (!linkM) continue;
    const loc = unwrap(linkM[1]);
    if (!loc.includes("/articles/")) continue;
    if (EXCLUDED_FROM_BRIEF.has(slug(loc))) continue;

    const titleM = block.match(/<title>([\s\S]*?)<\/title>/i);
    const title = unwrap(titleM ? titleM[1] : "") || "(untitled)";

    // Prefer <dc:date> (ISO-8601) over <pubDate> (RFC-822)
    let published = null;
    const dcM = block.match(/<dc:date>([\s\S]*?)<\/dc:date>/i);
    const pubM = block.match(/<pubDate>([\s\S]*?)<\/pubDate>/i);
    const rawDate = unwrap(dcM ? dcM[1] : (pubM ? pubM[1] : ""));
    if (rawDate) {
      const d = new Date(rawDate);
      if (!isNaN(d.getTime())) published = d.toISOString();
    }
    items.push({ loc, title, published, _ts: published ? Date.parse(published) : 0 });
  }
  items.sort((a, b) => b._ts - a._ts);
  return items.map(({ _ts, ...rest }) => rest);
}

export async function onRequestGet(context) {
  const url = new URL(context.request.url);
  let limit = parseInt(url.searchParams.get("limit") || "7", 10);
  if (isNaN(limit)) limit = 7;
  limit = Math.min(Math.max(limit, 1), 20);

  try {
    const resp = await fetch(SISTER_RSS, {
      headers: { "User-Agent": "InsightBridge-Brief/1.0" },
      cf: { cacheTtl: 900, cacheEverything: true },
    });
    if (!resp.ok) throw new Error("rss " + resp.status);
    const xml = await resp.text();
    const items = parseItems(xml).slice(0, limit);
    return new Response(JSON.stringify({ count: items.length, items }), {
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "public, max-age=900",
      },
    });
  } catch (err) {
    // Non-200 → the homepage falls back to its static curated brief list.
    return new Response(JSON.stringify({ count: 0, items: [], error: String(err) }), {
      status: 502,
      headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  }
}
