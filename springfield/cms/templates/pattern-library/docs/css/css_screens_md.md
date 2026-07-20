# Screen sizes

## Breakpoints

Our breakpoint approach has been inspired by [The 100% correct way to do CSS
breakpoints](https://www.freecodecamp.org/news/the-100-correct-way-to-do-css-breakpoints-88d6a5ba1862/).

Here are our breakpoints, followed by a device type in parentheses. The device type is
only for intuitive reference, but not a guarantee since there is a wide range of devices with each
viewport size and users may resize their browsers to different sizes.

```css
--viewport-sm-up (min-width: 600px); /* large phones */
--viewport-md-up (min-width: 900px); /* tablets in portrait */
--viewport-lg-up (min-width: 1200px); /* tablets in landscape & laptops */
```


For testing purposes we can consider these our target display sizes: `360px`, `768px`, `1024px`, `1280px`, `1366px`, `1440px`, `1536px`, and `1920px`. They are some of the most common screen sizes to visit our site and (unsurprisingly) correspond to some of the most common ones in the world according to [statcounter](https://gs.statcounter.com/screen-resolution-stats#monthly-202410-202511-bar).


## Mobile first

Code the mobile display first and then layer on improvements for larger screens. So, media queries should almost always target min-width. This saves the lower-powered mobile devices from doing extra processing.

Start with base styles (no media query) for mobile first design, then add styles for larger viewports using --viewport-*-up media queries.


```css
.fl-c-layout {
    display: grid;
    gap: var(--theme-gap);
    grid-template-columns: 1fr;
}

@media (--viewport-sm-up) {
    .fl-c-layout {
        grid-template-columns: repeat(2, 1fr);
    }
}

```

## Variables

A lot of screen size changes will be handled automatically by choosing the appropriate theme variable.

Typography, spacing, and sizing should all have theme variables for this use.

```css
:root {
    /* small is 24px at all screen sizes */
    --fl-theme-border-radius-sm: 24px;
    /* large will size up at each breakpoint */
    --fl-theme-border-radius-lg: 48px;
}

@media (min-width: 600px) {
    :root {
        /* large will size up at each breakpoint */
        --fl-theme-border-radius-lg: 80px;
    }
}

@media (min-width: 1200px) {
    :root {
        /* large will size up at each breakpoint */
        --fl-theme-border-radius-lg: 128px;
    }
}

.fl-c-card {
    border-radius: var(--fl-theme-border-radius-sm);
}

.fl-c-bubble {
    border-radius: var(--fl-theme-border-radius-lg);
}
```
