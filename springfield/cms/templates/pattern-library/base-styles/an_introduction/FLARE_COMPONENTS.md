# Flare Components

File structure and patterns for creating Flare components in Springfield's Wagtail CMS.

## Component Anatomy

Every Flare component has 4 parts:

1. [Base Template](#1-base-template) - Component markup and structure
2. [Component CSS](#2-component-css) - Styles and variations
3. [Wagtail Block](#3-wagtail-block) - CMS data bridge
4. [Pattern Library](#4-pattern-library) - Documentation and examples

### 1. Base Template

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

### 2. Component CSS

Pure CSS only (no preprocessors). Import into [`flare.css`](/springfield/media/css/cms/flare.css) using the `components` layer.

**Location**: `/media/css/cms/flare-{component-name}.css`

**Conventions**:
- Prefix classes with `fl-{component-name}-`
- Reference design tokens from [`flare-theme.css`](/springfield/media/css/cms/flare-theme.css)
- Use `calc(var(--token) * 1px)` for unitless values

**Example** (`flare-banner.css`):

```css
.fl-banner {
  display: flex;
  flex-direction: column;
  gap: calc(var(--scale-16) * 1px);
  background: light-dark(var(--neutrals-ash), var(--neutrals-charcoal));
}

@media (min-width: 768px) {
  .fl-banner {
    flex-direction: row;
  }
}

.fl-banner-body, .fl-banner-reverse .fl-banner-media {
  order: 2;
}

.fl-banner-media, .fl-banner-reverse .fl-banner-body {
  order: 1;
}
```

Import in `flare.css`:
```css
@import 'flare-banner.css' layer(components);
```

### 3. Wagtail Block

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

### 4. Pattern Library

The Django Pattern Library is used to preview and test components (similar to Storybook).

**View it**: http://localhost:8000/pattern-library/

#### Pattern Library Organization

Flare components are organized into three sections:

1. **Base Styles** - Typography, theme variables, and inherited styles
2. **Components** - Component examples and variations
3. **Pages** - Full page layouts combining components

#### Adding Examples

- Create matching `.html` and `.yaml` files with the same name in `/springfield/cms/templates/pattern-library/{section}/**/{example_name}.{html|yaml}`
- Use `<include>` and `<content>` to map YAML data to components
- Loop through parameter options to show multiple variants
- See [button_variants.html](/springfield/springfield/cms/templates/pattern-library/components/button/button_variants.html) for a good example

Learn more: [Pattern Library - Defining Template Context](https://torchbox.github.io/django-pattern-library/guides/defining-template-context/)

> **Note**: Springfield uses [the Lincoln Loop fork of Django Pattern Library](https://github.com/lincolnloop/django-pattern-library).
