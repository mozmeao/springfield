# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Data migration to convert button fields from list format to StreamValue format

from copy import deepcopy

from django.db import migrations

from wagtail.blocks.migrations.migrate_operation import MigrateStreamData
from wagtail.blocks.migrations.operations import BaseBlockOperation


class ConvertButtonsToStreamValueOperation(BaseBlockOperation):
    """Convert buttons from list of ButtonValue to StreamValue format."""

    def apply(self, block_value):
        value = deepcopy(block_value)
        return self._walk_and_transform(value)

    def _walk_and_transform(self, data):
        """Recursively walk through the block tree and transform buttons wherever found."""
        if isinstance(data, dict):
            # Transform buttons field if it exists and is a list
            if "buttons" in data and isinstance(data["buttons"], list):
                data["buttons"] = self._transform_button_list(data["buttons"])

            # Recursively transform nested structures
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    data[key] = self._walk_and_transform(value)

        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    data[i] = self._walk_and_transform(item)

        return data

    def _transform_button_list(self, buttons):
        """
        Transform a list of buttons to StreamValue format.

        Old format (with "type": "item"):
        [
            {
                'type': 'item',
                'value': {
                    'settings': {...},
                    'link': 'url',
                    'label': 'text'
                },
                'id': '...'
            }
        ]

        Or old format (direct ButtonValue):
        [
            {
                'settings': {...},
                'link': 'url',
                'label': 'text'
            }
        ]

        New format:
        [
            {
                'type': 'button',
                'value': {
                    'settings': {...},
                    'link': 'url',
                    'label': 'text'
                },
                'id': '...'
            }
        ]
        """
        new_buttons = []
        for button in buttons:
            if isinstance(button, dict):
                # Check if this has 'type' key
                if "type" in button:
                    # Has a type field - check if it needs conversion
                    if button["type"] == "item":
                        # Convert "item" to "button"
                        new_button = {
                            "type": "button",
                            "value": button.get("value", {}),
                            "id": button.get("id"),
                        }
                        new_buttons.append(new_button)
                    elif button["type"] == "button":
                        # Already correct, keep as is
                        new_buttons.append(button)
                    else:
                        # Unknown type, keep as is
                        new_buttons.append(button)
                elif "value" in button:
                    # Has 'value' but no 'type' - add type: button
                    new_button = {
                        "type": "button",
                        "value": button["value"],
                        "id": button.get("id"),
                    }
                    new_buttons.append(new_button)
                else:
                    # Direct button data (old format without type/value wrapper)
                    # Wrap it in the proper structure
                    new_button = {
                        "type": "button",
                        "value": button,
                        "id": button.get("id"),
                    }
                    # Remove 'id' from value if it exists there
                    if "id" in new_button["value"]:
                        del new_button["value"]["id"]
                    new_buttons.append(new_button)
            else:
                # Unknown format, keep as is
                new_buttons.append(button)

        return new_buttons

    @property
    def operation_name_fragment(self):
        return "convert_buttons_to_streamvalue"


# Define which blocks need to be processed
# These are the top-level block types that contain buttons either directly or in nested blocks
# The operation recursively processes all nested blocks, so we just need to specify the top-level paths
operations = [
    (ConvertButtonsToStreamValueOperation(), "intro"),
    (ConvertButtonsToStreamValueOperation(), "section"),
    # Note: Cards with buttons are nested inside section blocks, so they will be
    # processed by the recursive walker when we process "section" blocks above.
    # The walker processes: section -> content -> media_content/cards_list/step_cards -> buttons
]


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0014_alter_freeformpage_content_and_more"),
    ]

    operations = [
        MigrateStreamData(
            app_name="cms",
            model_name="WhatsNewPage",
            field_name="content",
            operations_and_block_paths=operations,
        ),
        MigrateStreamData(
            app_name="cms",
            model_name="FreeFormPage",
            field_name="content",
            operations_and_block_paths=operations,
        ),
    ]
