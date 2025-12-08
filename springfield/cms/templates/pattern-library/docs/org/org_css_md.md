# Component CSS

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
  gap: calc(var(--token-scale-16) * 1px);
  background: var(--fl-theme-surface-page);
}

@media (min-width: 768px) {
  .fl-banner {
    flex-direction: row;
  }
}

.fl-banner-body,
.fl-banner-reverse .fl-banner-media {
  order: 2;
}

.fl-banner-media,
.fl-banner-reverse .fl-banner-body {
  order: 1;
}
```

Import in `flare.css`:

```css
@import 'flare-banner.css' layer(components);
```

See [CSS Architecture](../css/css_build.html) for more details.
