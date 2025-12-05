# CSS Principles

- [Simple selectors](#simple-selectors)
- [Minimal nesting](#minimal-nesting)
- [Formatting](#formatting)
- [Units](#units)

## Simple selectors

Use the shortest, least specific selector required to do the job.

Favor classes over IDs. Using ID selectors can lead to specificity wars requiring ever more powerful selectors to override previous styling. A better option is an attribute selector like `[id='widget']` which selects the element by its ID but has the same specificity as a class. Everybody wins.

Avoid qualifying classes with type selectors. It slows down performance and makes classes less portable. E.g. `.widget` is better than `div.widget`.

## Minimal nesting

Don’t nest rules unless necessary for context and specificity. Don’t nest rules
just to group them together (use comments to label sections of the style sheet for grouping).

All the style declarations for the parent element should come before any nested rules.

Include a blank line before each nested rule to separate it from the rule or declaration above it.

```css
/* NO */
.widget-frame {
    float: right;
    .widgets {
        .widget-heading {
            background: #ccc;
            h3 {
                padding-bottom: 10px;
            }
            color: red;

        }
    }
    width: 30%;
}
```
```css
/* YES */
.widget-frame {
    float: right;
    width: 30%;
}

.widget-heading {
    background: #ccc;
    color: red;

    h3 {
        padding-bottom: 10px;
    }
}
```

## Formatting

These will mostly be enforced by the linter and you shouldn't have to think too hard about them.

* One selector per line.
* One declaration per line.
* Order declarations alphabetically (from A to Z).
* Use a soft indent of four spaces - don’t use tabs.
* Use one space between the selector and the first bracket.
* Use one space between property and value after `:`.
* Always add a semicolon after property value.
* Use single quotes.
* Do not specify units for a zero value.
* Omit the leading zero in decimal values, e.g. `.75em` not `0.75em`.
* Include a space after each comma in a comma-separated property list.
* Use lowercase and shorthand hex values, e.g. `#aaa`.
* Always use hex values unless you are declaring rgba.
* Separate each rule by a blank line.


```css
.selector1,
.selector2 {
    /* This is a comment */
    background: #333 url('img/icon.png') center no-repeat;
    color: #bada55;
    margin: 0 auto 0.75em;
}

.selector3,
.selector4 {
    background: rgba(255, 255, 255, 0.25);
    padding: 20px;
}
```

When possible, limit line lengths to 80 characters. It improves readability,
minimizes horizontal scrolling, makes it possible to view files side by side, and
produces more useful diffs with meaningful line numbers. There will be exceptions
such as long URLs or gradient syntax but most declarations should fit well within
80 characters even with indentation.

Long, comma-separated property values – such as multiple background images,
gradients, transforms, transitions, webfonts, or text and box shadows – can be
arranged across multiple lines (indented one level from their property).

```css
.selector {
    background-image:
        linear-gradient(#fff, #ccc),
        linear-gradient(#f3c, #4ec);
    box-shadow:
        1px 1px 1px #000,
        2px 2px 1px 1px #ccc inset;
    transition:
        border-color 500ms ease-in,
        opacity 100ms ease-in;
}
```

## Units

* Use pixels for fixed-width elements.
* Use percentages for fluid-width elements.
* Use rems for `font-size` because it respects user preferences.
* Use [unitless `line-height`](http://meyerweb.com/eric/thoughts/2006/02/08/unitless-line-heights/)
  in conjunction with `font-size`; it acts as a multiplier of font size. E.g.
  `line-height: 1.5`.
* Use milliseconds for timing, e.g. `500ms` not `.5s`.
