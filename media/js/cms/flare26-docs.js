/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

(function () {
    'use strict';
    var toggle = document.getElementById('fl-docs-inline-switch');
    var indexEl = document.querySelector('.fl-docs-index');
    var contentEl = document.querySelector('.fl-docs-index-content');
    var savedContent = contentEl.innerHTML;
    var iframe = null;

    function enableInlineMode() {
        indexEl.classList.add('fl-docs-inline-mode');
        indexEl.classList.remove('max-width-wide-banner');
        var firstLink = indexEl.querySelector(
            '.fl-docs-index-sidebar a[data-url]'
        );
        if (firstLink) {
            iframe = document.createElement('iframe');
            iframe.className = 'fl-docs-inline-frame';
            contentEl.innerHTML = '';
            contentEl.appendChild(iframe);
            iframe.src = firstLink.dataset.url;
            contentEl.scrollIntoView({ behavior: 'smooth' });
        }
    }

    toggle.addEventListener('change', function () {
        indexEl.classList.toggle('fl-docs-inline-mode', this.checked);
        indexEl.classList.toggle('max-width-wide-banner', !this.checked);
        if (this.checked) {
            enableInlineMode();
        } else {
            contentEl.innerHTML = savedContent;
            iframe = null;
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    });

    if (toggle.checked) {
        window.setTimeout(enableInlineMode, 500);
    }

    indexEl.addEventListener('click', function (e) {
        if (!toggle.checked) return;
        var link = e.target.closest('a');
        if (!link) return;
        var url = link.dataset.url;
        if (!url) {
            var href = link.getAttribute('href');
            if (!href || href.startsWith('#')) return;
            url = link.href;
        }
        e.preventDefault();
        if (!iframe) {
            iframe = document.createElement('iframe');
            iframe.className = 'fl-docs-inline-frame';
            contentEl.innerHTML = '';
            contentEl.appendChild(iframe);
        }
        iframe.src = url;
        indexEl.scrollIntoView({ behavior: 'smooth' });
    });
})();
