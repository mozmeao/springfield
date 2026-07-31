/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import {
    buildHelpText,
    renderConditionHelp,
    initConditionHelp
} from '../../../../../media/js/cms/routing/condition-help.es6.js';

const PAYLOAD = {
    platform: {
        valueType: 'enum',
        hint: 'Enter one of these values:',
        operators: [{ value: 'is', label: 'is' }],
        enumValues: [
            { value: 'windows', label: 'Windows' },
            { value: 'osx', label: 'macOS' }
        ]
    },
    firefox_version: {
        valueType: 'version',
        hint: 'Compared as a version. Available operators:',
        operators: [
            { value: 'gte', label: 'is at least' },
            { value: 'lt', label: 'is less than' }
        ],
        enumValues: []
    }
};

function makeConditionDOM(signalValue) {
    const container = document.createElement('div');
    const select = document.createElement('select');
    select.setAttribute('name', 'routing_rules-0-conditions-0-signal');
    Object.keys(PAYLOAD).forEach(function (name) {
        const option = document.createElement('option');
        option.value = name;
        select.appendChild(option);
    });
    select.value = signalValue;
    const fieldWrap = document.createElement('div');
    const input = document.createElement('input');
    input.setAttribute('name', 'routing_rules-0-conditions-0-expected_value');
    fieldWrap.appendChild(input);
    container.appendChild(select);
    container.appendChild(fieldWrap);
    return { container: container, select: select, fieldWrap: fieldWrap };
}

describe('cms/routing/condition-help.es6.js', function () {
    describe('buildHelpText', function () {
        it('renders the enumerated set for an enum signal', function () {
            const text = buildHelpText(PAYLOAD.platform);
            expect(text).toContain('Windows (windows)');
            expect(text).toContain('macOS (osx)');
            expect(text).toContain('Enter one of these values:');
        });

        it('renders the hint and operator meanings for a version signal', function () {
            const text = buildHelpText(PAYLOAD.firefox_version);
            expect(text).toContain('Compared as a version');
            expect(text).toContain('is at least');
            expect(text).toContain('is less than');
        });

        it('is empty for an unknown signal', function () {
            expect(buildHelpText(undefined)).toEqual('');
        });
    });

    describe('renderConditionHelp', function () {
        it('inserts enum help beneath the expected-value field', function () {
            const dom = makeConditionDOM('platform');
            renderConditionHelp(dom.select, PAYLOAD, dom.container);
            const help = dom.fieldWrap.querySelector('.routing-condition-help');
            expect(help).not.toBeNull();
            expect(help.textContent).toContain('Windows (windows)');
        });

        it('updates the help when the signal changes', function () {
            const dom = makeConditionDOM('platform');
            renderConditionHelp(dom.select, PAYLOAD, dom.container);
            dom.select.value = 'firefox_version';
            renderConditionHelp(dom.select, PAYLOAD, dom.container);
            const help = dom.fieldWrap.querySelector('.routing-condition-help');
            expect(help.textContent).toContain('is at least');
            expect(help.textContent).not.toContain('Windows');
        });
    });

    describe('initConditionHelp', function () {
        it('wires a change handler that refreshes the help', function () {
            const dom = makeConditionDOM('platform');
            initConditionHelp({ payload: PAYLOAD, root: dom.container });
            expect(
                dom.fieldWrap.querySelector('.routing-condition-help')
                    .textContent
            ).toContain('Windows');

            dom.select.value = 'firefox_version';
            dom.select.dispatchEvent(new Event('change'));
            expect(
                dom.fieldWrap.querySelector('.routing-condition-help')
                    .textContent
            ).toContain('is at least');
        });
    });
});
