/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { attributionRefactorEnabled } from '../../../base/consent/utils.es6';
import MarketingOptOut from './marketing-opt-out.es6.js';
import MarketingOptOutV2 from './marketing-opt-out-v2.es6.js';

if (attributionRefactorEnabled()) {
    MarketingOptOutV2.init();
} else {
    MarketingOptOut.init();
}
