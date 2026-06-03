/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

function initPencilBannerCloseButtons() {
    const pencilBannerCloseButtons = document.querySelectorAll(
        '.fl-pencil-banner .fl-button'
    );

    if (!pencilBannerCloseButtons.length) return;

    pencilBannerCloseButtons.forEach((button) => {
        button.addEventListener('click', () => {
            button.closest('.fl-pencil-banner').remove();
        });
    });
}

export default function setupPencilBanners() {
    initPencilBannerCloseButtons();
}
