/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import EmblaCarousel from 'embla-carousel';

const SLIDE_DURATION_MS = 4000;
const FADE_DURATION_MS = 800;

const clamp = (min, val, max) => Math.min(max, Math.max(min, val));

function prefersReducedMotion() {
    return (
        window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
}

function setActiveControl(controls, activeIndex) {
    controls.forEach((control, idx) => {
        if (idx === activeIndex) {
            control.classList.add('active');
        } else {
            control.classList.remove('active');
            control.style.removeProperty('--carousel-progress');
        }
    });
}

function createFadeOverlay(viewportEl, fromSlideEl, toSlideEl) {
    if (
        !viewportEl ||
        !fromSlideEl ||
        !toSlideEl ||
        fromSlideEl === toSlideEl
    ) {
        return;
    }

    const existing = viewportEl.querySelector('.fl-carousel-fade-overlay');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.className = 'fl-carousel-fade-overlay';

    const fromLayer = document.createElement('div');
    fromLayer.className = 'fl-carousel-fade-layer fl-carousel-fade-layer-from';

    const toLayer = document.createElement('div');
    toLayer.className = 'fl-carousel-fade-layer fl-carousel-fade-layer-to';

    const fromContent = fromSlideEl.querySelector('.fl-carousel-image');
    const toContent = toSlideEl.querySelector('.fl-carousel-image');

    if (fromContent) fromLayer.appendChild(fromContent.cloneNode(true));
    if (toContent) toLayer.appendChild(toContent.cloneNode(true));

    overlay.appendChild(fromLayer);
    overlay.appendChild(toLayer);
    viewportEl.appendChild(overlay);

    // Force a reflow so the transition triggers reliably.

    overlay.offsetWidth;
    overlay.classList.add('is-active');

    window.setTimeout(() => {
        overlay.remove();
    }, FADE_DURATION_MS + 50);
}

function initFlare26Carousel(rootEl) {
    const viewportEl = rootEl.querySelector('.fl-carousel-viewport');
    const controls = Array.from(
        rootEl.querySelectorAll('.fl-carousel-control-item')
    );
    const slides = Array.from(rootEl.querySelectorAll('.fl-carousel-slide'));

    if (!viewportEl || controls.length === 0 || slides.length === 0) {
        return;
    }

    const emblaApi = EmblaCarousel(viewportEl, {
        loop: true,
        draggable: false
    });

    let startTime = performance.now();
    let rafId = 0;
    let pausedElapsed = 0;
    let isPaused = false;

    const getSelected = () => emblaApi.selectedScrollSnap();

    const resetTimer = () => {
        startTime = performance.now();
        const active = controls[getSelected()];
        if (active) active.style.setProperty('--carousel-progress', '0');
    };

    const updateProgress = (elapsedMs) => {
        const active = controls[getSelected()];
        if (!active) return;
        const progress = clamp(0, (elapsedMs / SLIDE_DURATION_MS) * 100, 100);
        active.style.setProperty('--carousel-progress', progress.toFixed(2));
    };

    const scrollToIndex = (toIndex) => {
        const fromIndex = getSelected();
        if (toIndex === fromIndex) {
            resetTimer();
            return;
        }

        // Fade based on slide content, then jump the underlying Embla position.
        createFadeOverlay(viewportEl, slides[fromIndex], slides[toIndex]);
        emblaApi.scrollTo(toIndex, true);
        resetTimer();
    };

    const advance = () => {
        const count = emblaApi.scrollSnapList().length;
        if (count <= 1) return;
        const next = (getSelected() + 1) % count;
        scrollToIndex(next);
    };

    const onSelect = () => {
        setActiveControl(controls, getSelected());
        resetTimer();
    };

    emblaApi.on('select', onSelect).on('reInit', onSelect);
    onSelect();

    controls.forEach((controlEl, idx) => {
        controlEl.addEventListener(
            'click',
            (e) => {
                e.preventDefault();
                scrollToIndex(idx);
            },
            false
        );
    });

    const pause = () => {
        if (isPaused) return;
        isPaused = true;
        pausedElapsed = performance.now() - startTime;
    };

    const resume = () => {
        if (!isPaused) return;
        isPaused = false;
        startTime = performance.now() - pausedElapsed;
    };

    document.addEventListener(
        'visibilitychange',
        () => {
            if (document.hidden) pause();
            else resume();
        },
        false
    );

    const tick = (now) => {
        if (!prefersReducedMotion() && !isPaused) {
            const elapsed = now - startTime;
            updateProgress(elapsed);
            if (elapsed >= SLIDE_DURATION_MS) {
                // Ensure the ring completes before we advance.
                updateProgress(SLIDE_DURATION_MS);
                advance();
            }
        }
        rafId = window.requestAnimationFrame(tick);
    };

    // Start the loop (even in reduced motion so selection changes still keep controls in sync; progress/autoplay are disabled in tick).
    rafId = window.requestAnimationFrame(tick);

    // Ensure we don't leak timers if this init is re-run.
    // (Embla doesn't expose a destroy hook we can reliably watch here,
    // but this at least cancels the rAF on window unload.)
    window.addEventListener(
        'unload',
        () => {
            if (rafId) window.cancelAnimationFrame(rafId);
        },
        false
    );
}

function initFlare26Carousels() {
    const roots = document.querySelectorAll('.fl-carousel');
    roots.forEach((rootEl) => initFlare26Carousel(rootEl));
}

function initFooterCtaEmailValidation() {
    const forms = document.querySelectorAll('.fl-footer-form');
    if (!forms.length) {
        return;
    }

    const isValidEmail = (email) => {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    };

    forms.forEach((form) => {
        const emailInput = form.querySelector('input[type="email"]');
        const submitButton = form.querySelector('.fl-footer-form-submit');
        const errorSummary = form.querySelector('.fl-footer-form-errors');
        const fieldError = form.querySelector('.fl-footer-form-field-error');

        if (!emailInput || !submitButton) {
            return;
        }

        const setErrorState = (isError) => {
            if (isError) {
                emailInput.setAttribute('aria-invalid', 'true');
                submitButton.setAttribute('disabled', 'disabled');
                if (errorSummary) {
                    errorSummary.classList.remove('hidden');
                }
                if (fieldError) {
                    fieldError.classList.remove('hidden');
                }
                return;
            }

            emailInput.removeAttribute('aria-invalid');
            submitButton.removeAttribute('disabled');
            if (errorSummary) {
                errorSummary.classList.add('hidden');
            }
            if (fieldError) {
                fieldError.classList.add('hidden');
            }
        };

        emailInput.addEventListener('blur', () => {
            const value = (emailInput.value || '').trim();
            if (value && !isValidEmail(value)) {
                setErrorState(true);
                return;
            }

            setErrorState(false);
        });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    initFlare26Carousels();
    initFooterCtaEmailValidation();
});
