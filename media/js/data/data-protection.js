/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

(function () {

    'use strict';


    window.addEventListener('DOMContentLoaded', () => {
        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                const id = entry.target.getAttribute('id');
                if (entry.intersectionRatio > 0) {
                    document.querySelector(`.sidebar li a[href="#${id}"]`).classList.add('current');
                } else {
                    document.querySelector(`.sidebar li a[href="#${id}"]`).classList.remove('current');
                }
            });
        });

        document.querySelectorAll('.content-container section[id]').forEach((section) => {
            observer.observe(section);
        });

    });
})();
