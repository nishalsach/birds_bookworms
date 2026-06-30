#!/usr/bin/env python3
# Builds acl-2026-poster-v8.svg/pdf from acl-2026-poster-v7.svg:
#   - Removes the drop shadow filter from the blue title text
#   - Adds a hairline black stroke outline to the blue title glyphs instead
#     (paint-order="stroke" keeps the stroke outside the fill so letterforms stay clean)
import re, os, sys

ROOT = "/Users/jackb/GitHub/birds_bookworms/eval-eval-acl-poster"
SRC  = os.path.join(ROOT, "full-poster/acl-2026-poster-v7.svg")
OUT  = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "full-poster/acl-2026-poster-v8.svg")

with open(SRC) as f:
    content = f.read()

# ── 1. Remove the filter wrapper around the blue title path ────────────────
# Structure: <g filter="url(#filter0_d_0_1)">\n<path ... fill="#45AEE7"...>\n</g>
# Unwrap the <g> so the path stands alone, then add stroke to the path.

content = re.sub(
    r'<g filter="url\(#filter0_d_0_1\)">\n(<path [^\n]*fill="#45AEE7"[^\n]*>?)\n</g>',
    r'\1',
    content,
)

# ── 2. Add hairline stroke to the blue title path ──────────────────────────
# paint-order="stroke" paints stroke first so the fill covers the inner half,
# giving a clean outer outline without eating into the letter shapes.
content = re.sub(
    r'(<path [^\n]*fill="#45AEE7")',
    r'\1 stroke="black" stroke-width="0.4" paint-order="stroke"',
    content,
    count=1,
)

# ── 3. Remove the now-unused filter0_d_0_1 definition ─────────────────────
content = re.sub(
    r'<filter id="filter0_d_0_1"[^>]*>.*?</filter>\n?',
    '',
    content,
    flags=re.DOTALL,
)

with open(OUT, 'w') as f:
    f.write(content)

print(f"Wrote {OUT}  ({os.path.getsize(OUT):,} bytes)")
