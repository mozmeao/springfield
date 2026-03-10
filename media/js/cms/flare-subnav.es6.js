/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

// Sticky header
(function () {
    // Subnav menu
    const buttonEl = document.querySelector('.fl-subnav-toggle');
    const subnavListEl = document.querySelector('.fl-subnav-list');
    function closeMenu() {
        [buttonEl, subnavListEl].forEach(function (el) {
            el.classList.remove('is-open');
        });
        document.body.classList.remove('fl-modal-open');
        subnavListEl.removeAttribute('role');
        subnavListEl.removeAttribute('aria-modal');
    }

    if (buttonEl && subnavListEl) {
        // When the user clicks the toggle button while the menu is open,
        // mousedown fires before focusout. We set this flag so the focusout
        // handler can bail out and let the click handler do the closing instead,
        // avoiding a double-toggle (close + immediate reopen).
        let skipFocusOut = false;

        // Toggle the menu open/closed on button click.
        buttonEl.addEventListener('click', function (e) {
            e.preventDefault();
            // Reset the flag in case the button was already focused when clicked
            // (no focusout fired from the list, so the flag was never consumed).
            skipFocusOut = false;
            const mobileSubnavIsOpen =
                e.currentTarget.classList.contains('is-open');
            const elements = [e.currentTarget, subnavListEl];

            if (mobileSubnavIsOpen) {
                closeMenu();
            } else {
                elements.forEach(function (el) {
                    el.classList.add('is-open');
                });
                document.body.classList.add('fl-modal-open');
                subnavListEl.setAttribute('role', 'dialog');
                subnavListEl.setAttribute('aria-modal', 'true');
            }
        });

        buttonEl.addEventListener('mousedown', function () {
            if (buttonEl.classList.contains('is-open')) {
                skipFocusOut = true;
            }
        });

        // Close when focus leaves the button without entering the list
        // (e.g. Shift+Tab away from the button while the menu is open).
        // Tab forward from the button moves focus into the list, so relatedTarget
        // would be inside subnavListEl — that case is ignored.
        buttonEl.addEventListener('focusout', function (event) {
            if (
                buttonEl.classList.contains('is-open') &&
                event.relatedTarget &&
                !subnavListEl.contains(event.relatedTarget)
            ) {
                closeMenu();
            }
        });

        // Close on Escape key while focus is inside the list.
        subnavListEl.addEventListener('keyup', function (event) {
            if (event.key === 'Escape') {
                closeMenu();
            }
        });

        // Close when keyboard focus leaves the list entirely (e.g. Tab / Shift+Tab).
        // relatedTarget is the element receiving focus; if it's still inside the
        // list we ignore the event. If it's null (focus left the page entirely,
        // or a non-focusable element was clicked in Safari) we also ignore it —
        // the document click listener below handles the mouse case.
        subnavListEl.addEventListener('focusout', function (event) {
            if (skipFocusOut) {
                skipFocusOut = false;
                return;
            }
            if (
                event.relatedTarget &&
                !subnavListEl.contains(event.relatedTarget)
            ) {
                closeMenu();
            }
        });

        // Close when the user clicks anywhere outside the list or button.
        // This covers clicks on non-focusable elements where focusout alone
        // wouldn't fire with a usable relatedTarget.
        document.addEventListener('click', function (event) {
            if (
                buttonEl.classList.contains('is-open') &&
                !subnavListEl.contains(event.target) &&
                !buttonEl.contains(event.target)
            ) {
                closeMenu();
            }
        });
    }
})();
