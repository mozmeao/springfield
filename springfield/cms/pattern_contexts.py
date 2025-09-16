from pattern_library import register_context_modifier


@register_context_modifier(template="cms/patterns/blocks/button.html")
def button_turn_keys_that_should_be_callable_into_callables(context, request):
    """Turn keys that should be callable into callable keys."""
    # Create a dictionary where the keys are the expected method names, and the
    # values are the expected callables. For example, if
    # context["value"]["turn_into_callable__center_class"] is "center", then
    # dict_of_method_values["center_class"] will be a callable that returns "center".
    dict_of_method_values = {key[len("turn_into_callable__") :]: lambda value=value: value for key, value in context["value"].items()}
    # Set the callables into the context.
    for key, value in dict_of_method_values.items():
        context["value"][key] = value
