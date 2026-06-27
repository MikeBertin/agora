"""Render the 1200x630 Open Graph / social card to docs/og.png.

    python3 experiments/make_og.py
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
REG = "/System/Library/Fonts/Supplemental/Arial.ttf"
MONO = "/System/Library/Fonts/Menlo.ttc"

INK = (231, 231, 239)
MUTED = (138, 138, 156)
# demo accent colours (negotiation, auctions, voting, dcop)
STOPS = [(0.0, (124, 196, 255)), (0.40, (255, 194, 102)),
         (0.72, (95, 208, 197)), (1.0, (199, 155, 255))]
DEMOS = [("Negotiation", (124, 196, 255)), ("Auctions", (255, 194, 102)),
         ("Voting", (95, 208, 197)), ("Distributed optimisation", (199, 155, 255))]


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def gradient_at(t):
    for (t0, c0), (t1, c1) in zip(STOPS, STOPS[1:]):
        if t <= t1:
            return lerp(c0, c1, (t - t0) / (t1 - t0))
    return STOPS[-1][1]


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    img = Image.new("RGB", (W, H), (10, 10, 15))
    px = img.load()
    # vertical background gradient + soft top glow
    for y in range(H):
        base = lerp((22, 22, 31), (10, 10, 15), min(1.0, y / (H * 0.7)))
        for x in range(W):
            dx, dy = (x - W / 2) / W, (y + 80) / H
            glow = max(0.0, 1.0 - (dx * dx * 3 + dy * dy * 1.4)) * 14
            px[x, y] = tuple(min(255, round(base[i] + glow)) for i in range(3))
    d = ImageDraw.Draw(img)

    badge = ImageFont.truetype(MONO, 22)
    title = ImageFont.truetype(BOLD, 150)
    tag = ImageFont.truetype(REG, 38)
    demo = ImageFont.truetype(BOLD, 27)
    foot = ImageFont.truetype(MONO, 21)

    PAD = 84
    # badge
    d.text((PAD + 4, 78), "M U L T I - A G E N T   S Y S T E M S", font=badge, fill=MUTED)

    # gradient "Agora"
    x0, y0, x1, y1 = title.getbbox("Agora")
    tw, th = x1 - x0, y1 - y0
    grad = Image.new("RGB", (tw, th))
    gp = grad.load()
    for i in range(tw):
        c = gradient_at(i / (tw - 1))
        for j in range(th):
            gp[i, j] = c
    mask = Image.new("L", (tw, th), 0)
    ImageDraw.Draw(mask).text((-x0, -y0), "Agora", font=title, fill=255)
    img.paste(grad, (PAD, 132), mask)

    # tagline
    d.text((PAD + 4, 330), "Multi-agent systems, in the browser.", font=tag, fill=INK)

    # demo row (coloured dots + labels)
    x = PAD + 4
    y = 430
    for label, col in DEMOS:
        d.ellipse([x, y + 8, x + 14, y + 22], fill=col)
        d.text((x + 24, y), label, font=demo, fill=col)
        x += 24 + d.textlength(label, font=demo) + 40

    # footer
    d.text((PAD + 4, 556),
           "negotiation · auctions · voting · DCOP — a Python engine, live in-browser via Pyodide",
           font=foot, fill=MUTED)

    out = os.path.join(root, "docs", "og.png")
    img.save(out)
    print(f"wrote {out} ({W}x{H})")


if __name__ == "__main__":
    main()
