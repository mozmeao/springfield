/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

const fs = require('fs');
const path = require('path');

function readCss(file) {
    const p = path.resolve(__dirname, '..', 'media', 'css', 'cms', file);
    return fs.readFileSync(p, 'utf8');
}

module.exports = function (source, map) {
    // Inline any @import, anywhere:
    // - @import url('file.css') layer(name); -> @layer name { <contents> }
    // - @import url('file.css'); -> <contents>
    const importAnyRegex =
        /@import\s+(?:url\()?['"]?([^'"\)\s]+\.css)['"]?\)?(?:\s+layer\(\s*([^\)]+?)\s*\))?\s*;?/g;

    const self = this;

    // Recursively expand @imports depth-first, tracking the current call stack
    // to detect true circular dependencies (A imports B imports A) without
    // falsely flagging the same file being imported at multiple independent sites.
    function expand(content, stack) {
        return content.replace(importAnyRegex, (_, file, layerName) => {
            const absPath = path.resolve(
                __dirname,
                '..',
                'media',
                'css',
                'cms',
                file
            );
            if (stack.includes(absPath)) {
                throw new Error(
                    `[flare-import-anywhere-loader] Circular @import detected: ` +
                        `${[...stack, absPath].join(' -> ')}`
                );
            }
            self.addDependency(absPath);
            const fileContent = fs.readFileSync(absPath, 'utf8');
            const expanded = expand(fileContent, [...stack, absPath]);
            if (layerName) {
                return `@layer ${layerName} {${expanded}}`;
            }
            return expanded;
        });
    }

    const result = expand(source, []);
    this.callback(null, result, map);
};
