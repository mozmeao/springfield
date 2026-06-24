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

    function enableInlineMode(forcedUrl) {
        const url = getUrlForInlineMode(forcedUrl);

        indexEl.classList.add('fl-docs-inline-mode');
        indexEl.classList.remove('max-width-wide-banner');

        iframe = document.createElement('iframe');
        iframe.className = 'fl-docs-inline-frame';
        contentEl.innerHTML = '';
        contentEl.appendChild(iframe);
        iframe.src = url;
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

    document.querySelectorAll('.fl-docs-inline-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            const article = btn.closest('article');
            const url = article.querySelector('h3 a').href;
            history.replaceState(null, '', '#' + article.id);
            toggle.checked = true;
            enableInlineMode(url);
        });
    });

    if (toggle.checked) {
        window.setTimeout(enableInlineMode, 500);
    }
})();
