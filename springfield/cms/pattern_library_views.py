# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.http import Http404, HttpResponse
from django.utils.safestring import mark_safe

from pattern_library import get_base_template_names
from pattern_library.exceptions import TemplateIsNotPattern
from pattern_library.utils import (
    get_pattern_config,
    get_pattern_context,
    get_renderer,
    render_pattern,
)
from pattern_library.views import RenderPatternView as BaseRenderPatternView


class RenderPatternView(BaseRenderPatternView):
    """
    Extended RenderPatternView that passes pattern metadata (name)
    to the base template context.
    """

    def get(self, request, pattern_template_name=None):
        renderer = get_renderer()
        pattern_template_ancestors = renderer.get_template_ancestors(
            pattern_template_name,
            context=get_pattern_context(pattern_template_name),
        )
        pattern_is_fragment = set(pattern_template_ancestors).isdisjoint(set(get_base_template_names()))

        try:
            rendered_pattern = render_pattern(request, pattern_template_name)
        except TemplateIsNotPattern:
            raise Http404

        if pattern_is_fragment:
            context = self.get_context_data()
            context["pattern_library_rendered_pattern"] = mark_safe(rendered_pattern)

            # Add pattern config to context so name is available in base template
            pattern_config = get_pattern_config(pattern_template_name)
            context["pattern_config"] = pattern_config
            context["pattern_name"] = pattern_config.get("name", "")

            return self.render_to_response(context)

        return HttpResponse(rendered_pattern)
