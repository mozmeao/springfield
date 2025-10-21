# Flare CMS Components

This document describes the file structure and patterns for creating Wagtail CMS components in the Springfield project.

## Component Anatomy

Every Flare component in Springfield consists of 4 parts:

- [Base HTML Template](#base-html-template)
- [Component Styles](#component-styles)
- [Wagtail Block](#wagtail-block)
- [Pattern Library Documentation](#pattern-library-documentation)

### Base HTML Template

**Path**: `springfield/springfield/cms/templates/components/{component-name}.html`

**Purpose**: Jinja2 template containing the component's HTML markup

**Characteristics**:
- Accepts template parameters as variables
- Can receive content for slots via `{{ contents.slot_name }}`
- Contains only markup structure, no CMS logic

**Example** (Simple Component):
```jinja2
<a role="button" class="fl-button {{ theme_class }}" href="{{ link }}">
  {% if icon_name and icon_position == "left" %}
    <include:icon icon_name="{{ icon_name }}" />
  {% endif %}
  {{ label }}
  {% if icon_name and icon_position == "right" %}
    <include:icon icon_name="{{ icon_name }}" />
  {% endif %}
</a>
```

**Example** (Composite Component):
```jinja2
<div class="fl-banner">
  <div class="fl-banner-layout">
    {% if contents.media %}
      <div class="fl-banner-media">
        {{ contents.media }}
      </div>
    {% endif %}
    <div class="fl-banner-content">
      {{ contents.heading }}
      {% if contents.actions %}
        <div class="fl-banner-actions">
          {{ contents.actions }}
        </div>
      {% endif %}
    </div>
  </div>
</div>
```

### Component Styles

**Path**: `springfield/media/css/cms/flare-{component-name}.css`

**Purpose**: Pure CSS file with styles for the component and all its variations

**Characteristics**:
- Class names are prefixed with `fl-{component-name}-`
- Uses CSS custom properties from `flare-theme.css` to reference design tokens and variables
- Uses `calc(var(--token) * 1px)` pattern for unitless design tokens

**Example**:
```css
.fl-button {
    display: inline-block;
    padding: calc(var(--scale-16) * 1px) calc(var(--scale-32) * 1px);
    font-family: var(--font-family-body);
    background: light-dark(var(--neutrals-ash), var(--neutrals-charcoal));
    color: light-dark(var(--neutrals-charcoal), var(--neutrals-ash));
}
.fl-button-icon {
    fill: light-dark(var(--neutrals-charcoal), var(--neutrals-ash));
}
```

### Wagtail Block

**Path**: `springfield/springfield/cms/templates/cms/blocks/{component-name}.html`

**Purpose**: Adapter that bridges Wagtail CMS data to the base component

**Characteristics**:
- Uses `<include:{component-name}>` to render base component template(s)
- Maps CMS block field values (`value.*`) to component parameters
- Uses `<content:slot-name>` tags to **send** content into the base component's slots
- Inside `<content>` blocks, uses `{% include_block %}` to render Wagtail StreamField/StructBlock data

**Example** (Simple Component):
```jinja2
<include:button
  theme_class="{{ value.theme_class() }}"
  label="{{ value.label }}"
  link="{{ value.link }}"
  external="{{ value.settings.external }}"
  icon_name="{{ value.settings.icon }}"
  icon_position="{{ value.settings.icon_position }}"
/>
```

**Example** (Composite Component):
```jinja2
<include:banner
  theme="{{ value.settings.theme }}"
  media_after="{{ value.settings.media_after }}">
  <content:heading>
    {# Use include_block to render Wagtail block data #}
    {% set heading_level = 'h' ~ block_level if block_level else 'h2' %}
    <include:heading
      level="{{ heading_level }}"
      heading_text="{{ value.headline|richtext|remove_p_tag }}"
    />
  </content:heading>
  <content:actions>
    {# Loop through Wagtail blocks and render each #}
    {% for button in value.buttons %}
      {% include_block button %}
    {% endfor %}
  </content:actions>
  {% if value.image %}
    <content:media>
      {# Mix Wagtail template tags with component includes #}
      <include:image url="{{ image(value.image, 'width-800').url }}" alt="{{ value.image.alt }}" />
    </content:media>
  {% endif %}
</include:banner>
```

### Pattern Library Documentation

The [Django Pattern Library](https://github.com/torchbox/django-pattern-library) is used to preview and test components similar to Storybook. You can view Flare components in the Pattern Library at http://localhost:8000/pattern-library/

#### Organization

The Flare Components are organized into sections in the Pattern Library UI:

1. Base Styles - Examples of styles for things like typography and theme variables that are inherited by all components
2. Components - Examples of components and their variations rendered with data
3. Pages - Examples of full page layouts combining several components

#### Adding Examples

To add examples to these sections, you can add a Jinja2 html template with some markup that includes the components you want to demo, and a yaml file with the same name that contains example values to render into the component.
