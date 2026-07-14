/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { defineConfig } = require('@playwright/test');
const visualRegressionConfig = require('./playwright.visual-regression.config');

module.exports = defineConfig({
    ...visualRegressionConfig,
    testDir: './compare-live',
    snapshotDir: './test-results/compare-live-snapshots',
    outputDir: './test-results/compare-live',
    grep: undefined,
    globalSetup: undefined
});
