# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Server-side signal resolvers.

Each function takes ``(request, context)`` and returns the signal's value or
``None`` if it could not be resolved for this request. ``context`` is a
dict passed by the caller — currently used to convey per-call state that
isn't in the request itself, such as the target WNP version (needed to
compute ``lapsed_user``).

All resolvers must be side-effect free and cheap — they run on every WNP
dispatch request.
"""

import re
from typing import Any

from springfield.base.geo import get_country_from_request

# --- Version-delta configuration ---
# Number of major-version steps between the user's oldversion and the target
# version that qualifies as "lapsed". Chosen deliberately conservative;
# eventually configurable per-release if marketing needs finer control.
LAPSED_MIN_GAP = 5

_OLDVERSION_RE = re.compile(r"^(?:rv:)?(\d{1,3})")
_FIREFOX_VERSION_RE = re.compile(r"\bFirefox/(\d+)")
_NON_FIREFOX_RE = re.compile(r"\b(?:Iceweasel|SeaMonkey|Camino)\b", re.IGNORECASE)


def _target_version_major(context: dict[str, Any]) -> int | None:
    raw = context.get("target_version")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _oldversion_major(request: Any) -> int | None:
    raw = request.GET.get("oldversion", "")
    m = _OLDVERSION_RE.match(raw)
    if not m:
        return None
    return int(m.group(1))


# ---------------------------------------------------------------------------
# Server-side signal resolvers
# ---------------------------------------------------------------------------


def resolve_country(request: Any, context: dict[str, Any]) -> str | None:
    """ISO-3166-alpha-2 country code from the CDN geo header."""
    return get_country_from_request(request)


def resolve_locale(request: Any, context: dict[str, Any]) -> str | None:
    """Locale code the URL was routed under (e.g. ``"en-US"``, ``"pt-BR"``)."""
    locale = getattr(request, "locale", None)
    if locale:
        return locale
    return getattr(request, "LANGUAGE_CODE", None)


def resolve_lapsed_user(request: Any, context: dict[str, Any]) -> bool | None:
    """True if the user's ``oldversion`` is at least :data:`LAPSED_MIN_GAP`
    major versions behind the target version.

    Unknown (``None``) if either the target version or the oldversion is
    missing / unparseable — different from ``False``, which would be a
    definitive "not lapsed".
    """
    target_major = _target_version_major(context)
    if target_major is None:
        return None
    old_major = _oldversion_major(request)
    if old_major is None:
        return None
    return (target_major - old_major) >= LAPSED_MIN_GAP


def resolve_platform(request: Any, context: dict[str, Any]) -> str | None:
    """Coarse OS family from the User-Agent.

    Values match the existing ``PLATFORM_CHOICES`` in ``cms/blocks.py``
    (``osx``, ``linux``, ``windows``, ``android``, ``ios``, ``other-os``).
    ``windows-10-plus`` is deliberately a separate refinement — see
    :func:`resolve_os_version`.
    """
    ua = request.headers.get("User-Agent", "")
    if not ua:
        return None
    if "Android" in ua:
        return "android"
    if any(token in ua for token in ("iPhone", "iPad", "iPod")):
        return "ios"
    if "Windows" in ua:
        return "windows"
    if "Mac OS X" in ua or "Macintosh" in ua:
        return "osx"
    if "Linux" in ua:
        return "linux"
    return "other-os"


def resolve_os_version(request: Any, context: dict[str, Any]) -> str | None:
    """A refinement token for the OS version, when it can be reliably parsed
    from the User-Agent.

    Returns ``"windows-10-plus"`` when the UA indicates Windows 10 or newer,
    ``None`` otherwise. Extend as marketing needs additional distinctions
    (Windows 11 specifically, macOS Sequoia+, etc.).
    """
    ua = request.headers.get("User-Agent", "")
    if not ua:
        return None
    # Windows 10 and 11 both send "Windows NT 10.0" in the UA — Microsoft
    # deliberately did not bump it for Windows 11. This is the closest we
    # can get from UA alone.
    if "Windows NT 10" in ua:
        return "windows-10-plus"
    return None


def resolve_is_firefox(request: Any, context: dict[str, Any]) -> bool | None:
    """True if the User-Agent identifies as Firefox (excluding known
    Firefox-derived UAs)."""
    ua = request.headers.get("User-Agent", "")
    if not ua:
        return None
    if _NON_FIREFOX_RE.search(ua):
        return False
    return "Firefox" in ua


def resolve_firefox_version(request: Any, context: dict[str, Any]) -> int | None:
    """Major Firefox version from the UA, if this is Firefox. ``None`` if not
    Firefox or if the version cannot be parsed."""
    if not resolve_is_firefox(request, context):
        return None
    ua = request.headers.get("User-Agent", "")
    m = _FIREFOX_VERSION_RE.search(ua)
    if not m:
        return None
    try:
        return int(m.group(1))
    except (TypeError, ValueError):
        return None
