The `dialog` component is a native modal with a heading, body text, optional buttons and a close button. Any `fl-dialog-trigger` button whose `data-target-id` matches the dialog's id opens it; clicking outside or pressing Escape closes it.

There's no block of its own: the Set as Default button, the referral QR code and the help dialogs on the /firefox/all/ download pages use it. Give it a **label**, or point **aria_labelledby** at its heading, so it has an accessible name.
