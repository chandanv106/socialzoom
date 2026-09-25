"""Build the README's images from the app's own renders.

    python tools/compose.py <marketing dir>

<marketing dir> holds iphone_light/ and iphone_dark/, ten screens each,
rendered by the app's screenshot harness at iPhone 15 Pro size. Writes:

    assets/hero-light.png, assets/hero-dark.png   the banner, per GitHub theme
    assets/screens/<name>.png                    each screen, light beside dark
    assets/icon.png                              the app icon, rounded
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from iphone import phone, trim

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ONEST = ROOT / "tools" / "fonts" / "Onest-Variable.ttf"

# The app's own palette.
SUNSHINE_HI = (0xFF, 0xE6, 0x80)
SUNSHINE_LO = (0xFF, 0xC2, 0x1A)
INK = (0x1E, 0x21, 0x30)
INK2 = (0x5C, 0x62, 0x75)
NIGHT_PAGE = (0x18, 0x1B, 0x24)
NIGHT_INK = (0xED, 0xEE, 0xF3)
NIGHT_INK2 = (0xA7, 0xAD, 0xBF)

SCREENS = [
    "feed", "profile", "discover", "inbox", "chat",
    "group", "call", "story", "vanish", "privacy",
]


def onest(size: int, weight: int) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(ONEST), size)
    font.set_variation_by_axes([weight])
    return font


def gradient(size, a, b, *, diagonal: bool = True) -> Image.Image:
    """A smooth two-stop gradient, drawn small and scaled up."""
    w, h = size
    small = Image.new("RGB", (64, 64))
    for y in range(64):
        for x in range(64):
            t = (x + y) / 126 if diagonal else y / 63
            small.putpixel((x, y), tuple(round(p + (q - p) * t) for p, q in zip(a, b)))
    return small.resize((w, h), Image.BICUBIC)


def glow(size, centre, radius, colour, strength) -> Image.Image:
    """A soft coloured light, for behind the phones."""
    layer = Image.new("RGBA", size, colour + (0,))
    mask = Image.new("L", size, 0)
    cx, cy = centre
    ImageDraw.Draw(mask).ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius), fill=round(255 * strength)
    )
    layer.putalpha(mask.filter(ImageFilter.GaussianBlur(radius * 0.55)))
    return layer


def rounded_icon(size: int) -> Image.Image:
    src = ROOT.parent / "SocialZoom" / "store-graphics" / "socialzoom-yellow-icon-1024.png"
    icon = Image.open(src).convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size * 4 - 1, size * 4 - 1), radius=round(size * 4 * 0.225), fill=255
    )
    icon.putalpha(mask.resize((size, size), Image.LANCZOS))
    return icon


def scaled(img: Image.Image, width: int) -> Image.Image:
    return img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)


def chip(draw, xy, text, font, fill, ink) -> int:
    """A pill with a word in it. Returns its width."""
    x, y = xy
    box = draw.textbbox((0, 0), text, font=font)
    w = box[2] - box[0] + 34
    h = box[3] - box[1] + 22
    draw.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=fill)
    draw.text((x + 17, y + 11 - box[1]), text, font=font, fill=ink)
    return w


def hero(phones: dict[str, Image.Image], *, dark: bool) -> Image.Image:
    W, H = 1600, 880
    if dark:
        canvas = gradient((W, H), (0x10, 0x12, 0x19), (0x1E, 0x22, 0x31)).convert("RGBA")
        canvas.alpha_composite(glow((W, H), (1130, 470), 430, SUNSHINE_LO, 0.30))
        title, body, chip_fill, chip_ink = NIGHT_INK, NIGHT_INK2, (40, 44, 58), NIGHT_INK
    else:
        canvas = gradient((W, H), (0xFF, 0xF8, 0xDC), SUNSHINE_LO).convert("RGBA")
        canvas.alpha_composite(glow((W, H), (1130, 470), 430, (255, 255, 255), 0.55))
        title, body, chip_fill, chip_ink = INK, INK2, (255, 255, 255), INK

    draw = ImageDraw.Draw(canvas)

    # The words, on the left.
    x = 96
    canvas.alpha_composite(rounded_icon(132), (x, 150))
    draw.text((x, 318), "SocialZoom", font=onest(104, 800), fill=title)
    draw.text((x, 452), "Photos, stories, chat & calls.", font=onest(40, 600), fill=body)
    draw.text(
        (x, 510), "A full social app for iOS and Android,", font=onest(30, 450), fill=body
    )
    draw.text(
        (x, 550), "built end to end: app, backend and ops.", font=onest(30, 450), fill=body
    )
    cx = x
    for word in ("iOS", "Android", "Flutter", "Supabase", "WebRTC"):
        cx += chip(draw, (cx, 630), word, onest(21, 650), chip_fill, chip_ink) + 10

    # Three phones, fanned, on the right.
    order = ("chat", "feed", "profile")
    sizes = {"feed": 430, "chat": 360, "profile": 360}
    angles = {"chat": 9, "feed": 0, "profile": -9}
    centres = {"chat": 905, "feed": 1130, "profile": 1355}
    for name in order[::2] + order[1:2]:  # sides first, the middle in front
        p = scaled(phones[name], sizes[name])
        p = p.rotate(angles[name], resample=Image.BICUBIC, expand=True)
        y = 470 - p.height // 2 + (0 if name == "feed" else 30)
        canvas.alpha_composite(p, (centres[name] - p.width // 2, y))
    return canvas.convert("RGB")


def pair(light: Image.Image, dark: Image.Image) -> Image.Image:
    """Light beside dark, on a transparent canvas, trimmed to the shadows."""
    a, b = trim(light), trim(dark)
    width = 560
    a, b = scaled(a, width), scaled(b, width)
    gap = -40  # the shadows overlap a little; the bodies do not
    out = Image.new("RGBA", (a.width + b.width + gap, max(a.height, b.height)), (0, 0, 0, 0))
    out.alpha_composite(a, (0, 0))
    out.alpha_composite(b, (a.width + gap, 0))
    return out


def main(marketing: Path) -> None:
    (ASSETS / "screens").mkdir(parents=True, exist_ok=True)
    light = {n: phone(marketing / "iphone_light" / f"{n}.png") for n in SCREENS}
    dark = {n: phone(marketing / "iphone_dark" / f"{n}.png") for n in SCREENS}
    print("framed 20 screens")

    hero(light, dark=False).save(ASSETS / "hero-light.png", optimize=True)
    hero(dark, dark=True).save(ASSETS / "hero-dark.png", optimize=True)
    print("heroes")

    for n in SCREENS:
        pair(light[n], dark[n]).save(ASSETS / "screens" / f"{n}.png", optimize=True)
    print("pairs")

    rounded_icon(256).save(ASSETS / "icon.png", optimize=True)
    print("icon")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
