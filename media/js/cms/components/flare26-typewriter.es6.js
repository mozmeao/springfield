/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

export function typewriter(el, speed) {
    const text = el.textContent;
    const interval = speed || 30;

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        return;
    }

    el.textContent = '';
    el.classList.add('has-blinking-cursor');

    const observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (!entry.isIntersecting) {
                return;
            }
            observer.unobserve(el);
            let i = 0;
            const timer = setInterval(function () {
                el.textContent += text[i++];
                if (i >= text.length) {
                    clearInterval(timer);
                    setTimeout(function () {
                        el.classList.remove('has-blinking-cursor');
                    }, 1500);
                }
            }, interval);
        });
    });

    observer.observe(el);
}

function reserveTypewriterSpace() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    document.querySelectorAll('.fl-typewriter').forEach(function (el) {
        const container = el.closest('p');
        if (!container) return;
        container.style.minHeight = container.offsetHeight + 'px';
    });
}

function initTypewriter() {
    document.querySelectorAll('.fl-typewriter').forEach(function (el) {
        typewriter(el);
    });
}

export default function setupTypewriter() {
    reserveTypewriterSpace();
    initTypewriter();
}
