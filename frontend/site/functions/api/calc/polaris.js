// Cloudflare Pages Function — POST /api/calc/polaris
// Ports backend/calculators.py:compute_polaris. The 5 demand-driver weights
// are PROPRIETARY and stay in this edge Function — they are never shipped to
// the browser (identical protection to the old FastAPI endpoint).

// Order: cross_border, holiday_compression, weekend_effect,
//        ota_booking_pace, competitive_saturation
const POLARIS_WEIGHTS = [0.18, 0.16, 0.14, 0.12, 0.12];

function round2(n) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

export async function onRequestPost(context) {
  let payload;
  try {
    payload = await context.request.json();
  } catch {
    return json({ error: "invalid JSON body" }, 400);
  }

  const base = Math.max(0, num(payload.base));
  const ceil_ = Math.max(base, num(payload.ceiling));
  const occ = num(payload.occupancy) / 100.0;
  const maxUp = num(payload.max_uplift) / 100.0;
  const intensities = Array.isArray(payload.intensities) ? payload.intensities : [];
  if (intensities.length !== 5) {
    return json({ error: "intensities must have exactly 5 values" }, 400);
  }

  const wSum = POLARIS_WEIGHTS.reduce((a, b) => a + b, 0);
  let contrib = 0;
  for (let i = 0; i < 5; i++) {
    contrib += POLARIS_WEIGHTS[i] * (num(intensities[i]) / 100.0);
  }
  const demandIndex = wSum > 0 ? contrib / wSum : 0;

  const raw = base * (1.0 + maxUp * demandIndex);
  const rate = Math.min(Math.max(raw, base), ceil_);
  const hitCeiling = raw > ceil_ + 0.5;

  const trajectory = [];
  for (let i = 0; i <= 10; i++) {
    trajectory.push(round2(Math.min(base * (1.0 + maxUp * (i / 10.0)), ceil_)));
  }

  return json({
    rate: round2(rate),
    revpar: round2(rate * occ),
    hit_ceiling: hitCeiling,
    trajectory,
  });
}

function num(v) {
  const n = typeof v === "number" ? v : parseFloat(v);
  return isNaN(n) ? 0 : n;
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}
