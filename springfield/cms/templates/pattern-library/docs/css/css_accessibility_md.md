# Accessibility

We create sites to welcome the widest possible audience, free of obstacles. Be mindful of the broad range of human abilities and disabilities, as well as the variety of devices, browsers, and networks people use to access our sites.

## WCAG

In general if you have a question about how something should look or act you can use the [WCAG AA](https://www.w3.org/WAI/WCAG2AA-Conformance) guidelines to answer it.

## Semantic HTML

Use semantic HTML to achieve what you want, avoid using aria-roles if you can achieve the same affect using plain HTML.

Label page regions.

Links go places. Buttons do things. Use the appropriate HTML as the base no matter how you style it.

## Keyboard navigation

Do not mess with the default focus ring.

Use `:focus-visible` if you are enhancing the focus state.

When tabbing through a webpage focus should move left to right and top to bottom.

Javascript should be written with mindful focus management. For example, after closing a modal the user's focus should be returned to the element that opened it.

## Touch screen

All users benefit from large hit areas. Mobile users require them. Aim for a minimum of 44px x 44px.

Do not disable browser zoom.

Form inputs should have a font size ≥ 16px

## Motion & Animation

Respect `prefers-reduced-motion`.

Provide controls for any motion (video or animation).

Do not autoplay videos. Autoplay may be acceptable if:

- the video has no sound
- the video displays controls

Never `transition: all`. Explicitly list only the properties you intend to animate.
