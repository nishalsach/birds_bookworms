#!/usr/bin/env python3
# Builds acl-2026-poster-v9.svg/pdf from acl-2026-poster-v8.svg:
#   - Adds hairline black stroke to the subtitle blue text
#     ("Feminine Tropes and Implicit Gender Bias in Large Language Models", L10441)
#     using the same treatment as the main title (unwrap filter group, add stroke)
#   - Removes the black border from the white poster card (stroke="black" -> stroke="none")
import re, os, sys

ROOT = "/Users/jackb/GitHub/birds_bookworms/eval-eval-acl-poster"
SRC  = os.path.join(ROOT, "full-poster/acl-2026-poster-v8.svg")
OUT  = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "full-poster/acl-2026-poster-v9.svg")

with open(SRC) as f:
    content = f.read()

# ── 1. Unwrap subtitle filter group and add stroke in one step ────────────
# Structure: <g filter="url(#filter2_d_0_1)">\n<path ... fill="#45AEE7"...>\n</g>
# Inject stroke attributes while unwrapping so we patch exactly the right path.
content = re.sub(
    r'<g filter="url\(#filter2_d_0_1\)">\n(<path [^\n]*fill="#45AEE7"[^\n]*?)(/?>)\n</g>',
    r'\1 stroke="black" stroke-width="0.4" paint-order="stroke"\2',
    content,
)

# Remove the now-unused filter2_d_0_1 definition
content = re.sub(
    r'<filter id="filter2_d_0_1"[^>]*>.*?</filter>\n?',
    '',
    content,
    flags=re.DOTALL,
)

# ── 2. Remove black border from white poster card ──────────────────────────
content = content.replace(
    'fill="white" stroke="black"',
    'fill="white" stroke="none"',
    1,
)

with open(OUT, 'w') as f:
    f.write(content)

print(f"Wrote {OUT}  ({os.path.getsize(OUT):,} bytes)")
