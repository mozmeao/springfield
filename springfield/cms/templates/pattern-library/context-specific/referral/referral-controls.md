The `referral-controls` component lets a referrer share their personal invite link: the link itself, a copy button, an email button and a QR code dialog. It renders nothing without an invite link, which only the Referral Hub page builds, from the referrer's key.

Editors add Referral Controls to a Showcase tab on the Referral Hub page and only set the labels and email text — the URL is never editable. In the email body, {invite link} marks where the link goes; without it the link is added at the end. Each share is reported to analytics.
