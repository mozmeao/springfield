/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { getConsentCookie } from '../base/consent/utils.es6';
import VideoEngagement from '../base/datalayer-videoengagement.es6';

// Create namespace
if (typeof window.cms === 'undefined') {
    window.cms = {};
}

(function () {
    const Flare26 = {};

    function initNewsletterForm() {
        const emailInput = document.getElementById('newsletter-email');
        const formDetails = document.getElementById('newsletter-details');
        const privacyCheckbox = document.getElementById('newsletter-privacy');
        const termsCheckbox = document.getElementById('id_terms');
        const submit = document.getElementById('newsletter-submit');

        const include_country = document.getElementById('id_country') !== null;
        const include_language = document.getElementById('id_lang') !== null;

        if (!emailInput || !formDetails || !privacyCheckbox || !submit) {
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
            const privacyValid = privacyCheckbox.checked;
            const termsValid = !termsCheckbox || termsCheckbox.checked;

            submit.disabled = !(
                emailValid &&
                countryValid &&
                languageValid &&
                privacyValid &&
                termsValid
            );
        }

        emailInput.addEventListener('input', sync);
        privacyCheckbox.addEventListener('change', sync);
        if (termsCheckbox) {
            termsCheckbox.addEventListener('change', sync);
        }

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

            const email = formData.get('email');
            if (email === 'success@example.com') {
                showNewsletterSuccess();
                return;
            } else if (email === 'failure@example.com') {
                showNewsletterError(['An error occurred. Please try again.']);
                return;
            }

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
                            data.errors || data.desc
                                ? [data.desc]
                                : ['An error occurred. Please try again.']
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

    function initNotificationClose() {
        const closeButtons = document.querySelectorAll(
            '.fl-notification-close'
        );
        closeButtons.forEach(function (btn) {
            btn.addEventListener('click', function () {
                const wrapper = btn.closest('.fl-notification-wrapper');
                if (wrapper) {
                    wrapper.remove();
                }
            });
        });
    }

    function applyVideoAspectRatios() {
        const videoContainers = document.querySelectorAll(
            '.fl-video[data-aspect-ratio]'
        );

        videoContainers.forEach(function (container) {
            const ratio = container.getAttribute('data-aspect-ratio');

            if (!ratio) {
                return;
            }

            container.style.aspectRatio = ratio;
        });
    }

    function initVideoPlayers() {
        const videoButtons = document.querySelectorAll('.js-video-play');

        videoButtons.forEach(function (button) {
            button.addEventListener('click', function (e) {
                e.preventDefault();

                const videoType = button.getAttribute('data-video-type');
                const container = button.closest('.fl-video');

                if (!container) return;

                if (videoType === 'youtube') {
                    const videoId = button.getAttribute('data-video-id');

                    if (!videoId) return;

                    const iframe = document.createElement('iframe');
                    iframe.src = `https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&rel=0`;
                    iframe.title = button.getAttribute('aria-label') || 'Video';
                    iframe.allowFullscreen = true;
                    button.remove();
                    container.appendChild(iframe);
                } else if (videoType === 'cdn') {
                    const videoUrl = button.getAttribute('data-video-url');
                    const posterUrl = button.getAttribute('data-video-poster');

                    if (!videoUrl) return;

                    const video = document.createElement('video');
                    video.controls = true;
                    video.autoplay = true;

                    if (posterUrl) {
                        video.poster = posterUrl;
                    }

                    const source = document.createElement('source');
                    source.src = videoUrl;
                    source.type = 'video/webm';

                    video.appendChild(source);

                    button.remove();
                    container.appendChild(video);

                    video.addEventListener(
                        'play',
                        VideoEngagement.handleStart,
                        {
                            once: true
                        }
                    );

                    // Floor duration because we don't need precise numbers here
                    video.addEventListener('loadedmetadata', (e) => {
                        VideoEngagement.duration = Math.floor(
                            e.target.duration
                        );
                    });

                    // 'timeupdate' will handle both video_progress and video_complete data
                    // ('ended' not reliable: if 'loop' is true, it will not fire)
                    video.addEventListener(
                        'timeupdate',
                        VideoEngagement.throttledProgress
                    );
                }
            });
        });
    }

    function initAnimations() {
        const animations = document.querySelectorAll('.fl-animation');

        animations.forEach(function (container) {
            const video = container.querySelector('video');
            const button = container.querySelector('.js-animation-play');
            const playback = container.getAttribute('data-playback');

            if (!video || !button) return;

            if (
                playback === 'autoplay_once' &&
                !window.matchMedia('(prefers-reduced-motion: reduce)').matches
            ) {
                video.play().catch(function () {
                    container.classList.remove('fl-animation-playing');
                });
            } else if (playback === 'autoplay_once') {
                container.classList.remove('fl-animation-playing');
            }

            video.addEventListener('ended', function () {
                container.classList.remove('fl-animation-playing');
                video.currentTime = 0;
            });

            button.addEventListener('click', function () {
                container.classList.add('fl-animation-playing');
                video.currentTime = 0;
                video.play().catch(function () {
                    container.classList.remove('fl-animation-playing');
                });
            });
        });
    }

    function initAnimationPauseButtons() {
        const pauseButtons = document.querySelectorAll('.js-animation-pause');

        pauseButtons.forEach(function (button) {
            // Buttons inside the sliding carousel are handled by flare26.es6.js
            if (button.closest('[data-js="fl-sliding-carousel"]')) return;

            const container = button.closest('.fl-video');
            if (!container) return;

            const video = container.querySelector('video');
            if (!video) return;

            const pauseIcon = button.querySelector('.js-pause-icon');
            const playIcon = button.querySelector('.js-play-icon');

            button.addEventListener('click', function () {
                if (video.paused) {
                    video.play().catch();
                    button.setAttribute(
                        'aria-label',
                        button.dataset.labelPause
                    );
                    pauseIcon.hidden = false;
                    playIcon.hidden = true;
                } else {
                    video.pause();
                    button.setAttribute('aria-label', button.dataset.labelPlay);
                    pauseIcon.hidden = true;
                    playIcon.hidden = false;
                }
            });
        });
    }

    function initDownloadDropdown() {
        const dropdownEl = document.querySelector('.fl-platform-dropdown');

        if (dropdownEl) {
            const dropdownButtonEl = document.querySelector(
                '.fl-platform-dropdown-button'
            );
            dropdownButtonEl.addEventListener('click', function () {
                if (dropdownEl.classList.contains('dropdown-is-open')) {
                    dropdownEl.classList.remove('dropdown-is-open');
                } else {
                    dropdownEl.classList.add('dropdown-is-open');
                }
            });

            dropdownEl.addEventListener('keyup', function (e) {
                if (e.key === 'Escape') {
                    dropdownEl.classList.remove('dropdown-is-open');
                }
            });

            window.addEventListener('click', function (e) {
                if (!dropdownEl.contains(e.target)) {
                    dropdownEl.classList.remove('dropdown-is-open');
                }
            });
        }
    }

    function initQRCodeSnippet() {
        const COOKIE_ID = 'moz-qr-snippet-dismissed';
        const qrCodeSnippetEl = document.querySelector('.fl-qr-code-snippet');

        if (!qrCodeSnippetEl) {
            return;
        }

        const cookiesEnabled =
            typeof window.Mozilla.Cookies !== 'undefined' &&
            window.Mozilla.Cookies.enabled();

        // Don't show if previously dismissed.
        if (cookiesEnabled && Mozilla.Cookies.hasItem(COOKIE_ID)) {
            return;
        }

        const closeButton = qrCodeSnippetEl.querySelector(
            '.fl-qr-code-snippet-close'
        );

        qrCodeSnippetEl.setAttribute('aria-live', 'polite');

        setTimeout(function () {
            qrCodeSnippetEl.classList.add('is-open');
        }, 3000);

        if (qrCodeSnippetEl.classList.contains('fl-qr-code-snippet-closable')) {
            if (closeButton) {
                closeButton.addEventListener('click', function () {
                    qrCodeSnippetEl.classList.remove('is-open');

                    if (!cookiesEnabled) {
                        return;
                    }

                    /**
                     * Set a preference cookie to remember the user dismissed
                     * the QR code snippet. Legal are OK to set this without
                     * explicit consent because:
                     *
                     * 1) The cookie is not used for tracking purposes.
                     * 2) The cookie is set only after an explicit user action.
                     *
                     * We still honor not setting this cookie if preference
                     * cookies have been explicitly rejected by the user.
                     */
                    const cookie = getConsentCookie();
                    if (cookie && !cookie.preference) {
                        return;
                    }

                    const date = new Date();
                    const cookieDuration = 24 * 60 * 60 * 1000; // 24 hours
                    date.setTime(date.getTime() + cookieDuration);
                    Mozilla.Cookies.setItem(
                        COOKIE_ID,
                        true,
                        date.toUTCString(),
                        '/',
                        undefined,
                        false,
                        'lax'
                    );
                });
            }
        }
    }

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

    function reserveTypewriterSpace() {
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches)
            return;
        document.querySelectorAll('.fl-typewriter').forEach(function (el) {
            const container = el.closest('p');
            if (!container) return;
            container.style.minHeight = container.offsetHeight + 'px';
        });
    }

    function initTypewriter() {
        document.querySelectorAll('.fl-typewriter').forEach(function (el) {
            Flare26.typewriter(el);
        });
    }

    Flare26.typewriter = function (el, speed) {
        const text = el.textContent;
        const interval = speed || 30;

        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            return;
        }

        el.textContent = '';

        const observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) {
                    return;
                }
                observer.unobserve(el);
                let i = 0;
                const timer = setInterval(function () {
                    el.textContent += text[i++];
                    if (i >= text.length) {
                        clearInterval(timer);
                    }
                }, interval);
            });
        });

        observer.observe(el);
    };

    Flare26.initDialogs = () => {
        const triggerButtons = document.querySelectorAll('.fl-dialog-trigger');

        if (triggerButtons.length) {
            triggerButtons.forEach(function (buttonEl) {
                const dialogEl = document.getElementById(
                    buttonEl.dataset.targetId
                );

                if (dialogEl) {
                    buttonEl.addEventListener('click', function () {
                        dialogEl.showModal();
                    });
                    const closeButtonEl = dialogEl.querySelector(
                        '.fl-dialog-close-button'
                    );
                    if (closeButtonEl) {
                        closeButtonEl.addEventListener('click', function () {
                            dialogEl.close();
                        });
                    }
                }
            });
        }
    };

    Flare26.isUITourEnabled = function (timeout) {
        const delay = timeout || 500;
        return new window.Promise(function (resolve, reject) {
            const timer = window.setTimeout(reject, delay);
            Mozilla.UITour.ping(function () {
                window.clearTimeout(timer);
                resolve();
            });
        });
    };

    Flare26.setAsDefaultPage = {
        checkTimer: undefined,
        isDefaultBrowser() {
            return Flare26.isUITourEnabled().then(function () {
                return new window.Promise(function (resolve, reject) {
                    Mozilla.UITour.getConfiguration(
                        'appinfo',
                        function (details) {
                            if (details.defaultBrowser) {
                                resolve();
                            } else {
                                reject(
                                    details.canSetDefaultBrowserInBackground
                                );
                            }
                        }
                    );
                });
            });
        },
        trySetDefaultBrowser() {
            Mozilla.UITour.setConfiguration('defaultBrowser');
            Flare26.setAsDefaultPage.checkForDefaultSwitch();
        },
        onDefaultSwitch() {
            document
                .querySelector('html')
                .classList.remove('firefox-is-not-default');
            document.querySelector('html').classList.add('firefox-is-default');
            // GA4
            window.dataLayer.push({
                event: 'default_browser_set'
            });
            window.dataLayer.push({
                event: 'dimension_set',
                firefox_is_default: true
            });
        },
        checkForDefaultSwitch() {
            Flare26.setAsDefaultPage
                .isDefaultBrowser()
                .then(function () {
                    Flare26.setAsDefaultPage.onDefaultSwitch();
                    clearInterval(Flare26.setAsDefaultPage.checkTimer);
                })
                .catch(function () {
                    if (!Flare26.setAsDefaultPage.checkTimer) {
                        window.setTimeout(function () {
                            Flare26.setAsDefaultPage.checkTimer = setInterval(
                                Flare26.setAsDefaultPage.checkForDefaultSwitch,
                                1000
                            );
                        }, 1500);
                    }
                });
        },
        onLoad() {
            const setAsDefaultButtonEls = document.querySelectorAll(
                '.fl-set-as-default-button'
            );

            if (!setAsDefaultButtonEls.length) return;

            let hasValidSetAsDefaultTrigger = false;

            setAsDefaultButtonEls.forEach((setAsDefaultButtonEl) => {
                const targetId =
                    setAsDefaultButtonEl.getAttribute('data-target-id');
                const setAsDefaultDialogEl = targetId
                    ? document.getElementById(targetId)
                    : null;
                if (!setAsDefaultDialogEl) {
                    return;
                }
                hasValidSetAsDefaultTrigger = true;
                setAsDefaultButtonEl.addEventListener('click', () => {
                    Flare26.setAsDefaultPage.trySetDefaultBrowser();
                });
            });

            if (!hasValidSetAsDefaultTrigger) {
                return;
            }

            Flare26.setAsDefaultPage
                .isDefaultBrowser()
                .then(function () {
                    document
                        .querySelector('html')
                        .classList.add('firefox-is-default');
                    // GA4
                    window.dataLayer.push({
                        event: 'dimension_set',
                        firefox_is_default: true
                    });
                })
                .catch(function () {
                    document
                        .querySelector('html')
                        .classList.add('firefox-is-not-default');

                    // GA4
                    window.dataLayer.push({
                        event: 'dimension_set',
                        firefox_is_default: false
                    });
                });
        }
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            initNewsletterForm();
            handleNewsletterSubmission();
            initNotificationClose();
            applyVideoAspectRatios();
            initVideoPlayers();
            initAnimations();
            initAnimationPauseButtons();
            initDownloadDropdown();
            initQRCodeSnippet();
            initTopicListSidebar();
            reserveTypewriterSpace();
            initTypewriter();
            Flare26.initDialogs();
            Flare26.setAsDefaultPage.onLoad();
        });
    } else {
        initNewsletterForm();
        handleNewsletterSubmission();
        initNotificationClose();
        applyVideoAspectRatios();
        initVideoPlayers();
        initAnimations();
        initAnimationPauseButtons();
        initDownloadDropdown();
        initQRCodeSnippet();
        initTopicListSidebar();
        reserveTypewriterSpace();
        initTypewriter();
        Flare26.initDialogs();
        Flare26.setAsDefaultPage.onLoad();
    }

    window.cms.Flare26 = Flare26;
})();
