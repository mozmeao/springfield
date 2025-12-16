/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

// Show/hide the "Copy URL for translations" field based on link type selection
(function () {
    'use strict';

    function setSynchronizeUrlVisibility(link_type_selector) {
        // Find the parent link block container
        var link_block = link_type_selector.closest('.link_block');
        if (!link_block) {
            return;
        }

        // Find the field by its label (most reliable way to get the outer wrapper)
        var label = link_block.querySelector('label[for$="-synchronize_url"]');
        if (!label) {
            return;
        }

        // The parent of the label is the field wrapper we want to hide
        var synchronize_url_field = label.parentElement;

        // Hide by default
        synchronize_url_field.classList.add('link-block__hidden');

        // Show only when custom_url is selected
        if (link_type_selector.value === 'custom_url') {
            synchronize_url_field.classList.remove('link-block__hidden');
        }
    }

    function onload() {
        var link_choice_type_selectors = document.querySelectorAll(
            '.link_choice_type_selector select'
        );
        Array.prototype.forEach.call(
            link_choice_type_selectors,
            setSynchronizeUrlVisibility
        );
    }

    function onchange(event) {
        var link_choice_type_selector = event.target.closest(
            '.link_choice_type_selector'
        );
        if (link_choice_type_selector) {
            var select = link_choice_type_selector.querySelector('select');
            if (select) {
                setSynchronizeUrlVisibility(select);
            }
        }
    }

    window.addEventListener('load', onload);
    window.addEventListener('change', onchange);
})();
