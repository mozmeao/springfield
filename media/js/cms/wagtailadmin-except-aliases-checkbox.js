/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
 * "Select all except aliases" for locale checkboxes in wagtail-localize's
 * "Translate" form: a `select_all_except_aliases` checkbox added next to its
 * own "Select all" by the SubmitTranslationForm patch; alias locales carry a
 * `.locale-role-badge` in the label wrapping their checkbox.
 */

(function () {
    'use strict';

    function isAlias(checkbox) {
        const label = checkbox.closest('label');
        return label.querySelector('.locale-role-badge');
    }

    function setChecked(checkboxes, mode) {
        checkboxes.forEach(function (checkbox) {
            if (mode === 'all') {
                checkbox.checked = true;
            } else if (mode === 'non-alias') {
                checkbox.checked = !isAlias(checkbox);
            } else {
                checkbox.checked = false;
            }
        });
    }

    function initSubmitTranslationForm() {
        const exceptAliases = document.querySelector(
            'input[name="select_all_except_aliases"]'
        );
        if (!exceptAliases) {
            return;
        }

        const selectAll = document.querySelector('input[name="select_all"]');
        const locales = document.querySelectorAll('input[name="locales"]');

        exceptAliases.addEventListener('change', function () {
            if (selectAll) {
                selectAll.checked = false;
            }
            setChecked(locales, exceptAliases.checked ? 'non-alias' : 'none');
        });
        if (selectAll) {
            selectAll.addEventListener('change', function () {
                exceptAliases.checked = false;
            });
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        initSubmitTranslationForm();
    });
})();
