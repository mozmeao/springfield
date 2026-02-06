/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import VideoEngagement from '../base/datalayer-videoengagement.es6';

(function () {
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

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            initNewsletterForm();
            handleNewsletterSubmission();
            initNotificationClose();
            applyVideoAspectRatios();
            initVideoPlayers();
            initDownloadDropdown();
        });
    } else {
        initNewsletterForm();
        handleNewsletterSubmission();
        initNotificationClose();
        applyVideoAspectRatios();
        initVideoPlayers();
        initDownloadDropdown();
    }
})();
