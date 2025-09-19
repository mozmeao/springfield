from jinja2 import Environment


def custom_environment(**options):
    env = Environment(**options)

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

        # from pattern_library.loader_tags import template_new_context, visit_extends
        from pattern_library.loader_tags import template_new_context

        jinja_visit_Extends = JinjaCodeGenerator.visit_Extends
        JinjaTemplate.new_context = template_new_context
        # JinjaCodeGenerator.visit_Extends = visit_extends

    return env
