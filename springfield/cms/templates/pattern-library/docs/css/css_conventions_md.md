# Naming Conventions

- [Token vs Variable](#token-vs-variable)
- [Class Prefixes](#prefixes)
- [Sizes](#sizes)
- [Headings](#headings)

## Tokens vs variables

Tokens are prefixed with `--token-` and never change.

Variables which change are prefixed with `--fl-theme`.

```css
:root {
    /* tokens */
    --token-color-black: #000000;

    /* variables */
    --fl-theme-color-text-primary: var(--token-color-black);
}

@media (prefers-color-scheme: dark) {
    :root {
        --fl-theme-color-text-primary: var(--token-color-white);
    }
}

```

## Class Prefixes

For ease of integration and to avoid conflicts with other sites, frameworks,
and libraries, most classes in Flare are prefixed with our global namespace
`.fl-`.

After that, we follow a [SMACSS](https://smacss.com/book/categorizing)-based
naming convention with a set of prefixes to put rules into a few different
categories:

<table>
  <thead>
    <tr>
      <th>Prefix</th>
      <th>Purpose</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>c-</code></td>
      <td>Component names (e.g. <code>.fl-c-showcase</code>, <code>.fl-c-button</code>)</td>
    </tr>
    <tr>
      <td><code>t-</code></td>
      <td>Theme styles for alternative component styles (e.g. <code>.fl-t-reverse</code>)</td>
    </tr>
    <tr>
      <td><code>u-</code></td>
      <td>Utility styles with broad scope (e.g. <code>.fl-u-text-center</code>, <code>.fl-u-heading-md</code>)</td>
    </tr>
    <tr>
      <td><code>qa-</code></td>
      <td>Selector hooks for tests (no CSS styling should be applied)</td>
    </tr>
    <tr>
      <td><code>js-</code></td>
      <td>JavaScript behavior hooks (e.g. <code>.fl-js-sticky</code>, <code>.fl-js-toggle</code>)</td>
    </tr>
    <tr>
      <td><code>a-</code></td>
      <td>CSS animation names (e.g. <code>fl-a-fade-in</code>, <code>fl-a-slide-from-right</code>)</td>
    </tr>
  </tbody>
</table>


```css
/* Good - strikes the right balance between telling you
 * what it will look like without dictating the content */
.fl-c-button-solid {...}
.fl-c-split {...}
.fl-c-media-reverse {...}

/* Bad - related to a value which may change */
.fl-c-button-blue {...}

/* Bad - related contents which may change */
.fl-c-product-features {...}

/* Bad - too specific and too literal */
.fl-c-image-left {...}
```

## Sizes

We use a “T-shirt” convention when we need to describe sizes, e.g. “lg” for large and “sm” for small. In this t-shirt scale system, the default should be the medium “md” size and you can scale up or down from there.

```scss
.fl-t-size-2xl { ... }
.fl-t-size-xl { ... }
.fl-t-size-lg { ... }
.fl-t-size-md { ... }
.fl-t-size-sm { ... }
.fl-t-size-xs { ... }
.fl-t-size-2xs { ... }
```

Note that when we need multiple Xes we opt for a numeral. This avoids confusion or ambuguity in the event we need to reference some extreme size. “5xl” is more readable than “xxxxxl”.

## Headings

Headings use six sizes, named in t-shirt order: `display`, `xl`, `lg`, `md`, `sm` and `xs`. Each heading element shares a size with a class, and both follow the page's type scale. The Typography page in Base Styles lists every value.

| Size | Element | Class |
|---|---|---|
| display | — | `.fl-heading-display` |
| xl | `h1` | `.fl-heading-xl` |
| lg | `h2` | `.fl-heading-lg` |
| md | `h3` | `.fl-heading-md` |
| sm | `h4`, `h5`, `h6` | `.fl-heading-sm` |
| xs | — | `.fl-heading-xs` |

**Page headings** (the page title, section headings and rich-text headings) take no size class, so each is sized by its element. The page's first heading adds `.fl-heading-display`. The Heading block does this automatically, except in banners, and hand-built page titles add it themselves. In an intro with media beside the heading, Display steps down to the `h1` size from 900px, where the media moves beside it. The element rules use `:where()`, so they have zero specificity and any class beats them.

**Section headings keep a readable line length.** A heading or heading group directly inside `.fl-section-container` stops at `--token-width-desktop-content-lg` (934px), and centred ones stay centred. The rest of the section keeps the full container width.

**Component headings** (cards, forms, dialogs, tabs and so on) pass a size class at the size the component always renders at, plus `.fl-scale-regular`, so they keep their Regular size on Compact pages. There are no classes named after heading levels.

**Type scales.** Regular is the default. `.fl-scale-compact` on `<body>` switches a page to Compact, and either scale class on any element switches that element and everything inside it. Because custom properties inherit, an inner scale class wins. Page models choose their scale with `default_type_scale` (Free Form pages have a "Type scale" field), and Django-routed templates fill `{% block type_scale %}`.

**Variables** come in two layers:

| Layer | Example | Changes with |
|---|---|---|
| Tokens | `--token-heading-font-size-plus-1` | nothing |
| Heading sizes | `--fl-theme-heading-font-size-lg` | breakpoint and scale |

Heading size variables are named `--fl-theme-heading-<property>-<size>`: `font-size`, `font-stretch`, `font-weight`, `letter-spacing` (`--fl-theme-heading-tracking-<size>`) and `line-height`. Every size shares `--fl-theme-heading-font-family` and `--fl-theme-heading-margin`. The condensed sizes (display, xl and lg) take their width, weight and tracking from `--fl-theme-heading-font-stretch-condensed`, `--fl-theme-heading-font-weight-condensed` and `--fl-theme-heading-tracking-condensed`; the others use `normal`, `--fl-theme-heading-font-weight` and `--fl-theme-heading-tracking`. Themes change the face by overriding those shared variables. Enterprise, for example, makes the condensed sizes normal width, weight 400 and -0.02em tracking, and keeps md and smaller at the default weight and tracking. Width is set with `font-stretch`. Don't use `font-variation-settings` on headings, because it overrides `font-weight` and `font-stretch`.

**Component CSS doesn't set heading font properties.** Size a component's heading with a size class in its template. Component CSS can still set margin, alignment and colour. If a component needs a size that isn't one of the six, raise it with design rather than adding a local size.

**Non-heading elements** that look like headings (a legend, a pagination label) may use the heading variables, but only as a complete set for one size: `font-family`, `font-weight`, `font-stretch`, `font-size`, `line-height` and `letter-spacing`. Never use a heading size variable on its own. Add `.fl-scale-regular` to the element in its template if it shouldn't follow the page's scale.
