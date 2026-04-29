/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import DownloadAttribution from './download-attribution.es6';

DownloadAttribution.applyAttributionDataToLinks();

// We always want to refresh the essential data
// to avoid an outdated download experience
// If there's new essential data, update
// If there's no essential data, remove
DownloadAttribution.initEssential();
