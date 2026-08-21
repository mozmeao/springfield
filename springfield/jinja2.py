# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import contextvars

from includecontents.jinja2 import IncludeContentsExtension
from jinja2 import Environment
from wagtail.admin.jinja2tags import WagtailUserbarExtension

from springfield.cms.templatetags.cms_tags import richtext


class _ContextLocalRenderStack:
    """
    Data descriptor serving one ``_render_stack`` per thread or async task.

    django-includecontents 4.0.1 stores its render stack as a plain list on the
    extension instance, and Jinja2 builds one extension per Environment. Every
    request thread therefore pushes and pops frames on the same list, so a
    ``<content:...>`` block -- which is written to ``stack[-1]`` -- can land in a
    component another thread is rendering. The visible result is slots that come
    out empty or filled with another ``<include:...>`` tag's content.

    The ContextVar lives in the extension's ``__dict__`` rather than on this
    descriptor or the extension's ``__init__`` because Jinja renders components
    in an overlay environment, and ``Extension.bind`` shallow-copies the
    extension class for it. Sharing the var that way keeps nested components
    pushing onto the same stack, the same as when it was a shared list.
    """

    _VAR_ATTR = "_render_stack_var"

    def _var(self, extension):
        var = extension.__dict__.get(self._VAR_ATTR)
        if var is None:
            var = contextvars.ContextVar("includecontents_render_stack")
            extension.__dict__[self._VAR_ATTR] = var
        return var

    def __get__(self, extension, owner=None):
        if extension is None:
            return self
        var = self._var(extension)
        stack = var.get(None)
        if not stack:
            # Rebind whenever the stack is empty, i.e. at the start of every
            # render tree. An asyncio task inherits a copy of its parent's
            # context, so without this two tasks could mutate the same list.
            stack = []
            var.set(stack)
        return stack

    def __set__(self, extension, value):
        self._var(extension).set(list(value))


class ThreadSafeIncludeContentsExtension(IncludeContentsExtension):
    """
    ``IncludeContentsExtension`` with a render stack that is not shared between threads.

    FUTURE: drop this subclass when django-includecontents releases a new version which
            fixes django-includecontents#11.
    """

    _render_stack = _ContextLocalRenderStack()


def custom_environment(**options):
    extensions = [ThreadSafeIncludeContentsExtension, WagtailUserbarExtension]
    options["extensions"] = options.get("extensions", []) + extensions
    env = Environment(**options)
    env.filters["richtext"] = richtext

    from django.apps import apps

    if apps.is_installed("pattern_library"):
        # This is the recommended way to override jinja2 tags, but it causes
        # errors.
        # from pattern_library.monkey_utils import override_jinja_tags
        # override_jinja_tags()
        # This is the copy & pasted code of override_jinja_tags(), with lines
        # commented-out if they cause errors. TODO: find a more elegant way
        # to do this.
        global jinja_visit_Extends
        try:
            from jinja2.compiler import CodeGenerator as JinjaCodeGenerator
            from jinja2.environment import Template as JinjaTemplate
        except ModuleNotFoundError:
            ModuleNotFoundError("install jinja2 to override jinja tags")

        from pattern_library.loader_tags import template_new_context

        jinja_visit_Extends = JinjaCodeGenerator.visit_Extends
        JinjaTemplate.new_context = template_new_context
        # JinjaCodeGenerator.visit_Extends = visit_extends

    return env
