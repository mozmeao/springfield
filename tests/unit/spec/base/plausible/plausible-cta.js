/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/* For reference read the Jasmine and Sinon docs
 * Jasmine docs: https://jasmine.github.io/
 * Sinon docs: http://sinonjs.org/docs/
 */

import Plausible from '../../../../../media/js/base/plausible/plausible.es6';
import TrackCTAClick from '../../../../../media/js/base/plausible/plausible-cta.es6';

describe('plausible-cta.es6.js', function () {
    const ctaProps = {
        cta_text: 'Get Firefox - Download',
        cta_uid: '1a2b3c4d',
        cta_position: 'upper-block-1-intro.button-1',
        cta_type: 'firefox'
    };
    let fixture;

    beforeEach(function () {
        fixture = document.createElement('div');
        fixture.innerHTML = `
            <button type="button" id="cta"
                data-cta-text=" Get Firefox - Download "
                data-cta-uid="1a2b3c4d"
                data-cta-position="upper-block-1-intro.button-1"
                data-cta-type="firefox">
                <span id="cta-label">Download</span>
            </button>
            <button type="button" id="uid-only" data-cta-uid="5e6f7a8b">Link</button>
            <button type="button" id="empty-attrs" data-cta-text="Sign in" data-cta-uid="" data-cta-position=" ">Sign in</button>
            <button type="button" id="not-a-cta">Close</button>
            <a id="empty-cta" data-cta-text="" data-cta-uid="" data-cta-type="firefox">Download</a>
            <a data-cta-text="App Store badge">
                <img id="cta-img" alt="">
            </a>
            <a data-cta-text="Get Firefox">
                <svg viewBox="0 0 10 10"><g><path id="cta-svg-path" d="M0 0h10v10H0z"/></g></svg>
            </a>`;
        document.body.appendChild(fixture);
        spyOn(Plausible, 'trackEvent');
    });

    afterEach(function () {
        fixture.remove();
    });

    describe('getProps', function () {
        it('should map every data-cta-* attribute to a trimmed prop', function () {
            const props = TrackCTAClick.getProps(
                document.getElementById('cta')
            );
            expect(props).toEqual(ctaProps);
        });

        it('should leave out missing and empty attributes', function () {
            const props = TrackCTAClick.getProps(
                document.getElementById('empty-attrs')
            );
            expect(props).toEqual({ cta_text: 'Sign in' });
        });
    });

    describe('handleClick', function () {
        it('should send cta_click for a click inside a CTA', function () {
            TrackCTAClick.handleClick({
                target: document.getElementById('cta-label')
            });
            expect(Plausible.trackEvent).toHaveBeenCalledOnceWith(
                'cta_click',
                ctaProps
            );
        });

        it('should send cta_click for a click on an image inside a CTA', function () {
            TrackCTAClick.handleClick({
                target: document.getElementById('cta-img')
            });
            expect(Plausible.trackEvent).toHaveBeenCalledOnceWith('cta_click', {
                cta_text: 'App Store badge'
            });
        });

        it('should send cta_click for a click on an SVG path inside a CTA', function () {
            const path = document.getElementById('cta-svg-path');
            expect(path instanceof SVGElement).toBe(true);

            TrackCTAClick.handleClick({ target: path });
            expect(Plausible.trackEvent).toHaveBeenCalledOnceWith('cta_click', {
                cta_text: 'Get Firefox'
            });
        });

        it('should send cta_click for a CTA with only a uid', function () {
            TrackCTAClick.handleClick({
                target: document.getElementById('uid-only')
            });
            expect(Plausible.trackEvent).toHaveBeenCalledOnceWith('cta_click', {
                cta_uid: '5e6f7a8b'
            });
        });

        it('should not send an event for a click outside a CTA', function () {
            TrackCTAClick.handleClick({
                target: document.getElementById('not-a-cta')
            });
            expect(Plausible.trackEvent).not.toHaveBeenCalled();
        });

        it('should not send an event for a CTA with empty text and uid', function () {
            TrackCTAClick.handleClick({
                target: document.getElementById('empty-cta')
            });
            expect(Plausible.trackEvent).not.toHaveBeenCalled();
        });

        it('should not send an event when the target is not an element', function () {
            TrackCTAClick.handleClick({ target: document });
            expect(Plausible.trackEvent).not.toHaveBeenCalled();
        });
    });

    describe('init', function () {
        afterEach(function () {
            document.removeEventListener('click', TrackCTAClick.handleClick);
        });

        it('should track clicks that bubble up to the document', function () {
            TrackCTAClick.init();
            document.getElementById('cta').click();
            expect(Plausible.trackEvent).toHaveBeenCalledOnceWith(
                'cta_click',
                ctaProps
            );
        });

        it('should not track clicks on CTAs that stop propagation', function () {
            const cta = document.getElementById('cta');
            cta.addEventListener('click', (event) => event.stopPropagation());

            TrackCTAClick.init();
            cta.click();
            expect(Plausible.trackEvent).not.toHaveBeenCalled();
        });

        it('should track clicks dispatched from an SVG inside a CTA', function () {
            TrackCTAClick.init();
            document
                .getElementById('cta-svg-path')
                .dispatchEvent(new MouseEvent('click', { bubbles: true }));
            expect(Plausible.trackEvent).toHaveBeenCalledOnceWith('cta_click', {
                cta_text: 'Get Firefox'
            });
        });
    });
});
