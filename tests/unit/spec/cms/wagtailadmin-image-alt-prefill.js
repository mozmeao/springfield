/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import {
    altInputForPreview,
    initImageAltPrefill
} from '../../../../media/js/cms/wagtailadmin-image-alt-prefill.es6';

describe('wagtailadmin-image-alt-prefill.es6.js', function () {
    let container;
    let observer;

    /* Wagtail renders a chooser as an element with an id formed by the hidden
     * input's id plus the "-chooser", holding a preview image.
     * It sets the images's default alt text to a data-default-alt-text attribute.
     * Choosing an image is simulated by writing that
     * attribute, which is done by Wagtail's renderState method. */
    function buildChooser(prefix, { withAltInput = true } = {}) {
        const chooser = document.createElement('div');
        chooser.id = `${prefix}-chooser`;
        chooser.innerHTML = '<img data-chooser-image>';
        container.appendChild(chooser);

        if (withAltInput) {
            const altInput = document.createElement('input');
            altInput.id = `${prefix}_alt`;
            container.appendChild(altInput);
        }

        return chooser.querySelector('[data-chooser-image]');
    }

    function chooseImage(previewImage, defaultAltText) {
        previewImage.setAttribute('data-default-alt-text', defaultAltText);
        // Mutation records are delivered asynchronously.
        return new Promise((resolve) => window.setTimeout(resolve, 0));
    }

    beforeEach(function () {
        container = document.createElement('div');
        document.body.appendChild(container);
        observer = initImageAltPrefill();
    });

    afterEach(function () {
        observer.disconnect();
        container.remove();
    });

    describe('altInputForPreview', function () {
        it('should find the alt input paired with the preview image', function () {
            const previewImage = buildChooser('id_featured_image');
            expect(altInputForPreview(previewImage).id).toEqual(
                'id_featured_image_alt'
            );
        });

        it('should return null when the chooser has no paired alt input', function () {
            const previewImage = buildChooser('id_og_image', {
                withAltInput: false
            });
            expect(altInputForPreview(previewImage)).toBeNull();
        });
    });

    describe('prefilling', function () {
        it('should fill an empty alt input with the chosen image description', async function () {
            const previewImage = buildChooser('id_featured_image');

            await chooseImage(previewImage, 'A purple fox');

            expect(
                document.getElementById('id_featured_image_alt').value
            ).toEqual('A purple fox');
        });

        it('should leave the alt empty for a decorative image', async function () {
            const previewImage = buildChooser('id_featured_image');

            await chooseImage(previewImage, '');

            expect(
                document.getElementById('id_featured_image_alt').value
            ).toEqual('');
        });

        it('should keep wording the editor typed when the image is swapped', async function () {
            const previewImage = buildChooser('id_featured_image');
            const altInput = document.getElementById('id_featured_image_alt');

            await chooseImage(previewImage, 'A purple fox');
            altInput.value = 'The fox on the launch page';
            await chooseImage(previewImage, 'A red panda');

            expect(altInput.value).toEqual('The fox on the launch page');
        });

        it('should replace its own earlier value when the image is swapped', async function () {
            const previewImage = buildChooser('id_featured_image');

            await chooseImage(previewImage, 'A purple fox');
            await chooseImage(previewImage, 'A red panda');

            expect(
                document.getElementById('id_featured_image_alt').value
            ).toEqual('A red panda');
        });

        it('should fill only the alt input belonging to the chosen image', async function () {
            const chosenPreview = buildChooser('id_featured_image');
            buildChooser('id_listing_image');

            await chooseImage(chosenPreview, 'A purple fox');

            expect(
                document.getElementById('id_listing_image_alt').value
            ).toEqual('');
        });

        it('should do nothing when the chooser has no paired alt input', async function () {
            const previewImage = buildChooser('id_og_image', {
                withAltInput: false
            });

            await chooseImage(previewImage, 'A purple fox');

            expect(document.getElementById('id_og_image_alt')).toBeNull();
        });
    });
});
