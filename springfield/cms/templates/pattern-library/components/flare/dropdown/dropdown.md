The `dropdown` component is a button that opens a panel below it, usually a list of links. Clicking outside or pressing Escape closes it, and Escape returns focus to the button.

There's no block of its own. The Enterprise Download block uses one per platform for its list of builds, and the navigation uses it for the Firefox for mobile QR code. The panel is absolutely positioned, so it covers the content below instead of pushing it down; don't put it in a container that clips overflow.
