/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

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
        errorList.innerHTML = '';

        errors.forEach((error) => {
            const li = document.createElement('li');
            li.textContent = error;
            errorList.appendChild(li);
        });

        errorDiv.classList.remove('hidden');
    }
}

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
        document.getElementById('id_country').addEventListener('change', sync);
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

        const submitButton = document.getElementById('newsletter-submit');
        const originalText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.textContent = 'Subscribing...';

        fetch(form.action, {
            method: 'POST',
            body: formData
        })
            .then((response) => {
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    return response.json();
                } else {
                    if (response.status === 200) {
                        return { success: true };
                    } else {
                        return { success: false, errors: ['Server error'] };
                    }
                }
            })
            .then((data) => {
                if (data.success || data.status === 'ok') {
                    showNewsletterSuccess();

                    if (window.dataLayer) {
                        for (let i = 0; i < newsletters.length; ++i) {
                            window.dataLayer.push({
                                event: 'newsletter_subscribe',
                                newsletter_id: newsletters[i]
                            });
                        }
                    }
                } else {
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
                showNewsletterError(['An error occurred. Please try again.']);
            })
            .finally(() => {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            });
    });
}

export default function setupNewsletter() {
    initNewsletterForm();
    handleNewsletterSubmission();
}
