The `image` component is a plain image in a `media` wrapper, with no responsive sources or lazy loading. Outside the pattern library it only appears in the Scroll To See More snippet preview.

CMS images don't use it: Image blocks render through the image variants template, with responsive sizes and optional dark-mode and mobile versions, and other image fields use `srcset_image` in their own templates. Use those paths for anything an editor uploads.
