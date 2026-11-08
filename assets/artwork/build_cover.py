"""Rebuild the homepage artwork from the archived print scan and existing fan title.

Run from any directory with Python and Pillow: python assets/artwork/build_cover.py
The source paths, scan-space mask, and printed colors are independent of the layout.
"""

from hashlib import sha256
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps


HERE = Path(__file__).resolve().parent
SCAN = HERE / 'japanese-retail-front.jpg'
SCAN_SHA = '246108fd30f463f6b9da87c3af0d81617ab3895ed9c10ed91325e7bbe59f29c4'
ENGLISH = HERE / 'cover-title-english.png'
ENGLISH_SHA = '51d12d07c8bbae61a1d13751bf8c6c5760e3d69cf13f8c1ce5ef61a8bb53e1c0'
LANCZOS = Image.Resampling.LANCZOS
OVERLAY_HEIGHT = 872


def checked_image(path, digest):
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError(f'Unexpected source image: {path.name}')
    return Image.open(path)


def english_overlay(scan, title):
    # Use the paper above the original title for the spaces exposed by localizing it.
    # Alternate the direction of the strip to keep its grain continuous at the joins.
    upper = scan.crop((0, 0, scan.width, OVERLAY_HEIGHT))
    strip = scan.crop((0, 20, scan.width, 54))
    paper = Image.new('RGB', upper.size)
    for y in range(0, upper.height, strip.height):
        paper.paste(strip, (0, y))
        strip = ImageOps.flip(strip)

    # Keep the scan's existing paper visible around the printing. Detect ink at
    # quarter scale, fill the holes within letters, then feather the outside edges.
    small = (upper.width // 4, upper.height // 4)
    difference = ImageChops.difference(upper.resize(small, LANCZOS), paper.resize(small, LANCZOS))
    red, green, blue = difference.split()
    ink = ImageChops.lighter(ImageChops.lighter(red, green), blue).point(lambda p: 255 if p > 16 else 0)
    ink = ink.filter(ImageFilter.MaxFilter(7))
    filled = ink.copy()
    ImageDraw.floodfill(filled, (0, 0), 127)
    ink = filled.point(lambda p: 0 if p == 127 else 255)
    ink = ink.resize(upper.size, LANCZOS).filter(ImageFilter.GaussianBlur(2))

    # The tail lies beside the subtitle. The red pompom touches its black outline.
    # This traced boundary follows the visible pompom edge in the untouched scan.
    # Only the ink above the boundary can be removed; no figure is reconstructed.
    limit = Image.new('L', upper.size)
    ImageDraw.Draw(limit).polygon([
        (140, 40), (2770, 40), (2770, 760), (2300, 760), (2230, 848),
        (1220, 848), (1211, 836), (1206, 824), (1199, 820), (1192, 812),
        (1185, 809), (1177, 812), (1172, 818), (1167, 814), (1154, 815),
        (1148, 801), (1143, 796), (1137, 799), (1127, 805), (1114, 809),
        (1101, 813), (1095, 820), (1089, 825), (1083, 829), (1072, 848),
        (140, 848),
    ], fill=255)
    paper.putalpha(ImageChops.multiply(ink, limit))
    # Preserve the English title's own aspect ratio, including its printed subtitle.
    title = title.resize((2324, round(2324 * title.height / title.width)), LANCZOS)
    paper.alpha_composite(title, ((scan.width - title.width) // 2, 12))
    return paper


def make_icons():
    sprite = Image.open(HERE.parent / 'slime-still.png').convert('RGBA')
    sprite = sprite.crop(sprite.getbbox())
    for size, width, name in [(32, 28, 'favicon.png'), (180, 136, 'apple-touch-icon.png')]:
        icon = Image.new('RGB', (size, size), '#102239')
        slime = sprite.resize((width, round(width * sprite.height / sprite.width)), Image.Resampling.NEAREST)
        icon.paste(slime, ((size - slime.width) // 2, (size - slime.height) // 2), slime)
        icon.save(HERE / name, optimize=True)


def make_social_card(scan):
    card = Image.new('RGB', (1200, 630), '#102239')
    cover = scan.copy()
    cover.thumbnail((505, 513), LANCZOS)
    position = (61, (card.height - cover.height) // 2)
    card.paste(cover, position)
    draw = ImageDraw.Draw(card)
    x = 618
    for y, label, size, color in [
        (145, 'Dragon Quest', 65, '#fff6df'), (226, 'Monsters 1 & 2', 65, '#fff6df'),
        (353, 'English patch for PlayStation', 36, '#eac779'),
        (483, 'dqm-psx.github.io', 27, '#b7c6d6'),
    ]:
        draw.text((x, y), label, fill=color, font=ImageFont.load_default(size=size))
    card.save(HERE / 'social-card.jpg', quality=88, optimize=True, progressive=True, subsampling=0)


def verify_overlay(path):
    # Inspect the encoded alpha channel at each delivery size. The lower cover,
    # tail and visible center of the pompom must remain supplied by the base.
    alpha = Image.open(path).getchannel('A')
    scale = alpha.width / 2906
    protected = [(0, 857, 2906, 872), (2303, 774, 2605, 872), (1108, 831, 1186, 865)]
    for box in protected:
        if alpha.crop(tuple(round(value * scale) for value in box)).getbbox():
            raise ValueError(f'{path.name} overlaps a protected part of the illustration')


def main():
    scan = checked_image(SCAN, SCAN_SHA).convert('RGB')
    title = checked_image(ENGLISH, ENGLISH_SHA).convert('RGBA')
    overlay = english_overlay(scan, title)
    for width in (560, 1120):
        base_size = (width, round(width * scan.height / scan.width))
        scan.resize(base_size, LANCZOS).save(HERE / f'cover-japanese-{width}.webp', quality=90, method=6)
        overlay_size = (width, round(width * OVERLAY_HEIGHT / scan.width))
        top = overlay.resize(overlay_size, LANCZOS)
        # Clear the resampler's faint ringing below the last edited scan row.
        top.paste((0, 0, 0, 0), (0, round(852 * width / scan.width), width, top.height))
        overlay_path = HERE / f'cover-english-overlay-{width}.webp'
        top.save(overlay_path, quality=90, method=6)
        verify_overlay(overlay_path)
    make_icons()
    make_social_card(scan)


if __name__ == '__main__':
    main()
