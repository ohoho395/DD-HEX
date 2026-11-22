"""Generate DD HEX's monochrome smoked-glass icon and Windows size variants."""
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)


def rounded_box(x, y, cx, cy, half_w, half_h, radius):
    """Signed distance to a rounded rectangle, negative inside."""
    dx = np.abs(x - cx) - half_w + radius
    dy = np.abs(y - cy) - half_h + radius
    return np.hypot(np.maximum(dx, 0), np.maximum(dy, 0)) + np.minimum(np.maximum(dx, dy), 0) - radius


def d_shape(x, y, left, top, width, height):
    """Flat stem with a curved bowl on the right."""
    radius = height / 2
    bowl = np.hypot(np.maximum(x - (left + width - radius), 0), y - (top + radius)) - radius
    return np.maximum(left - x, bowl)


def render(size=1024):
    axis = (np.arange(size, dtype=np.float32) + .5) / size
    x, y = np.meshgrid(axis, axis)
    tile = rounded_box(x, y, .5, .5, .463, .463, .205)
    # One curved transition crosses the face like light reflected by dark glass.
    horizon = .235 + .38 * (1 - x)**2
    reflection = 1 / (1 + np.exp(np.clip((y - horizon) / .015, -30, 30)))
    face = 14 + 16 * (1 - y) + 29 * reflection + 8 * x
    face += 12 * np.exp(-((y - .91) / .048)**2) * (1 - x)
    face += 15 * np.exp(-((y - horizon) / .009)**2) * (1 - x)**1.5
    # A refracted highlight hugs the lower-right curved edge and fades inward.
    caustic = np.exp(-((x - .76) / .19)**2 - ((y - .87) / .17)**2)
    face += 39 * caustic * np.exp(-((tile + .027) / .015)**2)
    # Narrow directional rim plus a soft inner bevel, with no opaque corner pixels.
    edge = np.exp(-((tile + .005) / .005)**2)
    rim_light = .28 + .72 * np.maximum(1 - y, x * y)
    face += 140 * rim_light * edge + 24 * np.exp(-((tile + .017) / .010)**2)

    for left, tone in ((.152, 148), (.518, 103)):
        def glyph(xx, yy):
            outer = d_shape(xx, yy, left, .308, .330, .384)
            hole = d_shape(xx, yy, left + .086, .391, .153, .218)
            return np.maximum(outer, -hole)
        mark = glyph(x, y)
        shadow = np.clip(1 - np.maximum(glyph(x, y - .008), 0) / .014, 0, 1)
        face *= 1 - .37 * shadow
        # Keep both letter counters open at 16 px. The graphite face and
        # brushed edge carry the letterform even when the reflection disappears.
        letter = tone + 26 * (1 - y) + 24 * reflection + 6 * (1 - x)
        ny, nx = np.gradient(mark, 1 / size)
        incidence = np.clip(-.48 * nx - .75 * ny, -1, 1)
        letter += (24 + 41 * incidence) * np.exp(-((mark + .005) / .007)**2)
        coverage = np.clip(.5 - size * mark, 0, 1)
        face = face * (1 - coverage) + letter * coverage

    gray = np.uint8(np.clip(face, 0, 255))
    alpha = np.uint8(255 * np.clip(.5 - size * tile, 0, 1))
    return Image.fromarray(np.dstack((gray, gray, gray, alpha)))


def main():
    master = render()
    frames = []
    for n in ICO_SIZES:
        frame = master.resize((n, n), Image.Resampling.LANCZOS)
        # Remove almost invisible resampling specks outside the glass.
        frame.putalpha(frame.getchannel("A").point(lambda a: 0 if a < 3 else a))
        frames.append(frame)
    frames[-1].save(ROOT / "lolhex/ui/icon.png")
    frames[-1].save(ROOT / "packaging/lolhex.ico", sizes=[f.size for f in frames], append_images=frames[:-1])


if __name__ == "__main__":
    main()
