/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
 * Turns every django-pattern-library sample (a template plus the .yaml beside it)
 * into a Storybook story, with the YAML context as editable controls. Django does
 * the rendering, so `npm start` must be running for the stories to load.
 */

import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { mergeConfig } from 'vite';
import { parse } from 'yaml';

// `npm start` runs webpack-dev-server here: it serves /media/ and forwards the rest to Django.
const DJANGO_ORIGIN = 'http://localhost:8000';

const TEMPLATES_ROOT = path.resolve(
    import.meta.dirname,
    '../springfield/cms/templates'
);

// Django only renders samples inside the folders of PATTERN_LIBRARY["SECTIONS"] in settings/base.py.
const SAMPLE_FOLDERS = ['docs', 'base-styles', 'components/flare'];
const SAMPLE_FILE = /\/pattern-library\/.+\.yaml$/;

// Bundles that cms/base-pattern.html loads around each sample. Keep in sync with it.
// (flare_base is the legacy fallback, which base-flare.html only serves to old IE.)
const CSS_BUNDLES = [
    'flare',
    'pattern_library',
    'flare-referral-hub',
    'flare-blog'
];
const JS_BUNDLES = [
    'lib',
    'data',
    'firefox-cms-flare',
    'ui-tour-buttons',
    'flare-navigation',
    'flare-lang-switcher'
];

async function readSample(fileName) {
    const templateName = path
        .relative(TEMPLATES_ROOT, fileName)
        .replace(/\.yaml$/, '.html');
    const exportName = path
        .basename(templateName, '.html')
        .replace(/(?:^|[^a-z0-9]+)([a-z0-9])/gi, (_, character) =>
            character.toUpperCase()
        );
    const { name, context } = parse(await readFile(fileName, 'utf-8'));

    return {
        templateName,
        title: path.dirname(templateName).replace('pattern-library/', ''),
        exportName,
        name: name ?? exportName,
        context: context ?? {}
    };
}

// ponytail: experimental_indexers is an experimental Storybook API; if it breaks on
// upgrade, fall back to hand-written .stories.js files for the components that matter.
const sampleIndexer = {
    test: SAMPLE_FILE,
    createIndex: async (fileName) => {
        const { title, exportName, name } = await readSample(fileName);
        return [
            { type: 'story', importPath: fileName, exportName, title, name }
        ];
    }
};

// Storybook can only load JS, so this makes each sample's YAML importable as a CSF module.
const sampleStoriesPlugin = {
    name: 'pattern-library-sample-stories',
    enforce: 'pre',
    async load(id) {
        const fileName = id.split('?')[0];
        if (!SAMPLE_FILE.test(fileName)) {
            return null;
        }
        const { templateName, title, exportName, name, context } =
            await readSample(fileName);

        return `
            export default { title: ${JSON.stringify(title)} };
            export const ${exportName} = {
                name: ${JSON.stringify(name)},
                args: ${JSON.stringify(context)},
                parameters: { djangoTemplate: ${JSON.stringify(templateName)} }
            };
        `;
    }
};

export default {
    framework: '@storybook/html-vite',
    stories: SAMPLE_FOLDERS.map(
        (folder) =>
            `../springfield/cms/templates/pattern-library/${folder}/**/*.yaml`
    ),
    addons: ['@storybook/addon-a11y'],
    experimental_indexers: (indexers) => [...indexers, sampleIndexer],
    // site.js rewrites the "windows" and "no-js" classes that base-flare.html puts on <html>
    // (to the detected platform and "js"), so they have to be there before it runs.
    previewHead: (head) => `
        ${head}
        <script>document.documentElement.classList.add('windows', 'no-js');</script>
        ${CSS_BUNDLES.map((bundle) => `<link href="/media/css/${bundle}.css" rel="stylesheet">`).join('')}
        <script src="/media/js/site.js"></script>
    `,
    // These scripts must block parsing (no defer): they only wait for DOMContentLoaded, which
    // simulateLoading fires after each render, while the document is still "loading".
    previewBody: (body) => `
        ${body}
        ${JS_BUNDLES.map((bundle) => `<script src="/media/js/${bundle}.js"></script>`).join('')}
    `,
    viteFinal: (config) =>
        mergeConfig(config, {
            plugins: [sampleStoriesPlugin],
            server: {
                proxy: {
                    '/pattern-library': DJANGO_ORIGIN,
                    '/media': DJANGO_ORIGIN
                }
            }
        })
};
