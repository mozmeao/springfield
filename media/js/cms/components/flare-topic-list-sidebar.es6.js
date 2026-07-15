/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

function initTopicListSidebar() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            const id = entry.target.getAttribute('id');
            if (entry.intersectionRatio > 0) {
                // try/catch because it errors if there's no matching selector
                try {
                    document
                        .querySelector(
                            `.fl-topic-list-sidebar li a[href="#${id}"]`
                        )
                        .parentElement.classList.add('current');
                    return true;
                } catch (e) {
                    return false;
                }
            } else {
                // try/catch because it errors if there's no matching selector
                try {
                    document
                        .querySelector(
                            `.fl-topic-list-sidebar li a[href="#${id}"]`
                        )
                        .parentElement.classList.remove('current');
                    return true;
                } catch (e) {
                    return false;
                }
            }
        });
    });

    document.querySelectorAll('.fl-topic').forEach((section) => {
        observer.observe(section);
    });
}

export default function setupTopicListSidebar() {
    initTopicListSidebar();
}
