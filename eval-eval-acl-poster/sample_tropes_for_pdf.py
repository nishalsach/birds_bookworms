import csv
import random
import os
import textwrap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# --- Fonts ---
script_dir = os.path.dirname(os.path.abspath(__file__))
font_dir = os.path.join(script_dir, 'fonts')
fm.fontManager.addfont(os.path.join(font_dir, 'LibreFranklin-Regular.ttf'))
fm.fontManager.addfont(os.path.join(font_dir, 'LibreFranklin-Bold.ttf'))
FONT = 'Libre Franklin'

LIGHT_GRAY = '#ebebeb'

# --- Sample tropes ---
with open('../all_211_feminine_tropes.csv', newline='', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

tropes_to_keep = ('CagedBirdMetaphor', 'CuteBookworm', 'EverythingsBetterWithSparkles',
                  'NatureLover', 'DruggedLipstick', 'TreeCover', 'HotScientist', 'RedheadInGreen',
                  'AcademicAlphaBitch', 'PromWrecker', 'BracesOfOrthodonticOverkill')
anchor_map = {r['TropeName']: r for r in rows if r['TropeName'] in tropes_to_keep}
anchor = [anchor_map[t] for t in tropes_to_keep]
rest   = [r for r in rows if r['TropeName'] not in tropes_to_keep]

random.seed(2027)
sample = anchor + random.sample(rest, 21)

# --- Save CSV (real data only, no ellipsis row) ---
csv_columns = ['#', 'TropeName', 'They', 'He', 'She', 'Ambiguous']
csv_rows = []
for i, row in enumerate(sample, 1):
    csv_rows.append([211 if i == len(sample) else i,
                     row['TropeName'], row['They'], '', '', ''])

with open('tropes_for_poster.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(csv_columns)
    writer.writerows(csv_rows)

# --- Build table rows (with ellipsis row second-to-last) ---
columns = ['#', 'Trope Name', "'They' prompt", "'He' prompt", "'She' prompt", "'Ambiguous' prompt"]

table_rows = []
for i, row in enumerate(sample[:-1], 1):
    table_rows.append([str(i), row['TropeName'], row['They'], '...', '...', '...'])
table_rows.append(['...', '...', '...', '...', '...', '...'])
table_rows.append(['211', sample[-1]['TropeName'], sample[-1]['They'], '...', '...', '...'])

# --- Layout constants ---
FONT_SIZE     = 7.5
LINE_HEIGHT   = FONT_SIZE / 72 * 1.45   # inches per text line
CELL_PAD      = 0.09                    # vertical padding per cell
HEADER_HEIGHT = 0.26
FIG_WIDTH     = 16

col_widths = [0.04, 0.16, 0.56, 0.08, 0.08, 0.08]
TEXT_PAD   = 0.006                          # left padding applied to every cell text
# 0.62 char-width ratio (vs naive 0.52) accounts for Libre Franklin being wider than monospace average
THEY_WRAP = int((col_widths[2] - 2 * TEXT_PAD) * FIG_WIDTH * 72 / FONT_SIZE / 0.62)
x_starts   = [sum(col_widths[:i]) for i in range(len(col_widths))]

# Wrap They text; measure max lines to set a single consistent row height
def wrap_they(text):
    if text == '...':
        return '...'
    PREFIX = 'Write a short summary of a story in which'
    lines = textwrap.wrap(text, THEY_WRAP)
    if len(lines) > 2 and text.startswith(PREFIX):
        lines = textwrap.wrap('...' + text[len(PREFIX):], THEY_WRAP)
    if len(lines) > 2:
        lines = lines[:2]
        lines[-1] = lines[-1].rstrip() + '...'
    return '\n'.join(lines)

for row in table_rows:
    row[2] = wrap_they(row[2])

max_lines = max(cell.count('\n') + 1 for row in table_rows for cell in row)
ROW_HEIGHT = max_lines * LINE_HEIGHT + CELL_PAD

n_rows = len(table_rows)
FIG_HEIGHT = HEADER_HEIGHT + n_rows * ROW_HEIGHT + 0.3

fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))
ax.set_xlim(0, 1)
ax.set_ylim(0, FIG_HEIGHT)
ax.axis('off')

y = FIG_HEIGHT - 0.15

# Header
y -= HEADER_HEIGHT
for label, w, x in zip(columns, col_widths, x_starts):
    ax.add_patch(plt.Rectangle((x, y), w, HEADER_HEIGHT,
                                facecolor='white', edgecolor='white', clip_on=False))
    ax.text(x + TEXT_PAD, y + HEADER_HEIGHT / 2, label,
            va='center', ha='left', fontsize=FONT_SIZE,
            fontfamily=FONT, fontweight='bold', clip_on=False)

# Data rows — collect positions, then draw all backgrounds before any text so
# no rectangle can paint over text from an adjacent column.
row_positions = []
for ri, row in enumerate(table_rows):
    y -= ROW_HEIGHT
    row_positions.append((ri, row, y))

for ri, row, row_y in row_positions:
    bg = LIGHT_GRAY if ri % 2 == 1 else 'white'
    for w, x in zip(col_widths, x_starts):
        ax.add_patch(plt.Rectangle((x, row_y), w, ROW_HEIGHT,
                                    facecolor=bg, edgecolor='white', clip_on=False))

for ri, row, row_y in row_positions:
    for cell, w, x in zip(row, col_widths, x_starts):
        txt = ax.text(x + TEXT_PAD, row_y + ROW_HEIGHT / 2, cell,
                va='center', ha='left', fontsize=FONT_SIZE,
                fontfamily=FONT, linespacing=1.4, clip_on=True)
        clip_rect = plt.Rectangle((x, row_y), w, ROW_HEIGHT, transform=ax.transData)
        txt.set_clip_path(clip_rect)

fig.savefig('tropes_for_poster.pdf', bbox_inches='tight', dpi=150)
fig.savefig('tropes_for_poster.svg', bbox_inches='tight')
plt.close(fig)

print(f'Saved tropes_for_poster.csv ({len(csv_rows)} rows), .pdf, and .svg')
