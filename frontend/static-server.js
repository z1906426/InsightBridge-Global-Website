/* Tiny zero-dependency static file server for InsightBridge Global corporate site.
 * Serves /app/frontend/site/ on PORT (default 3000).
 * - Adds correct MIME types
 * - Falls back to /index.html for extensionless paths if a same-named .html exists
 * - 404 on missing files (no SPA rewrite — this is a multi-page static site)
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const ROOT = path.resolve(__dirname, 'site');
const PORT = parseInt(process.env.PORT, 10) || 3000;
const HOST = process.env.HOST || '0.0.0.0';

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.htm':  'text/html; charset=utf-8',
  '.css':  'text/css; charset=utf-8',
  '.js':   'application/javascript; charset=utf-8',
  '.mjs':  'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg':  'image/svg+xml',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif':  'image/gif',
  '.webp': 'image/webp',
  '.ico':  'image/x-icon',
  '.woff': 'font/woff',
  '.woff2':'font/woff2',
  '.ttf':  'font/ttf',
  '.otf':  'font/otf',
  '.eot':  'application/vnd.ms-fontobject',
  '.txt':  'text/plain; charset=utf-8',
  '.xml':  'application/xml; charset=utf-8',
  '.map':  'application/json; charset=utf-8',
  '.pdf':  'application/pdf',
};

function safeJoin(root, reqPath) {
  // prevent path traversal
  const decoded = decodeURIComponent(reqPath.split('?')[0]);
  const normalized = path.posix.normalize(decoded).replace(/^\/+/, '');
  const full = path.join(root, normalized);
  if (!full.startsWith(root)) return null;
  return full;
}

function send(res, code, headers, body) {
  res.writeHead(code, headers);
  if (body) res.end(body); else res.end();
}

function serveFile(filePath, res, reqMethod) {
  fs.stat(filePath, (err, stat) => {
    if (err || !stat) return send(res, 404, { 'Content-Type': 'text/plain' }, 'Not Found');
    if (stat.isDirectory()) {
      // try index.html
      return serveFile(path.join(filePath, 'index.html'), res, reqMethod);
    }
    const ext = path.extname(filePath).toLowerCase();
    const type = MIME[ext] || 'application/octet-stream';
    const headers = {
      'Content-Type': type,
      'Content-Length': stat.size,
      'Cache-Control': ext === '.html' ? 'public, max-age=60' : 'public, max-age=3600',
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'SAMEORIGIN',
      'Cross-Origin-Opener-Policy': 'same-origin',
      'Permissions-Policy': 'geolocation=(), microphone=(), camera=(), payment=(), usb=()',
      // SEO: explicitly tell crawlers everything is fair game
      'X-Robots-Tag': 'index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1',
      'Referrer-Policy': 'strict-origin-when-cross-origin',
    };
    // ─── PDF-specific headers (per AI-crawler optimization memo 2026-07-17) ───
    // 1) canonical Link header → tells AI crawlers where the article version lives
    // 2) Accept-Ranges → allows chunked / parallel downloads by AI indexers
    // 3) Access-Control-Allow-Origin → lets public AI-indexing pipelines fetch
    // 4) Cache-Control tuned for 30-day CDN caching without transformation
    if (ext === '.pdf') {
      headers['Link'] = '<https://intelligence.insightbridge.global/articles/2027-ai-global-hospitality-tourism-whitepaper-frontier-framework-frontier-market>; rel="canonical"';
      headers['Accept-Ranges'] = 'bytes';
      headers['Access-Control-Allow-Origin'] = '*';
      headers['Cache-Control'] = 'public, no-transform, must-revalidate, max-age=2592000';
    }
    if (reqMethod === 'HEAD') return send(res, 200, headers);
    res.writeHead(200, headers);
    fs.createReadStream(filePath).pipe(res);
  });
}

const server = http.createServer((req, res) => {
  const parsed = url.parse(req.url);
  let pathname = parsed.pathname || '/';

  // Health check for ingress
  if (pathname === '/healthz') {
    return send(res, 200, { 'Content-Type': 'text/plain' }, 'ok');
  }

  // Root → index.html
  if (pathname === '/' || pathname === '') {
    return serveFile(path.join(ROOT, 'index.html'), res, req.method);
  }

  const filePath = safeJoin(ROOT, pathname);
  if (!filePath) return send(res, 400, { 'Content-Type': 'text/plain' }, 'Bad Request');

  fs.stat(filePath, (err, stat) => {
    if (!err && stat) {
      return serveFile(filePath, res, req.method);
    }
    // Try with .html appended (clean URLs)
    const withHtml = filePath + '.html';
    fs.stat(withHtml, (err2, stat2) => {
      if (!err2 && stat2 && stat2.isFile()) {
        return serveFile(withHtml, res, req.method);
      }
      return send(res, 404, { 'Content-Type': 'text/plain' }, 'Not Found');
    });
  });
});

server.listen(PORT, HOST, () => {
  console.log(`[static-server] InsightBridge Global serving ${ROOT} on http://${HOST}:${PORT}`);
});
