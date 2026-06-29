"""
Generate a 'link corner' (PDF + SVG) for the poster: a single vertical list of
links, each preceded by an icon. Websites get a globe icon, the GitHub repo gets
the GitHub logo, and the Bluesky profiles get the Bluesky logo. Text is set in
Courier New, with shortened (scheme-stripped) URLs.
"""

import os
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Circle, Ellipse
from matplotlib.lines import Line2D
import matplotlib.transforms as mtransforms

# --- Font: Courier New (macOS system font) ---
fm.fontManager.addfont('/System/Library/Fonts/Supplemental/Courier New.ttf')
FONT = 'Courier New'

INK = '#1a1a1a'

# Official logo paths from simple-icons (viewBox 0 0 24 24, y-down).
GITHUB_PATH = ("M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12")
BLUESKY_PATH = ("M5.202 2.857C7.954 4.922 10.913 9.11 12 11.358c1.087-2.247 4.046-6.436 6.798-8.501C20.783 1.366 24 .213 24 3.883c0 .732-.42 6.156-.667 7.037-.856 3.061-3.978 3.842-6.755 3.37 4.854.826 6.089 3.562 3.422 6.299-5.065 5.196-7.28-1.304-7.847-2.97-.104-.305-.152-.448-.153-.327 0-.121-.05.022-.153.327-.568 1.666-2.782 8.166-7.847 2.97-2.667-2.737-1.432-5.473 3.422-6.3-2.777.473-5.899-.308-6.755-3.369C.42 10.04 0 4.615 0 3.883c0-3.67 3.217-2.517 5.202-1.026")

_TOKEN_RE = re.compile(r'([MmLlHhVvCcSsQqTtAaZz])|([-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?)')


def svg_path_to_mpl(d):
    """Parse an SVG path 'd' string (M/L/H/V/C/S/Q/T/Z) into a matplotlib Path."""
    tokens = _TOKEN_RE.findall(d)
    verts, codes = [], []
    cx = cy = 0.0       # current point
    sx = sy = 0.0       # subpath start
    pcx = pcy = 0.0     # previous control point (for S/T reflection)
    prev_cmd = None
    cmd = None
    nums = []
    i = 0

    def take(n):
        nonlocal i
        out = nums[i:i + n]
        i += n
        return [float(v) for v in out]

    # Flatten tokens into a sequence of (command, numbers-following) groups.
    groups = []
    for letter, number in tokens:
        if letter:
            groups.append([letter, []])
        else:
            if not groups:
                continue
            groups[-1][1].append(number)

    for letter, raw in groups:
        nums = raw
        i = 0
        rel = letter.islower()
        c = letter.upper()
        first = True
        # A command may be followed by multiple coordinate sets.
        while i < len(nums) or (c == 'Z' and first):
            if c == 'M':
                x, y = take(2)
                if rel:
                    x += cx; y += cy
                if first:
                    cx, cy = x, y
                    sx, sy = x, y
                    verts.append((x, y)); codes.append(Path.MOVETO)
                else:
                    cx, cy = x, y
                    verts.append((x, y)); codes.append(Path.LINETO)
            elif c == 'L':
                x, y = take(2)
                if rel:
                    x += cx; y += cy
                cx, cy = x, y
                verts.append((x, y)); codes.append(Path.LINETO)
            elif c == 'H':
                (x,) = take(1)
                if rel:
                    x += cx
                cx = x
                verts.append((cx, cy)); codes.append(Path.LINETO)
            elif c == 'V':
                (y,) = take(1)
                if rel:
                    y += cy
                cy = y
                verts.append((cx, cy)); codes.append(Path.LINETO)
            elif c == 'C':
                x1, y1, x2, y2, x, y = take(6)
                if rel:
                    x1 += cx; y1 += cy; x2 += cx; y2 += cy; x += cx; y += cy
                verts += [(x1, y1), (x2, y2), (x, y)]
                codes += [Path.CURVE4] * 3
                pcx, pcy = x2, y2
                cx, cy = x, y
            elif c == 'S':
                x2, y2, x, y = take(4)
                if rel:
                    x2 += cx; y2 += cy; x += cx; y += cy
                if prev_cmd in ('C', 'S'):
                    x1, y1 = 2 * cx - pcx, 2 * cy - pcy
                else:
                    x1, y1 = cx, cy
                verts += [(x1, y1), (x2, y2), (x, y)]
                codes += [Path.CURVE4] * 3
                pcx, pcy = x2, y2
                cx, cy = x, y
            elif c == 'Q':
                x1, y1, x, y = take(4)
                if rel:
                    x1 += cx; y1 += cy; x += cx; y += cy
                verts += [(x1, y1), (x, y)]
                codes += [Path.CURVE3] * 2
                pcx, pcy = x1, y1
                cx, cy = x, y
            elif c == 'T':
                x, y = take(2)
                if rel:
                    x += cx; y += cy
                if prev_cmd in ('Q', 'T'):
                    x1, y1 = 2 * cx - pcx, 2 * cy - pcy
                else:
                    x1, y1 = cx, cy
                verts += [(x1, y1), (x, y)]
                codes += [Path.CURVE3] * 2
                pcx, pcy = x1, y1
                cx, cy = x, y
            elif c == 'Z':
                verts.append((sx, sy)); codes.append(Path.CLOSEPOLY)
                cx, cy = sx, sy
            else:
                raise ValueError(f"Unsupported path command: {letter}")
            first = False
            prev_cmd = c
            if c == 'Z':
                break

    return Path(verts, codes)


def add_svg_icon(ax, path, x0, y0, size, color):
    """Place a 24x24-viewBox SVG path into a `size`-inch box at (x0, y0), y-flipped."""
    tr = (mtransforms.Affine2D()
          .scale(size / 24.0, -size / 24.0)
          .translate(x0, y0 + size)) + ax.transData
    ax.add_patch(PathPatch(path, transform=tr, facecolor=color, edgecolor='none'))


def add_globe(ax, x0, y0, size, color):
    """Draw a simple globe (circle + meridian + latitude lines) in a `size`-inch box."""
    r = size / 2.0
    cx, cy = x0 + r, y0 + r
    lw = size * 2.5
    circle = Circle((cx, cy), r, fill=False, edgecolor=color, lw=lw)
    ax.add_patch(circle)
    # Meridian (vertical ellipse) + a thinner one for depth.
    ax.add_patch(Ellipse((cx, cy), r, 2 * r, fill=False, edgecolor=color, lw=lw))
    # Equator + two latitude chords, clipped to the disk.
    for frac in (0.0, 0.5, -0.5):
        yy = cy + frac * r
        half = (r ** 2 - (frac * r) ** 2) ** 0.5
        line = Line2D([cx - half, cx + half], [yy, yy], color=color, lw=lw)
        ax.add_line(line)
        line.set_clip_path(circle)


# --- Links: (kind, shortened display text) ---
LINKS = [
    ('github',  'github.com/nishalsach/birds_bookworms'),
    ('globe',   'nishalsach.github.io'),
    ('globe',   'jackbandy.com'),
    ('bluesky', 'bsky.app/profile/jackbandy.com'),
    ('bluesky', 'bsky.app/profile/sachnishal.bsky.social'),
]

# --- Layout (inches) ---
FONT_SIZE = 12
ICON_SIZE = 0.20
ROW_H     = 0.34
GAP       = 0.12          # space between icon and text
MARGIN    = 0.10
CHAR_W    = FONT_SIZE * 0.60 / 72.0   # Courier New is monospaced

text_x = MARGIN + ICON_SIZE + GAP
max_chars = max(len(text) for _, text in LINKS)
FIG_WIDTH  = text_x + max_chars * CHAR_W + MARGIN
FIG_HEIGHT = 2 * MARGIN + len(LINKS) * ROW_H

GITHUB_MPL = svg_path_to_mpl(GITHUB_PATH)
BLUESKY_MPL = svg_path_to_mpl(BLUESKY_PATH)

fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))
ax.set_xlim(0, FIG_WIDTH)
ax.set_ylim(0, FIG_HEIGHT)
ax.set_aspect('equal')
ax.axis('off')

y = FIG_HEIGHT - MARGIN
for kind, text in LINKS:
    y -= ROW_H
    icon_y = y + (ROW_H - ICON_SIZE) / 2.0
    if kind == 'github':
        add_svg_icon(ax, GITHUB_MPL, MARGIN, icon_y, ICON_SIZE, INK)
    elif kind == 'bluesky':
        add_svg_icon(ax, BLUESKY_MPL, MARGIN, icon_y, ICON_SIZE, '#1185fe')
    else:
        add_globe(ax, MARGIN, icon_y, ICON_SIZE, INK)
    ax.text(text_x, y + ROW_H / 2, text, va='center', ha='left',
            fontsize=FONT_SIZE, fontfamily=FONT, color=INK)

script_dir = os.path.dirname(os.path.abspath(__file__))
pdf_path = os.path.join(script_dir, 'link_corner.pdf')
svg_path = os.path.join(script_dir, 'link_corner.svg')
fig.savefig(pdf_path, bbox_inches='tight', dpi=150)
fig.savefig(svg_path, bbox_inches='tight')
plt.close(fig)

print(f'Saved {os.path.basename(pdf_path)} and {os.path.basename(svg_path)} '
      f'({len(LINKS)} links)')
