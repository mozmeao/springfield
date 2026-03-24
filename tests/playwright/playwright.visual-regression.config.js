/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { defineConfig } = require('@playwright/test');
const baseConfig = require('./playwright.config');

module.exports = defineConfig({
    ...baseConfig,
    fullyParallel: false,
    workers: 1,
    expect: {
        toHaveScreenshot: {
            threshold: 0.3,
            maxDiffPixelRatio: 0.02
        }
    },
    projects: [baseConfig.projects.find((p) => p.name === 'chromium')]
});
