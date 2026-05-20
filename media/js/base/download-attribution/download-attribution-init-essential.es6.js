/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import DownloadAttribution from './download-attribution.es6';

// Refresh the essential data to avoid an outdated download experience
// NO essential data?
// - If analytics data exists, update attribution to remove essential but keep analytics
// - If no other data, remove attribution entirely
// NEW essential data?
// - update attribution to use latest essential data
DownloadAttribution.initEssential();
