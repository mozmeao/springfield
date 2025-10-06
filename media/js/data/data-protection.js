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
                    // try/catch because it errors if there's no matching selector
                    try {
                        document
                            .querySelector(`.sidebar li a[href="#${id}"]`)
                            .parentElement.classList.add('current');
                        return true;
                    } catch (e) {
                        return false;
                    }
                } else {
                     // try/catch because it errors if there's no matching selector
                    try {
                        document.querySelector(`.sidebar li a[href="#${id}"]`).parentElement.classList.remove('current');
                        return true;
                    } catch (e) {
                        return false;
                    }
                }
            });
        });

        document.querySelectorAll('.content-container section[id]').forEach((section) => {
            observer.observe(section);
        });
    });
})();
