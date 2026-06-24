/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

(function () {
    'use strict';
    const toggle = document.getElementById('fl-docs-inline-switch');
    const indexEl = document.querySelector('.fl-docs-index');
    const sidebarLinks = indexEl.querySelectorAll(
        '.fl-docs-index-sidebar a[data-url]'
    );
    const contentEl = document.querySelector('.fl-docs-index-content');
    const savedContent = contentEl.innerHTML;
    let iframe = null;

    function getUrlForInlineMode(forcedUrl) {
        if (forcedUrl) return forcedUrl;

        const currentHash = window.location.hash;
        const hashLink = document.querySelector(`a[href="${currentHash}"]`);
        if (hashLink) return hashLink.dataset.url;

        return sidebarLinks[0].dataset.url;
    }

    function lockOuterScroll() {
        document.body.style.overflowY = 'hidden';
    }

    function unlockOuterScroll() {
        document.body.style.overflowY = '';
    }

    function preventScrollChaining(iframeEl) {
        try {
            const innerDoc = iframeEl.contentDocument;
            const scrollEl =
                innerDoc.scrollingElement || innerDoc.documentElement;
            innerDoc.addEventListener(
                'wheel',
                (e) => {
                    const atTop = scrollEl.scrollTop === 0 && e.deltaY < 0;
                    const atBottom =
                        Math.ceil(scrollEl.scrollTop + scrollEl.clientHeight) >=
                            scrollEl.scrollHeight && e.deltaY > 0;
                    if (atTop || atBottom) {
                        e.preventDefault();
                    }
                },
                { passive: false }
            );
        } catch (_) {
            /* no-op */
        }
    }

    function enableInlineMode(forcedUrl) {
        const url = getUrlForInlineMode(forcedUrl);

        indexEl.classList.add('fl-docs-inline-mode');
        indexEl.classList.remove('max-width-wide-banner');

        iframe = document.createElement('iframe');
        iframe.className = 'fl-docs-inline-frame';
        iframe.addEventListener('load', () => preventScrollChaining(iframe));
        contentEl.innerHTML = '';
        contentEl.appendChild(iframe);
        iframe.src = url + (url.includes('?') ? '&' : '?') + 'fl_docs_inline=1';
        lockOuterScroll();
        contentEl.scrollIntoView({ behavior: 'smooth' });
    }

    toggle.addEventListener('change', function () {
        indexEl.classList.toggle('fl-docs-inline-mode', this.checked);
        indexEl.classList.toggle('max-width-wide-banner', !this.checked);

        if (this.checked) {
            enableInlineMode();
        } else {
            contentEl.innerHTML = savedContent;
            iframe = null;
            unlockOuterScroll();
            const target = window.location.hash
                ? document.getElementById(window.location.hash.slice(1))
                : null;
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            } else {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        }
    });

    sidebarLinks.forEach((link) => {
        link.addEventListener('click', () => {
            if (toggle.checked) {
                enableInlineMode(link.dataset.url);
            }
        });
    });

    contentEl.addEventListener('click', (e) => {
        const btn = e.target.closest('.fl-docs-inline-btn');
        if (!btn) return;
        const article = btn.closest('article');
        const url = article.querySelector('h3 a').href;
        history.replaceState(null, '', '#' + article.id);
        toggle.checked = true;
        enableInlineMode(url);
    });

    if (toggle.checked) {
        window.setTimeout(enableInlineMode, 500);
    }
})();
