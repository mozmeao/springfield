/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

const fs = require('fs');
const path = require('path');

function readCss(file) {
    const p = path.resolve(__dirname, 'css/cms', file);
    return fs.readFileSync(p, 'utf8');
}

module.exports = function (source, map) {
    let result = source;

    // Inline any @import, anywhere:
    // - @import url('file.css') layer(name); -> @layer name { <contents> }
    // - @import url('file.css'); -> <contents>
    const importAnyRegex =
        /@import\s+(?:url\()?['"]?([^'"\)\s]+\.css)['"]?\)?(?:\s+layer\(\s*([^\)]+?)\s*\))?\s*;?/g;

    result = result.replace(importAnyRegex, (_, file, layerName) => {
        const content = readCss(file);
        if (layerName) {
            return `@layer ${layerName} {${content}}`;
        }
        return content;
    });

    this.callback(null, result, map);
};
