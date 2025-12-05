# Base Template

Base templates use Jinja2 syntax for markup structure only, no CMS code. They:

- Accept parameters as variables
- Receive content slots via `{{ contents.slot_name }}`
- Optionally include child components via `<include:component-name>`

**Location**: `/springfield/cms/templates/components/{component-name}.html`

**Example** (`banner.html`):

```jinja2
<div class="fl-banner{% if media_position == 'after' %} fl-banner-reverse{% endif %}">
  <div class="fl-banner-body">
    {% if contents.body %}
      {{ contents.body }}
    {% endif %}
    {% if contents.actions %}
      {{ contents.actions }}
    {% endif %}
  </div>
  {% if media_src %}
    <div class="fl-banner-media">
      <include:media src="{{ media_src }}" />
    </div>
  {% endif %}
</div>
```
