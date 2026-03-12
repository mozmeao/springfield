/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/* Show/hide the "Custom text" field in FluentOrCustomTextBlock (StructBlock
 * inside StreamField) and PreFooterCTASnippet (model FieldPanels) based on
 * whether "Custom text" is selected in the preset dropdown.
 *
 * Follows the same IIFE + load/change pattern used by wagtail-link-block's
 * link_block.js so that dynamically-added StreamField blocks are handled via
 * event delegation on window.
 *
 * For StructBlock instances the custom_text field starts hidden thanks to the
 * form_template (fluent_or_custom_text.html) which sets hidden on the wrapper.
 */
(function () {
    'use strict';

    var CUSTOM_VALUE = 'custom';

    // -- StructBlock context (FluentOrCustomTextBlock in StreamField) --------

    function toggleStructBlockCustomField(select) {
        var block = select.closest('.fluent-or-custom-text-block');
        if (!block) return;
        var customField = block.querySelector(
            '.fluent-or-custom-text-block__custom-text'
        );
        if (!customField) return;

        if (select.value === CUSTOM_VALUE) {
            customField.removeAttribute('hidden');
        } else {
            customField.setAttribute('hidden', '');
        }
    }

    function initStructBlocks() {
        // With a custom form_template, Wagtail uses data-structblock-child
        // (not data-contentpath) for child block placeholders.
        var selects = document.querySelectorAll(
            '.fluent-or-custom-text-block select'
        );
        Array.prototype.forEach.call(selects, toggleStructBlockCustomField);
    }

    // -- Snippet FieldPanel context (PreFooterCTASnippet) --------------------

    function toggleSnippetCustomLabel(select) {
        var form = select.closest('form');
        if (!form) return;
        var customField = form.querySelector(
            '[data-contentpath="custom_label"]'
        );
        if (!customField) return;

        if (select.value === CUSTOM_VALUE) {
            customField.removeAttribute('hidden');
        } else {
            customField.setAttribute('hidden', '');
        }
    }

    function initSnippetPanels() {
        var selects = document.querySelectorAll(
            '[data-contentpath="pretranslated_label"] select'
        );
        Array.prototype.forEach.call(selects, toggleSnippetCustomLabel);
    }

    // -- Event wiring --------------------------------------------------------

    function onload() {
        initStructBlocks();
        initSnippetPanels();
    }

    function onchange(event) {
        var target = event.target;
        if (target.tagName !== 'SELECT') return;

        // StructBlock context
        if (target.closest('.fluent-or-custom-text-block')) {
            toggleStructBlockCustomField(target);
        }

        // Snippet FieldPanel context
        if (target.closest('[data-contentpath="pretranslated_label"]')) {
            toggleSnippetCustomLabel(target);
        }
    }

    window.addEventListener('load', onload);
    window.addEventListener('change', onchange);
})();
