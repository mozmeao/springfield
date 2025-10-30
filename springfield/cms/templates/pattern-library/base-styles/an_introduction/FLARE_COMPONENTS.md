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

See [CSS Architecture](#css-architecture) for more details.

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

## CSS Architecture

Flare uses a two-tiered CSS system: modern layered CSS for evergreen browsers, or legacy fallback CSS for older browsers.

Modern and legacy CSS are delivered via two separate bundles which are defined in `static-bundles.json`. See [Browser Support](#browser-support) for details on which browsers receive which bundle.

### `flare_base` Bundle (Legacy Fallback)

Provides a minimal, accessible, and branded experience with basic typography and single-column layout. This bundle includes `flare-base.css`, and also `flare-icon.css` and `flare-utilities.css`.

### `flare` Bundle (Modern CSS)

Uses CSS `@layer` for explicit cascade control with modern CSS features (custom properties, `light-dark()`, etc.)

#### CSS Layers

The modern `flare` bundle uses seven CSS layers to control cascade order (lower layers can be overridden by higher layers):

##### 1. `base` Layer (`flare-base.css`)

Reset, font-face declarations, and minimal base styles. This is the same file used in the legacy bundle, ensuring a consistent baseline across all browsers.

##### 2. `theme` Layer (`flare-theme.css`)

CSS custom properties (variables) only, no element styles. Includes things like:

- Color tokens from Figma design system
- Scale variables (spacing, sizing)
- Typography tokens (font families, weights)
- Grid and width constraints
- Transition variables

This file is partially generated using the Figma MCP tool to extract design tokens from Figma.

**Generating/Updating Tokens**

1. Open Figma file in Figma desktop app and select the frame that contains the tokens you want to update
2. Use an LLM with Figma MCP tool to call `mcp_Figma_get_variable_defs` to get all variables and update their values in the file
3. Manually review and adjust the results (this process is non-deterministic)

##### 3. `defaults` Layer (`flare-defaults.css`)

Default styles for classless HTML elements using theme variables. Overrides constraints from the base layer (e.g., removes body width constraint, adds theme colors).

##### 4. `template` Layer (`flare-template.css`)

Page structure styles: header, footer, navigation, and content containers.

##### 5. `components` Layer

Components are modular CSS files for individual UI components. Each one is imported into the same components later with `@import 'filename.css' layer(components)`.

Note: The icon component styles are also included in the legacy stylesheet because they are essential for accessibility.

##### 6. `utilities` Layer (`flare-utilities.css`)

Text alignment, font weights, visibility helpers that are also included in legacy bundle so utility classes can be used in legacy browsers as well, important for things like hidden classes.

##### 7. `overrides` Layer (`flare-overrides.css`)

Specific exceptions that can't be handled by other layers. Use sparingly.

### Browser Support

#### IE8-11

These browsers receive only the `flare_base` bundle, served via `{{ css_bundle('flare_base', target_old_ie=True) }}` which wraps the bundle in conditional comments for IE9 and lower, and uses a media query for IE10/11. They get a basic, accessible, branded single-column layout.

#### Safari 12.1-15.3

These browsers receive the `flare` bundle but don't support CSS `@layer`, so all `@import` statements with `layer()` are invalid and ignored. A fallback block inside `flare.css` provides base styles. This results in the legacy CSS experience.

#### Modern Browsers (Safari 15.6+, Chrome 109+, Firefox ESR 115+)

These browsers receive the full `flare` bundle with all layered CSS and modern features, providing the complete design system with all components.

### Custom Import Loader

The only pre-processing that needs to happen for Flare CSS is that `@import`s need to be inlined for performance and so nested imports (which are not supported by browsers) will work.

This is achieved with a simple webpack loader in `webpack/flare-import-anywhere-loader.js` that just inlines all `@import` statements.

This custom loader avoids unneeded third party dependencies like `postcss-import` which often don't support the technically invalid nested imports.

### Usage Patterns

Some common patterns that are useful in this CSS setup:

Use `light-dark` for dark mode support:

```css
background: light-dark(var(--neutrals-ash), var(--neutrals-charcoal));
```

Add units to unitless tokens using calc and multiplying by 1:

```css
padding: calc(var(--scale-16) * 1px);
```

#### Breakpoint Variables

Using CSS variables inside a media query declaration is invalid. This will NOT work: `@media (min-width: var(--mobile-width))`, but instead of defining media queries in every component, we can use media queries in `flare-theme.css` to toggle variable values in one place:

```css
:root {
  --layout-direction: column;
}

@media (min-width: 768px) {
  :root {
    --layout-direction: row;
  }
}
```

And then we can use that variable in other layers:

```css
.fl-banner {
  flex-direction: var(--layout-direction);
}
```

### Legacy Mode

To manually toggle legacy CSS mode in development (useful for previewing legacy styles without needing to run legacy browsers) you can set `FLARECSS_LEGACY_MODE=True` in the `.env` file, and only the legacy CSS will be served to all browsers.
