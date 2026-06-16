/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
  WARNING! This file is referenced in the CMS directly.
  Before altering, ensure you have an up-to-date database and check for pages that have
  extra_js="flare26-kick-page" to avoid breaking the page functionality.
*/

function isAlphaWebmUnsupported() {
    const ua = navigator.userAgent;
    if (/iPad|iPhone|iPod/.test(ua)) return true;
    if (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1) return true;
    return /^((?!chrome|android|crios|fxios).)*safari/i.test(ua);
}

const setupKickPage = () => {
    if (!document.querySelector('.flare26-kick-page')) return;
    if (isAlphaWebmUnsupported()) return;

    const logoLink = document.querySelector('.fl-logo-fx');

    if (!logoLink) return;

    const existingLogo = logoLink.querySelector('img');
    if (existingLogo) existingLogo.remove();

    const wrapper = document.createElement('div');
    wrapper.className = 'fl-video';

    const video = document.createElement('video');
    video.muted = true;
    video.poster = '/media/img/logos/firefox/logo-word-hor-white-2026.svg';

    const source = document.createElement('source');
    source.src = 'https://assets.mozilla.net/wc/logo-1-alpha.webm';
    source.type = 'video/webm';

    video.appendChild(source);
    wrapper.appendChild(video);
    logoLink.appendChild(wrapper);

    video.addEventListener('mouseover', () => {
        video.play();
    });
    video.addEventListener('mouseout', () => {
        video.pause();
        video.currentTime = 0;
    });

    // play and pause to trigger the first frame to be loaded
    video.play();
    video.pause();
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupKickPage);
} else {
    setupKickPage();
}
