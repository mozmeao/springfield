The `heading` component is Flare's headline: a heading with an optional superheading above and subheading below, grouped in an `hgroup` when either is set. It renders nothing when all three texts are empty.

The Heading block nests in nearly every Flare block and takes its level from where it sits on the page (h2 by default), so editors never pick a level or size. It adds `fl-heading-display` when it's the page's `h1`, except in banners. **link** turns the text into a link.

**heading_size** takes a size class (`fl-heading-display`, `fl-heading-xl` … `fl-heading-xs`), which beats the element size. Leave it empty to size the heading by its element. See CSS conventions in Docs for when to use a size class.
