# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Heading levels for the top-level blocks of a page region.

Conditional blocks are mutually exclusive alternatives that occupy one position, but
they are authored as consecutive siblings. Assigning heading levels by document order
therefore hands the second variant an <h2>, so a visitor who sees that one gets a page
whose top heading is an <h2> and whose <h1> is hidden.

Templates used to count headings inline with a Jinja namespace, once per region and
fourteen times over. Doing it here means one implementation and one place to fix.
"""

from dataclasses import dataclass
from typing import Any


def has_heading(block) -> bool:
    """Whether a block contributes a heading, mirroring what the templates rendered.

    Blocks nest a HeadingBlock under `heading`, or carry a flat `headline`. Values that
    are neither (rich text, lists) have no heading and no `.get`.
    """
    value = getattr(block, "value", None)
    if not hasattr(value, "get"):
        return False

    heading = value.get("heading")
    if hasattr(heading, "get") and heading.get("heading_text"):
        return True

    return bool(value.get("headline"))


def conditions_of(block) -> dict | None:
    """The block's display conditions, or None if an editor set none.

    Every ConditionalDisplayBlock child defaults to empty, so any truthy value means a
    condition is set. Stored JSON can predate a child, hence `.get`.
    """
    value = getattr(block, "value", None)
    if not hasattr(value, "get"):
        return None

    settings = value.get("settings")
    if not hasattr(settings, "get"):
        return None

    show_to = settings.get("show_to")
    if not hasattr(show_to, "items"):
        return None

    conditions = {key: _normalise(val) for key, val in show_to.items() if val}
    return conditions or None


def is_conditional(block) -> bool:
    """Whether an editor has restricted who sees this block."""
    return conditions_of(block) is not None


def _normalise(value):
    """Make condition values comparable — the multi-choice ones are order-insensitive."""
    return frozenset(value) if isinstance(value, list) else value


def are_alternatives(first, second) -> bool:
    """Whether two blocks can never be visible at the same time.

    Only blocks that differ on exactly one condition, with values that cannot both
    match, are alternatives. Requiring a single differing condition is deliberately
    strict: `firefox: is-firefox` and `platforms: [windows]` differ on two, and a
    Windows visitor running Firefox sees both, so they are sequential rather than
    alternatives and must not share a heading level.
    """
    a, b = conditions_of(first), conditions_of(second)
    if a is None or b is None:
        return False

    differing = [key for key in set(a) | set(b) if a.get(key) != b.get(key)]
    if len(differing) != 1:
        return False

    left, right = a.get(differing[0]), b.get(differing[0])
    if not left or not right:
        # one side leaves this condition open, so it also matches the other's audience
        return False
    if isinstance(left, frozenset) and isinstance(right, frozenset):
        return left.isdisjoint(right)
    return left != right


@dataclass(frozen=True)
class BlockSlot:
    """One logical position in a region, and the block rendered into it.

    `index` stays the raw authoring order, because analytics needs to tell variants
    apart even though they share a `position`.
    """

    block: Any
    index: int
    position: int
    heading_level: int | None

    @property
    def block_type(self) -> str:
        return self.block.block_type


def build_slots(blocks, start_level, seen_headings, flat_level=None):
    """Assign a logical position and heading level to each block in one region.

    Consecutive conditional blocks share a position: only one of them is ever visible,
    so they are alternatives at the same point in the page rather than a sequence.

    Returns the slots and the running heading count, which callers thread through the
    regions that share a counter.
    """
    blocks = list(blocks)
    positions = _positions(blocks)

    slots = []
    level_for_position: dict[int, int] = {}

    for index, (block, position) in enumerate(zip(blocks, positions), start=1):
        if flat_level is not None:
            level = flat_level
        elif not has_heading(block):
            # nothing at this level to anchor to, so let the block template pick its own
            level = None
        elif position in level_for_position:
            # a sibling variant at this position already claimed a level
            level = level_for_position[position]
        else:
            level = start_level if seen_headings == 0 else start_level + 1
            level_for_position[position] = level
            seen_headings += 1

        slots.append(BlockSlot(block=block, index=index, position=position, heading_level=level))

    if flat_level is not None and blocks:
        seen_headings += 1

    return slots, seen_headings


def _positions(blocks) -> list[int]:
    """Map each block to a logical position, collapsing runs of alternatives.

    A block joins the run only if it excludes every block already in it, so a run is
    always a set of genuine alternatives rather than merely adjacent conditionals.
    """
    positions = []
    position = -1
    run = []

    for block in blocks:
        if run and all(are_alternatives(block, other) for other in run):
            run.append(block)
        else:
            position += 1
            run = [block] if is_conditional(block) else []
        positions.append(position)

    return positions
