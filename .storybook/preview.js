/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
 * Every story is a django-pattern-library sample: Django renders its template with
 * the story's args as context. The wrapper matches the one in cms/base-pattern.html.
 */

import { renderPattern, simulateLoading } from 'storybook-django';

const RENDER_PATTERN_ENDPOINT = '/pattern-library/api/v1/render-pattern';

export default {
    parameters: {
        layout: 'fullscreen'
    },
    render: (args, { parameters }) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'pl-wrapper';

        renderPattern(RENDER_PATTERN_ENDPOINT, parameters.djangoTemplate, args)
            .then((response) => response.text())
            .then((html) => simulateLoading(wrapper, html));

        return wrapper;
    }
};
