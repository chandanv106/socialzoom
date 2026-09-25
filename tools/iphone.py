"""Draw an app screenshot into an iPhone 15 Pro.

The screenshots come from the app's own widgets rendered at an iPhone 15
Pro's size - 393 x 852 points at 3x, 1179 x 2556 pixels - with its real safe
areas: 59 points at the top, 34 at the bottom. So the app has already left
room for the Dynamic Island and the status bar, and this only has to draw
them in, with the device around them.

Geometry is the phone's own, in points, scaled by SCALE:
  display corner radius 55, Dynamic Island 126 x 37 set 11 from the top,
  home indicator 134 x 5 set 8 from the bottom.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

SCALE = 3  # device pixels per point

# The display, in pixels.
SCREEN_W, SCREEN_H = 393 * SCALE, 852 * SCALE
SCREEN_RADIUS = 55 * SCALE

# The device around it: a titanium rim, then the black bezel.
RIM = 14
BEZEL = 26
BODY_W = SCREEN_W + 2 * (RIM + BEZEL)
BODY_H = SCREEN_H + 2 * (RIM + BEZEL)
BEZEL_RADIUS = SCREEN_RADIUS + BEZEL
BODY_RADIUS = BEZEL_RADIUS + RIM

# Room around the body for the buttons and the shadow.
PAD = 150

FONT_DIR = Path("C:/Windows/Fonts")
TIME_FONT = FONT_DIR / "seguisb.ttf"  # Segoe UI Semibold, standing in for SF


def _rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    """A rounded rectangle, drawn at 4x and brought down so its edge is soft."""
    w, h = size
    big = Image.new("L", (w * 4, h * 4), 0)
    ImageDraw.Draw(big).rounded_rectangle(
        (0, 0, w * 4 - 1, h * 4 - 1), radius=radius * 4, fill=255
    )
    return big.resize((w, h), Image.LANCZOS)


def _vertical_gradient(size, top, bottom) -> Image.Image:
    w, h = size
    column = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        column.putpixel(
            (0, y), tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))
        )
    return column.resize((w, h))


def _status_bar(draw: ImageDraw.ImageDraw, ink: tuple, ox: int, oy: int) -> None:
    """9:41, then the signal, Wi-Fi and battery, beside the Dynamic Island."""
    island_mid = oy + (11 + 37 / 2) * SCALE

    # The time, centred in the space left of the island.
    font = ImageFont.truetype(str(TIME_FONT), 17 * SCALE)
    text = "9:41"
    box = draw.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    left_mid = ox + (SCREEN_W / 2 - 126 * SCALE / 2) / 2 + 6 * SCALE
    draw.text(
        (left_mid - tw / 2, island_mid - th / 2 - box[1]), text, font=font, fill=ink
    )

    # The right-hand cluster, centred in the space right of the island.
    right_start = ox + SCREEN_W / 2 + 126 * SCALE / 2
    cluster_w = (18 + 6 + 17 + 6 + 27) * SCALE
    x = right_start + (SCREEN_W / 2 - 126 * SCALE / 2 - cluster_w) / 2 - 4 * SCALE
    base = island_mid + 6 * SCALE

    # Signal: four bars, rising.
    bar_w, gap = 3 * SCALE, 1.5 * SCALE
    for i, height in enumerate((4, 6, 8.5, 11)):
        bx = x + i * (bar_w + gap)
        draw.rounded_rectangle(
            (bx, base - height * SCALE, bx + bar_w, base),
            radius=SCALE, fill=ink,
        )
    x += 4 * bar_w + 3 * gap + 6 * SCALE

    # Wi-Fi: three arcs from one point, drawn as nested wedges.
    cx, cy = x + 8.5 * SCALE, base
    for r, width in ((11.5, 2.7), (7.7, 2.7), (3.6, 3.6)):
        rr = r * SCALE
        draw.arc(
            (cx - rr, cy - rr, cx + rr, cy + rr),
            start=225, end=315, fill=ink, width=round(width * SCALE),
        )
    x += 17 * SCALE + 6 * SCALE

    # Battery: an outline, a charge, and the nub.
    bw, bh = 24 * SCALE, 11.5 * SCALE
    top = base - bh
    draw.rounded_rectangle(
        (x, top, x + bw, base), radius=round(3.5 * SCALE),
        outline=ink, width=round(1.1 * SCALE),
    )
    inset = 2 * SCALE
    draw.rounded_rectangle(
        (x + inset, top + inset, x + bw * 0.78, base - inset),
        radius=round(1.6 * SCALE), fill=ink,
    )
    draw.rounded_rectangle(
        (x + bw + 1.2 * SCALE, top + bh * 0.33, x + bw + 2.6 * SCALE, base - bh * 0.33),
        radius=SCALE, fill=ink,
    )


def _is_dark(screen: Image.Image) -> bool:
    """Whether the top of the screen is dark, so the status bar goes light."""
    strip = screen.crop((0, 0, SCREEN_W, 59 * SCALE)).convert("L").resize((1, 1))
    return strip.getpixel((0, 0)) < 128


def phone(screenshot: Path, *, shadow: bool = True) -> Image.Image:
    """The screenshot in an iPhone, on a transparent canvas."""
    screen = Image.open(screenshot).convert("RGB")
    if screen.size != (SCREEN_W, SCREEN_H):
        raise ValueError(
            f"{screenshot.name} is {screen.size}; expected {(SCREEN_W, SCREEN_H)} "
            "(render with SZ_MARKETING_DEVICE=iphone)"
        )
    dark = _is_dark(screen)
    ink = (250, 250, 252) if dark else (18, 20, 28)

    # The status bar, drawn straight onto the screen's own reserved band.
    draw = ImageDraw.Draw(screen)
    _status_bar(draw, ink, 0, 0)

    # The Dynamic Island, with the faintest lens inside it.
    iw, ih = 126 * SCALE, 37 * SCALE
    ix = (SCREEN_W - iw) // 2
    iy = 11 * SCALE
    draw.rounded_rectangle((ix, iy, ix + iw, iy + ih), radius=ih // 2, fill=(0, 0, 0))
    lens_r = 5 * SCALE
    lx, ly = ix + iw - ih // 2 - 4 * SCALE, iy + ih // 2
    draw.ellipse(
        (lx - lens_r, ly - lens_r, lx + lens_r, ly + lens_r), fill=(18, 20, 30)
    )
    draw.ellipse(
        (lx - lens_r * 0.35, ly - lens_r * 0.35, lx + lens_r * 0.35, ly + lens_r * 0.35),
        fill=(40, 48, 72),
    )

    # The home indicator.
    hw, hh = 134 * SCALE, 5 * SCALE
    hx = (SCREEN_W - hw) // 2
    hy = SCREEN_H - 8 * SCALE - hh
    draw.rounded_rectangle(
        (hx, hy, hx + hw, hy + hh), radius=hh // 2,
        fill=(236, 237, 242) if dark else (22, 24, 32),
    )

    canvas = Image.new("RGBA", (BODY_W + 2 * PAD, BODY_H + 2 * PAD), (0, 0, 0, 0))
    bx, by = PAD, PAD

    # The shadow: the body's silhouette, blurred and dropped.
    if shadow:
        silhouette = Image.new("L", canvas.size, 0)
        silhouette.paste(_rounded_mask((BODY_W, BODY_H), BODY_RADIUS), (bx, by + 46))
        silhouette = silhouette.filter(ImageFilter.GaussianBlur(56))
        shade = Image.new("RGBA", canvas.size, (10, 12, 22, 0))
        shade.putalpha(silhouette.point(lambda v: round(v * 0.42)))
        canvas.alpha_composite(shade)

    # The side buttons, behind the rim so only their edges show.
    buttons = ImageDraw.Draw(canvas)
    button = (58, 58, 62, 255)
    for top, height in ((250, 100), (430, 190), (660, 190)):  # action, volume up, down
        buttons.rounded_rectangle(
            (bx - 7, by + top, bx + 10, by + top + height), radius=6, fill=button
        )
    buttons.rounded_rectangle(
        (bx + BODY_W - 10, by + 540, bx + BODY_W + 7, by + 830), radius=6, fill=button
    )

    # The titanium rim: a graphite gradient with a lit edge.
    rim = _vertical_gradient((BODY_W, BODY_H), (78, 78, 84), (40, 40, 44)).convert("RGBA")
    rim.putalpha(_rounded_mask((BODY_W, BODY_H), BODY_RADIUS))
    canvas.alpha_composite(rim, (bx, by))
    edge = Image.new("RGBA", (BODY_W, BODY_H), (0, 0, 0, 0))
    ImageDraw.Draw(edge).rounded_rectangle(
        (1, 1, BODY_W - 2, BODY_H - 2), radius=BODY_RADIUS - 1,
        outline=(150, 150, 158, 150), width=2,
    )
    canvas.alpha_composite(edge, (bx, by))

    # The black bezel, then the screen inside it.
    bezel = Image.new("RGBA", (BODY_W - 2 * RIM, BODY_H - 2 * RIM), (4, 4, 6, 255))
    bezel.putalpha(_rounded_mask(bezel.size, BEZEL_RADIUS))
    canvas.alpha_composite(bezel, (bx + RIM, by + RIM))

    shown = screen.convert("RGBA")
    shown.putalpha(_rounded_mask((SCREEN_W, SCREEN_H), SCREEN_RADIUS))
    canvas.alpha_composite(shown, (bx + RIM + BEZEL, by + RIM + BEZEL))
    return canvas


def trim(image: Image.Image) -> Image.Image:
    """Crops away fully transparent margin, keeping the shadow."""
    box = image.getchannel("A").point(lambda v: 255 if v > 3 else 0).getbbox()
    return image.crop(box) if box else image


if __name__ == "__main__":
    import sys

    out = phone(Path(sys.argv[1]))
    out.save(sys.argv[2])
    print(out.size)
