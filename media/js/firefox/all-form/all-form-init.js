/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { init } from './all-form';

const island = document.getElementById('allFormData');
if (!island) throw new Error('Missing #allFormData data island');
init(JSON.parse(island.textContent));
