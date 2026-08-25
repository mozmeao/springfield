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
from PIL import ImageDraw
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask
from qrcode.image.styles.moduledrawers.pil import CircleModuleDrawer, StyledPilQRModuleDrawer
from qrcode.image.svg import SvgPathFillImage

cache = caches["qrcode"]

FIREFOX_LOGO_PNG = os.path.join(settings.ROOT_PATH, "media/img/logos/firefox/firefox-logo-white-bg.png")


class RoundedEyeDrawer(StyledPilQRModuleDrawer):
    """Draw the three QR finder patterns (eyes) as concentric squircles.

    `qrcode.image.styles.moduledrawers.pil.RoundedModuleDrawer` rounds each module independently,
    so it can only shave a corner by up to half a module and leaves the concave inner corners of
    the finder frame square. This drawer instead paints the whole 7×7 eye as three rounded
    rectangles — outer frame, white gap, and centre dot — giving the larger, fully-rounded corners.
    """

    needs_neighbors = False

    def initialize(self, *args, **kwargs):
        super().initialize(*args, **kwargs)
        self.imgDraw = ImageDraw.Draw(self.img._img)
        box_size = self.img.box_size
        self.outer_radius = int(box_size * 1.5)
        self.ring_radius = int(self.outer_radius * 5 / 7)  # inner white gap — proportional to outer radius
        self.dot_radius = int(box_size * 0.75)
        # Module (row, col) coordinates of each eye's top-left corner.
        last = self.img.width - 7
        self.eye_origins = {(0, 0), (0, last), (last, 0)}

    def drawrect(self, box, is_active):
        box_size = self.img.box_size
        col = round(box[0][0] / box_size) - self.img.border
        row = round(box[0][1] / box_size) - self.img.border
        # Paint the whole eye once, when we reach its top-left module.
        if (row, col) not in self.eye_origins:
            return
        dark = self.img.paint_color
        light = self.img.color_mask.back_color
        x0, y0 = box[0]
        # Outer 7×7 rounded rectangle.
        eye_px = 7 * box_size
        self.imgDraw.rounded_rectangle([x0, y0, x0 + eye_px - 1, y0 + eye_px - 1], radius=self.outer_radius, fill=dark)
        # White interior (5×5) — also rounded so the inner corners of the ring match.
        ring_px = 5 * box_size
        ix0, iy0 = x0 + box_size, y0 + box_size
        self.imgDraw.rounded_rectangle([ix0, iy0, ix0 + ring_px - 1, iy0 + ring_px - 1], radius=self.ring_radius, fill=light)
        # Centre 3×3 rounded dot.
        dot_px = 3 * box_size
        cx0, cy0 = x0 + 2 * box_size, y0 + 2 * box_size
        self.imgDraw.rounded_rectangle([cx0, cy0, cx0 + dot_px - 1, cy0 + dot_px - 1], radius=self.dot_radius, fill=dark)


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
            module_drawer=CircleModuleDrawer(),
            eye_drawer=RoundedEyeDrawer(),
            color_mask=SolidFillColorMask(front_color=(51, 51, 51)),
            embedded_image_path=FIREFOX_LOGO_PNG,
            embedded_image_ratio=0.23,
        )
        buf = BytesIO()
        qr_img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        cache.set(key, b64)
    return Markup(f'<img src="data:image/png;base64,{b64}" alt="" aria-hidden="true">')
