#!/usr/bin/env python3
# Builds acl-2026-poster-v10.svg/pdf from acl-2026-poster-v9.svg:
#   - Halves the left/right gray margin (15 -> 7.5) and matches top/bottom to it (21.01 -> 7.5)
#   Gray background:  x=11.5  y=-14.51  width=909  height=1285.14
#   Old white card:   x=26.5  y=6.5     width=879  height=1243.12   (margins: 15 lr, 21.01 tb)
#   New white card:   x=19    y=-7.01   width=894  height=1270.14   (margins: 7.5 all)
import os, sys

ROOT = "/Users/jackb/GitHub/birds_bookworms/eval-eval-acl-poster"
SRC  = os.path.join(ROOT, "full-poster/acl-2026-poster-v9.svg")
OUT  = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "full-poster/acl-2026-poster-v10.svg")

with open(SRC) as f:
    content = f.read()

content = content.replace(
    '<rect x="26.5" y="6.5" width="879" height="1243.12" fill="white" stroke="none"/>',
    '<rect x="19" y="-7.01" width="894" height="1270.14" fill="white" stroke="none"/>',
    1,
)

with open(OUT, 'w') as f:
    f.write(content)

print(f"Wrote {OUT}  ({os.path.getsize(OUT):,} bytes)")
