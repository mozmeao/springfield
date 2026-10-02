# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from uuid import uuid4

from springfield.cms.fixtures.base_fixtures import SHOW_TO_ALL

ANIMATION_URL = "https://assets.mozilla.net/video/red-pandas.webm"


# Links, buttons and display conditions


def link_value(custom_url="", page=None, relative_url="", link_to=None, new_window=False):
    """A SpringfieldLinkBlock value. Links to ``page`` when one is given, otherwise to ``custom_url``,
    unless ``link_to`` names another target such as ``relative_url``, or is empty for no link."""
    if link_to is None:
        link_to = "page" if page else "custom_url"
    return {
        "link_to": link_to,
        "page": page.id if page else None,
        "file": None,
        "custom_url": custom_url,
        "anchor": "",
        "email": "",
        "phone": "",
        "new_window": new_window,
        "relative_url": relative_url,
    }


def link_block(block_id, label, analytics_id, custom_url, new_window=False):
    return {
        "type": "link",
        "value": {
            "settings": {"analytics_id": analytics_id},
            "label": label,
            "link": link_value(custom_url=custom_url, new_window=new_window),
        },
        "id": block_id,
    }


def button(block_id, label, analytics_id, url="", page=None, theme="", size=""):
    return {
        "type": "button",
        "value": {
            "settings": {
                "theme": theme,
                "size": size,
                "icon": "",
                "icon_position": "right",
                "analytics_id": analytics_id,
            },
            "pretranslated_label": None,
            "custom_label": label,
            "link": link_value(custom_url=url, page=page),
        },
        "id": block_id,
    }


def download_button(block_id, label, analytics_id, theme=""):
    return {
        "type": "download_button",
        "value": {
            "pretranslated_label": None,
            "custom_label": label,
            "settings": {
                "theme": theme,
                "icon": "downloads",
                "icon_position": "right",
                "analytics_id": analytics_id,
                "show_default_browser_checkbox": False,
            },
        },
        "id": block_id,
    }


def buttons_block(block_id, buttons):
    return {"type": "buttons", "value": buttons, "id": block_id}


def button_row(block_id, buttons, orientation="horizontal", spacing="", alignment="", help_text=""):
    return {
        "type": "button_row",
        "value": {
            "orientation": orientation,
            "spacing": spacing,
            "alignment": alignment,
            "buttons": buttons,
            "help_text": help_text,
        },
        "id": block_id,
    }


def show_to_value(
    platforms=None,
    firefox="",
    auth_state="",
    default_browser="",
    min_version=None,
    max_version=None,
    geo=None,
    ai_controls="",
    bind_to_uitour=False,
    min_days_since_last_session=None,
    max_days_since_last_session=None,
    sample_rate=None,
):
    """A ConditionalDisplayBlock value; with no arguments it shows the block to everyone."""
    return {
        "platforms": platforms or [],
        "firefox": firefox,
        "auth_state": auth_state,
        "default_browser": default_browser,
        "min_version": min_version,
        "max_version": max_version,
        "geo": geo or [],
        "ai_controls": ai_controls,
        "bind_to_uitour": bind_to_uitour,
        "min_days_since_last_session": min_days_since_last_session,
        "max_days_since_last_session": max_days_since_last_session,
        "sample_rate": sample_rate,
    }


# Headings and text


def heading_value(block_key, heading_text, subheading_text="", superheading_text=""):
    """A heading StructBlock value; ``block_key`` prefixes the rich text block keys."""
    return {
        "superheading_text": f'<p data-block-key="{block_key}sup">{superheading_text}</p>' if superheading_text else "",
        "heading_text": f'<p data-block-key="{block_key}head">{heading_text}</p>',
        "subheading_text": f'<p data-block-key="{block_key}sub">{subheading_text}</p>' if subheading_text else "",
    }


def heading_block(block_id, heading_text, subheading_text="", superheading_text=""):
    return {
        "type": "heading",
        "value": heading_value(block_id, heading_text, subheading_text=subheading_text, superheading_text=superheading_text),
        "id": block_id,
    }


def pricing_heading_block(block_id, heading_text, subheading_text="", superheading_text=""):
    return {
        "type": "pricing_heading",
        "value": heading_value(block_id, heading_text, subheading_text=subheading_text, superheading_text=superheading_text),
        "id": block_id,
    }


def subheading_block(block_id, text):
    return {
        "type": "subheading",
        "value": f'<p data-block-key="{block_id}">{text}</p>',
        "id": block_id,
    }


def rich_text(block_id, html):
    return {"type": "rich_text", "value": html, "id": block_id}


# Sections


def section(section_id, heading_text, content_blocks=None, subheading_text=""):
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": SHOW_TO_ALL, "anchor_id": ""},
            "heading": heading_value(section_id, heading_text, subheading_text=subheading_text),
            "content": content_blocks or [],
            "cta": [],
        },
        "id": section_id,
    }


def hero(block_id, heading_text, subheading_text, buttons, media, superheading_text=""):
    """A featured_image_section hero: heading, a button row, and the hero media."""
    return {
        "type": "featured_image_section",
        "value": {
            "scroll_to_see_more_snippet": None,
            "heading": heading_value(block_id, heading_text, subheading_text=subheading_text, superheading_text=superheading_text),
            "content": [button_row(f"{block_id}-btnrow", buttons=buttons)],
            "media": media,
        },
        "id": block_id,
    }


def banner(block_id, theme, heading_text, subheading_text, buttons, slim=False):
    return {
        "type": "banner",
        "value": {
            "settings": {
                "theme": theme,
                "media_after": False,
                "show_to": SHOW_TO_ALL,
                "anchor_id": "",
                "slim": slim,
                "remove_border_radius": False,
                "centralize_content": False,
            },
            "media": [],
            "heading": heading_value(block_id, heading_text, subheading_text=subheading_text),
            "content": [buttons_block(f"{block_id}-btns", buttons)],
        },
        "id": block_id,
    }


def media_content(block_id, heading_text, subheading_text, body_blocks, media, media_after=False):
    return {
        "type": "media_content",
        "value": {
            "settings": {"media_after": media_after},
            "media": media,
            "heading": heading_value(block_id, heading_text, subheading_text=subheading_text),
            "content": body_blocks,
        },
        "id": block_id,
    }


def intro(block_id, heading_text, subheading_text, content_blocks, media, layout="right", remove_border_radius=False):
    return {
        "type": "intro",
        "value": {
            "settings": {
                "layout": layout,
                "full_width": False,
                "slim": False,
                "anchor_id": "",
                "remove_border_radius": remove_border_radius,
            },
            "media": media,
            "heading": heading_value(block_id, heading_text, subheading_text=subheading_text),
            "content": content_blocks,
        },
        "id": block_id,
    }


def showcase(block_id, headline, caption_description, media):
    return {
        "type": "showcase",
        "value": {
            "settings": {"layout": "expanded"},
            "headline": f'<p data-block-key="{block_id}h">{headline}</p>',
            "media": media,
            "caption_title": "",
            "caption_description": f'<p data-block-key="{block_id}c">{caption_description}</p>',
        },
        "id": block_id,
    }


def notification_block(block_id, message, show_to, headline=None, color="purple", icon="information", closable=False):
    return {
        "type": "notification",
        "value": {
            "settings": {
                "icon": icon,
                "color": color,
                "stacked": False,
                "closable": closable,
                "show_to": show_to,
                "anchor_id": "",
            },
            **({"headline": f'<p data-block-key="{block_id}h">{headline}</p>'} if headline else {}),
            "message": f'<p data-block-key="{block_id}">{message}</p>',
        },
        "id": f"{block_id}-0000-0000-0000-000000000001",
    }


# Media


def image_value(image_id, dark_mode_image_id=None):
    """An image-with-variants value carrying only the main and dark mode images."""
    return {
        "image": image_id,
        "settings": {
            "dark_mode_image": dark_mode_image_id,
            "mobile_image": None,
            "dark_mode_mobile_image": None,
        },
    }


def image_block(block_id, image_id, dark_mode_image_id=None):
    return {"type": "image", "value": image_value(image_id, dark_mode_image_id), "id": block_id}


def animation_block(block_id, poster_image_id, show_pause_button=False):
    value = {
        "video_url": ANIMATION_URL,
        "alt": "Lorem ipsum animation.",
        "poster": poster_image_id,
        "playback": "autoplay_loop",
    }
    if show_pause_button:
        value["show_pause_button"] = True
    return {"type": "animation", "value": value, "id": block_id}


# Cards


def card_settings(variant="", align="start", expand_link=False):
    return {"variant": variant, "align": align, "expand_link": expand_link, "show_to": SHOW_TO_ALL}


def card(block_id, settings, content, media=None):
    return {
        "type": "card",
        "value": {
            "settings": settings,
            "media": media or [],
            "content": content,
        },
        "id": block_id,
    }


def card_content(block_id, content):
    return {"type": "content", "value": f'<p data-block-key="{block_id}c">{content}</p>', "id": f"{block_id}-content"}


def icon_card(block_id, icon, content, headline=""):
    """A Card with an icon in the media area above the body copy, optionally preceded by a heading."""
    content_blocks = [card_content(block_id, content)]
    if headline:
        content_blocks.insert(0, heading_block(f"{block_id}-heading", headline))
    return card(
        block_id,
        card_settings(),
        content_blocks,
        media=[{"type": "icon", "value": icon, "id": f"{block_id}-icon"}],
    )


def pictogram_card(block_id, headline, content, pictogram):
    """An outline, left-aligned Card with the ``pictogram`` image value in the top media area."""
    return card(
        block_id,
        card_settings(variant="outline"),
        [heading_block(f"{block_id}-heading", headline), card_content(block_id, content)],
        media=[{"type": "pictogram", "value": pictogram, "id": f"{block_id}-pictogram"}],
    )


def illustration_card(block_id, headline, content, media):
    """A Card with the full-width ``media`` blocks above the heading and body copy."""
    return card(
        block_id,
        card_settings(),
        [heading_block(f"{block_id}-heading", headline), card_content(block_id, content)],
        media=[{"type": "media", "value": media, "id": f"{block_id}-media"}],
    )


def testimonial_card(block_id, content, attribution, attribution_role, attribution_image):
    return {
        "type": "card",
        "value": {
            "settings": card_settings(variant="outline"),
            "content": [
                {
                    "type": "testimonial",
                    "value": {
                        "content": content,
                        "attribution": attribution,
                        "attribution_role": attribution_role,
                        "attribution_image": attribution_image,
                    },
                    "id": f"{block_id[:7]}-0000-0000-0000-000000000010",
                }
            ],
        },
        "id": block_id,
    }


def cards_list(block_id, cards, container_width="", cards_per_row="", two_wide_xs=False):
    return {
        "type": "cards_list",
        "value": {
            "settings": {"container_width": container_width, "cards_per_row": cards_per_row, "two_wide_xs": two_wide_xs},
            "cards": cards,
        },
        "id": block_id,
    }


def two_column_card(block_id, content_blocks, tag="", image_position=""):
    return {
        "type": "card",
        "value": {
            "settings": {"image_position": image_position},
            "tag": tag,
            "content": content_blocks,
        },
        "id": block_id,
    }


def two_column_cards(block_id, cards, anchor_id="", theme="light-dark", reduce_card_padding=False):
    return {
        "type": "two_column_cards",
        "value": {
            "settings": {
                "show_to": SHOW_TO_ALL,
                "anchor_id": anchor_id,
                "theme": theme,
                "reduce_card_padding": reduce_card_padding,
            },
            "cards": cards,
        },
        "id": block_id,
    }


# Lists


def icon_list_item(item_id, icon, text):
    return {
        "type": "item",
        "value": {
            "icon": icon,
            "text": f'<p data-block-key="{item_id}">{text}</p>',
        },
        "id": item_id,
    }


def icon_list(block_id, items):
    """An icon list built from ``items``, each a dict with ``icon`` and ``text``."""
    return {
        "type": "icon_list",
        "value": {
            "list_items": [icon_list_item(f"{block_id}i{index}", item["icon"], item["text"]) for index, item in enumerate(items)],
        },
        "id": block_id,
    }


def numbered_list(block_id, items):
    """A numbered list built from ``items``, each a dict with ``heading`` and ``text``."""
    return {
        "type": "numbered_list",
        "value": {
            "list_items": [
                {
                    "type": "item",
                    "value": {
                        "heading": f'<p data-block-key="{block_id}h{index}">{item["heading"]}</p>',
                        "text": f'<p data-block-key="{block_id}t{index}">{item["text"]}</p>',
                    },
                    "id": f"{block_id}n{index}",
                }
                for index, item in enumerate(items)
            ],
        },
        "id": block_id,
    }


def timeline(block_id, items):
    """A timeline built from ``items``, each a dict with ``superheading_text``, ``heading_text`` and ``subheading_text``."""
    return {
        "type": "timeline",
        "value": {
            "list_items": [
                {
                    "type": "item",
                    "value": {
                        "superheading_text": f'<p data-block-key="{block_id}s{index}">{item["superheading_text"]}</p>',
                        "heading_text": f'<p data-block-key="{block_id}h{index}">{item["heading_text"]}</p>',
                        "subheading_text": f'<p data-block-key="{block_id}sub{index}">{item["subheading_text"]}</p>',
                    },
                    "id": f"{block_id}ti{index}",
                }
                for index, item in enumerate(items)
            ],
        },
        "id": block_id,
    }


def certification_item(item_id, text, url=""):
    return {
        "type": "item",
        "value": {
            "text": text,
            "link": link_value(custom_url=url) if url else link_value(link_to=""),
        },
        "id": item_id,
    }


# Tables


def table_cell(cell_id, content, column_span=1):
    return {
        "type": "item",
        "value": {"content": content, "column_span": column_span},
        "id": cell_id,
    }


def table_row(row_id, cells):
    return {"type": "item", "value": {"cells": cells}, "id": row_id}


def browser_table_cell(cell_id, content, column_span=1, optional_content=None):
    return {
        "type": "item",
        "value": {
            "content": content,
            "optional_content": optional_content or [],
            "column_span": column_span,
        },
        "id": cell_id,
    }


def browser_table_result_cell(cell_id, result, label=""):
    return browser_table_cell(
        cell_id,
        "",
        optional_content=[{"type": "comparison_result", "value": {"result": result, "label": label}, "id": f"{cell_id}-oc"}],
    )


def browser_table_image_header_cell(cell_id, label, image_id, dark_mode_image_id=None):
    return browser_table_cell(
        cell_id,
        "",
        optional_content=[
            {
                "type": "image_header",
                "value": {"image": image_id, "dark_mode_image": dark_mode_image_id, "alt": "", "label": label},
                "id": f"{cell_id}-oc",
            }
        ],
    )


# Smart Window


def smart_window_instructions(block_id, typewriter_text, instructions_text):
    return {
        "type": "smart_window_instructions",
        "value": {
            "pre_typewriter_text": "Type this",
            "typewriter_text": typewriter_text,
            "instructions": f'<p data-block-key="{block_id}i">{instructions_text}</p>',
        },
        "id": block_id,
    }


# Navigation


def nav_link(block_id, label, custom_url="", icon="", icon_position="left", has_button_style=False, new_window=False, analytics_id=None):
    return {
        "type": "link",
        "value": {
            "pretranslated_label": None,
            "custom_label": label,
            "link": link_value(custom_url=custom_url, new_window=new_window),
            "icon": icon,
            "icon_position": icon_position,
            "has_button_style": has_button_style,
            "analytics_id": analytics_id or str(uuid4()),
        },
        "id": block_id,
    }


def nav_separator(block_id):
    return {"type": "separator", "value": None, "id": block_id}


def nav_column(block_id, children):
    return {"type": "item", "value": children, "id": block_id}


def nav_folder(block_id, label, columns):
    return {
        "type": "folder",
        "value": {
            "pretranslated_label": None,
            "custom_label": label,
            "sub_items": columns,
        },
        "id": block_id,
    }


def nav_top_level_link(block_id, label, custom_url="", page=None, new_window=False, analytics_id=None):
    return {
        "type": "top_level_link",
        "value": {
            "pretranslated_label": None,
            "custom_label": label,
            "link": link_value(custom_url=custom_url, page=page, new_window=new_window),
            "analytics_id": analytics_id or str(uuid4()),
        },
        "id": block_id,
    }
