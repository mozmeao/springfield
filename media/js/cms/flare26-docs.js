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

    toggle.addEventListener('change', function () {
        indexEl.classList.toggle('fl-docs-inline-mode', this.checked);
        indexEl.classList.toggle('max-width-wide-banner', !this.checked);
        if (!this.checked) {
            contentEl.innerHTML = savedContent;
            iframe = null;
        }
    });

    if (toggle.checked) {
        indexEl.classList.add('fl-docs-inline-mode');
        indexEl.classList.remove('max-width-wide-banner');
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
    });
})();
