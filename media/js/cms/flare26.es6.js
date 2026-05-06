/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import setupAnimations from './components/flare26-animations.es6';
import setupCarousels from './components/flare26-carousel.es6';
import setupCopyToClipboardButtons from './components/flare26-copy-to-clipboard.es6';
import setupDialogs, { initDialogs } from './components/flare26-dialogs.es6';
import setupDownloadDropdown from './components/flare26-download-dropdown.es6';
import setupFirefoxVersionConditionalDisplay from './components/flare26-firefox-version.es6';
import setupNewsletter from './components/flare26-newsletter.es6';
import setupNotificationClose from './components/flare26-notification-close.es6';
import setupQRCodeSnippet from './components/flare26-qr-code-snippet.es6';
import setupScrollingCardGrid from './components/flare26-scrolling-card-grid.es6';
import { setupSetAsDefault } from './components/flare26-set-as-default.es6';
import setupSlidingCarousels from './components/flare26-sliding-carousel.es6';
import setupTopicListSidebar from './components/flare26-topic-list-sidebar.es6';
import setupTypewriter, {
    typewriter
} from './components/flare26-typewriter.es6';
import setupVideo from './components/flare26-video.es6';

// Create namespace
if (typeof window.cms === 'undefined') {
    window.cms = {};
}

window.cms.Flare26 = { typewriter, initDialogs };

function setupComponents() {
    setupNewsletter();
    setupNotificationClose();
    setupVideo();
    setupAnimations();
    setupDownloadDropdown();
    setupQRCodeSnippet();
    setupTopicListSidebar();
    setupTypewriter();
    setupDialogs();
    setupCarousels();
    setupScrollingCardGrid();
    setupCopyToClipboardButtons();
    setupFirefoxVersionConditionalDisplay();
    setupSlidingCarousels();
    setupSetAsDefault();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupComponents);
} else {
    setupComponents();
}
