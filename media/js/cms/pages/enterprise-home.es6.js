/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
  WARNING! This file is referenced in the CMS directly.
  Before altering, ensure you have an up-to-date database and check for pages that have
  extra_js="enterprise-home" to avoid breaking the page functionality.
*/

const setupEnterpriseHome = () => {
    if (!document.querySelector('.enterprise-home')) return;

    const topVideoContainer = document.querySelector('.fl-split-page-upper');
    const bottomVideoContainer = document.querySelector('.fl-main');

    if (!topVideoContainer) return;

    // Stop here if the user prefers reduced motion
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const createVideo = () => {
        const video = document.createElement('video');
        video.className = 'body-bg-video';
        video.autoplay = true;
        video.muted = true;
        video.loop = true;
        video.playsInline = true;

        const source = document.createElement('source');
        source.src =
            'https://assets.mozilla.net/enterprise/video/HOMEPAGE_HEROBUBBLES_a.webm';
        source.type = 'video/webm';

        video.appendChild(source);
        return video;
    };

    [topVideoContainer, bottomVideoContainer].forEach((container) => {
        if (!container) return;

        const video = createVideo();
        container.appendChild(video);

        video.play().catch((error) => {
            // Autoplay interrupted, ignore
            if (error && error.name === 'AbortError') return;
            throw error;
        });
    });
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupEnterpriseHome);
} else {
    setupEnterpriseHome();
}
