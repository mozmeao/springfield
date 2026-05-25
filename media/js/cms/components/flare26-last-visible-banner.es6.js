/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

function updateLastVisibleBanner(section) {
    section
        .querySelectorAll('.fl-banner-container.is-last-visible')
        .forEach(function (el) {
            el.classList.remove('is-last-visible');
        });

    // Find the last visible direct child of the section
    const children = [...section.children];
    let lastVisibleChild = null;
    for (const child of children) {
        if (getComputedStyle(child).display !== 'none') {
            lastVisibleChild = child;
        }
    }

    if (!lastVisibleChild) return;

    // Only mark a banner if it is (or is inside) the last visible child
    const bannerContainer = lastVisibleChild.classList.contains(
        'fl-banner-container'
    )
        ? lastVisibleChild
        : lastVisibleChild.querySelector('.fl-banner-container');

    if (bannerContainer) {
        const bannerChild = bannerContainer.querySelector('.fl-banner');
        if (!bannerChild.classList.contains('fl-banner-outlined')) {
            bannerContainer.classList.add('is-last-visible');
        }
    }
}

function setupLastVisibleBanner() {
    const sections = document.querySelectorAll(
        '.fl-split-page-lower, .fl-main:not(:has(.fl-split-page-lower))'
    );
    if (!sections.length) return;

    sections.forEach(updateLastVisibleBanner);

    // Re-run when body or html classes change (auth state, firefox version conditions, etc.)
    const observer = new MutationObserver(function () {
        sections.forEach(updateLastVisibleBanner);
    });

    observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['class']
    });
    observer.observe(document.body, {
        attributes: true,
        attributeFilter: ['class']
    });
}

export default setupLastVisibleBanner;
