/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

(function () {
    'use strict';

    function setCorrectFormAction() {
        var form = document.querySelector('.contact-form');
        if (!form) {
            return;
        }
        var realAction = form.getAttribute('data-actn');
        var decoyAction = form.getAttribute('action');
        form.setAttribute('action', realAction);
        form.setAttribute('data-actn', decoyAction);

        var honeypot = document.getElementById('office-fax');
        if (honeypot) {
            honeypot.removeAttribute('required');
        }
    }

    function startDocumentDownload() {
        var link = document.querySelector('.contact-form-download');
        if (link) {
            link.click();
            link.classList.add('hidden');
        }
    }

    function init() {
        window.setTimeout(setCorrectFormAction, 3000);
        startDocumentDownload();
    }

    if (document.readyState !== 'loading') {
        init();
    } else {
        document.addEventListener('DOMContentLoaded', init);
    }
})();
