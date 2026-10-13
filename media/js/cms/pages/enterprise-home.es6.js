/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
  WARNING! This file is referenced in the CMS directly.
  Before altering, ensure you have an up-to-date database and check for pages that have
  extra_js="enterprise-home" to avoid breaking the page functionality.
*/

// Decorative animated bubbles, styled and animated in css/cms/themes/enterprise-home.css.
const BUBBLES_MARKUP = `
<div class="fl-ent-bubbles" aria-hidden="true">
  <div class="fl-ent-haze"></div>
  <div class="fl-ent-bubble fl-ent-bubble-right">
    <div class="fl-ent-fade"><div class="fl-ent-fill"></div></div>
  </div>
  <div class="fl-ent-bubble fl-ent-bubble-left">
    <div class="fl-ent-fade"><div class="fl-ent-fill"></div></div>
    <div class="fl-ent-lens-wrap"><div class="fl-ent-lens"></div></div>
  </div>
</div>`;

const setupEnterpriseHome = () => {
    if (!document.querySelector('.enterprise-home')) return;

    const heroContainer = document.querySelector('.fl-split-page-upper');
    const footerContainer = document.querySelector('.fl-main');

    if (!heroContainer) return;

    [heroContainer, footerContainer].forEach((container) => {
        if (!container) return;
        container.insertAdjacentHTML('beforeend', BUBBLES_MARKUP);
    });
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupEnterpriseHome);
} else {
    setupEnterpriseHome();
}
