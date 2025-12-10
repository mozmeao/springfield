# Naming Conventions

- [Token vs Variable](#token-vs-variable)
- [Class Prefixes](#prefixes)
- [Sizes](#sizes)

## Tokens vs variables

Tokens are prefixed with `--token-` and never change.

Variables which change are prefixed with `--fl-theme`.

```css
:root {
    /* tokens */
    --token-color-black: 0, 0, 0; /* rgb(0, 0, 0) */

    /* variables */
    --fl-theme-color-text-primary: rgb(var(--token-color-black));
}

@media (prefers-color-scheme: dark) {
    :root {
        --fl-theme-color-text-primary: rgb(var(--token-color-white));
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
