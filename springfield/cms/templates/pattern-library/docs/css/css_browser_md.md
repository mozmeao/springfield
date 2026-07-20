# Browser Support

Firefox supports the following operating systems:

- Windows 10 and above
- macOS 10.15 and above
- Linux

Because of that we support the following browser versions:

- Safari 15.6
- Firefox ESR

And the following evergreen browsers:

- Firefox
- Chrome
- Edge
- Brave
- Opera

Next revision: March 2026, after ESR drops support for MacOS 10.15.

## Modern Experience

Despite our support requirements the technique we use to split the modern vs legacy experiences means
that the following browsers receive the full `flare` bundle with all layered CSS and modern features, providing the complete design system with all components:

- Chrome 99+
- Firefox 97+
- Safari 15.4+

## Legacy Experience

The legacy experience is a basic, accessible, branded single-column layout.

To manually toggle legacy CSS mode in development (useful for previewing legacy styles without needing to run legacy browsers) you can set `FLARECSS_LEGACY_MODE=True` in the `.env` file, and only the legacy CSS will be served to all browsers.

### Full bundle

These browsers receive the full `flare` bundle but don't support CSS `@layer` so all `@import` statements are invalid and ignored. A fallback block inside the `flare` bundle provides base styles. This results in the legacy CSS experience for browsers which load `flare` but don't support it.

- Firefox 96 and lower
- Chrome 98 and lower
- Safari 15.3 and lower

### Base bundle

These browsers receive only the `flare_base` bundle, served via `{{ css_bundle('flare_base', target_old_ie=True) }}`:

- IE8/IE9 get the `flare_base` legacy styles through conditional comments.
- IE10/11 get the `flare_base` legacy styles via a media query.


## Legacy Mode

To manually toggle legacy CSS mode in development (useful for previewing legacy styles without needing to run legacy browsers) you can set `FLARECSS_LEGACY_MODE=True` in the `.env` file, and only the legacy CSS will be served to all browsers.
