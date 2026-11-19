/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

// Crop every icon SVG's viewBox to the bounds of its rendered artwork.
// Usage: node crop.js <playwright-core dir> <icons dir> [--dry-run]
// Renders each SVG onto a canvas in Chromium and keeps the non-transparent
// pixels, so strokes, clip-paths, transforms and embedded images all count.

const fs = require('fs');
const path = require('path');

const [playwrightDir, iconsDir, ...flags] = process.argv.slice(2);
const { chromium } = require(path.resolve(playwrightDir));
const dryRun = flags.includes('--dry-run');
const CANVAS_SIZE = 2048;

function listSvgs(dir) {
    return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
        if (entry.name.startsWith('.')) return [];
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) return listSvgs(full);
        return entry.name.endsWith('.svg') ? [full] : [];
    });
}

function formatNumber(value) {
    return String(Number(value.toFixed(2)));
}

function rootTagBox(svgText) {
    const rootTag = svgText.match(/<svg\b[^>]*>/)[0];
    const viewBox = rootTag.match(/viewBox="([^"]+)"/);
    if (viewBox)
        return viewBox[1]
            .trim()
            .split(/[\s,]+/)
            .map(Number);
    return [
        0,
        0,
        parseFloat(rootTag.match(/width="([^"]+)"/)[1]),
        parseFloat(rootTag.match(/height="([^"]+)"/)[1])
    ];
}

function withBox(svgText, [x, y, width, height]) {
    return svgText.replace(/<svg\b[^>]*>/, (rootTag) => {
        const tag = rootTag.replace(/\s(width|height|viewBox)="[^"]*"/g, '');
        const attrs = ` width="${formatNumber(width)}" height="${formatNumber(height)}" viewBox="${[x, y, width, height].map(formatNumber).join(' ')}"`;
        return tag.replace(/^<svg/, '<svg' + attrs);
    });
}

async function measure(page, svgText, box) {
    const [, , boxWidth, boxHeight] = box;
    const scale = CANVAS_SIZE / Math.max(boxWidth, boxHeight);
    const sized = withBox(svgText, box).replace(/<svg\b[^>]*>/, (rootTag) =>
        rootTag
            .replace(/width="[^"]*"/, `width="${boxWidth * scale}"`)
            .replace(/height="[^"]*"/, `height="${boxHeight * scale}"`)
    );
    const pixels = await page.evaluate(
        async ({ text, canvasWidth, canvasHeight }) => {
            const image = new Image();
            image.src =
                'data:image/svg+xml;base64,' +
                btoa(unescape(encodeURIComponent(text)));
            await image.decode();
            const canvas = document.createElement('canvas');
            canvas.width = canvasWidth;
            canvas.height = canvasHeight;
            const context = canvas.getContext('2d');
            context.drawImage(image, 0, 0, canvasWidth, canvasHeight);
            const { data } = context.getImageData(
                0,
                0,
                canvasWidth,
                canvasHeight
            );
            let left = canvasWidth,
                top = canvasHeight,
                right = -1,
                bottom = -1;
            for (let row = 0; row < canvasHeight; row++) {
                for (let column = 0; column < canvasWidth; column++) {
                    if (data[(row * canvasWidth + column) * 4 + 3] > 0) {
                        if (column < left) left = column;
                        if (column > right) right = column;
                        if (row < top) top = row;
                        if (row > bottom) bottom = row;
                    }
                }
            }
            return right < 0 ? null : { left, top, right, bottom };
        },
        {
            text: sized,
            canvasWidth: Math.ceil(boxWidth * scale),
            canvasHeight: Math.ceil(boxHeight * scale)
        }
    );
    if (!pixels) return null;
    const [boxX, boxY] = box;
    const tolerance = 2 / scale;
    const snap = (value, edge) => {
        if (Math.abs(value - edge) <= tolerance) return edge;
        const onQuarterGrid = Math.round(value * 4) / 4;
        return Math.abs(value - onQuarterGrid) <= tolerance
            ? onQuarterGrid
            : value;
    };
    const x0 = snap(Math.floor((boxX + pixels.left / scale) * 100) / 100, boxX);
    const y0 = snap(Math.floor((boxY + pixels.top / scale) * 100) / 100, boxY);
    const x1 = snap(
        Math.ceil((boxX + (pixels.right + 1) / scale) * 100) / 100,
        boxX + boxWidth
    );
    const y1 = snap(
        Math.ceil((boxY + (pixels.bottom + 1) / scale) * 100) / 100,
        boxY + boxHeight
    );
    return [x0, y0, x1 - x0, y1 - y0];
}

async function selfCheck(page) {
    const svg =
        '<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><rect x="4" y="6" width="10" height="8" fill="black"/></svg>';
    const cropped = await measure(page, svg, rootTagBox(svg));
    const expected = [4, 6, 10, 8];
    cropped.forEach((value, index) => {
        if (Math.abs(value - expected[index]) > 0.03)
            throw new Error(
                `self-check failed: got ${cropped}, expected ${expected}`
            );
    });
}

(async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage();
    await selfCheck(page);
    const skipped = [];
    let changed = 0;
    for (const file of listSvgs(iconsDir)) {
        const svgText = fs.readFileSync(file, 'utf8');
        const cropped = await measure(page, svgText, rootTagBox(svgText)).catch(
            (error) => {
                skipped.push(`${file}: ${error.message}`);
                return undefined;
            }
        );
        if (cropped === undefined) continue;
        if (cropped === null) {
            skipped.push(`${file}: nothing rendered`);
            continue;
        }
        const original = rootTagBox(svgText);
        if (
            cropped.every(
                (value, index) => Math.abs(value - original[index]) <= 0.02
            )
        )
            continue;
        const output = withBox(svgText, cropped);
        if (output !== svgText) {
            changed++;
            if (dryRun)
                process.stdout.write(
                    `${path.relative(iconsDir, file)}: ${original.join(' ')} -> ${cropped.map(formatNumber).join(' ')}\n`
                );
            else fs.writeFileSync(file, output);
        }
    }
    await browser.close();
    process.stdout.write(
        `${dryRun ? 'would change' : 'changed'} ${changed} files\n`
    );
    if (skipped.length)
        process.stdout.write('skipped:\n  ' + skipped.join('\n  ') + '\n');
})();
