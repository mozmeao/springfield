The `conditional-display` component wraps content shown only to some visitors: by platform, Firefox or not, signed-in state, default-browser status, country, Firefox version, last session, AI controls, a UI Tour button, or a sample rate. Different conditions combine, and all of them must match; picking several platforms or countries matches any of them. Every block's **Show To** setting renders through it.

Content stays hidden until CSS or JS confirms a match, so keep a sensible show-to-all fallback. Many conditions depend on the real browser and can't be faked here.
