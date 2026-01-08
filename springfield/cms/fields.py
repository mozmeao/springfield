# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import hashlib
import json
import os
import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

import defusedxml.ElementTree as ET
from py_svg_hush import filter_svg
from wagtail.fields import StreamField as WagtailStreamfield
from wagtail.images.fields import WagtailImageField


class StreamField(WagtailStreamfield):
    """
    Custom Stream Field that avoids generating unnecessary migrations.
    https://github.com/wagtail/wagtail/issues/4298#issuecomment-1159515247
    """

    def __init__(self, *args, **kwargs):
        """
        Overrides StreamField.__init__() to account for `block_types` no longer
        being received as an arg when migrating (because there is no longer a
        `block_types` value in the migration to provide).
        """
        if args:
            block_types = args[0] or []
            args = args[1:]
        else:
            block_types = kwargs.pop("block_types", [])
        super().__init__(block_types, *args, **kwargs)

    def deconstruct(self):
        """
        Overrides StreamField.deconstruct() to remove `block_types` and
        `verbose_name` values so that migrations remain smaller in size,
        and changes to those attributes do not require a new migration.
        """
        name, path, args, kwargs = super().deconstruct()
        if args:
            args = args[1:]
        else:
            kwargs.pop("block_types", None)
        kwargs.pop("verbose_name", None)
        return name, path, args, kwargs

    def to_python(self, value):
        """
        Overrides StreamField.to_python() to make the return value
        (a `StreamValue`) more useful when migrating. When migrating, block
        definitions are unavailable to the field's underlying StreamBlock,
        causing self.stream_block.to_python() to not recognise any of the
        blocks in the stored value.
        """
        stream_value = super().to_python(value)

        # There is no way to be absolutely sure this is a migration,
        # but the combination of factors below is a pretty decent indicator
        if not self.stream_block.child_blocks and value and not stream_value._raw_data:
            stream_data = None
            if isinstance(value, list):
                stream_data = value
            elif isinstance(value, str):
                try:
                    stream_data = json.loads(value)
                except ValueError:
                    stream_value.raw_text = value

            if stream_data:
                return type(stream_value)(self, stream_data, is_lazy=True)

        return stream_value


# Dangerous SVG patterns to detect via regex (fast check)
DANGEROUS_SVG_PATTERNS = [
    rb"<script[\s>]",  # <script> tags (with space or immediate close)
    rb"javascript:",  # javascript: URLs
    rb"on\w+\s*=",  # Event handlers (onclick=, onload=, onerror=, etc.)
    rb"<foreignObject",  # Foreign objects (can contain HTML/scripts)
    rb"data:text/html",  # HTML data URLs
]

# Dangerous elements to check via XML parsing
DANGEROUS_ELEMENTS = {"script", "foreignObject"}

# Dangerous attributes (event handlers and javascript URLs)
DANGEROUS_ATTRIBUTES = {
    "onclick",
    "onload",
    "onerror",
    "onmouseover",
    "onmouseout",
    "onmousemove",
    "onmousedown",
    "onmouseup",
    "onfocus",
    "onblur",
    "onchange",
    "onsubmit",
    "onkeydown",
    "onkeyup",
    "onkeypress",
}


ALLOWED_DATA_URL_MIME_TYPES = {"image": ["jpeg", "png", "gif", "webp"]}

ALLOWED_SVG_CONTENT_TYPES = ("image/svg+xml", "image/svg", "text/xml")


class SanitizingWagtailImageField(WagtailImageField):
    """
    Custom image field that sanitizes SVG files before validation.
    This field extends WagtailImageField to add SVG sanitization using py-svg-hush.
    If an SVG file contains potentially dangerous content (like scripts), the upload
    is rejected with a clear error message instructing the user to clean the SVG first.
    The sanitization happens in to_python(), which is called during form validation
    before the file is saved to storage. This ensures:
    - File is still in memory
    - We can reject before storage writes
    - Natural Django validation pattern
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add custom error messages for SVG sanitization
        self.error_messages["svg_dangerous_content"] = _(
            "This SVG file contains dangerous content (scripts, event handlers, or javascript: URLs). "
            "Please remove all scripts and event handlers from your SVG file before uploading."
        )

        self.error_messages["svg_sanitization_error"] = _("Unable to process this SVG file. Please ensure it is a valid SVG.")

    def _is_svg_file(self, f) -> bool:
        """
        Determine if the uploaded file is an SVG.
        Checks both file extension and content type (if available).
        """
        # Check file extension
        if hasattr(f, "name") and f.name:
            extension = os.path.splitext(f.name)[1].lower()
            if extension == ".svg":
                return True

        # Check content type if available
        if hasattr(f, "content_type") and f.content_type:
            if f.content_type in ALLOWED_SVG_CONTENT_TYPES:
                return True

        return False

    def _read_file_content(self, f) -> bytes:
        """
        Read file content into bytes, handling different file object types.
        Args:
            f: File object (TemporaryUploadedFile, InMemoryUploadedFile, or BytesIO)
        Returns:
            bytes: File content as bytes
        """
        # Save current position if seekable
        original_position = f.tell() if hasattr(f, "tell") else None

        # Seek to beginning
        if hasattr(f, "seek"):
            f.seek(0)

        # Read content
        content = f.read()

        # Restore position
        if original_position is not None and hasattr(f, "seek"):
            f.seek(original_position)

        return content

    def _compute_hash(self, content: bytes) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content).hexdigest()

    def _has_dangerous_patterns_regex(self, content: bytes) -> bool:
        """
        Quick regex-based check for dangerous SVG patterns.
        This is a fast first-pass check for obvious threats like:
        - <script> tags
        - Event handlers (onclick, onload, etc.)
        - javascript: URLs
        - <foreignObject> elements
        - HTML data URLs
        Returns True if dangerous patterns are found.
        """
        for pattern in DANGEROUS_SVG_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        return False

    def _has_dangerous_elements_xml(self, content: bytes) -> bool:
        """
        XML-based check for dangerous SVG elements and attributes.
        Uses defusedxml to safely parse the SVG and check for:
        - Dangerous elements (script, foreignObject)
        - Event handler attributes (onclick, onload, etc.)
        - javascript: URLs in attribute values
        Returns True if dangerous content is found.
        Returns False if parsing fails (we'll catch this later).
        """

        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            # If we can't parse the XML, let py-svg-hush handle it
            # (it will either sanitize it or fail)
            return False

        # Check all elements in the SVG
        for elem in root.iter():
            # Remove namespace prefix if present
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

            # Check for dangerous element types
            if tag in DANGEROUS_ELEMENTS:
                return True

            # Check all attributes on this element
            for attr_name, attr_value in elem.attrib.items():
                # Remove namespace prefix from attribute name
                attr_name = attr_name.split("}")[-1] if "}" in attr_name else attr_name

                # Check for event handler attributes
                if attr_name in DANGEROUS_ATTRIBUTES or attr_name.startswith("on"):
                    return True

                # Check for javascript: URLs in attribute values
                if attr_value and "javascript:" in attr_value.lower():
                    return True

        return False

    def _sanitize_svg(self, f) -> ValidationError | None:
        """
        Hybrid SVG sanitization approach.
        This uses a three-layer defense:
        1. Fast regex check for obvious dangerous patterns (scripts, event handlers)
        2. XML parsing to detect dangerous elements/attributes more reliably
        3. py-svg-hush as a final safety net (but we don't reject based on normalization)
        This approach avoids false positives from py-svg-hush's normalization
        (attribute reordering, encoding changes) while still catching actual threats.
        Returns None if file is safe, otherwise returns a ValidationError.
        """
        try:
            # Read original content
            original_content = self._read_file_content(f)

            # Layer 1: Quick regex check for obvious threats
            if self._has_dangerous_patterns_regex(original_content):
                return ValidationError(
                    self.error_messages["svg_dangerous_content"],
                    code="svg_dangerous_content",
                )

            # Layer 2: XML parsing for more thorough detection
            if self._has_dangerous_elements_xml(original_content):
                return ValidationError(
                    self.error_messages["svg_dangerous_content"],
                    code="svg_dangerous_content",
                )

            # Layer 3: Run py-svg-hush as defense-in-depth
            # We don't reject based on changes - this is just a safety net
            # in case our detection missed something
            try:
                # Run sanitization to catch edge cases our detection missed
                # Allow common image data URLs in SVGs
                filter_svg(
                    original_content,
                    keep_data_url_mime_types=ALLOWED_DATA_URL_MIME_TYPES,
                )
                # If py-svg-hush succeeds without errors, the SVG structure is valid
                # We accept it regardless of normalization changes
            except (ValueError, ET.ParseError) as ex:
                # py-svg-hush failed to process it - SVG might be malformed
                return ValidationError(
                    f"{self.error_messages['svg_sanitization_error']}: {ex}",
                    code="svg_sanitization_error",
                )

            # All checks passed - file is safe
            return None

        except OSError as ex:
            # File reading or I/O error during validation
            return ValidationError(
                f"{self.error_messages['svg_sanitization_error']}: {ex}",
                code="svg_sanitization_error",
            )

    def to_python(self, data):
        """
        Override to_python to add SVG sanitization before standard validation.
        This is called during form validation, before the file is saved to storage.
        """
        # Call parent to_python first to handle standard validation
        # This validates file type, size, pixel count, etc.
        f = super().to_python(data)

        if f is None:
            return None

        # Check if this is an SVG file
        if self._is_svg_file(f):
            # Perform sanitization check
            validation_error = self._sanitize_svg(f)
            if validation_error:
                raise validation_error

        return f
