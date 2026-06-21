#!/usr/bin/env python3
"""Generate iceberg-v3-{N}poly.svg: full iceberg scene matched to iceberg.jpg,
with the underwater mass fitted as N polygons (<=16 sides each).

Coordinates are the native photo space (1094x1197); iceberg-underwater.png shares
those dimensions, so the fitted underwater polygons land exactly where the berg
sits in the photo. Sky/ocean colors and the above-water silhouette are sampled /
traced from iceberg.jpg. Underwater polygons come from brightness bands of the
cutout, outer (dark edge) to inner (bright core)."""

import numpy as np
import cv2

CUTOUT = "iceberg-underwater.png"
OUTDIR = "/Users/jackb/GitHub/birds_bookworms/eval-eval-acl-poster/sandbox"
WL = 306                                   # waterline y in photo space

png = cv2.imread(CUTOUT, cv2.IMREAD_UNCHANGED)      # BGRA
H, W = png.shape[:2]
rgb = cv2.cvtColor(png[..., :3], cv2.COLOR_BGR2RGB).astype(np.float32)
alpha = png[..., 3].astype(np.float32) / 255.0
inside = alpha > 0.5
lum = cv2.GaussianBlur(rgb @ np.array([0.30, 0.59, 0.11], np.float32), (0, 0), 6)
lum[~inside] = 0.0

ys, xs = np.where(lum > np.percentile(lum[inside], 92))
core = (float(xs.mean()), float(ys.mean()))

# Above-water silhouette traced from iceberg.jpg (whiteness mask, simplified).
ABOVE = [(669, 209), (649, 216), (607, 170), (557, 150), (508, 226), (484, 230),
         (468, 197), (444, 188), (393, 274), (335, 305), (532, 305), (555, 278),
         (606, 275), (603, 223), (645, 251)]


def fit_polygon(mask, max_sides=16):
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(c) < 200:
        return None
    peri = cv2.arcLength(c, True)
    lo, hi = 0.001, 0.15
    for _ in range(40):
        eps = (lo + hi) / 2 * peri
        if len(cv2.approxPolyDP(c, eps, True)) > max_sides:
            lo = eps / peri
        else:
            hi = eps / peri
    return [(float(p[0][0]), float(p[0][1]))
            for p in cv2.approxPolyDP(c, hi * peri, True)]


def band_color(mask_bool):
    m = mask_bool & inside
    if m.sum() < 30:
        m = inside
    r, g, b = rgb[m].mean(axis=0).round().astype(int)
    return "#%02x%02x%02x" % (r, g, b)


def poly_str(pts):
    return " ".join("%.1f,%.1f" % p for p in pts)


lab = cv2.cvtColor(png[..., :3], cv2.COLOR_BGR2Lab).astype(np.float32)
OK = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
CK = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17))


DIL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (19, 19))


def background_layers(n_bg=4):
    """3-4 nested brightness silhouettes (dark edge -> mid core) drawn under the
    mosaic so any seams read as a smooth gradient instead of a hard gap."""
    lo, hi = np.percentile(lum[inside], 5), np.percentile(lum[inside], 72)
    layers = []
    ts = np.linspace(lo, hi, n_bg)
    for i, t in enumerate(ts):
        mask = (inside if i == 0 else ((lum >= t) & inside)).astype(np.uint8) * 255
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, OK)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, CK)
        pts = fit_polygon(mask)
        if not pts or len(pts) < 3:
            continue
        ring = (lum >= t) & (lum < ts[i + 1]) if i + 1 < n_bg else (lum >= t)
        layers.append((pts, band_color(ring)))
    return layers


def underwater_polys(n):
    """Partition the berg into N distinct regions via position-weighted k-means
    on color+location, then trace each (slightly enlarged) region as its own
    polygon. Nested background layers sit underneath for continuity. Different N
    (and a per-N seed) -> genuinely different splits, not nested copies."""
    iy, ix = np.where(inside)
    # features: spatial position + Lab color, separately weighted
    pos = np.stack([ix / W, iy / H], 1) * 2.2          # favor contiguous chunks
    col = np.stack([lab[iy, ix, 0] / 255,
                    lab[iy, ix, 1] / 255,
                    lab[iy, ix, 2] / 255], 1) * 1.0
    feat = np.hstack([pos, col]).astype(np.float32)

    k = max(1, n)                                       # n mosaic shapes
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    cv2.setRNGSeed(1000 + n)                            # vary the split per version
    _, labels, _ = cv2.kmeans(feat, k, None, crit, 4, cv2.KMEANS_PP_CENTERS)
    labels = labels.ravel()

    lab_img = np.full((H, W), -1, np.int32)
    lab_img[iy, ix] = labels

    out = background_layers()                           # continuity scaffold

    regions = []
    for c in range(k):
        mask = (lab_img == c).astype(np.uint8) * 255
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, OK)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, CK)
        # enlarge slightly (clamped to the silhouette) so neighbors overlap
        mask = cv2.dilate(mask, DIL) & (inside.astype(np.uint8) * 255)
        pts = fit_polygon(mask)
        if not pts or len(pts) < 3:
            continue
        m = (lab_img == c)
        r, g, b = rgb[m].mean(axis=0).round().astype(int)
        regions.append((cv2.contourArea(np.array(pts, np.float32)), pts,
                        "#%02x%02x%02x" % (r, g, b)))
    # large regions first so smaller bright facets land on top
    regions.sort(key=lambda z: -z[0])
    out += [(p, c) for _, p, c in regions]
    return out


def scene(n):
    polys = underwater_polys(n)
    cx, cy = core[0] / W * 100, (core[1] - WL) / (H - WL) * 100
    L = []
    a = L.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
      f'width="{W}" height="{H}">')
    a(f'  <!-- NOTICE: generated by an LLM (sandbox/gen_iceberg_v3.py). Full scene')
    a(f'       matched to iceberg.jpg; underwater mass fitted as {n} polygons')
    a(f'       (<=16 sides) from brightness bands of iceberg-underwater.png. -->')
    a('  <defs>')
    a('    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">')
    a('      <stop offset="0%" stop-color="#3a8cdf"/>'
      '<stop offset="55%" stop-color="#7dbfed"/>'
      '<stop offset="100%" stop-color="#9fcdf0"/>')
    a('    </linearGradient>')
    a('    <linearGradient id="sea" x1="0" y1="0" x2="0" y2="1">')
    a('      <stop offset="0%" stop-color="#0b377c"/>'
      '<stop offset="22%" stop-color="#0b2b6e"/>'
      '<stop offset="55%" stop-color="#0e1c44"/>'
      '<stop offset="100%" stop-color="#0d0c18"/>')
    a('    </linearGradient>')
    a('    <linearGradient id="ice" x1="0" y1="0.5" x2="1" y2="0.5">')
    a('      <stop offset="0%" stop-color="#bcd6ea"/>'
      '<stop offset="35%" stop-color="#eef6fc"/>'
      '<stop offset="60%" stop-color="#ffffff"/>'
      '<stop offset="100%" stop-color="#c4dcee"/>')
    a('    </linearGradient>')
    a(f'    <radialGradient id="glow" cx="{cx:.0f}%" cy="{cy:.0f}%" r="60%">')
    a('      <stop offset="0%" stop-color="#1f7fc8" stop-opacity="0.55"/>'
      '<stop offset="100%" stop-color="#0b2b6e" stop-opacity="0"/>')
    a('    </radialGradient>')
    a(f'    <clipPath id="below"><rect x="0" y="{WL}" width="{W}" '
      f'height="{H-WL}"/></clipPath>')
    a('  </defs>')
    a('')
    # sky + clouds
    a(f'  <rect x="0" y="0" width="{W}" height="{WL}" fill="url(#sky)"/>')
    a('  <g fill="white" opacity="0.30">')
    a('    <ellipse cx="150" cy="70" rx="180" ry="13"/>'
      '<ellipse cx="780" cy="86" rx="210" ry="15"/>')
    a('    <ellipse cx="940" cy="64" rx="120" ry="9"/>'
      '<ellipse cx="470" cy="116" rx="80" ry="7"/>')
    a('  </g>')
    # above-water iceberg
    a(f'  <polygon points="{poly_str([(float(x),float(y)) for x,y in ABOVE])}" '
      f'fill="url(#ice)"/>')
    a(f'  <ellipse cx="557" cy="160" rx="26" ry="14" fill="white" opacity="0.9"/>')
    # ocean + glow
    a(f'  <rect x="0" y="{WL}" width="{W}" height="{H-WL}" fill="url(#sea)"/>')
    a(f'  <rect x="0" y="{WL}" width="{W}" height="{H-WL}" fill="url(#glow)" '
      f'clip-path="url(#below)"/>')
    # underwater fitted polygons
    a(f'  <!-- {len(polys)} fitted polygons, outer (dark) to inner (bright) -->')
    a('  <g clip-path="url(#below)">')
    for p, c in polys:
        a('    <polygon points="%s" fill="%s"/>' % (poly_str(p), c))
    a('  </g>')
    # waterline
    a(f'  <rect x="0" y="{WL-4}" width="{W}" height="7" fill="#08284f" opacity="0.85"/>')
    a('  <g stroke="#9fd2ec" stroke-width="1.6" opacity="0.35">')
    a(f'    <line x1="40" y1="{WL+8}" x2="300" y2="{WL+8}"/>'
      f'<line x1="700" y1="{WL+6}" x2="1040" y2="{WL+6}"/>')
    a('  </g>')
    a('</svg>\n')
    path = "%s/iceberg-v3-%dpoly.svg" % (OUTDIR, n)
    with open(path, "w") as f:
        f.write("\n".join(L))
    print("wrote", path, "->", len(polys), "polygons")


for n in (5, 10, 15, 20, 25, 30):
    scene(n)
