
# Wagtail Block

Wagtail blocks bridge CMS data to components. They focus on CMS logic, not markup. They:

- Map Wagtail `value.*` fields to component parameters
- Use `<include:{component-name}>` to render base components
- Send content to component slots via `<content:slot-name>` tags
- Use `{% include_block %}` to render Wagtail StreamField/StructBlock data

> **Note**: `{% include_block %}` is **only** used in Wagtail block templates, never in base templates or pattern library templates.

**Location**: `/springfield/cms/templates/cms/blocks/**/{component-name}.html`

See [django-includecontents docs](https://smileychris.github.io/django-includecontents/) for `<include>` and `<content>` syntax.

**Example** (`banner.html`):

```jinja2
<include:banner
  media_url="{{ value.media_url }}"
  media_position="{{ value.media_position }}"
>
  {% if value.body_text %}
    <content:body>
      {{ value.body_text|richtext|remove_p_tag }}
    </content:body>
  {% endif %}
  {% if value.actions %}
    <content:actions>
      {% for action in value.actions %}
        {% include_block action %}
      {% endfor %}
    </content:actions>
  {% endif %}
</include:banner>
```
