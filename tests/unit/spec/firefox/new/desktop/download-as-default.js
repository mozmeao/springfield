/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/* For reference read the Jasmine and Sinon docs
 * Jasmine docs: https://jasmine.github.io/
 * Sinon docs: http://sinonjs.org/docs/
 */

import DownloadAsDefault from '../../../../../../media/js/firefox/download/desktop/download-as-default-v2.es6';

describe('download-as-default.es6.js', function () {
    beforeEach(function () {
        const optOut = `<div id="opt-out">
            <label for="default-opt-out-primary" class="default-browser-label hidden">
                <input type="checkbox" id="default-opt-out-primary"" class="default-browser-checkbox">
                Set Firefox as your default browser.
            </label>
            <label for="default-opt-out-secondary" class="default-browser-label hidden">
                <input type="checkbox" id="default-opt-out-secondary" class="default-browser-checkbox">
                Set Firefox as your default browser.
            </label>
        </div>`;

        document.body.insertAdjacentHTML('beforeend', optOut);
    });

    beforeEach(function () {
        window.site.platform = 'windows';
        window.site.fxSupported = 'true';
    });

    afterEach(function () {
        const optOut = document.getElementById('opt-out');
        optOut.parentNode.removeChild(optOut);

        document
            .getElementsByTagName('html')[0]
            .removeAttribute('data-needs-consent');

        window.site.platform = 'other';
    });

    describe('meetsRequirements', function () {
        it('should return false if OS is not Windows', function () {
            window.site.platform = 'osx';

            const result = DownloadAsDefault.meetsRequirements();
            expect(result).toBeFalse();
        });

        it('should return false if OS is too old', function () {
            window.site.fxSupported = false;

            const result = DownloadAsDefault.meetsRequirements();
            expect(result).toBeFalse();
        });

        it('should return false if attribution requirements are not satisfied', function () {
            spyOn(
                window.Mozilla.DownloadAttribution,
                'meetsFunctionalRequirements'
            ).and.returnValue(false);

            const result = DownloadAsDefault.meetsRequirements();
            expect(result).toBeFalse();
        });

        it('should return true if attribution requirements are satisfied', function () {
            const result = DownloadAsDefault.meetsRequirements();
            expect(result).toBeTrue();
        });
    });
    describe('init()', function () {
        it('should refresh attribution data when visitor unchecks input', function () {
            spyOn(DownloadAsDefault, 'meetsRequirements').and.returnValue(true);
            spyOn(window.Mozilla.DownloadAttribution, 'removeAttributionData');
            spyOn(
                window.Mozilla.DownloadAttribution,
                'initEssential'
            ).and.callFake((campaign, successCallback) => {
                successCallback();
            });

            const result = DownloadAsDefault.init();
            expect(result).toBeTrue();

            let checkboxes = document.querySelectorAll(
                '.default-browser-checkbox:checked'
            );
            expect(checkboxes.length).toEqual(2);

            document.getElementById('default-opt-out-primary').click();

            expect(
                window.Mozilla.DownloadAttribution.initEssential
            ).toHaveBeenCalledWith(
                null,
                jasmine.any(Function),
                jasmine.any(Function)
            );

            checkboxes = document.querySelectorAll(
                '.default-browser-checkbox:checked'
            );
            expect(checkboxes.length).toEqual(0);
        });

        it('should opt back into essential attribution if visitor re-checks input', function () {
            spyOn(DownloadAsDefault, 'meetsRequirements').and.returnValue(true);
            spyOn(window.Mozilla.DownloadAttribution, 'removeAttributionData');
            spyOn(
                window.Mozilla.DownloadAttribution,
                'initEssential'
            ).and.callFake((campaign, successCallback) => {
                successCallback();
            });

            const result = DownloadAsDefault.init();
            expect(result).toBeTrue();

            expect(
                window.Mozilla.DownloadAttribution.initEssential
            ).toHaveBeenCalledWith(
                'SET_DEFAULT_BROWSER',
                jasmine.any(Function),
                jasmine.any(Function)
            );

            let checkboxes = document.querySelectorAll(
                '.default-browser-checkbox:checked'
            );
            expect(checkboxes.length).toEqual(2);

            // Opt out
            document.getElementById('default-opt-out-primary').click();
            expect(
                window.Mozilla.DownloadAttribution.initEssential
            ).toHaveBeenCalledWith(
                null,
                jasmine.any(Function),
                jasmine.any(Function)
            );

            checkboxes = document.querySelectorAll(
                '.default-browser-checkbox:checked'
            );
            expect(checkboxes.length).toEqual(0);

            // Opt in
            document.getElementById('default-opt-out-secondary').click();
            expect(
                window.Mozilla.DownloadAttribution.initEssential
            ).toHaveBeenCalledWith(
                'SET_DEFAULT_BROWSER',
                jasmine.any(Function),
                jasmine.any(Function)
            );

            checkboxes = document.querySelectorAll(
                '.default-browser-checkbox:checked'
            );
            expect(checkboxes.length).toEqual(2);
        });
    });
});
