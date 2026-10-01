/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
 * "Select all except aliases" for locale checkboxes.
 *
 * - Bulk translation checklists: buttons with `data-checklist-select`; alias
 *   locales' checkboxes carry a `data-alias` attribute.
 * - wagtail-localize's "Translate" form: a `select_all_except_aliases` checkbox
 *   added next to its own "Select all" by the SubmitTranslationForm patch; alias
 *   locales carry a `.locale-role-badge` in the label wrapping their checkbox.
 */

(function () {
    'use strict';

    function isAlias(checkbox) {
        var label = checkbox.closest('label');
        return (
            checkbox.hasAttribute('data-alias') ||
            Boolean(label && label.querySelector('.locale-role-badge'))
        );
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

    function initChecklists() {
        document
            .querySelectorAll('[data-translation-checklist]')
            .forEach(function (checklist) {
                var checkboxes = checklist.querySelectorAll(
                    'input[name="translations"]'
                );
                checklist
                    .querySelectorAll('[data-checklist-select]')
                    .forEach(function (button) {
                        button.addEventListener('click', function () {
                            setChecked(
                                checkboxes,
                                button.dataset.checklistSelect
                            );
                        });
                    });
            });
    }

    function initSubmitTranslationForm() {
        var exceptAliases = document.querySelector(
            'input[name="select_all_except_aliases"]'
        );
        if (!exceptAliases) return;

        var selectAll = document.querySelector('input[name="select_all"]');
        var locales = document.querySelectorAll('input[name="locales"]');

        exceptAliases.addEventListener('change', function () {
            if (selectAll) selectAll.checked = false;
            setChecked(locales, exceptAliases.checked ? 'non-alias' : 'none');
        });
        if (selectAll) {
            selectAll.addEventListener('change', function () {
                exceptAliases.checked = false;
            });
        }
    }

    // Submit buttons with `data-translation-confirm` ask before submitting.
    function initConfirmations() {
        document
            .querySelectorAll('[data-translation-confirm]')
            .forEach(function (button) {
                button.addEventListener('click', function (event) {
                    // eslint-disable-next-line no-alert
                    if (!window.confirm(button.dataset.translationConfirm)) {
                        event.preventDefault();
                    }
                });
            });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initChecklists();
        initSubmitTranslationForm();
        initConfirmations();
    });
})();
