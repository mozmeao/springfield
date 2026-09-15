/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/* For reference read the Jasmine and Sinon docs
 * Jasmine docs: https://jasmine.github.io/
 * Sinon docs: http://sinonjs.org/docs/
 */

import {
    getSampleRate,
    withinSampleRate,
    initSampleRate
} from '../../../../media/js/cms/flare-sample-rate.es6';

describe('flare-sample-rate.es6.js', function () {
    const html = document.documentElement;

    describe('getSampleRate', function () {
        afterEach(function () {
            delete html.dataset.experimentSampleRate;
        });

        it('should return the sample rate as a percentage', function () {
            html.dataset.experimentSampleRate = '10';
            expect(getSampleRate()).toEqual(10);
        });

        it('should support rates below 1%', function () {
            html.dataset.experimentSampleRate = '0.1';
            expect(getSampleRate()).toEqual(0.1);
        });

        it('should return 0 if the data attribute is not present', function () {
            expect(getSampleRate()).toEqual(0);
        });

        it('should not return negative values', function () {
            html.dataset.experimentSampleRate = '-5';
            expect(getSampleRate()).toEqual(0);
        });

        it('should not return values greater than 100', function () {
            html.dataset.experimentSampleRate = '150';
            expect(getSampleRate()).toEqual(100);
        });

        it('should return 0 for non-numeric values', function () {
            html.dataset.experimentSampleRate = 'foo';
            expect(getSampleRate()).toEqual(0);
        });
    });

    describe('withinSampleRate', function () {
        it('should return true when the roll lands inside the rate', function () {
            spyOn(window.Math, 'random').and.returnValue(0.05);
            expect(withinSampleRate(10)).toBeTrue();
        });

        it('should return false when the roll lands outside the rate', function () {
            spyOn(window.Math, 'random').and.returnValue(0.15);
            expect(withinSampleRate(10)).toBeFalse();
        });
    });

    describe('initSampleRate', function () {
        beforeEach(function () {
            window.Mozilla.gpcEnabled = sinon.stub().returns(false);
            window.Mozilla.dntEnabled = sinon.stub().returns(false);
            window.dataLayer = [];
            html.dataset.experimentSampleRate = '10';
            html.dataset.experimentId = 'test-page';
        });

        afterEach(function () {
            delete window.Mozilla.gpcEnabled;
            delete window.Mozilla.dntEnabled;
            delete window.dataLayer;
            delete html.dataset.experimentSampleRate;
            delete html.dataset.experimentId;
            html.classList.remove('in-experiment-sample');
        });

        it('should reveal the page and log one experiment_view event when in the sample', function () {
            spyOn(window.Math, 'random').and.returnValue(0.05);
            initSampleRate();
            expect(html.classList.contains('in-experiment-sample')).toBeTrue();
            expect(window.dataLayer).toEqual([
                {
                    event: 'experiment_view',
                    id: 'test-page',
                    variant: 'in-sample'
                }
            ]);
        });

        it('should roll only once, so every sample-rated block on the page shares one roll', function () {
            spyOn(window.Math, 'random').and.returnValue(0.05);
            initSampleRate();
            expect(window.Math.random.calls.count()).toEqual(1);
        });

        it('should not reveal the page or log anything when outside the sample', function () {
            spyOn(window.Math, 'random').and.returnValue(0.5);
            initSampleRate();
            expect(html.classList.contains('in-experiment-sample')).toBeFalse();
            expect(window.dataLayer).toEqual([]);
        });

        it('should do nothing when there is no sample rate set', function () {
            delete html.dataset.experimentSampleRate;
            spyOn(window.Math, 'random').and.returnValue(0.05);
            initSampleRate();
            expect(html.classList.contains('in-experiment-sample')).toBeFalse();
            expect(window.dataLayer).toEqual([]);
        });

        it('should not reveal the page when Global Privacy Control is enabled', function () {
            window.Mozilla.gpcEnabled = sinon.stub().returns(true);
            spyOn(window.Math, 'random').and.returnValue(0.05);
            initSampleRate();
            expect(html.classList.contains('in-experiment-sample')).toBeFalse();
            expect(window.dataLayer).toEqual([]);
        });

        it('should not reveal the page when Do Not Track is enabled', function () {
            window.Mozilla.dntEnabled = sinon.stub().returns(true);
            spyOn(window.Math, 'random').and.returnValue(0.05);
            initSampleRate();
            expect(html.classList.contains('in-experiment-sample')).toBeFalse();
            expect(window.dataLayer).toEqual([]);
        });
    });
});
