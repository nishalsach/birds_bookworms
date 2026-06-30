#!/usr/bin/env python3
# Builds acl-2026-poster-v7.svg/pdf from acl-2026-poster-v6.svg:
#   - Replaces embedded example-bias-prompts table with the re-rendered version
#     (wider Reference column so "Nangia, Mania & Bhalerao, EMNLP 2020" fits on one line)
#   - Strengthens the drop shadow on the blue title text at the top
#     (was stdDeviation=0.5, offset=0.5/1 — barely visible; now 2.5 / 1.5,2)
import re, os, sys

ROOT = "/Users/jackb/GitHub/birds_bookworms/eval-eval-acl-poster"
SRC  = os.path.join(ROOT, "full-poster/acl-2026-poster-v6.svg")
ASSET = os.path.join(ROOT, "example-bias-prompts.svg")
OUT  = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "full-poster/acl-2026-poster-v7.svg")

with open(SRC) as f:
    lines = f.readlines()

# ── 1. Locate the table region ─────────────────────────────────────────────
# Structure in v6:
#   L6073  <g filter="url(#filter1_d_0_1)">
#   L6074  <rect x="432" y="208" width="464" height="172" fill="white"/>
#   L6075  <g transform="translate(432,209) scale(...)" fill="#1A1A1A">   ← old table
#   ...
#   L10443 </g>                                                            ← closes L6075
#   L10444 <use xlink:href="#image0_0_1" .../>                            ← iceberg (keep)
#   L10445 </g>                                                            ← closes L6073

TABLE_OPEN_RE  = re.compile(r'<g transform="translate\(432,209\) scale\([^)]+\)" fill="#1A1A1A">')
WHITE_RECT_RE  = re.compile(r'<rect x="432" y="208" width="464" height="172" fill="white"/>')

table_open_line  = None  # 0-indexed line of old table group open
table_close_line = None  # 0-indexed line of old table group close (</g>)
white_rect_line  = None

for i, line in enumerate(lines):
    if WHITE_RECT_RE.search(line):
        white_rect_line = i
    if TABLE_OPEN_RE.search(line):
        table_open_line = i
        # Walk forward to find the matching </g>
        depth = 1
        for j in range(i + 1, len(lines)):
            depth += lines[j].count('<g')
            depth -= lines[j].count('</g>')
            if depth <= 0:
                table_close_line = j
                break
        break

assert white_rect_line  is not None, "white rect not found"
assert table_open_line  is not None, "old table group not found"
assert table_close_line is not None, "old table group close not found"

print(f"Table: white_rect=L{white_rect_line+1}, open=L{table_open_line+1}, close=L{table_close_line+1}")

# ── 2. Build new table group ────────────────────────────────────────────────
# Box in poster: x0=432, y=208..380 (height 172)
# New SVG viewBox: 0 0 628.2 232.5333
# Scale to height-fit: 171 / 232.5333
TABLE_BOX = (432, 208, 896, 380)
bx0, by0 = TABLE_BOX[0], TABLE_BOX[1]

raw = open(ASSET).read()
raw = re.sub(r'<\?xml[^>]*\?>', '', raw)
raw = re.sub(r'<!DOCTYPE[^>]*>', '', raw, flags=re.S)
m = re.search(r'<svg\b[^>]*>', raw)
inner = raw[m.end():]
inner = re.sub(r'</svg>\s*$', '', inner)

s = 171.0 / 232.5333
white_rect = f'<rect x="{bx0}" y="{by0}" width="{TABLE_BOX[2]-bx0}" height="{TABLE_BOX[3]-by0}" fill="white"/>\n'
table_group = f'<g transform="translate({bx0},209) scale({s:.5f})" fill="#1A1A1A">{inner}</g>\n'

# ── 3. Strengthen the drop shadow on the blue title text ───────────────────
# Filter "filter0_d_0_1" was: feOffset dx=0.5 dy=1, feGaussianBlur stdDeviation=0.5, opacity=0.5
# Update to: feOffset dx=1.5 dy=2, feGaussianBlur stdDeviation=2.5, opacity=0.55

def patch_filter(content):
    # Target the specific filter by id
    pattern = re.compile(
        r'(<filter id="filter0_d_0_1"[^>]*>.*?'
        r'<feOffset )dx="[^"]*" dy="[^"]*"(.*?'
        r'<feGaussianBlur )stdDeviation="[^"]*"(.*?'
        r'<feColorMatrix [^/]*)values="[^"]*"',
        re.DOTALL
    )
    def replacer(m):
        return (m.group(1) + 'dx="1.5" dy="2"' +
                m.group(2) + 'stdDeviation="2.5"' +
                m.group(3) + 'values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.55 0"')
    patched, n = pattern.subn(replacer, content)
    print(f"Shadow filter patches: {n}")
    return patched

# ── 4. Assemble ────────────────────────────────────────────────────────────
# Replace white_rect_line through table_close_line with new content
new_lines = (
    lines[:white_rect_line] +
    [white_rect, table_group] +
    lines[table_close_line + 1:]
)
result = "".join(new_lines)
result = patch_filter(result)

with open(OUT, 'w') as f:
    f.write(result)

print(f"Wrote {OUT}  ({os.path.getsize(OUT):,} bytes)")
