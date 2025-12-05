# Localization

We support languages that are longer, shorter, go the opposite direction, and/or use different character sets than English. All of these come with code considerations.


## Translation sources

Content which is not in the CMS is localized with Fluent.

[Fluent documentation](https://mozmeao.github.io/platform-docs/l10n/).

## RTL

Ensure support for RTL languages by using [CSS logical properties](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Logical_properties_and_values).


## Length

Plan for longer words and longer sentences.

## Non-latin characters

Languages which

`intl.css` `X-LocaleSpecific`

## Testing

If translated content has not yet been provided you can use a [pseudolocalization tool](https://addons.mozilla.org/en-US/firefox/addon/pseudolocalize/) to test the flexability of your styles.



- test with words that are longer
- test with languages that need more words
- test with RTL
- test with languages that our fonts don't support
