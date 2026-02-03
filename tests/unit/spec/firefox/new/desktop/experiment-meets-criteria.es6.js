/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/* For reference read the Jasmine and Sinon docs
 * Jasmine docs: https://jasmine.github.io/
 * Sinon docs: http://sinonjs.org/docs/
 */

import { meetsExperimentCriteria } from '../../../../../../media/js/firefox/experiment-meets-criteria.es6.js';

describe('experiment-meets-criteria.es6.js', function () {
    beforeEach(function () {
        window.site.fxSupported = 'true';
    });

    afterEach(function () {
        document
            .getElementsByTagName('html')[0]
            .removeAttribute('data-needs-consent');
    });

    describe('meetsExperimentRequirements', function () {
        it('should return false if OS is too old', function () {
            window.site.fxSupported = false;

            const result = meetsExperimentCriteria();
            expect(result).toBeFalse();
        });

        it('should return false if cookies are disabled', function () {
            spyOn(window.Mozilla.Cookies, 'enabled').and.returnValue(false);

            const result = meetsExperimentCriteria();
            expect(result).toBeFalse();
        });

        it('should return false if visitor rejected analytics', function () {
            spyOn(window.Mozilla.Cookies, 'enabled').and.returnValue(true);
            spyOn(window.Mozilla.Cookies, 'hasItem')
                .withArgs('moz-consent-pref')
                .and.returnValue(true);
            spyOn(window.Mozilla.Cookies, 'getItem').and.returnValue(
                JSON.stringify({
                    analytics: false,
                    preference: true
                })
            );

            const result = meetsExperimentCriteria();
            expect(result).toBeFalse();
        });

        it('should return false if consent is required and we do not have analytics cookie', function () {
            document
                .getElementsByTagName('html')[0]
                .setAttribute('data-needs-consent', 'True');
            spyOn(window.Mozilla.Cookies, 'hasItem')
                .withArgs('moz-consent-pref')
                .and.returnValue(false);

            const result = meetsExperimentCriteria();
            expect(result).toBeFalse();
        });

        it('should return false if there is an existing stub attribution cookie', function () {
            spyOn(window.Mozilla.Cookies, 'hasItem')
                .withArgs('moz-consent-pref')
                .and.returnValue(false)
                .withArgs('moz-exp-download-privacy')
                .and.returnValue(false)
                .withArgs('moz-stub-attribution-code')
                .and.returnValue(true)
                .withArgs('moz-stub-attribution-sig')
                .and.returnValue(true);

            const result = meetsExperimentCriteria();
            expect(result).toBeFalse();
        });

        it('should return true if consent is not required and other attribution requirements met', function () {
            const result = meetsExperimentCriteria();
            expect(result).toBeTrue();
        });

        it('should return true if consent is required and other attribution requirements met', function () {
            document
                .getElementsByTagName('html')[0]
                .setAttribute('data-needs-consent', 'True');
            spyOn(window.Mozilla.Cookies, 'hasItem')
                .withArgs('moz-consent-pref')
                .and.returnValue(true);
            spyOn(window.Mozilla.Cookies, 'getItem').and.returnValue(
                JSON.stringify({
                    analytics: true,
                    preference: false
                })
            );

            const result = meetsExperimentCriteria();
            expect(result).toBeTrue();
        });
    });
});
