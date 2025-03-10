# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ValidationError

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


class FeaturesVideoBlock(blocks.StructBlock):
    """Block for a features detail page video embed."""

    image = ImageChooserBlock(
        help_text="Video placeholder image.",
    )

    title = blocks.CharBlock(
        char_max_length=100,
        help_text="Video embed accessible title.",
    )

    youtube_video_id = blocks.CharBlock(
        required=False,
        char_max_length=100,
        help_text="YouTube video string ID to pass to embed.",
    )

    cdn_video_url = blocks.URLBlock(
        required=False,
        char_max_length=255,
        help_text="URL for webm format video hosted on https://assets.mozilla.net/.",
    )

    def clean(self, value):
        """
        Custom validation to ensure:
        - At least one of the youtube_video_id and cdn_video_url fields is filled.
        - Both fields are not filled at the same time.
        """
        errors = {}

        youtube_video_id = value.get("youtube_video_id", "").strip()
        cdn_video_url = value.get("cdn_video_url", "").strip()

        if not youtube_video_id and not cdn_video_url:
            error_msg = "At least one of 'Youtube vide id' or 'Video source url' must be filled."
            errors["video_embed"] = ValidationError(error_msg)

        if youtube_video_id and cdn_video_url:
            error_msg = "Only one of 'Youtube vide id' or 'Video source url' can be filled, not both."
            errors["video_embed"] = ValidationError(error_msg)

        if errors:
            raise ValidationError(errors)

        return super().clean(value)

    class Meta:
        icon = "media"
        label = "Video embed"
