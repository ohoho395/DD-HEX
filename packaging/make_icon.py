"""Render DD HEX's original HP mark, without fonts or downloaded assets.

The geometric monogram is drawn at 4x resolution and exported as the Qt PNG
and multi-size Windows ICO. Run with the normal Pillow runtime dependency.
"""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent


def render(size: int = 1024) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def rect(box, fill, radius=0):
        draw.rounded_rectangle([round(n * size) for n in box], radius=round(radius * size), fill=fill)

    rect((.04, .04, .96, .96), "#112333", .20)
    # Teal edge and compact H/P forms remain readable at small tray sizes.
    draw.rounded_rectangle((.04 * size, .04 * size, .96 * size, .96 * size),
                           radius=round(.20 * size), outline="#5de2c2", width=max(1, round(.025 * size)))
    for left, color in ((.15, "#e5fff8"), (.53, "#5de2c2")):
        rect((left, .28, left+.32, .72), color, .13)
        rect((left, .28, left+.10, .72), color)
        rect((left+.09, .37, left+.23, .63), "#112333", .06)
    return image


def main():
    big = render()
    ico = ROOT / "packaging/lolhex.ico"
    png = ROOT / "lolhex/ui/icon.png"
    big.save(ico, sizes=[(n, n) for n in (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)])
    big.resize((256, 256), Image.Resampling.LANCZOS).save(png)
    print("written", ico, png)


if __name__ == "__main__":
    main()
