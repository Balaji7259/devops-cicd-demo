"""Composes the three screenshots into one LinkedIn-ready image.

1200x1500 (4:5) is the tallest portrait LinkedIn shows in-feed without cropping.

Each card crops to its content band before scaling. The portfolio pages centre
their content in a 1440px viewport, so a naive full-width shot spends a third of
the card on empty gutter and shrinks the text for no reason.
"""

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 1500
M = 52
CARD_W = W - 2 * M

BG = (15, 18, 20)
CARD_BG = (22, 26, 30)
BORDER = (43, 49, 55)
TEXT = (233, 237, 240)
MUTED = (152, 163, 173)
ACCENT = (111, 206, 157)

FONT_DIR = "C:/Windows/Fonts/"
f_label = ImageFont.truetype(FONT_DIR + "seguisb.ttf", 19)
f_title = ImageFont.truetype(FONT_DIR + "segoeuib.ttf", 50)
f_sub = ImageFont.truetype(FONT_DIR + "segoeui.ttf", 22)
f_cap = ImageFont.truetype(FONT_DIR + "segoeui.ttf", 19)

# path, source crop box (x0, y0, x1, y1), card height, caption
CARDS = [
    ("shots/01-portfolio-home.png", (338, 0, 1462, 548), 530,
     "The live portfolio \u2014 served from the container this pipeline deploys"),
    ("shots/02-case-study.png", (338, 180, 1462, 470), 283,
     "A case study explaining the pipeline, shipped inside the same image"),
    ("shots/03-actions-green.png", (0, 0, 1782, 488), 300,
     "Run #30 \u2014 four jobs green in 1m 02s, from commit to live"),
]


def card(path, box, height):
    src = Image.open(path).convert("RGB").crop(box)
    scale = CARD_W / src.width
    src = src.resize((CARD_W, max(1, int(round(src.height * scale)))), Image.LANCZOS)

    # Keep the target height: pad with the card background if the crop is short,
    # trim from the bottom if it is long. Never stretch the pixels.
    out = Image.new("RGB", (CARD_W, height), CARD_BG)
    out.paste(src.crop((0, 0, CARD_W, min(src.height, height))), (0, 0))

    mask = Image.new("L", (CARD_W, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, CARD_W - 1, height - 1], 12, fill=255)
    rounded = Image.new("RGB", (CARD_W, height), BG)
    rounded.paste(out, (0, 0), mask)
    ImageDraw.Draw(rounded).rounded_rectangle([0, 0, CARD_W - 1, height - 1], 12,
                                              outline=BORDER, width=1)
    return rounded


def main():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    d.text((M, 50), "CASE STUDY  \u00b7  RUN #30", font=f_label, fill=ACCENT)
    d.text((M, 80), "Commit to live in one minute.", font=f_title, fill=TEXT)
    d.text((M, 148), "AWS  \u00b7  Docker  \u00b7  GitHub Actions  \u00b7  Amazon ECR  \u00b7  Systems Manager",
           font=f_sub, fill=MUTED)

    y = 210
    for path, box, h, caption in CARDS:
        img.paste(card(path, box, h), (M, y))
        y += h + 10
        d.ellipse([M + 2, y + 7, M + 9, y + 14], fill=ACCENT)
        d.text((M + 20, y), caption, font=f_cap, fill=MUTED)
        y += 44

    img.save("shots/linkedin-post.png", optimize=True)
    print(f"saved  {W}x{H}  content ends at y={y - 44} (canvas {H})")


if __name__ == "__main__":
    main()

