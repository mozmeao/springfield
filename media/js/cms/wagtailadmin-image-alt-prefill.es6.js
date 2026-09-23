/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
 * Fills an image's alt text field with the image's own description when an
 * editor picks it.
 *
 * An alt input is paired with its chooser by id: a chooser element `foo-chooser`
 * pairs with the alt text input `foo_alt`, whether `foo` is a page form field id
 * or a StructBlock child's hyphen-joined prefix.
 *
 * The value is only written when the editor has not typed their own, so swapping
 * the image never discards their wording. A decorative image carries an empty
 * default alt text, so it prefills nothing.
 */

const CHOOSER_ID_SUFFIX = '-chooser';
const DEFAULT_ALT_TEXT_ATTRIBUTE = 'data-default-alt-text';

/**
 * The alt text input corresponding to the chooser that holds this preview image,
 * or null when that chooser has no alt text field.
 */
export function altInputForPreview(previewImage) {
    const chooser = previewImage.closest(`[id$="${CHOOSER_ID_SUFFIX}"]`);

    if (!chooser) {
        return null;
    }

    const fieldId = chooser.id.slice(0, -CHOOSER_ID_SUFFIX.length);
    return document.getElementById(`${fieldId}_alt`);
}

/**
 * Starts watching for image choices. Returns the observer so it can be stopped.
 */
export function initImageAltPrefill() {
    const lastPrefilledValues = new WeakMap();

    const observer = new MutationObserver(function (records) {
        records.forEach(function (record) {
            const previewImage = record.target;
            const altInput = altInputForPreview(previewImage);

            if (!altInput) {
                return;
            }

            const defaultAltText =
                previewImage.getAttribute(DEFAULT_ALT_TEXT_ATTRIBUTE) || '';
            const lastPrefilledValue = lastPrefilledValues.get(altInput) || '';
            const editorTypedTheirOwnWording =
                altInput.value !== '' && altInput.value !== lastPrefilledValue;

            if (editorTypedTheirOwnWording) {
                return;
            }

            altInput.value = defaultAltText;
            lastPrefilledValues.set(altInput, defaultAltText);
        });
    });

    observer.observe(document.documentElement, {
        subtree: true,
        attributes: true,
        attributeFilter: [DEFAULT_ALT_TEXT_ATTRIBUTE]
    });

    return observer;
}
