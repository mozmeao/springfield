/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
  Loaded site-wide behind the `easter-egg-logo` waffle switch. Swaps the
  Firefox header logo for a WebM that plays on hover. To retire or change
  the easter egg, edit this file (and the matching CSS) or flip the switch off.
*/

function isAlphaWebmUnsupported() {
    const ua = navigator.userAgent;
    if (/iPad|iPhone|iPod/.test(ua)) return true;
    if (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1) return true;
    return /^((?!chrome|android|crios|fxios).)*safari/i.test(ua);
}

const setupEasterEggLogo = () => {
    // The kick/sidekick pages have their own scoped script; let it own the logo there.
    if (document.body.classList.contains('flare26-kick-page')) return;
    // Enterprise pages use a wider (200x40) wordmark; our sizing tweaks don't fit.
    if (document.body.classList.contains('fl-theme-enterprise')) return;
    if (isAlphaWebmUnsupported()) return;
    if (
        window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches
    )
        return;

    const logoLink = document.querySelector('.fl-logo-fx');

    if (!logoLink) return;
    if (logoLink.querySelector('.fl-video')) return;

    const existingLogo = logoLink.querySelector('img');
    if (existingLogo) existingLogo.remove();

    // Hide the wordmark that .fl-logo-fx paints as a background.
    logoLink.style.backgroundImage = 'none';
    // Widen the logo container so the WebM's flame lands at the same visual
    // size as the SVG wordmark, and shift it back so the layout doesn't move.
    logoLink.style.setProperty('inline-size', '130px');
    logoLink.style.setProperty('block-size', '55px');
    logoLink.style.setProperty('margin-inline-start', '-5px');

    const wrapper = document.createElement('div');
    wrapper.className = 'fl-video';
    wrapper.style.setProperty('max-block-size', '56px');

    const video = document.createElement('video');
    video.muted = true;

    const source = document.createElement('source');
    source.src = 'https://assets.mozilla.net/wc/logo-1-alpha.webm';
    source.type = 'video/webm';

    video.appendChild(source);
    wrapper.appendChild(video);
    logoLink.appendChild(wrapper);

    const HOVER_INTENT_MS = 1000;
    const COOLDOWN_MS = 10000;

    let hoverTimer = null;
    let isPlaying = false;
    let cooldownUntil = 0;

    video.addEventListener(
        'canplaythrough',
        () => {
            video.addEventListener('mouseover', () => {
                if (isPlaying || hoverTimer) return;
                if (Date.now() < cooldownUntil) return;

                hoverTimer = setTimeout(() => {
                    hoverTimer = null;
                    isPlaying = true;
                    video.play().catch((error) => {
                        if (error && error.name === 'AbortError') return;
                        throw error;
                    });
                }, HOVER_INTENT_MS);
            });

            video.addEventListener('mouseout', () => {
                // Cancel a pending start if the user leaves before hover-intent fires.
                // Do NOT stop an in-progress animation — let it play through.
                if (hoverTimer) {
                    clearTimeout(hoverTimer);
                    hoverTimer = null;
                }
            });

            video.addEventListener('ended', () => {
                isPlaying = false;
                cooldownUntil = Date.now() + COOLDOWN_MS;
                video.currentTime = 0;
            });
        },
        { once: true }
    );
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupEasterEggLogo);
} else {
    setupEasterEggLogo();
}
