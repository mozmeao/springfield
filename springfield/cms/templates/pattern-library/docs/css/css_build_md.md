# CSS Build Architecture

Flare uses a two-tiered CSS system: modern layered CSS for evergreen browsers, or legacy fallback CSS for older browsers.

Modern and legacy CSS are delivered via two separate bundles which are defined in `static-bundles.json`. See [Browser Support](../css/css_browser.html) for details on which browsers receive which bundle.

## `flare_base` Bundle (Legacy Fallback)

Provides a minimal, accessible, and branded experience with basic typography and single-column layout. This bundle includes `flare-base.css`, and also `flare-icon.css` and `flare-utilities.css`.

## `flare` Bundle (Modern CSS)

Uses CSS `@layer` for explicit cascade control with modern CSS features (custom properties, etc.)

### CSS Layers

The modern `flare` bundle uses seven CSS layers to control cascade order (lower layers can be overridden by higher layers):

#### 1. `base` Layer (`flare-base.css`)

Reset, font-face declarations, and minimal base styles. This is the same file used in the legacy bundle, ensuring a consistent baseline across all browsers.

#### 2. `theme` Layer (`flare-theme.css`)

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

#### 3. `defaults` Layer (`flare-defaults.css`)

Default styles for classless HTML elements using theme variables. Overrides constraints from the base layer (e.g., removes body width constraint, adds theme colors).

#### 4. `template` Layer (`flare-template.css`)

Page structure styles: header, footer, navigation, and content containers.

#### 5. `components` Layer

Components are modular CSS files for individual UI components. Each one is imported into the same components layer with `@import 'filename.css' layer(components)`.

Note: The icon component styles are also included in the legacy stylesheet because they are essential for accessibility.

#### 6. `utilities` Layer (`flare-utilities.css`)

Text alignment, font weights, visibility helpers that are also included in legacy bundle so utility classes can be used in legacy browsers as well, important for things like hidden classes.

#### 7. `overrides` Layer (`flare-overrides.css`)

Specific exceptions that can't be handled by other layers. Use sparingly.

## Custom Import Loader

The only pre-processing that needs to happen for Flare CSS is that `@import`s need to be inlined for performance and so nested imports (which are not supported by browsers) will work.

This is achieved with a simple webpack loader in `webpack/flare-import-anywhere-loader.js` that just inlines all `@import` statements.

This custom loader avoids unneeded third party dependencies like `postcss-import` which often don't support the technically invalid nested imports.

## Usage Patterns

Some common patterns that are useful in this CSS setup:

Define semantic CSS custom properties in `flare-theme.css` and use `@media` blocks there to override values for any context you can detect globally (dark mode, reduced motion, viewport size, etc.). Components then consume those variables without needing their own media queries.

```css
/* flare-theme.css */
:root {
  --fl-component-surface: var(--token-neutrals-ash);
  --fl-component-text: var(--token-neutrals-charcoal);
  --fl-component-padding: calc(var(--token-scale-16) * 1px);
}

@media (prefers-color-scheme: dark) {
  :root {
    --fl-component-surface: var(--token-neutrals-charcoal);
    --fl-component-text: var(--token-neutrals-white);
  }
}

@media (max-width: 768px) {
  :root {
    --fl-component-padding: calc(var(--token-scale-12) * 1px);
  }
}

/* component stylesheet */
.fl-component {
  background: var(--fl-component-surface);
  color: var(--fl-component-text);
  padding: var(--fl-component-padding);
}
```

Add units to unitless tokens using calc and multiplying by 1:

```css
padding: calc(var(--token-scale-16) * 1px);
```

### Breakpoint Variables

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

## Legacy Mode

To manually toggle legacy CSS mode in development (useful for previewing legacy styles without needing to run legacy browsers) you can set `FLARECSS_LEGACY_MODE=True` in the `.env` file, and only the legacy CSS will be served to all browsers.
