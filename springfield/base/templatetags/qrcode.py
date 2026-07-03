# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import base64
import os
from hashlib import sha1
from io import BytesIO

from django.conf import settings
from django.core.cache import caches

import qrcode as qr
from django_jinja import library
from markupsafe import Markup
from PIL import Image, ImageDraw
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask
from qrcode.image.styles.moduledrawers.pil import SquareModuleDrawer
from qrcode.image.svg import SvgPathFillImage

cache = caches["qrcode"]

_FIREFOX_LOGO_PNG = os.path.join(settings.ROOT_PATH, "media/img/logos/firefox/firefox-flame-qr.png")


def _draw_rounded_eyes(qr_img, pil_img, box_size, modules_count):
    """Overdraw the three QR finder-pattern squares as squircle shapes."""
    draw = ImageDraw.Draw(pil_img)
    dark = (51, 51, 51)
    light = (255, 255, 255)
    outer_r = int(box_size * 1.5)
    ring_r = int(outer_r * 5 / 7)  # inner white gap — proportional to outer radius
    inner_r = int(box_size * 0.75)
    eye_px = 7 * box_size

    eye_starts = [
        (0, 0),
        (0, modules_count - 7),
        (modules_count - 7, 0),
    ]
    for row_s, col_s in eye_starts:
        x0, y0 = qr_img.pixel_box(row_s, col_s)[0]
        # Erase full 7×7 to white so rounded corners aren't covered by existing dark modules
        draw.rectangle([x0, y0, x0 + eye_px - 1, y0 + eye_px - 1], fill=light)
        # Outer 7×7 rounded rectangle
        draw.rounded_rectangle([x0, y0, x0 + eye_px - 1, y0 + eye_px - 1], radius=outer_r, fill=dark)
        # White interior (5×5) — also rounded so the inner corners of the ring match
        ix0, iy0 = qr_img.pixel_box(row_s + 1, col_s + 1)[0]
        ring_px = 5 * box_size
        draw.rounded_rectangle([ix0, iy0, ix0 + ring_px - 1, iy0 + ring_px - 1], radius=ring_r, fill=light)
        # Center 3×3 rounded dot
        cx0, cy0 = qr_img.pixel_box(row_s + 2, col_s + 2)[0]
        dot_px = 3 * box_size
        draw.rounded_rectangle([cx0, cy0, cx0 + dot_px - 1, cy0 + dot_px - 1], radius=inner_r, fill=dark)


@library.global_function
def qrcode(data, box_size=20):
    key = sha1(f"{data}-{box_size}".encode()).hexdigest()
    svg = cache.get(key)
    if not svg:
        img = qr.make(data, image_factory=SvgPathFillImage, box_size=box_size)
        svg = BytesIO()
        img.save(svg)
        svg = svg.getvalue().decode("utf-8")
        cache.set(key, svg)

    return Markup(svg)


@library.global_function
def qrcode_rounded(data, box_size=20):
    key = sha1(f"rounded-{data}-{box_size}".encode()).hexdigest()
    b64 = cache.get(key)
    if not b64:
        qr_obj = qr.QRCode(
            error_correction=qr.constants.ERROR_CORRECT_H,
            box_size=box_size,
            border=4,
        )
        qr_obj.add_data(data)
        qr_obj.make(fit=True)
        qr_img = qr_obj.make_image(
            image_factory=StyledPilImage,
            module_drawer=SquareModuleDrawer(),
            eye_drawer=SquareModuleDrawer(),
            color_mask=SolidFillColorMask(front_color=(51, 51, 51)),
            embedded_image_path=_FIREFOX_LOGO_PNG,
            embedded_image_ratio=0.20,
        )
        # Save then reopen as plain PIL Image for post-processing
        buf = BytesIO()
        qr_img.save(buf, format="PNG")
        buf.seek(0)
        pil_img = Image.open(buf).convert("RGB")

        _draw_rounded_eyes(qr_img, pil_img, box_size, qr_obj.modules_count)

        buf2 = BytesIO()
        pil_img.save(buf2, format="PNG")
        b64 = base64.b64encode(buf2.getvalue()).decode()
        cache.set(key, b64)
    return Markup(f'<img src="data:image/png;base64,{b64}" alt="" aria-hidden="true">')
