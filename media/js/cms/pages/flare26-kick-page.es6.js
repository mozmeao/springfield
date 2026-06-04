/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

const setupKickPage = () => {
    if (!document.querySelector('.flare26-kick-page')) return;

    /**
     * @type {HTMLVideoElement | null}
     */
    const videoLogo = document.querySelector('.fl-logo-fx video');

    if (videoLogo) {
        videoLogo.addEventListener('mouseover', () => {
            videoLogo.play();
        });
        videoLogo.addEventListener('mouseout', () => {
            videoLogo.pause();
            videoLogo.currentTime = 0;
        });

        // we play and pause just to trigger the first frame to be loaded
        videoLogo.play();
        videoLogo.pause();
    }
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupKickPage);
} else {
    setupKickPage();
}
