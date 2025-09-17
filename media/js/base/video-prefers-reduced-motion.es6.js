/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
This JS requires the supporting CSS:

    @keyframes js-check-autoplay {}
    video[autoplay] {
        animation: js-check-autoplay 0s;
    }
*/

document.addEventListener(
    'animationstart',
    (event) => {
        if (
            event.animationName === 'js-check-autoplay' &&
            matchMedia('(prefers-reduced-motion: reduce)').matches
        ) {
            // pause the video
            event.target.pause();
            // make sure they can start the video if they want it
            event.target.setAttribute('controls', 'controls');
        }
    },
    { capture: true }
);
