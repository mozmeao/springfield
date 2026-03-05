/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/* Extends wagtail_link_block's show/hide logic to support the relative_url link type.
 *
 * link_block.js hides all known fields and then shows the one matching the
 * selected type.  Because it doesn't know about relative_url, it falls through
 * to the else-branch and leaves relative_url_link_field hidden.  This script
 * listens to the same events and un-hides relative_url_link_field whenever
 * "relative_url" is the selected type.
 */
(function () {
    'use strict';

    function handleRelativeUrl(selector) {
        var parent = selector.closest('.link_block');
        if (!parent) return;
        var field = parent.querySelector('.relative_url_link_field');
        if (!field) return;
        var newWindowField = parent.querySelector('.new_window_link_field');

        if (selector.value === 'relative_url') {
            field.classList.remove('link-block__hidden');
            if (newWindowField) {
                newWindowField.classList.remove('link-block__hidden');
            }
        } else {
            field.classList.add('link-block__hidden');
        }
    }

    function onload() {
        var selectors = document.querySelectorAll(
            '.link_choice_type_selector select'
        );
        Array.prototype.forEach.call(selectors, handleRelativeUrl);
    }

    function onchange(event) {
        var linkChoiceDiv = event.target.closest('.link_choice_type_selector');
        if (linkChoiceDiv !== null) {
            handleRelativeUrl(event.target);
        }
    }

    // Run after link_block.js has already fired its own load/change handlers.
    window.addEventListener('load', onload);
    window.addEventListener('change', onchange);
})();
