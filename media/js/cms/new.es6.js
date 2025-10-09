/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

(function () {
    const storageKey = 'wnp-theme';
    const root = document.documentElement;
    const toggle = document.querySelector('.wnp-nav-toggle');
    const hamburger = document.querySelector('.wnp-hamburger');
    const nav = document.getElementById('wnp-nav');
    const themeButtons = document.querySelectorAll('.wnp-theme-btn');

    function swapStickerSourcesForTheme(theme) {
        const stickers = document.querySelectorAll(
            '.fl-card-sticker[data-dark-src]'
        );
        stickers.forEach(function (img) {
            // Preserve the original light src once
            if (!img.getAttribute('data-light-src')) {
                img.setAttribute('data-light-src', img.getAttribute('src'));
            }
            const lightSrc = img.getAttribute('data-light-src');
            const darkSrc = img.getAttribute('data-dark-src');
            if (!darkSrc) return;
            if (theme === 'dark') {
                if (img.getAttribute('src') !== darkSrc)
                    img.setAttribute('src', darkSrc);
            } else {
                if (img.getAttribute('src') !== lightSrc)
                    img.setAttribute('src', lightSrc);
            }
        });
    }

    function applyStoredTheme() {
        const stored = localStorage.getItem(storageKey);
        if (stored === 'light' || stored === 'dark') {
            root.setAttribute('data-theme', stored);
            if (toggle) toggle.setAttribute('aria-pressed', stored === 'dark');
            themeButtons.forEach(function (btn) {
                btn.classList.toggle(
                    'is-active',
                    btn.getAttribute('data-theme') === stored
                );
            });
            swapStickerSourcesForTheme(stored);
        } else {
            const sys =
                window.matchMedia &&
                window.matchMedia('(prefers-color-scheme: dark)').matches
                    ? 'dark'
                    : 'light';
            root.setAttribute('data-theme', sys);

            if (toggle) {
                toggle.setAttribute('aria-pressed', sys === 'dark');
            }
            themeButtons.forEach(function (btn) {
                btn.classList.toggle(
                    'is-active',
                    btn.getAttribute('data-theme') === sys
                );
            });
            swapStickerSourcesForTheme(sys);
        }
    }

    function toggleTheme() {
        const forced = root.getAttribute('data-theme');
        if (!forced) {
            const isSystemDark =
                window.matchMedia &&
                window.matchMedia('(prefers-color-scheme: dark)').matches;
            const next = isSystemDark ? 'light' : 'dark';
            localStorage.setItem(storageKey, next);
        } else {
            const nextForced = forced === 'dark' ? 'light' : 'dark';
            localStorage.setItem(storageKey, nextForced);
        }
        applyStoredTheme();
    }

    if (toggle) {
        toggle.addEventListener('click', toggleTheme);
    }

    function toggleMobileNav() {
        if (!nav || !hamburger) return;
        const open = nav.classList.toggle('is-open');
        hamburger.setAttribute('aria-expanded', open);
        const openLabel = hamburger.getAttribute('data-label-open') || 'Close';
        const closedLabel =
            hamburger.getAttribute('data-label-closed') || 'Menu';
        hamburger.setAttribute('aria-label', open ? openLabel : closedLabel);
        // Lock scroll when open
        document.body.style.overflow = open ? 'hidden' : '';
    }

    if (hamburger && nav) {
        hamburger.addEventListener('click', toggleMobileNav);
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && nav.classList.contains('is-open')) {
                toggleMobileNav();
            }
        });
    }

    if (themeButtons.length) {
        themeButtons.forEach(function (btn) {
            btn.addEventListener('click', function () {
                const choice = btn.getAttribute('data-theme');
                if (choice === 'light' || choice === 'dark') {
                    localStorage.setItem(storageKey, choice);
                    applyStoredTheme();
                }
            });
        });
    }

    if (window.matchMedia) {
        const mql = window.matchMedia('(prefers-color-scheme: dark)');
        const onChange = function () {
            if (!localStorage.getItem(storageKey)) applyStoredTheme();
        };
        mql.addEventListener
            ? mql.addEventListener('change', onChange)
            : mql.addListener && mql.addListener(onChange);
    }

    function initNewsletterForm() {
        const emailInput = document.getElementById('newsletter-email');
        const formDetails = document.getElementById('newsletter-details');
        const checkbox = document.getElementById('newsletter-privacy');
        const submit = document.getElementById('newsletter-submit');

        const include_country = document.getElementById('id_country') !== null;
        const include_language = document.getElementById('id_lang') !== null;

        if (!emailInput || !formDetails || !checkbox || !submit) {
            return;
        }

        let isFormExpanded = false;

        emailInput.addEventListener('input', function () {
            if (this.value.length > 0 && !isFormExpanded) {
                formDetails.classList.remove('fl-newsletterform-row-hidden');
                emailInput
                    .closest('.fl-newsletterform')
                    .classList.add('fl-newsletterform-expanded');
                isFormExpanded = true;
            } else if (this.value.length === 0 && isFormExpanded) {
                formDetails.classList.add('fl-newsletterform-row-hidden');
                emailInput
                    .closest('.fl-newsletterform')
                    .classList.remove('fl-newsletterform-expanded');
                isFormExpanded = false;
            }
        });

        emailInput.addEventListener('focus', function () {
            if (this.value.length > 0 && !isFormExpanded) {
                formDetails.classList.remove('fl-newsletterform-row-hidden');
                emailInput
                    .closest('.fl-newsletterform')
                    .classList.add('fl-newsletterform-expanded');
                isFormExpanded = true;
            }
        });

        function sync() {
            const emailValid = emailInput.value.length > 0;
            const countryValid =
                !include_country ||
                (document.getElementById('id_country') &&
                    document.getElementById('id_country').value !== '');
            const languageValid =
                !include_language ||
                (document.getElementById('id_lang') &&
                    document.getElementById('id_lang').value !== '');
            const consentValid = checkbox.checked;

            submit.disabled = !(
                emailValid &&
                countryValid &&
                languageValid &&
                consentValid
            );
        }

        emailInput.addEventListener('input', sync);
        checkbox.addEventListener('change', sync);

        if (include_country && document.getElementById('id_country')) {
            document
                .getElementById('id_country')
                .addEventListener('change', sync);
        }
        if (include_language && document.getElementById('id_lang')) {
            document.getElementById('id_lang').addEventListener('change', sync);
        }

        sync();
    }

    function handleNewsletterSubmission() {
        const form = document.getElementById('newsletter-form');
        if (!form) return;

        form.addEventListener('submit', function (e) {
            e.preventDefault();

            const formData = new FormData(form);
            const newsletters = Array.from(
                form.querySelectorAll('input[name="newsletters"]:checked')
            ).map((input) => input.value);

            // Disable form during submission
            const submitButton = document.getElementById('newsletter-submit');
            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.textContent = 'Subscribing...';

            // Submit to Basket
            fetch(form.action, {
                method: 'POST',
                body: formData
            })
                .then((response) => {
                    // Check if response is JSON
                    const contentType = response.headers.get('content-type');
                    if (
                        contentType &&
                        contentType.includes('application/json')
                    ) {
                        return response.json();
                    } else {
                        // If not JSON, treat as success for 200 status
                        if (response.status === 200) {
                            return { success: true };
                        } else {
                            return { success: false, errors: ['Server error'] };
                        }
                    }
                })
                .then((data) => {
                    if (data.success || data.status === 'ok') {
                        // Show success message
                        showNewsletterSuccess();

                        // Analytics tracking
                        if (window.dataLayer) {
                            for (let i = 0; i < newsletters.length; ++i) {
                                window.dataLayer.push({
                                    event: 'newsletter_subscribe',
                                    newsletter_id: newsletters[i]
                                });
                            }
                        }
                    } else {
                        // Show error message
                        showNewsletterError(
                            data.errors || [
                                'An error occurred. Please try again.'
                            ]
                        );
                    }
                })
                .catch((error) => {
                    // eslint-disable-next-line no-console
                    console.error('Newsletter subscription error:', error);
                    showNewsletterError([
                        'An error occurred. Please try again.'
                    ]);
                })
                .finally(() => {
                    // Re-enable form
                    submitButton.disabled = false;
                    submitButton.textContent = originalText;
                });
        });
    }

    function showNewsletterSuccess() {
        const form = document.getElementById('newsletter-form');
        const successDiv = document.getElementById('newsletter-thanks');

        if (form && successDiv) {
            form.style.display = 'none';
            successDiv.classList.remove('hidden');
        }
    }

    function showNewsletterError(errors) {
        const errorDiv = document.getElementById('newsletter-errors');
        const errorList =
            errorDiv && errorDiv.querySelector('.fl-newsletterform-error-list');

        if (errorDiv && errorList) {
            // Clear existing errors
            errorList.innerHTML = '';

            // Add new errors
            errors.forEach((error) => {
                const li = document.createElement('li');
                li.textContent = error;
                errorList.appendChild(li);
            });

            errorDiv.classList.remove('hidden');
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            initNewsletterForm();
            handleNewsletterSubmission();
        });
    } else {
        initNewsletterForm();
        handleNewsletterSubmission();
    }

    applyStoredTheme();
})();
