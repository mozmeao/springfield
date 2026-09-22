/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
 * Fills an image's alt text field with the image's own description when an
 * editor picks it.
 *
 * Wagtail's chooser widgets dispatch their "chosen" event on the widget
 * object itself (an instance of window.Chooser, which extends EventTarget
 * directly), not on a DOM node, so the event never bubbles and cannot be
 * caught with a single document-level listener. Patching the shared
 * setStateFromModalData method instead reaches every chooser on the page -
 * both page form fields and StreamField blocks - however and whenever it was
 * constructed, since JavaScript looks up a method on the prototype chain at
 * call time rather than when the instance was created.
 *
 * An alt input is paired with its chooser by id: the chooser's hidden input
 * `foo` pairs with the alt text input `foo_alt`, whether `foo` is a page
 * form field id or a StructBlock child's hyphen-joined prefix - Wagtail
 * always appends a child field's own name to its parent's prefix as one
 * unbroken string, so the "_alt" suffix lines up in both cases.
 *
 * The value is only written when the editor has not typed their own, so
 * swapping the image never discards their wording. A decorative image
 * prefills nothing.
 */

document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    // Wagtail only loads window.Chooser as widget media on pages that actually
    // render a chooser, so most admin pages (login, dashboard, listings,
    // reports, settings) never load it at all.
    if (!document.querySelector('[id$="-chooser"]')) {
        return;
    }

    // window.Chooser and its setStateFromModalData method are Wagtail internals
    // we don't control: a future Wagtail upgrade could rename or restructure
    // either one. A page that has a chooser but not this method is the
    // genuine "Wagtail moved under us" signal, so it logs loudly here - this
    // patch must not attach to nothing and fail silently, since editors would
    // then keep shipping images with blank alt text with no error to explain
    // why.
    if (typeof window.Chooser !== 'function') {
        // eslint-disable-next-line no-console
        console.error(
            'wagtailadmin-image-alt-prefill: expected window.Chooser to be a function, but found',
            window.Chooser
        );
        return;
    }

    const originalSetStateFromModalData =
        window.Chooser.prototype.setStateFromModalData;
    if (typeof originalSetStateFromModalData !== 'function') {
        // eslint-disable-next-line no-console
        console.error(
            'wagtailadmin-image-alt-prefill: expected window.Chooser.prototype.setStateFromModalData to be a function, but found',
            originalSetStateFromModalData
        );
        return;
    }

    const lastPrefilledValues = new WeakMap();

    window.Chooser.prototype.setStateFromModalData = function (state) {
        const originalReturnValue = originalSetStateFromModalData.apply(
            this,
            arguments
        );

        // is_decorative is only present on the image chooser's response, so its
        // absence means this chooser is not one an alt text field can follow.
        // The typeof check comes first because the "in" operator throws on a
        // non-object, and state's shape here isn't ours to guarantee.
        if (
            typeof state !== 'object' ||
            !state ||
            !('is_decorative' in state)
        ) {
            return originalReturnValue;
        }

        const chooserInput = this.input;
        if (!chooserInput) {
            return originalReturnValue;
        }

        const altInput = document.getElementById(`${chooserInput.id}_alt`);
        if (!altInput) {
            return originalReturnValue;
        }

        const lastPrefilledValue = lastPrefilledValues.get(altInput) || '';
        const editorTypedTheirOwnWording =
            altInput.value !== '' && altInput.value !== lastPrefilledValue;
        if (editorTypedTheirOwnWording) {
            return originalReturnValue;
        }

        const nextValue = state.is_decorative
            ? ''
            : state.default_alt_text || '';
        altInput.value = nextValue;
        lastPrefilledValues.set(altInput, nextValue);

        return originalReturnValue;
    };
});
