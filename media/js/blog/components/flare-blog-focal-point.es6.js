/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

// The CSP blocks inline style attributes, so focal points are set through the CSSOM.
export default function setupBlogFocalPoints() {
    document.querySelectorAll('[data-focal-point]').forEach((el) => {
        el.style.setProperty('--focal-point', el.dataset.focalPoint);
    });
}
